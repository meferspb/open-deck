"""Профили панелей: загрузка, строгая валидация и атомарное сохранение.

Профиль — обычный JSON-файл в каталоге `profiles/`, поэтому его можно
редактировать вручную, держать в git и горячо перезагружать: шлюз читает
файл при каждом запросе, кэша нет.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Final

from . import telemetry

SCHEMA_VERSION: Final = 1
WIDGET_TYPES: Final = frozenset(
    {
        "attitude",
        "gauge.radial",
        "readout",
        "switch.toggle",
        "knob.rotary",
        "annunciator",
        "vsi",
        "altimeter",
        "heading",
    }
)
FORM_FACTORS: Final = ("phone", "tablet-sm", "tablet-lg")
PROFILE_ID_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
COLOR_PATTERN: Final = re.compile(r"^#[0-9a-fA-F]{3,8}$")

#: Пользовательские переменные профиля (LVAR/RPN для сложных ВС).
#: Первый сегмент — строчный (обычно `custom`), дальше допускается camelCase.
CUSTOM_KEY_PATTERN: Final = re.compile(r"^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$")
CUSTOM_KINDS: Final = frozenset({"number", "bool", "string"})
CUSTOM_SOURCES: Final = frozenset({"lvar", "rpn"})

#: Какие привязки обязательны для каждого типа виджета.
REQUIRED_BINDINGS: Final[dict[str, tuple[str, ...]]] = {
    "attitude": ("pitch", "bank"),
    "gauge.radial": ("value",),
    "readout": ("value",),
    "switch.toggle": ("state",),
    "knob.rotary": ("value",),
    "annunciator": ("active",),
    "vsi": ("value",),
    "altimeter": ("value",),
    "heading": ("heading",),
}


class ProfileError(ValueError):
    """Профиль не соответствует схеме."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        self.errors = list(errors or [])
        detail = f"{message}: {'; '.join(self.errors)}" if self.errors else message
        super().__init__(detail)


class ProfileNotFound(ProfileError):
    """Профиль не найден в каталоге."""

    pass


# ----------------------------------------------------------------------
# Валидация
# ----------------------------------------------------------------------
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_rect(rect: Any, where: str, errors: list[str]) -> None:
    if not isinstance(rect, dict):
        errors.append(f"{where}: прямоугольник должен быть объектом")
        return
    for key in ("x", "y", "w", "h"):
        if not _is_number(rect.get(key)):
            errors.append(f"{where}: поле {key!r} должно быть числом")
            return
        if not 0.0 <= float(rect[key]) <= 1.0:
            errors.append(f"{where}: поле {key!r} должно быть в диапазоне 0..1")
            return
    if float(rect["w"]) <= 0 or float(rect["h"]) <= 0:
        errors.append(f"{where}: ширина и высота должны быть больше нуля")
    if float(rect["x"]) + float(rect["w"]) > 1.0001 or float(rect["y"]) + float(rect["h"]) > 1.0001:
        errors.append(f"{where}: прямоугольник выходит за границы панели")


def _validate_bindings(
    widget: dict[str, Any],
    widget_id: str,
    errors: list[str],
    known_keys: set[str],
) -> None:
    bindings = widget.get("bindings")
    if not isinstance(bindings, dict):
        errors.append(f"widgets[{widget_id}].bindings: обязательный объект")
        return

    widget_type = widget.get("type")
    for role in REQUIRED_BINDINGS.get(str(widget_type), ()):
        if role not in bindings:
            errors.append(f"widgets[{widget_id}].bindings: отсутствует роль {role!r}")

    for role, key in bindings.items():
        if not isinstance(key, str) or key not in known_keys:
            errors.append(
                f"widgets[{widget_id}].bindings.{role}: неизвестная переменная телеметрии {key!r}"
            )


def _validate_command(widget: dict[str, Any], widget_id: str, errors: list[str]) -> None:
    widget_type = widget.get("type")
    if widget_type not in {"switch.toggle", "knob.rotary"}:
        return
    command = widget.get("command")
    if not isinstance(command, dict):
        errors.append(f"widgets[{widget_id}].command: обязательный объект для {widget_type}")
        return
    key = command.get("key")
    if not isinstance(key, str) or not telemetry.is_writable(key):
        errors.append(f"widgets[{widget_id}].command.key: переменная {key!r} не принимает команды")
    action = command.get("action", "set")
    if action not in {"set", "toggle"}:
        errors.append(f"widgets[{widget_id}].command.action: ожидалось 'set' или 'toggle'")


