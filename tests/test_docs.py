"""Проверки документации: сгенерированные файлы и относительные ссылки."""

import re
import unittest
from pathlib import Path

from msfs_gateway import docsgen
from msfs_gateway.settings import APP_ROOT

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")
LOCALES = ("ru", "de", "zh", "es", "ja")
LOCALIZED_DOCS = (
    "README.md",
    "architecture.md",
    "service.md",
    "protocol.md",
    "telemetry.md",
    "widgets.md",
    "profile-schema.md",
    "development.md",
    "pricing.md",
    "android.md",
    "packaging.md",
    "contributing.md",
    "security.md",
    "changelog.md",
    "code-of-conduct.md",
)


def markdown_files(root: Path) -> list[Path]:
    files = [
        root / "README.md",
        root / "CONTRIBUTING.md",
        root / "SECURITY.md",
        root / "CHANGELOG.md",
    ]
    files += sorted((root / "docs").rglob("*.md"))
    files += sorted(root.glob("README_*.md"))
    files += [root / "android" / "README.md", root / "packaging" / "windows" / "README.md"]
    return [path for path in files if path.is_file()]


def broken_links(path: Path, root: Path) -> list[str]:
    problems: list[str] = []
    in_code = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        for target in LINK_RE.findall(line):
            target = target.strip()
            if target.startswith(SKIP_PREFIXES) or not target:
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                problems.append(f"{path.name}:{number}: ссылка вне репозитория: {target}")
                continue
            if not resolved.exists():
                problems.append(f"{path.name}:{number}: нет файла: {target}")
    return problems


class GeneratedDocsTest(unittest.TestCase):
    def test_generated_docs_are_current(self):
        stale = docsgen.check_docs(APP_ROOT)
        self.assertEqual(
            stale,
            [],
            "Устарели: " + ", ".join(stale) + ". Запустите: python -m msfs_gateway.docsgen --write",
        )

    def test_widgets_doc_covers_every_type(self):
        content = docsgen.generate_widgets_doc()
        for widget_type in docsgen.WIDGET_ORDER:
            self.assertIn(f"`{widget_type}`", content)
        from msfs_gateway.profiles import WIDGET_TYPES

        self.assertEqual(set(docsgen.WIDGET_ORDER), set(WIDGET_TYPES))

    def test_telemetry_doc_covers_every_variable(self):
        content = docsgen.generate_telemetry_doc()
        for key in docsgen.telemetry.VARIABLES:
            self.assertIn(f"`{key}`", content)


class LocalizedDocsTest(unittest.TestCase):
    def test_every_locale_has_documentation_set(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                locale_dir = APP_ROOT / "docs" / locale
                missing = [name for name in LOCALIZED_DOCS if not (locale_dir / name).is_file()]
                self.assertEqual(missing, [], f"docs/{locale}: missing {missing}")

    def test_every_locale_has_readme(self):
        names = {
            "ru": "README_RU.md",
            "de": "README_DE.md",
            "zh": "README_ZH.md",
            "es": "README_ES.md",
            "ja": "README_JA.md",
        }
        for locale, name in names.items():
            with self.subTest(locale=locale):
                self.assertTrue((APP_ROOT / name).is_file(), f"missing {name}")


class DocsLinksTest(unittest.TestCase):
    def test_relative_links_resolve(self):
        problems: list[str] = []
        for path in markdown_files(APP_ROOT):
            problems.extend(broken_links(path, APP_ROOT))
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
