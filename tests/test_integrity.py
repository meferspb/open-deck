"""Тесты проверки целостности критичных файлов."""

import json
import tempfile
import unittest
from pathlib import Path

from msfs_gateway import integrity
from msfs_gateway.integrity import build_manifest, verify


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        # Создаём фейковое дерево критичных файлов.
        for relative in integrity.CRITICAL_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"content of {relative}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_manifest_covers_all_critical_files(self):
        manifest = build_manifest(self.root)
        self.assertEqual(set(manifest["files"]), set(integrity.CRITICAL_FILES))
        self.assertEqual(manifest["schemaVersion"], integrity.MANIFEST_VERSION)

    def test_verify_passes_on_unchanged_files(self):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(build_manifest(self.root)), encoding="utf-8")
        report = verify(self.root, manifest_path)
        self.assertTrue(report.verified, report.errors)

    def test_verify_fails_on_modified_file(self):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(build_manifest(self.root)), encoding="utf-8")
        target = self.root / integrity.CRITICAL_FILES[0]
        target.write_text("tampered\n", encoding="utf-8")

        report = verify(self.root, manifest_path)
        self.assertFalse(report.verified)
        self.assertTrue(any("изменён" in error for error in report.errors))

    def test_verify_fails_without_manifest(self):
        report = verify(self.root, self.root / "missing.json")
        self.assertFalse(report.verified)
        self.assertFalse(report.manifest_present)

    def test_write_manifest_keeps_timestamp_when_hashes_unchanged(self):
        manifest_path = self.root / "manifest.json"
        first = integrity.write_manifest(self.root, manifest_path)
        first_text = manifest_path.read_text(encoding="utf-8")

        second = integrity.write_manifest(self.root, manifest_path)
        second_text = manifest_path.read_text(encoding="utf-8")

        self.assertEqual(first["files"], second["files"])
        self.assertEqual(second["generatedAt"], first["generatedAt"])
        self.assertEqual(second_text, first_text)

    def test_write_manifest_updates_when_file_changes(self):
        manifest_path = self.root / "manifest.json"
        first = integrity.write_manifest(self.root, manifest_path)

        target = self.root / integrity.CRITICAL_FILES[0]
        target.write_text("changed\n", encoding="utf-8")
        second = integrity.write_manifest(self.root, manifest_path)

        self.assertNotEqual(first["files"], second["files"])


if __name__ == "__main__":
    unittest.main()
