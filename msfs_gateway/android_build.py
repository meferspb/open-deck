"""Сборка Android APK из дистрибутива (с настройками).

Зачем: на хосте с MSFS удобно тут же собрать APK под свой шлюз — с именем
приложения, package id, версией и адресом хоста по умолчанию. Настройки
лежат в `config/android-build.json`, сборка запускается из веб-страницы
`/android.html` или командой `OpenDeck.exe --build-apk`.

Нужны только инструменты сборки (JDK 17, Android SDK, Gradle) — исходники
Android уже входят в дистрибутив. Если инструментов нет, страница честно
скажет, чего не хватает, и предложит готовый APK из `android/dist`.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from glob import glob as _glob
from pathlib import Path
from typing import Any

from .settings import APP_ROOT

logger = logging.getLogger("msfs_gateway.android")

DEFAULT_SETTINGS_PATH = APP_ROOT / "config" / "android-build.json"

APP_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")
VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$")
HOST_RE = re.compile(r"^[A-Za-z0-9._-]*$")
#: Дополнительные аргументы Gradle ограничены безопасным allowlist:
#: произвольный `--init-script` или `-I` — это выполнение кода.
GRADLE_ARG_RE = re.compile(
    r"^(-P[A-Za-z0-9_.-]+=[^\r\n]{0,200}"
    r"|--(?:offline|stacktrace|info|debug|warning-mode=(?:all|fail|summary)))$"
)

#: Ключи JSON (camelCase) → поля dataclass.
_FIELDS = {
    "appName": "app_name",
    "applicationId": "application_id",
    "versionName": "version_name",
    "versionCode": "version_code",
    "defaultHost": "default_host",
    "defaultPort": "default_port",
    "outputDir": "output_dir",
    "jdkPath": "jdk_path",
    "sdkPath": "sdk_path",
    "gradlePath": "gradle_path",
    "timeoutSec": "timeout_sec",
    "extraGradleArgs": "extra_gradle_args",
}


class AndroidBuildError(RuntimeError):
    """Сборка невозможна: настройки или инструменты."""


@dataclass
class AndroidBuildSettings:
    """Настройки сборки APK (имя, id, версия, пути)."""

    app_name: str = "Open Deck for MSFS"
    application_id: str = "com.opendeck.msfs"
    version_name: str = "0.1.0"
    version_code: int = 1
    default_host: str = ""
    default_port: int = 8760
    output_dir: str = "dist"
    jdk_path: str = ""
    sdk_path: str = ""
    gradle_path: str = ""
    timeout_sec: int = 900
    extra_gradle_args: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> AndroidBuildSettings:
        """Создаёт настройки из JSON-словаря."""
        values = {}
        for key, target in _FIELDS.items():
            if key in data:
                values[target] = data[key]
        return cls(**values)

    def to_dict(self) -> dict:
        """Сериализует настройки в JSON-словарь."""
        raw = asdict(self)
        return {key: raw[target] for key, target in _FIELDS.items()}

    def validate(self) -> list[str]:
        """Проверяет настройки и возвращает список ошибок."""
        errors: list[str] = []
        name = self.app_name.strip() if isinstance(self.app_name, str) else ""
        if not 1 <= len(name) <= 48:
            errors.append("appName: 1–48 символов")
        elif any(ord(char) < 32 or ord(char) == 127 for char in name):
            errors.append("appName: управляющие символы недопустимы")
        elif any(char in name for char in '&<>"'):
            errors.append('appName: символы & < > " недопустимы в manifest')
        application_id = self.application_id if isinstance(self.application_id, str) else ""
        if not APP_ID_RE.match(application_id):
            errors.append("applicationId: ожидается вида com.example.panel")
        version_name = self.version_name if isinstance(self.version_name, str) else ""
        if not VERSION_RE.match(version_name):
            errors.append("versionName: ожидается 1.2.3")

        def as_int(value: Any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        version_code = as_int(self.version_code)
        if version_code is None or not 1 <= version_code <= 2_100_000_000:
            errors.append("versionCode: целое 1..2100000000")
        default_port = as_int(self.default_port)
        if default_port is None or not 1 <= default_port <= 65535:
            errors.append("defaultPort: 1..65535")
        default_host = self.default_host if isinstance(self.default_host, str) else None
        if default_host is None:
            errors.append("defaultHost: строка")
        elif default_host and not HOST_RE.match(default_host):
            errors.append("defaultHost: только буквы, цифры, точка, дефис, подчёркивание")
        timeout_sec = as_int(self.timeout_sec)
        if timeout_sec is None or not 1 <= timeout_sec <= 3600:
            errors.append("timeoutSec: 60..3600")
        if not isinstance(self.extra_gradle_args, list) or any(
            not isinstance(item, str) for item in self.extra_gradle_args
        ):
            errors.append("extraGradleArgs: список строк")
        else:
            for item in self.extra_gradle_args:
                if not GRADLE_ARG_RE.match(item):
                    errors.append(
                        f"extraGradleArgs: недопустимый аргумент {item!r} "
                        "(разрешены -P… и --offline/--stacktrace/--info/--debug)"
                    )
        if not isinstance(self.output_dir, str):
            errors.append("outputDir: строка")
        else:
            output = Path(self.output_dir or "dist")
            # На Windows Path("C:foo") не абсолютный, но drive-relative:
            # (APP_ROOT / output) ушёл бы на другой диск.
            if output.is_absolute() or output.drive or output.anchor or ".." in output.parts:
                errors.append("outputDir: относительный путь внутри дистрибутива")
        return errors


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> AndroidBuildSettings:
    """Читает config/android-build.json."""
    if not path.is_file():
        return AndroidBuildSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AndroidBuildError(f"Не читается {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AndroidBuildError(f"{path}: ожидался JSON-объект")
    settings = AndroidBuildSettings.from_dict(raw)
    errors = settings.validate()
    if errors:
        raise AndroidBuildError("; ".join(errors))
    return settings


def save_settings(settings: AndroidBuildSettings, path: Path = DEFAULT_SETTINGS_PATH) -> None:
    """Сохраняет настройки сборки."""
    errors = settings.validate()
    if errors:
        raise AndroidBuildError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings.to_dict(), ensure_ascii=False, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")


# ---------------------------------------------------------------------
# Инструменты
# ---------------------------------------------------------------------
@dataclass
class Toolchain:
    """Найденные JDK, Android SDK и Gradle."""

    jdk: Path
    sdk: Path
    gradle: Path


def _first_existing(candidates: Iterable[Path], check: Callable[[Path], bool]) -> Path | None:
    for candidate in candidates:
        try:
            expanded = Path(os.path.expandvars(str(candidate)))
        except (OSError, ValueError):
            continue
        if check(expanded):
            return expanded
    return None


def _is_jdk(path: Path) -> bool:
    return (path / "bin" / ("java.exe" if os.name == "nt" else "java")).is_file()


def _is_sdk(path: Path) -> bool:
    return path.is_dir() and ((path / "platform-tools").is_dir() or (path / "platforms").is_dir())


def _is_gradle(path: Path) -> bool:
    return path.is_file()


def _glob_toolchain(pattern: str) -> list[Path]:
    try:
        return [Path(item) for item in sorted(_glob(pattern))]
    except (OSError, ValueError):
        return []


def resolve_toolchain(settings: AndroidBuildSettings) -> Toolchain:
    """Ищет JDK/SDK/Gradle: настройки → переменные окружения → типовые пути."""
    jdk_candidates: list[Path] = []
    if settings.jdk_path:
        jdk_candidates.append(Path(settings.jdk_path))
    for env_name in ("JAVA_HOME", "JDK_HOME"):
        value = os.environ.get(env_name)
        if value:
            jdk_candidates.append(Path(value))
    jdk_candidates += [Path(p) for p in _glob_toolchain("C:/Program Files/Java/jdk*")]
    jdk = _first_existing(jdk_candidates, _is_jdk)

    sdk_candidates: list[Path] = []
    if settings.sdk_path:
        sdk_candidates.append(Path(settings.sdk_path))
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(env_name)
        if value:
            sdk_candidates.append(Path(value))
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        sdk_candidates.append(Path(local_appdata) / "Android" / "Sdk")
    sdk = _first_existing(sdk_candidates, _is_sdk)

    gradle_candidates: list[Path] = []
    if settings.gradle_path:
        gradle_candidates.append(Path(settings.gradle_path))
    env_gradle = os.environ.get("OPEN_DECK_GRADLE") or os.environ.get("GRADLE_HOME")
    if env_gradle:
        pointer = Path(env_gradle)
        gradle_candidates.append(pointer / "bin" / "gradle.bat" if pointer.is_dir() else pointer)
    found = shutil.which("gradle")
    if found:
        gradle_candidates.append(Path(found))
    gradle_candidates += [Path(p) for p in _glob_toolchain("C:/Gradle/*/bin/gradle.bat")]
    gradle = _first_existing(gradle_candidates, _is_gradle)

    missing = []
    if jdk is None:
        missing.append("JDK 17 (jdkPath или JAVA_HOME)")
    if sdk is None:
        missing.append("Android SDK (sdkPath или ANDROID_HOME)")
    if gradle is None:
        missing.append("Gradle 8.x (gradlePath или gradle в PATH)")
    if missing:
        raise AndroidBuildError(
            "Не найдены инструменты сборки: "
            + ", ".join(missing)
            + ". Укажите пути на странице /android.html или установите инструменты."
        )
    assert jdk is not None and sdk is not None and gradle is not None
    return Toolchain(jdk=jdk, sdk=sdk, gradle=gradle)


def toolchain_status(settings: AndroidBuildSettings) -> dict:
    """Статус инструментов для страницы сборки."""
    try:
        chain = resolve_toolchain(settings)
    except AndroidBuildError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "jdk": str(chain.jdk),
        "sdk": str(chain.sdk),
        "gradle": str(chain.gradle),
    }


# ---------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------
@dataclass
class BuildResult:
    """Результат сборки APK."""

    ok: bool
    apk: Path | None
    log: list[str]
    duration_sec: float


LogSink = Callable[[str], None]


def _default_runner(
    args: list[str], cwd: Path, env: dict[str, str], timeout: float
) -> tuple[int, list[str]]:
    process = subprocess.Popen(
        args,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    lines: list[str] = []
    timed_out = threading.Event()

    def kill_on_timeout() -> None:
        timed_out.set()
        with contextlib.suppress(OSError):
            process.kill()

    # Сторож срабатывает, даже если Gradle завис и ничего не печатает:
    # проверка «после каждой строки» этого не ловит.
    watchdog = threading.Timer(max(1.0, timeout), kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()
    assert process.stdout is not None
    try:
        for line in process.stdout:
            lines.append(line.rstrip("\n"))
    finally:
        watchdog.cancel()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=30)

    if timed_out.is_set():
        raise AndroidBuildError(f"Сборка превысила таймаут ({timeout:g} с)")
    return process.returncode, lines


def _writable_dir(path: Path) -> bool:
    """Проверяет, можно ли писать в каталог (создаст его при необходимости)."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".write-test-{uuid.uuid4().hex}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def build_apk(
    settings: AndroidBuildSettings,
    *,
    project_dir: Path | None = None,
    output_root: Path | None = None,
    runner: Callable[..., tuple[int, list[str]]] = _default_runner,
    on_log: LogSink | None = None,
) -> BuildResult:
    """Собирает debug-APK через Gradle."""
    started = time.monotonic()
    errors = settings.validate()
    if errors:
        raise AndroidBuildError("; ".join(errors))

    project = project_dir or (APP_ROOT / "android")
    if not (project / "app" / "build.gradle.kts").is_file():
        raise AndroidBuildError(f"Не найден Android-проект: {project}")

    chain = resolve_toolchain(settings)
    (project / "local.properties").write_text(f"sdk.dir={chain.sdk.as_posix()}\n", encoding="utf-8")

    args = [
        str(chain.gradle),
        "--no-daemon",
        "--console=plain",
        "assembleDebug",
        f"-PappName={settings.app_name}",
        f"-PappId={settings.application_id}",
        f"-PappVersionName={settings.version_name}",
        f"-PappVersionCode={settings.version_code}",
        f"-PdefaultHost={settings.default_host}",
        f"-PdefaultPort={settings.default_port}",
        *settings.extra_gradle_args,
    ]
    env = dict(os.environ)
    env["JAVA_HOME"] = str(chain.jdk)
    env["ANDROID_HOME"] = str(chain.sdk)
    env["ANDROID_SDK_ROOT"] = str(chain.sdk)
    env["PATH"] = str(chain.jdk / "bin") + os.pathsep + env.get("PATH", "")

    def sink(line: str) -> None:
        if on_log is not None:
            on_log(line)

    # Gradle хранит кэш в ~/.gradle, а Kotlin пишет во временный каталог.
    # Если они недоступны для записи (политики, песочницы) — уводим в
    # каталог дистрибутива: сборка продолжит работать.
    root = output_root or APP_ROOT
    if not env.get("GRADLE_USER_HOME") and not _writable_dir(Path.home() / ".gradle"):
        fallback = root / ".gradle-home"
        if _writable_dir(fallback):
            env["GRADLE_USER_HOME"] = str(fallback)
            sink(f"Кэш Gradle: {fallback} (профиль недоступен для записи)")

    temp_root = Path(env.get("TEMP") or env.get("TMP") or "")
    if not env.get("OPEN_DECK_ANDROID_KEEP_TMP") and not _writable_dir(temp_root):
        tmp_dir = root / ".tmp"
        if _writable_dir(tmp_dir):
            env["TMP"] = str(tmp_dir)
            env["TEMP"] = str(tmp_dir)

    # Debug-keystore Android по умолчанию лежит в ~/.android — при запрете
    # записи в профиль уводим и его в каталог дистрибутива.
    android_home = Path(env.get("ANDROID_USER_HOME") or (Path.home() / ".android"))
    if not env.get("ANDROID_USER_HOME") and not _writable_dir(android_home):
        fallback_user = root / ".android-home"
        if _writable_dir(fallback_user):
            env["ANDROID_USER_HOME"] = str(fallback_user)
            sink(f"Android user home: {fallback_user}")

    log: list[str] = []
    try:
        code, output = runner(args, cwd=project, env=env, timeout=settings.timeout_sec)
    except AndroidBuildError:
        raise
    except Exception as exc:
        raise AndroidBuildError(f"Не удалось запустить Gradle: {exc}") from exc
    log.extend(output)
    for line in output:
        sink(line)

    apk = project / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if code != 0 or not apk.is_file():
        raise AndroidBuildError(
            f"Gradle завершился с кодом {code}. Последние строки:\n" + "\n".join(output[-25:])
        )

    output_dir = (output_root or APP_ROOT) / settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"OpenDeck-Android-{settings.version_name}.apk"
    shutil.copy2(apk, target)
    sink(f"APK: {target}")

    return BuildResult(ok=True, apk=target, log=log, duration_sec=time.monotonic() - started)


