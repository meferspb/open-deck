"""Тесты сборщика Android APK: настройки, поиск инструментов, запуск сборки."""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from msfs_gateway import android_build as ab


class SettingsTest(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(ab.AndroidBuildSettings().validate(), [])

    def test_dict_roundtrip_uses_camel_case(self):
        raw = {
            "appName": "MSFS Panel",
            "applicationId": "com.example.panel",
            "versionName": "1.2.3",
            "versionCode": 12,
            "defaultHost": "192.168.1.5",
            "defaultPort": 9000,
        }
        settings = ab.AndroidBuildSettings.from_dict(raw)
        self.assertEqual(settings.app_name, "MSFS Panel")
        back = settings.to_dict()
        for key, value in raw.items():
            self.assertEqual(back[key], value)

    def test_rejects_bad_application_id(self):
        settings = ab.AndroidBuildSettings(application_id="not a package")
        self.assertTrue(any("applicationId" in error for error in settings.validate()))

    def test_rejects_bad_port_and_version(self):
        settings = ab.AndroidBuildSettings(default_port=70000, version_name="v1")
        errors = settings.validate()
        self.assertTrue(any("defaultPort" in error for error in errors))
        self.assertTrue(any("versionName" in error for error in errors))

    def test_rejects_absolute_output_dir(self):
        settings = ab.AndroidBuildSettings(output_dir="C:/temp")
        self.assertTrue(any("outputDir" in error for error in settings.validate()))

    def test_rejects_drive_relative_output_dir(self):
        settings = ab.AndroidBuildSettings(output_dir="C:temp")
        self.assertTrue(any("outputDir" in error for error in settings.validate()))

    def test_bad_types_return_errors_instead_of_crashing(self):
        for settings in (
            ab.AndroidBuildSettings(app_name=123),  # type: ignore[arg-type]
            ab.AndroidBuildSettings(version_code="abc"),  # type: ignore[arg-type]
            ab.AndroidBuildSettings(output_dir=123),  # type: ignore[arg-type]
        ):
            self.assertTrue(settings.validate())

    def test_rejects_quotes_in_app_name(self):
        settings = ab.AndroidBuildSettings(app_name='Panel "X"')
        self.assertTrue(any("appName" in error for error in settings.validate()))

    def test_rejects_extra_args_not_list(self):
        settings = ab.AndroidBuildSettings(extra_gradle_args="--foo")  # type: ignore[arg-type]
        self.assertTrue(any("extraGradleArgs" in error for error in settings.validate()))

    def test_rejects_unsafe_extra_args(self):
        settings = ab.AndroidBuildSettings(extra_gradle_args=["--init-script=evil.gradle"])
        self.assertTrue(any("недопустимый" in error for error in settings.validate()))
        safe = ab.AndroidBuildSettings(extra_gradle_args=["--offline", "-Pfoo=bar"])
        self.assertEqual(safe.validate(), [])

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "android-build.json"
            settings = ab.AndroidBuildSettings(app_name="Panel X", default_port=8761)
            ab.save_settings(settings, path)
            loaded = ab.load_settings(path)
            self.assertEqual(loaded.app_name, "Panel X")
            self.assertEqual(loaded.default_port, 8761)
            # Настройки пишутся в camelCase-формате.
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("appName", raw)

    def test_load_missing_file_gives_defaults(self):
        loaded = ab.load_settings(Path(tempfile.gettempdir()) / "definitely-missing-android.json")
        self.assertEqual(loaded.application_id, ab.AndroidBuildSettings().application_id)

    def test_load_broken_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{ not json", encoding="utf-8")
            with self.assertRaises(ab.AndroidBuildError):
                ab.load_settings(path)


def make_project(root: Path) -> Path:
    project = root / "android"
    (project / "app").mkdir(parents=True)
    (project / "app" / "build.gradle.kts").write_text("// test project", encoding="utf-8")
    return project


def make_toolchain(root: Path) -> Path:
    jdk = root / "jdk"
    (jdk / "bin").mkdir(parents=True)
    (jdk / "bin" / "java.exe").write_text("", encoding="utf-8")
    sdk = root / "sdk"
    (sdk / "platforms").mkdir(parents=True)
    gradle = root / "gradle-bin"
    gradle.write_text("", encoding="utf-8")
    return jdk, sdk, gradle


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = make_project(self.root)
        self.jdk, self.sdk, self.gradle = make_toolchain(self.root)
        self.settings = ab.AndroidBuildSettings(
            jdk_path=str(self.jdk),
            sdk_path=str(self.sdk),
            gradle_path=str(self.gradle),
            version_name="0.3.1",
            app_name="Тестовая панель",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_copies_apk_and_passes_properties(self):
        seen = {}

        def runner(args, cwd, env, timeout):
            seen["args"] = args
            seen["cwd"] = cwd
            seen["env"] = env
            apk = cwd / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
            apk.parent.mkdir(parents=True)
            apk.write_bytes(b"fake apk")
            return 0, ["BUILD SUCCESSFUL"]

        result = ab.build_apk(
            self.settings,
            project_dir=self.project,
            output_root=self.root,
            runner=runner,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.apk.name, "RudPanel-Android-0.3.1.apk")
        self.assertEqual(result.apk.read_bytes(), b"fake apk")
        self.assertEqual(seen["cwd"], self.project)
        self.assertIn("-PappName=Тестовая панель", seen["args"])
        self.assertIn("-PdefaultPort=8760", seen["args"])
        self.assertEqual(seen["env"]["JAVA_HOME"], str(self.jdk))
        self.assertTrue((self.project / "local.properties").is_file())

    def test_failed_gradle_raises_with_log_tail(self):
        def runner(args, cwd, env, timeout):
            return 1, ["error: something broke"]

        with self.assertRaises(ab.AndroidBuildError) as ctx:
            ab.build_apk(
                self.settings,
                project_dir=self.project,
                output_root=self.root,
                runner=runner,
            )
        self.assertIn("something broke", str(ctx.exception))

    def test_missing_project_raises(self):
        with self.assertRaises(ab.AndroidBuildError):
            ab.build_apk(
                self.settings,
                project_dir=self.root / "nope",
                output_root=self.root,
                runner=lambda *a, **k: (0, []),
            )

    def test_invalid_settings_rejected_before_build(self):
        settings = ab.AndroidBuildSettings(application_id="bad id")
        with self.assertRaises(ab.AndroidBuildError):
            ab.build_apk(settings, project_dir=self.project, output_root=self.root)


class ToolchainTest(unittest.TestCase):
    def test_custom_paths_are_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            jdk, sdk, gradle = make_toolchain(Path(tmp))
            settings = ab.AndroidBuildSettings(
                jdk_path=str(jdk), sdk_path=str(sdk), gradle_path=str(gradle)
            )
            chain = ab.resolve_toolchain(settings)
            self.assertEqual(chain.jdk, jdk)
            self.assertEqual(chain.gradle, gradle)
            status = ab.toolchain_status(settings)
            self.assertTrue(status["ok"])

    def test_status_reports_missing_tools(self):
        settings = ab.AndroidBuildSettings(
            jdk_path="C:/no-such-jdk", sdk_path="C:/no-such-sdk", gradle_path="C:/no-such-gradle"
        )
        original = ab._glob_toolchain
        ab._glob_toolchain = lambda pattern: []
        try:
            status = ab.toolchain_status(settings)
        finally:
            ab._glob_toolchain = original
        self.assertFalse(status["ok"])
        self.assertIn("JDK", status["error"])


class BuildManagerTest(unittest.TestCase):
    def test_success_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / "settings.json"
            ab.save_settings(ab.AndroidBuildSettings(), settings_path)
            apk = root / "Panel.apk"
            apk.write_bytes(b"apk")

            manager = ab.BuildManager(
                settings_path,
                builder=lambda settings, **kwargs: ab.BuildResult(
                    ok=True, apk=apk, log=["ok"], duration_sec=0.1
                ),
            )
            manager.start()
            status = manager.wait(5.0)
            self.assertEqual(status["state"], "success")
            self.assertEqual(status["apk"], str(apk))
            self.assertFalse(status["running"])

    def test_failure_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            ab.save_settings(ab.AndroidBuildSettings(), settings_path)

            def boom(settings, **kwargs):
                raise ab.AndroidBuildError("нет Gradle")

            manager = ab.BuildManager(settings_path, builder=boom)
            manager.start()
            status = manager.wait(5.0)
            self.assertEqual(status["state"], "failed")
            self.assertIn("Gradle", status["error"])

    def test_second_start_rejected_while_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            ab.save_settings(ab.AndroidBuildSettings(), settings_path)
            release = threading.Event()

            def slow(settings, **kwargs):
                release.wait(2.0)
                return ab.BuildResult(ok=True, apk=None, log=[], duration_sec=0.1)

            manager = ab.BuildManager(settings_path, builder=slow)
            manager.start()
            with self.assertRaises(ab.AndroidBuildError):
                manager.start()
            release.set()
            manager.wait(5.0)
            self.assertEqual(manager.status()["state"], "success")


class RunnerTimeoutTest(unittest.TestCase):
    def test_hung_process_is_killed_by_watchdog(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ab.AndroidBuildError) as ctx:
            ab._default_runner(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=Path(tmp),
                env=dict(os.environ),
                timeout=0.4,
            )
        self.assertIn("таймаут", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
