"""Проверка целостности критичных файлов интерфейса.

Условие лицензии: блок поддержки автора обязателен и не может быть
удалён или подменён. Хост проверяет SHA-256 файлов, участвующих в его
отображении, и отказывается запускаться при расхождении.

Манифест — обычный JSON (`integrity/manifest.json`), он генерируется
командой `python -m msfs_gateway.integrity --write` после намеренного
изменения критичных файлов. Авторитетная проверка — именно здесь, на
хосте; клиентская (web/js/ui/integrity.js) лишь отображает результат.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from .settings import REPO_ROOT

MANIFEST_VERSION: Final = 1
MANIFEST_PATH: Final = REPO_ROOT / "integrity" / "manifest.json"

#: Файлы, изменение которых обходит условия лицензии.
CRITICAL_FILES: Final[tuple[str, ...]] = (
    "web/index.html",
    "web/editor.html",
    "web/js/ui/donation.js",
    "web/js/ui/integrity.js",
    "web/css/donation.css",
    "config/donation.json",
)


class IntegrityError(RuntimeError):
    """Целостность нарушена — запуск запрещён."""


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    verified: bool
    checked_at: str
    files: dict[str, str]
    errors: tuple[str, ...]
    manifest_present: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "checkedAt": self.checked_at,
            "files": dict(self.files),
            "errors": list(self.errors),
            "criticalFiles": list(CRITICAL_FILES),
            "manifestPresent": self.manifest_present,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path = REPO_ROOT) -> dict[str, Any]:
    files: dict[str, str] = {}
    missing: list[str] = []
    for relative in CRITICAL_FILES:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        files[relative] = sha256_file(path)
    if missing:
        raise IntegrityError(f"Нет критичных файлов: {', '.join(missing)}")

    return {
        "schemaVersion": MANIFEST_VERSION,
        "algorithm": "sha256",
        "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": files,
    }


def write_manifest(root: Path = REPO_ROOT, manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Записывает манифест. Если хеши не изменились — файл не трогаем.

    Так `generatedAt` не «дёргается» на каждом запуске, а в git не появляется
    шумных диффов после каждой сборки.
    """
    manifest = build_manifest(root)
    existing = load_manifest(manifest_path)
    if existing is not None and existing.get("files") == manifest["files"]:
        return existing

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> dict[str, Any] | None:
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return manifest if isinstance(manifest, dict) else None


def verify(root: Path = REPO_ROOT, manifest_path: Path = MANIFEST_PATH) -> IntegrityReport:
    """Сверяет критичные файлы с манифестом. Ничего не меняет на диске."""
    checked_at = datetime.now(UTC).isoformat(timespec="seconds")
    errors: list[str] = []
    actual: dict[str, str] = {}

    manifest = load_manifest(manifest_path)
    if manifest is None:
        return IntegrityReport(
            verified=False,
            checked_at=checked_at,
            files=actual,
            errors=(
                f"Манифест целостности отсутствует или повреждён: {manifest_path}. "
                + "Сгенерируйте его командой python -m msfs_gateway.integrity --write",
            ),
            manifest_present=False,
        )

    if manifest.get("schemaVersion") != MANIFEST_VERSION:
        errors.append(f"Неподдерживаемая версия манифеста: {manifest.get('schemaVersion')!r}")

    expected = manifest.get("files")
    if not isinstance(expected, dict):
        errors.append("Манифест не содержит карты файлов")
        expected = {}

    for relative in CRITICAL_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"Файл отсутствует: {relative}")
            continue
        digest = sha256_file(path)
        actual[relative] = digest
        expected_digest = expected.get(relative)
        if not isinstance(expected_digest, str):
            errors.append(f"Файл не покрыт манифестом: {relative}")
        elif digest != expected_digest:
            errors.append(f"Файл изменён: {relative}")

    return IntegrityReport(
        verified=not errors,
        checked_at=checked_at,
        files=actual,
        errors=tuple(errors),
        manifest_present=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m msfs_gateway.integrity",
        description="Проверка/обновление манифеста целостности критичных файлов.",
    )
    parser.add_argument("--write", action="store_true", help="Пересчитать и записать манифест.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH, help="Путь к манифесту.")
    args = parser.parse_args(argv)

    if args.write:
        manifest = write_manifest(manifest_path=args.manifest)
        print(f"Манифест записан: {args.manifest}")
        for name, digest in manifest["files"].items():
            print(f"  {digest[:16]}…  {name}")
        return 0

    report = verify(manifest_path=args.manifest)
    for name, digest in report.files.items():
        print(f"  {digest[:16]}…  {name}")
    if report.verified:
        print("Целостность в порядке.")
        return 0
    print("Целостность нарушена:", file=sys.stderr)
    for error in report.errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