# ---------------------------------------------------------------------
# Фоновая сборка для веб-страницы
# ---------------------------------------------------------------------
class BuildManager:
    """Одна активная сборка за раз, статус и лог — для /api/android/build."""

    def __init__(
        self,
        settings_path: Path = DEFAULT_SETTINGS_PATH,
        *,
        builder: Callable[..., BuildResult] = build_apk,
        project_dir: Path | None = None,
    ) -> None:
        self.settings_path = settings_path
        self._builder = builder
        self._project_dir = project_dir
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._state = "idle"
        self._log: list[str] = []
        self._apk: Path | None = None
        self._error: str | None = None
        self._started_at: float = 0.0
        self._finished_at: float = 0.0
        self._job_id: str | None = None

    # --- API --------------------------------------------------------
    def status(self) -> dict:
        with self._lock:
            return {
                "jobId": self._job_id,
                "state": self._state,
                "running": self._state == "running",
                "log": self._log[-300:],
                "apk": str(self._apk) if self._apk else None,
                "error": self._error,
                "startedAt": self._started_at or None,
                "finishedAt": self._finished_at or None,
            }

    def start(self) -> str:
        with self._lock:
            if self._state == "running":
                raise AndroidBuildError("Сборка уже идёт")
            self._state = "running"
            self._log = []
            self._error = None
            self._apk = None
            self._job_id = uuid.uuid4().hex[:8]
            self._started_at = time.time()
            self._finished_at = 0.0
            job_id = self._job_id

        self._thread = threading.Thread(target=self._run, name="android-build", daemon=True)
        self._thread.start()
        return job_id

    def wait(self, timeout: float = 5.0) -> dict:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return self.status()

    def _run(self) -> None:
        try:
            settings = load_settings(self.settings_path)
            result = self._builder(
                settings,
                project_dir=self._project_dir,
                on_log=self._append,
            )
            with self._lock:
                self._state = "success"
                self._apk = result.apk
        except Exception as exc:
            logger.warning("Сборка APK не удалась: %s", exc)
            with self._lock:
                self._state = "failed"
                self._error = str(exc)
                self._log.append(str(exc))
        finally:
            with self._lock:
                self._finished_at = time.time()

    def _append(self, line: str) -> None:
        with self._lock:
            self._log.append(line)


def prebuilt_apk() -> Path | None:
    """Готовый APK из дистрибутива — если сборка недоступна."""
    candidates = [
        APP_ROOT / "android" / "dist",
        APP_ROOT / "dist",
    ]
    for directory in candidates:
        if directory.is_dir():
            apks = sorted(directory.glob("*.apk"))
            if apks:
                return apks[0]
    return None


def build_from_file(settings_path: Path | None = None, *, on_log: LogSink | None = None) -> int:
    """CLI: собрать APK и напечатать лог. 0 — успех."""
    path = settings_path or DEFAULT_SETTINGS_PATH
    try:
        settings = load_settings(path)
        result = build_apk(settings, on_log=on_log or (lambda line: print(line, flush=True)))
    except AndroidBuildError as exc:
        print(f"Сборка APK невозможна: {exc}", file=sys.stderr)
        return 1
    print(f"\nГотово: {result.apk} за {result.duration_sec:.1f} с")
    return 0
