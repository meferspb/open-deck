"""Генерация справочных документов из кода.

Единый источник правды — реестры `telemetry.VARIABLES` и
`profiles.WIDGET_TYPES`/`REQUIRED_BINDINGS`, поэтому документация не
расходится с реализацией. Скрипт поддерживает два режима:

    python -m msfs_gateway.docsgen --write   # обновить docs/telemetry.md и docs/widgets.md
    python -m msfs_gateway.docsgen --check   # проверить, что файлы актуальны
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Final

from . import telemetry
from .profiles import (
    CUSTOM_KEY_PATTERN,
    CUSTOM_KINDS,
    CUSTOM_SOURCES,
    FORM_FACTORS,
    REQUIRED_BINDINGS,
    WIDGET_TYPES,
)

TELEMETRY_DOC: Final = "telemetry.md"
WIDGETS_DOC: Final = "widgets.md"

#: Человеческие заголовки групп (первый сегмент ключа телеметрии).
GROUP_TITLES: Final[dict[str, str]] = {
    "power": "Электрика и питание",
    "engine": "Двигатель",
    "attitude": "Пространственное положение",
    "altitude": "Высота",
    "speed": "Скорость",
    "verticalSpeed": "Вариометр",
    "heading": "Курс",
    "flaps": "Механизация крыла",
    "fuel": "Топливо",
    "autopilot": "Автопилот",
    "aircraft": "Состояние воздушного судна",
    "groundSpeed": "Руление",
    "nav": "Навигация (ILS)",
    "controls": "Органы управления",
    "brakes": "Тормоза",
}
GROUP_ORDER: Final[tuple[str, ...]] = tuple(GROUP_TITLES)

#: Порядок и описания типов приборов (UI-часть, в Python-реестре её нет).
WIDGET_ORDER: Final[tuple[str, ...]] = (
    "attitude",
    "gauge.radial",
    "readout",
    "switch.toggle",
    "knob.rotary",
    "annunciator",
    "vsi",
    "altimeter",
    "heading",
)
WIDGET_TITLES: Final[dict[str, str]] = {
    "attitude": "Авиагоризонт",
    "gauge.radial": "Круговая шкала",
    "readout": "Цифровое табло",
    "switch.toggle": "Тумблер",
    "knob.rotary": "Галетник / энкодер",
    "annunciator": "Табло-лампы",
    "vsi": "Вариометр",
    "altimeter": "Высотомер",
    "heading": "Курсоуказатель",
}
WIDGET_DESCRIPTIONS: Final[dict[str, str]] = {
    "attitude": (
        "Авиагоризонт: тангаж и крен по `pitch`/`bank`, шкала крена, "
        "метка нуля. Дополнительных опций нет."
    ),
    "gauge.radial": (
        "Круговая стрелочная шкала: значение `value` в диапазоне `min..max`, "
        "деления, красная зона, подпись и единицы."
    ),
    "readout": (
        "Цифровое табло: форматирует `value` с заданным числом знаков, "
        "единицами и подписью; умеет подсвечивать аварийный порог."
    ),
    "switch.toggle": (
        "Тумблер: показывает логическое `state` и отправляет команду "
        "`command.key`; действие `set` посылает противоположное значение, "
        "`toggle` — событие-переключатель."
    ),
    "knob.rotary": (
        "Галетник/энкодер: вращение и свайпы меняют `value` на `step` в "
        "диапазоне `min..max`, отправляя команду с новым значением."
    ),
    "annunciator": (
        "Табло-лампы: горит при истинном `active`; подпись, тон и инверсия настраиваются опциями."
    ),
    "vsi": ("Вариометр: стрелка вертикальной скорости, шкала ограничена `limit`, подписи в fpm."),
    "altimeter": (
        "Высотомер с тремя стрелками (сотни/тысячи/десятки тысяч футов) по значению `value`."
    ),
    "heading": (
        "Курсоуказатель с вращающейся картушкой и «жучком»; значение — магнитный курс в градусах."
    ),
}
#: Опции приборов по данным веб-клиента. (имя, описание, обязательность)
WIDGET_OPTIONS: Final[dict[str, tuple[tuple[str, str, bool], ...]]] = {
    "attitude": (),
    "gauge.radial": (
        ("min", "минимум шкалы", True),
        ("max", "максимум шкалы", True),
        ("redline", "красная зона (в диапазоне min..max)", False),
        ("zones", "дополнительные цветные зоны", False),
        ("majorTicks", "число больших делений", False),
        ("minorTicks", "число малых делений", False),
        ("decimals", "знаков после запятой", False),
        ("unit", "единицы подписи", False),
    ),
    "readout": (
        ("unit", "единицы", False),
        ("decimals", "знаков после запятой", False),
        ("caption", "подпись над значением", False),
        ("alarm", "порог аварийной подсветки", False),
    ),
    "switch.toggle": (
        ("caption", "подпись тумблера", False),
        ("onLabel", "текст включённого состояния", False),
        ("offLabel", "текст выключенного состояния", False),
    ),
    "knob.rotary": (
        ("min", "минимум", False),
        ("max", "максимум", False),
        ("step", "шаг изменения", False),
        ("wrap", "зацикливать значение", False),
        ("unit", "единицы", False),
        ("decimals", "знаков после запятой", False),
        ("caption", "подпись", False),
    ),
    "annunciator": (
        ("caption", "подпись лампы", False),
        ("tone", "цвет/тон свечения", False),
        ("invert", "инвертировать логику", False),
    ),
    "vsi": (("limit", "предел шкалы, fpm", False),),
    "altimeter": (),
    "heading": (),
}
#: Приборы, которым обязателен блок `command`.
COMMAND_TYPES: Final[frozenset[str]] = frozenset({"switch.toggle", "knob.rotary"})


#: Русские описания переменных (label в реестре — английский, для кода).
VARIABLE_DESCRIPTIONS: Final[dict[str, str]] = {
    "power.batteryMaster": "Выключатель аккумулятора",
    "power.avionicsMaster": "Питание авионики",
    "power.busVolts": "Напряжение основной шины",
    "engine.rpm": "Обороты двигателя",
    "engine.fuelFlowGph": "Часовой расход топлива",
    "engine.torquePct": "Момент турбовинтового двигателя",
    "engine.ittC": "Температура ИТТ",
    "engine.propRpm": "Обороты воздушного винта",
    "engine.n1Pct": "N1 двигателя №1",
    "engine.n1Pct2": "N1 двигателя №2",
    "attitude.pitchDeg": "Тангаж",
    "attitude.bankDeg": "Крен",
    "heading.magneticDeg": "Магнитный курс",
    "altitude.indicatedFt": "Приборная высота",
    "verticalSpeed.fpm": "Вертикальная скорость",
    "speed.iasKt": "Приборная скорость",
    "autopilot.headingBugDeg": "Заданный курс (heading bug)",
    "autopilot.master": "Автопилот включён",
    "autopilot.approachHold": "Режим APR — команда включения",
    "autopilot.approach": "Режим APR активен",
    "aircraft.onGround": "Самолёт на земле",
    "aircraft.radioAltitudeFt": "Радиовысота над ВПП",
    "groundSpeed.kt": "Путевая скорость",
    "nav.localizer": "Отклонение от курсового маяка",
    "nav.glideSlope": "Отклонение от глиссады",
    "nav.locFlag": "Курсовой маяк захвачен",
    "nav.gsFlag": "Глиссада захвачена",
    "controls.throttlePct": "Положение РУД (команда ассистента)",
    "controls.rudder": "Руль направления (команда ассистента)",
    "brakes.parking": "Стояночный тормоз",
    "flaps.percent": "Положение закрылков",
    "fuel.leftGal": "Топливо в левом баке",
    "fuel.rightGal": "Топливо в правом баке",
    "fuel.totalGal": "Всего топлива",
    "aircraft.title": "Название борта в симуляторе",
}


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|")


def _group_of(key: str) -> str:
    return key.split(".", 1)[0]


def _sorted_groups() -> list[str]:
    groups = {_group_of(key) for key in telemetry.VARIABLES}
    ordered = [group for group in GROUP_ORDER if group in groups]
    return ordered + sorted(groups - set(ordered))


def generate_telemetry_doc() -> str:
    """Возвращает markdown-каталог всех переменных телеметрии."""
    lines: list[str] = [
        "# 📊 Каталог переменных телеметрии",
        "",
        "> Файл сгенерирован из `msfs_gateway/telemetry.py`; не редактируйте вручную.",
        "> Обновить: `python -m msfs_gateway.docsgen --write`.",
        "",
        "Реестр — единственный источник правды: по этим ключам профили панелей",
        "привязывают приборы, а шлюз читает SimVar и отправляет команды.",
        "",
        "## Как читать таблицу",
        "",
        "- **Ключ** — имя переменной в кадре телеметрии и в `bindings` профиля.",
        "- **Тип** — `number`, `bool` или `string`; `bool` в JSON приходит как",
        "  `true/false`, числа — как `float`.",
        "- **Чтение** — SimVar, из которого шлюз берёт значение (для `custom.*`",
        "  источника нет: их читает WASM-мост по описанию из профиля).",
        "- **Команда** — SimConnect-событие, которым переменная меняется;",
        "  прочерк означает «только чтение».",
        "",
        "## Переменные по группам",
        "",
    ]

    for group in _sorted_groups():
        title = GROUP_TITLES.get(group, group)
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for variable in telemetry.VARIABLES.values():
            if _group_of(variable.key) != group:
                continue
            description = VARIABLE_DESCRIPTIONS.get(variable.key, variable.label)
            lines.append(
                f"| `{variable.key}` | {variable.kind} | {_cell(variable.unit)} "
                f"| {_cell(variable.sim_var)} | {_cell(variable.sim_event)} "
                f"| {_cell(description)} |"
            )
        lines.append("")

    writable = [variable for variable in telemetry.VARIABLES.values() if variable.writable]
    lines += [
        "## Переменные с командами",
        "",
        "Эти ключи можно менять через `POST /api/sim/command` и WebSocket",
        "`command`. Значение приводится к типу переменной; для событий с",
        "параметром оно масштабируется (например, проценты → 0..16383).",
        "",
        "| Ключ | Событие | Параметр | Масштаб |",
        "| --- | --- | --- | --- |",
    ]
    for variable in writable:
        lines.append(
            "| `{}` | `{}` | {} | {} |".format(
                variable.key,
                variable.sim_event,
                "да" if variable.sim_event_param else "нет",
                variable.sim_event_scale,
            )
        )
    lines += [
        "",
        "## Пользовательские переменные `custom.*`",
        "",
        "Профиль может объявить свои LVAR/RPN в блоке `variables`; ключ обязан",
        "начинаться со строчного сегмента (обычно `custom.`) и не совпадать со",
        "встроенными. Такой ключ появляется в кадре как обычная переменная.",
        "",
        f"Допустимые виды: {', '.join(sorted(CUSTOM_KINDS))}; источники: "
        f"{', '.join(sorted(CUSTOM_SOURCES))}. Формат ключа: "
        f"`{CUSTOM_KEY_PATTERN.pattern}`.",
        "",
        "Пример:",
        "",
        "```json",
        '{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",',
        '  "name": "APU_BLEED", "initial": false }',
        "```",
        "",
        "Подробности — в "
        "[profile-schema.md](profile-schema.md#6-пользовательские-переменные-lvar--rpn).",
        "",
    ]
    return "\n".join(lines)


def _bindings_text(widget_type: str) -> str:
    roles = REQUIRED_BINDINGS.get(widget_type, ())
    return ", ".join(f"`{role}`" for role in roles) or "—"


def _options_text(widget_type: str) -> str:
    options = WIDGET_OPTIONS.get(widget_type, ())
    if not options:
        return "—"
    return ", ".join(
        f"`{name}`{'*' if required else ''}" for name, _description, required in options
    )


def generate_widgets_doc() -> str:
    """Возвращает markdown-каталог типов приборов и их опций."""
    unknown = set(WIDGET_TYPES) - set(WIDGET_ORDER)
    if unknown:
        raise RuntimeError(f"docsgen: нет описания для типов {sorted(unknown)}")

    lines: list[str] = [
        "# 🧩 Каталог приборов",
        "",
        "> Файл сгенерирован из `msfs_gateway/profiles.py` (типы и обязательные",
        "> привязки) и веб-клиента (опции). Обновить:",
        "> `python -m msfs_gateway.docsgen --write`.",
        "",
        "Каждый прибор — элемент массива `widgets[]` профиля. Полная схема",
        "профиля — в [profile-schema.md](profile-schema.md).",
        "",
        "## Общая структура",
        "",
        "```json",
        "{",
        '  "id": "attitude-main",',
        '  "type": "attitude",',
        '  "label": "Авиагоризонт",',
        '  "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },',
        '  "layout": {',
        '    "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },',
        '    "phone": { "x": 0.03, "y": 0.02, "w": 0.94, "h": 0.3 }',
        "  },",
        '  "options": { "unit": "FT", "decimals": 0 }',
        "}",
        "```",
        "",
        "- `id` — уникальный slug (`[a-z0-9][a-z0-9-]`), используется в редакторе",
        "  и для привязки событий.",
        "- `layout` — координаты в долях панели; обязателен `base`, опциональны",
        f"  {', '.join(f'`{factor}`' for factor in FORM_FACTORS)}.",
        "- `options` — необязательный объект, зависит от типа.",
        "- `command` — обязателен для тумблера и галетника (см. ниже).",
        "",
        "## Типы приборов",
        "",
        "| Тип | Прибор | Обязательные bindings | `command` | Основные options |",
        "| --- | --- | --- | --- | --- |",
    ]
    for widget_type in WIDGET_ORDER:
        lines.append(
            "| `{}` | {} | {} | {} | {} |".format(
                widget_type,
                WIDGET_TITLES[widget_type],
                _bindings_text(widget_type),
                "обязателен" if widget_type in COMMAND_TYPES else "—",
                _options_text(widget_type),
            )
        )
    lines += [
        "",
        "`*` у опции — обязательна. Остальные опции имеют разумные значения по",
        "умолчанию и нужны для настройки внешнего вида.",
        "",
        "## Описание типов",
        "",
    ]
    for widget_type in WIDGET_ORDER:
        lines += [
            f"### `{widget_type}` — {WIDGET_TITLES[widget_type]}",
            "",
            WIDGET_DESCRIPTIONS[widget_type],
            "",
        ]
        options = WIDGET_OPTIONS.get(widget_type, ())
        if options:
            lines += ["| Опция | Значение | Обязательна |", "| --- | --- | --- |"]
            for name, description, required in options:
                lines.append(f"| `{name}` | {description} | {'да' if required else 'нет'} |")
            lines.append("")
        lines += [
            "Минимальный пример:",
            "",
            "```json",
            _example_widget(widget_type),
            "```",
            "",
        ]

    lines += [
        "## Команды с тумблера и галетника",
        "",
        "Блок `command` описывает, что отправить на шлюз:",
        "",
        "| Поле | Значение |",
        "| --- | --- |",
        "| `key` | переменная с признаком «принимает команды» (см. каталог телеметрии) |",
        "| `action` | `set` — отправить новое значение; `toggle` — событие-переключатель |",
        "| `value` | для `set`: `true/false`/число; по умолчанию противоположное текущему |",
        "",
        "Пример тумблера:",
        "",
        "```json",
        '{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },',
        '  "command": { "key": "power.batteryMaster", "action": "set" } }',
        "```",
        "",
        "## Валидация",
        "",
        "- Тип обязан входить в список выше; неизвестный тип редактор не сохранит.",
        "- Обязательные роли `bindings` должны ссылаться на существующие ключи",
        "  телеметрии.",
        "- `layout.base` и переопределения обязаны быть прямоугольниками в",
        "  пределах `0..1` (см. схему профиля).",
        "",
    ]
    return "\n".join(lines)


def _example_widget(widget_type: str) -> str:
    layouts = '"layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } }'
    examples = {
        "attitude": (
            '{ "id": "attitude", "type": "attitude", '
            '"bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, '
            + layouts
            + " }"
        ),
        "gauge.radial": (
            '{ "id": "speed", "type": "gauge.radial", '
            '"bindings": { "value": "speed.iasKt" }, '
            '"options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, ' + layouts + " }"
        ),
        "readout": (
            '{ "id": "alt", "type": "readout", '
            '"bindings": { "value": "altitude.indicatedFt" }, '
            '"options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, ' + layouts + " }"
        ),
        "switch.toggle": (
            '{ "id": "battery", "type": "switch.toggle", '
            '"bindings": { "state": "power.batteryMaster" }, '
            '"command": { "key": "power.batteryMaster", "action": "set" }, ' + layouts + " }"
        ),
        "knob.rotary": (
            '{ "id": "hdg", "type": "knob.rotary", '
            '"bindings": { "value": "autopilot.headingBugDeg" }, '
            '"command": { "key": "autopilot.headingBugDeg", "action": "set" }, '
            '"options": { "min": 0, "max": 359, "step": 1, "wrap": true }, ' + layouts + " }"
        ),
        "annunciator": (
            '{ "id": "bus", "type": "annunciator", '
            '"bindings": { "active": "power.busVolts" }, '
            '"options": { "caption": "BUS OFF", "invert": true }, ' + layouts + " }"
        ),
        "vsi": (
            '{ "id": "vsi", "type": "vsi", '
            '"bindings": { "value": "verticalSpeed.fpm" }, '
            '"options": { "limit": 2000 }, ' + layouts + " }"
        ),
        "altimeter": (
            '{ "id": "altimeter", "type": "altimeter", '
            '"bindings": { "value": "altitude.indicatedFt" }, ' + layouts + " }"
        ),
        "heading": (
            '{ "id": "heading", "type": "heading", '
            '"bindings": { "heading": "heading.magneticDeg" }, ' + layouts + " }"
        ),
    }
    return examples[widget_type]


def write_docs(root: Path) -> None:
    """Записывает сгенерированные документы."""
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / TELEMETRY_DOC).write_text(generate_telemetry_doc(), encoding="utf-8")
    (docs / WIDGETS_DOC).write_text(generate_widgets_doc(), encoding="utf-8")


def check_docs(root: Path) -> list[str]:
    """Возвращает список устаревших файлов (пусто — всё актуально)."""
    expected = {
        TELEMETRY_DOC: generate_telemetry_doc(),
        WIDGETS_DOC: generate_widgets_doc(),
    }
    stale = []
    for name, content in expected.items():
        path = root / "docs" / name
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(name)
    return stale


def main(argv: list[str] | None = None) -> int:
    """CLI генерации/проверки документации."""
    from .settings import APP_ROOT

    parser = argparse.ArgumentParser(prog="msfs_gateway.docsgen", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="записать docs/telemetry.md и docs/widgets.md"
    )
    mode.add_argument("--check", action="store_true", help="проверить актуальность файлов")
    args = parser.parse_args(argv)

    if args.write:
        write_docs(APP_ROOT)
        print(f"Обновлено: docs/{TELEMETRY_DOC}, docs/{WIDGETS_DOC}")
        return 0

    stale = check_docs(APP_ROOT)
    if stale:
        print("Документация устарела: " + ", ".join(stale), file=sys.stderr)
        print("Запустите: python -m msfs_gateway.docsgen --write", file=sys.stderr)
        return 1
    print("Документация актуальна.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