def _validate_widget(
    widget: Any,
    index: int,
    seen_ids: set[str],
    errors: list[str],
    known_keys: set[str],
) -> None:
    if not isinstance(widget, dict):
        errors.append(f"widgets[{index}]: элемент должен быть объектом")
        return

    widget_id = widget.get("id")
    if not isinstance(widget_id, str) or not PROFILE_ID_PATTERN.match(widget_id):
        errors.append(f"widgets[{index}].id: ожидался slug вида 'attitude-main'")
        return
    if widget_id in seen_ids:
        errors.append(f"widgets[{widget_id}].id: идентификатор повторяется")
        return
    seen_ids.add(widget_id)

    widget_type = widget.get("type")
    if widget_type not in WIDGET_TYPES:
        errors.append(f"widgets[{widget_id}].type: неизвестный тип {widget_type!r}")

    if "label" in widget and not isinstance(widget["label"], str):
        errors.append(f"widgets[{widget_id}].label: ожидалась строка")

    layout = widget.get("layout")
    if not isinstance(layout, dict) or "base" not in layout:
        errors.append(f"widgets[{widget_id}].layout: обязателен блок 'base'")
    else:
        _check_rect(layout["base"], f"widgets[{widget_id}].layout.base", errors)
        for factor in FORM_FACTORS:
            if factor in layout:
                _check_rect(layout[factor], f"widgets[{widget_id}].layout.{factor}", errors)

    _validate_bindings(widget, widget_id, errors, known_keys)
    _validate_command(widget, widget_id, errors)

    options = widget.get("options", {})
    if not isinstance(options, dict):
        errors.append(f"widgets[{widget_id}].options: ожидался объект")
        return

    if widget_type == "gauge.radial":
        minimum, maximum = options.get("min"), options.get("max")
        if not _is_number(minimum) or not _is_number(maximum):
            errors.append(f"widgets[{widget_id}].options: для gauge.radial нужны числа min и max")
        elif float(minimum) >= float(maximum):
            errors.append(f"widgets[{widget_id}].options: min должен быть меньше max")
        redline = options.get("redline")
        if (
            redline is not None
            and _is_number(redline)
            and _is_number(minimum)
            and _is_number(maximum)
            and not float(minimum) <= float(redline) <= float(maximum)
        ):
            errors.append(f"widgets[{widget_id}].options.redline: вне диапазона min..max")


def _validate_custom_variables(profile: dict[str, Any], errors: list[str]) -> set[str]:
    """Проверяет блок `variables` (LVAR/RPN) и возвращает набор ключей."""
    keys: set[str] = set()
    variables = profile.get("variables")
    if variables is None:
        return keys
    if not isinstance(variables, list):
        errors.append("variables: ожидался массив")
        return keys
    if len(variables) > 64:
        errors.append("variables: не больше 64 переменных")
        return keys

    for index, item in enumerate(variables):
        where = f"variables[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: ожидался объект")
            continue

        key = item.get("key")
        if not isinstance(key, str) or not CUSTOM_KEY_PATTERN.match(key):
            errors.append(f"{where}.key: ожидался ключ вида 'custom.fuelLbs'")
        elif key in telemetry.VARIABLES:
            errors.append(f"{where}.key: ключ {key!r} уже занят встроенной переменной")
        elif key in keys:
            errors.append(f"{where}.key: ключ {key!r} повторяется")
        else:
            keys.add(key)

        kind = item.get("kind", "number")
        if kind not in CUSTOM_KINDS:
            errors.append(f"{where}.kind: ожидалось одно из {sorted(CUSTOM_KINDS)}")

        source = item.get("source")
        if source not in CUSTOM_SOURCES:
            errors.append(f"{where}.source: ожидалось одно из {sorted(CUSTOM_SOURCES)}")
        elif source == "lvar":
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append(f"{where}.name: обязательно имя LVAR")
            elif len(name.encode("utf-8")) >= 128:
                errors.append(f"{where}.name: имя LVAR длиннее 127 байт")
        elif source == "rpn":
            expression = item.get("expression")
            if not isinstance(expression, str) or not expression.strip():
                errors.append(f"{where}.expression: обязательный RPN-скрипт")

        if "label" in item and not isinstance(item["label"], str):
            errors.append(f"{where}.label: ожидалась строка")
        if "unit" in item and not isinstance(item["unit"], str):
            errors.append(f"{where}.unit: ожидалась строка")
        if "initial" in item:
            initial = item["initial"]
            if kind == "number" and not _is_number(initial):
                errors.append(f"{where}.initial: ожидалось число")
            elif kind == "bool" and not isinstance(initial, bool):
                errors.append(f"{where}.initial: ожидалось true/false")
            elif kind == "string" and not isinstance(initial, str):
                errors.append(f"{where}.initial: ожидалась строка")

    return keys


def custom_variable_specs(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Нормализованные спецификации пользовательских переменных для моста."""
    specs: list[dict[str, Any]] = []
    for item in profile.get("variables") or []:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        source = item.get("source")
        if not isinstance(key, str) or source not in CUSTOM_SOURCES:
            continue
        spec: dict[str, Any] = {
            "key": key,
            "kind": item.get("kind", "number"),
            "source": source,
            "initial": item.get("initial"),
        }
        if source == "lvar":
            spec["name"] = item.get("name", "")
        else:
            spec["expression"] = item.get("expression", "")
        specs.append(spec)
    return specs


def validate_profile(profile: Any) -> list[str]:
    """Возвращает список ошибок; пустой список — профиль корректен."""
    errors: list[str] = []
    if not isinstance(profile, dict):
        return ["профиль должен быть JSON-объектом"]

    if profile.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion: ожидалось {SCHEMA_VERSION}")

    profile_id = profile.get("id")
    if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.match(profile_id):
        errors.append("id: ожидался slug вида 'cessna-172-skyhawk'")

    if not isinstance(profile.get("name"), str) or not profile["name"].strip():
        errors.append("name: непустая строка обязательна")

    if "icao" in profile and (
        not isinstance(profile["icao"], str) or not 2 <= len(profile["icao"]) <= 4
    ):
        errors.append("icao: ожидался код из 2-4 символов")

    revision = profile.get("revision", 1)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append("revision: целое число >= 1")

    panel = profile.get("panel")
    if not isinstance(panel, dict):
        errors.append("panel: обязательный объект")
    else:
        background = panel.get("background")
        if not isinstance(background, str) or not COLOR_PATTERN.match(background):
            errors.append("panel.background: ожидался цвет вида '#0d131a'")

    sim = profile.get("sim", {})
    if not isinstance(sim, dict):
        errors.append("sim: ожидался объект")
    else:
        match = sim.get("match", {})
        if not isinstance(match, dict):
            errors.append("sim.match: ожидался объект")
        else:
            for field_name in ("title", "atcModel", "livery"):
                if field_name in match and not isinstance(match[field_name], str):
                    errors.append(f"sim.match.{field_name}: ожидалась строка")

    widgets = profile.get("widgets")
    custom_keys = _validate_custom_variables(profile, errors)
    known_keys = set(telemetry.VARIABLES) | custom_keys

    if not isinstance(widgets, list):
        errors.append("widgets: обязательный массив")
    elif not 1 <= len(widgets) <= 64:
        errors.append("widgets: ожидалось от 1 до 64 элементов")
    else:
        seen_ids: set[str] = set()
        for index, widget in enumerate(widgets):
            _validate_widget(widget, index, seen_ids, errors, known_keys)

    return errors


def ensure_valid(profile: Any) -> None:
    """Проверяет профиль и бросает ProfileError со списком ошибок."""
    errors = validate_profile(profile)
    if errors:
        raise ProfileError("Профиль не прошёл валидацию", errors)


# ----------------------------------------------------------------------
# Файлы
# ----------------------------------------------------------------------
def load_profile_file(path: Path) -> dict[str, Any]:
    """Читает JSON-профиль и применяет legacy-адаптер."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileError(f"Не удалось прочитать профиль {path.name}: {exc}") from exc

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"{path.name}: некорректный JSON ({exc.msg}, строка {exc.lineno})"
        ) from exc

    # Локальный импорт разрывает цикл profiles <-> legacy.
    from .legacy import adapt_if_needed

    try:
        profile = adapt_if_needed(profile)
    except ProfileError as exc:
        raise ProfileError(f"{path.name}: {exc}") from exc

    try:
        ensure_valid(profile)
    except ProfileError as exc:
        raise ProfileError(f"{path.name}: {exc}") from exc
    return profile


def summary_of(profile: dict[str, Any]) -> dict[str, Any]:
    """Короткое описание для списка профилей в клиенте."""
    return {
        "id": profile["id"],
        "name": profile["name"],
        "icao": profile.get("icao", ""),
        "revision": profile.get("revision", 1),
        "widgetCount": len(profile.get("widgets", [])),
    }


class ProfileStore:
    """Каталог профилей с потокобезопасной записью."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._lock = threading.Lock()
        self._logger = logging.getLogger("msfs_gateway.profiles")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, profile_id: str) -> Path:
        if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.match(profile_id):
            raise ProfileError(f"Некорректный идентификатор профиля: {profile_id!r}")
        return self.root / f"{profile_id}.json"

    def list_summaries(self) -> list[dict[str, Any]]:
        """Краткие карточки всех валидных профилей."""
        summaries: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                summaries.append(summary_of(load_profile_file(path)))
            except ProfileError as exc:
                # Битый файл не должен ломать весь список — показываем в логе.
                self._logger.warning("Пропуск профиля: %s", exc)
        return summaries

    def get(self, profile_id: str) -> dict[str, Any]:
        """Возвращает профиль по id или бросает ProfileNotFound."""
        path = self._path_for(profile_id)
        if not path.is_file():
            raise ProfileNotFound(f"Профиль не найден: {profile_id}")
        return load_profile_file(path)

    def save(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Атомарно сохраняет профиль после валидации."""
        ensure_valid(profile)
        path = self._path_for(profile["id"])
        payload = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"

        with self._lock:
            tmp = path.with_name(path.name + ".tmp")
            try:
                with tmp.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, path)
            except OSError as exc:
                tmp.unlink(missing_ok=True)
                raise ProfileError(f"Не удалось сохранить профиль {path.name}: {exc}") from exc

        self._logger.info("Профиль сохранён: %s", path.name)
        return profile
