"""Generate reference documents from code.

The single source of truth is the `telemetry.VARIABLES` and
`profiles.WIDGET_TYPES`/`REQUIRED_BINDINGS` registries, so the documentation
does not drift from the implementation. The script supports two modes:

    python -m msfs_gateway.docsgen --write   # update docs/telemetry.md and docs/widgets.md
    python -m msfs_gateway.docsgen --check   # verify that the files are up to date
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

#: Human-readable group titles (the first segment of a telemetry key).
GROUP_TITLES: Final[dict[str, str]] = {
    "power": "Electrical and power",
    "engine": "Engine",
    "attitude": "Spatial attitude",
    "altitude": "Altitude",
    "speed": "Speed",
    "verticalSpeed": "VSI",
    "heading": "Heading",
    "flaps": "Wing flaps",
    "fuel": "Fuel",
    "autopilot": "Autopilot",
    "aircraft": "Aircraft state",
    "groundSpeed": "Taxi",
    "nav": "Navigation (ILS)",
    "controls": "Controls",
    "brakes": "Brakes",
}
GROUP_ORDER: Final[tuple[str, ...]] = tuple(GROUP_TITLES)

#: Order and descriptions of instrument types (the UI part is not in the Python registry).
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
    "attitude": "Attitude indicator",
    "gauge.radial": "Circular gauge",
    "readout": "Digital readout",
    "switch.toggle": "Toggle switch",
    "knob.rotary": "Rotary selector / encoder",
    "annunciator": "Annunciator lights",
    "vsi": "VSI",
    "altimeter": "Altimeter",
    "heading": "Heading indicator",
}
WIDGET_DESCRIPTIONS: Final[dict[str, str]] = {
    "attitude": (
        "Attitude indicator: pitch and bank via `pitch`/`bank`, a bank scale, "
        "and a zero mark. There are no additional options."
    ),
    "gauge.radial": (
        "Circular needle gauge: the `value` within the `min..max` range, "
        "tick marks, a red zone, a caption, and units."
    ),
    "readout": (
        "Digital readout: formats `value` with the given number of digits, "
        "units, and a caption; it can highlight an alarm threshold."
    ),
    "switch.toggle": (
        "Toggle switch: shows a boolean `state` and sends the `command.key` "
        "command; the `set` action sends the opposite value, and `toggle` "
        "sends a toggle event."
    ),
    "knob.rotary": (
        "Rotary selector/encoder: rotation and swipes change `value` by `step` "
        "within the `min..max` range, sending a command with the new value."
    ),
    "annunciator": (
        "Annunciator lights: light up when `active` is true; the caption, "
        "tone, and inversion are configured through options."
    ),
    "vsi": ("VSI: a vertical speed needle, with the gauge limited by `limit`, and labels in fpm."),
    "altimeter": (
        "A three-pointer altimeter (hundreds/thousands/tens of thousands of feet) "
        "based on the `value`."
    ),
    "heading": (
        'A heading indicator with a rotating compass card and a "bug"; '
        "the value is the magnetic heading in degrees."
    ),
}
#: Instrument options based on the web client data. (name, description, required)
WIDGET_OPTIONS: Final[dict[str, tuple[tuple[str, str, bool], ...]]] = {
    "attitude": (),
    "gauge.radial": (
        ("min", "gauge minimum", True),
        ("max", "gauge maximum", True),
        ("redline", "red zone (within the min..max range)", False),
        ("zones", "additional colored zones", False),
        ("majorTicks", "number of major tick marks", False),
        ("minorTicks", "number of minor tick marks", False),
        ("decimals", "digits after the decimal point", False),
        ("unit", "unit label", False),
    ),
    "readout": (
        ("unit", "units", False),
        ("decimals", "digits after the decimal point", False),
        ("caption", "caption above the value", False),
        ("alarm", "alarm highlight threshold", False),
    ),
    "switch.toggle": (
        ("caption", "toggle caption", False),
        ("onLabel", "text for the on state", False),
        ("offLabel", "text for the off state", False),
    ),
    "knob.rotary": (
        ("min", "minimum", False),
        ("max", "maximum", False),
        ("step", "change step", False),
        ("wrap", "loop the value", False),
        ("unit", "units", False),
        ("decimals", "digits after the decimal point", False),
        ("caption", "caption", False),
    ),
    "annunciator": (
        ("caption", "lamp caption", False),
        ("tone", "glow color/tone", False),
        ("invert", "invert the logic", False),
    ),
    "vsi": (("limit", "gauge limit, fpm", False),),
    "altimeter": (),
    "heading": (),
}
#: Instrument types that require a `command` block.
COMMAND_TYPES: Final[frozenset[str]] = frozenset({"switch.toggle", "knob.rotary"})


#: Human-readable variable descriptions (the registry label is an English fallback for code).
VARIABLE_DESCRIPTIONS: Final[dict[str, str]] = {
    "power.batteryMaster": "Battery master switch",
    "power.avionicsMaster": "Avionics power",
    "power.busVolts": "Main bus voltage",
    "engine.rpm": "Engine RPM",
    "engine.fuelFlowGph": "Fuel flow per hour",
    "engine.torquePct": "Turboprop engine torque",
    "engine.ittC": "ITT temperature",
    "engine.propRpm": "Propeller RPM",
    "engine.n1Pct": "Engine #1 N1",
    "engine.n1Pct2": "Engine #2 N1",
    "attitude.pitchDeg": "Pitch",
    "attitude.bankDeg": "Bank",
    "heading.magneticDeg": "Magnetic heading",
    "altitude.indicatedFt": "Indicated altitude",
    "verticalSpeed.fpm": "Vertical speed",
    "speed.iasKt": "Indicated airspeed",
    "autopilot.headingBugDeg": "Target heading (heading bug)",
    "autopilot.master": "Autopilot engaged",
    "autopilot.approachHold": "APR mode — engage command",
    "autopilot.approach": "APR mode active",
    "aircraft.onGround": "Aircraft on the ground",
    "aircraft.radioAltitudeFt": "Radio altitude above the runway",
    "groundSpeed.kt": "Ground speed",
    "nav.localizer": "Localizer deviation",
    "nav.glideSlope": "Glideslope deviation",
    "nav.locFlag": "Localizer captured",
    "nav.gsFlag": "Glideslope captured",
    "controls.throttlePct": "Throttle lever position (assist command)",
    "controls.rudder": "Rudder (assist command)",
    "brakes.parking": "Parking brake",
    "flaps.percent": "Flap position",
    "fuel.leftGal": "Left tank fuel",
    "fuel.rightGal": "Right tank fuel",
    "fuel.totalGal": "Total fuel",
    "aircraft.title": "Aircraft title in the simulator",
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
    """Returns a Markdown catalog of all telemetry variables."""
    lines: list[str] = [
        "# 📊 Telemetry Variable Catalog",
        "",
        "> This file is generated from `msfs_gateway/telemetry.py`; do not edit it manually.",
        "> Update: `python -m msfs_gateway.docsgen --write`.",
        "",
        "The registry is the single source of truth: panel profiles bind instruments to",
        "these keys, and the gateway reads SimVars and sends commands.",
        "",
        "## How to read the table",
        "",
        "- **Key** — the variable name in the telemetry frame and in the profile's",
        "  `bindings`.",
        "- **Type** — `number`, `bool`, or `string`; `bool` arrives in JSON as",
        "  `true/false`, numbers as `float`.",
        "- **Read** — the SimVar from which the gateway takes the value (for `custom.*`",
        "  there is no source: they are read by the WASM bridge according to the profile",
        "  description).",
        "- **Command** — the SimConnect event used to change the variable;",
        '  a dash means "read-only".',
        "",
        "## Variables by group",
        "",
    ]

    for group in _sorted_groups():
        title = GROUP_TITLES.get(group, group)
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| Key | Type | Unit | Read (SimVar) | Command | Description |")
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
        "## Variables with commands",
        "",
        "These keys can be changed through `POST /api/sim/command` and the WebSocket",
        "`command`. The value is coerced to the variable type; for events with a",
        "parameter it is scaled (for example, percent → 0..16383).",
        "",
        "| Key | Event | Parameter | Scale |",
        "| --- | --- | --- | --- |",
    ]
    for variable in writable:
        lines.append(
            "| `{}` | `{}` | {} | {} |".format(
                variable.key,
                variable.sim_event,
                "yes" if variable.sim_event_param else "no",
                variable.sim_event_scale,
            )
        )
    lines += [
        "",
        "## Custom variables `custom.*`",
        "",
        "A profile can declare its own LVAR/RPN in the `variables` block; the key must",
        "start with a lowercase segment (usually `custom.`) and must not collide with",
        "built-in variables. Such a key appears in the frame as an ordinary variable.",
        "",
        f"Allowed kinds: {', '.join(sorted(CUSTOM_KINDS))}; sources: "
        f"{', '.join(sorted(CUSTOM_SOURCES))}. Key format: "
        f"`{CUSTOM_KEY_PATTERN.pattern}`.",
        "",
        "Example:",
        "",
        "```json",
        '{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",',
        '  "name": "APU_BLEED", "initial": false }',
        "```",
        "",
        "Details are in [profile-schema.md](profile-schema.md#6-custom-variables-lvar--rpn).",
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
    """Returns a Markdown catalog of instrument types and their options."""
    unknown = set(WIDGET_TYPES) - set(WIDGET_ORDER)
    if unknown:
        raise RuntimeError(f"docsgen: no description for types {sorted(unknown)}")

    lines: list[str] = [
        "# 🧩 Instrument Catalog",
        "",
        "> This file is generated from `msfs_gateway/profiles.py` (types and required",
        "> bindings) and the web client (options). Update:",
        "> `python -m msfs_gateway.docsgen --write`.",
        "",
        "Each instrument is an element of the profile's `widgets[]` array. The full",
        "profile schema is in [profile-schema.md](profile-schema.md).",
        "",
        "## Common structure",
        "",
        "```json",
        "{",
        '  "id": "attitude-main",',
        '  "type": "attitude",',
        '  "label": "Attitude indicator",',
        '  "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },',
        '  "layout": {',
        '    "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },',
        '    "phone": { "x": 0.03, "y": 0.02, "w": 0.94, "h": 0.3 }',
        "  },",
        '  "options": { "unit": "FT", "decimals": 0 }',
        "}",
        "```",
        "",
        "- `id` — a unique slug (`[a-z0-9][a-z0-9-]`), used in the editor",
        "  and for binding events.",
        "- `layout` — coordinates in panel fractions; `base` is required,",
        f"  {', '.join(f'`{factor}`' for factor in FORM_FACTORS)} are optional.",
        "- `options` — an optional object that depends on the type.",
        "- `command` — required for a toggle switch and a rotary selector (see below).",
        "",
        "## Instrument types",
        "",
        "| Type | Instrument | Required bindings | `command` | Main options |",
        "| --- | --- | --- | --- | --- |",
    ]
    for widget_type in WIDGET_ORDER:
        lines.append(
            "| `{}` | {} | {} | {} | {} |".format(
                widget_type,
                WIDGET_TITLES[widget_type],
                _bindings_text(widget_type),
                "required" if widget_type in COMMAND_TYPES else "—",
                _options_text(widget_type),
            )
        )
    lines += [
        "",
        "`*` next to an option means it is required. The other options have sensible",
        "defaults and are used to configure the appearance.",
        "",
        "## Type descriptions",
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
            lines += ["| Option | Meaning | Required |", "| --- | --- | --- |"]
            for name, description, required in options:
                lines.append(f"| `{name}` | {description} | {'yes' if required else 'no'} |")
            lines.append("")
        lines += [
            "Minimal example:",
            "",
            "```json",
            _example_widget(widget_type),
            "```",
            "",
        ]

    lines += [
        "## Commands from a toggle switch and a rotary selector",
        "",
        "The `command` block describes what to send to the gateway:",
        "",
        "| Field | Meaning |",
        "| --- | --- |",
        '| `key` | a variable with the "commands accepted" flag (see the telemetry catalog) |',
        "| `action` | `set` — send a new value; `toggle` — a toggle event |",
        "| `value` | for `set`: `true/false`/number; by default the opposite "
        "of the current value |",
        "",
        "Toggle switch example:",
        "",
        "```json",
        '{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },',
        '  "command": { "key": "power.batteryMaster", "action": "set" } }',
        "```",
        "",
        "## Validation",
        "",
        "- The type must be in the list above; the editor will not save an unknown type.",
        "- The required `bindings` roles must reference existing telemetry keys.",
        "- `layout.base` and the overrides must be rectangles within `0..1`",
        "  (see the profile schema).",
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
    """Writes the generated documents."""
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / TELEMETRY_DOC).write_text(generate_telemetry_doc(), encoding="utf-8")
    (docs / WIDGETS_DOC).write_text(generate_widgets_doc(), encoding="utf-8")


def check_docs(root: Path) -> list[str]:
    """Returns a list of stale files (empty means everything is up to date)."""
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
    """CLI for generating and checking documentation."""
    from .settings import APP_ROOT

    parser = argparse.ArgumentParser(prog="msfs_gateway.docsgen", description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="write docs/telemetry.md and docs/widgets.md"
    )
    mode.add_argument("--check", action="store_true", help="verify that the files are up to date")
    args = parser.parse_args(argv)

    if args.write:
        write_docs(APP_ROOT)
        print(f"Updated: docs/{TELEMETRY_DOC}, docs/{WIDGETS_DOC}")
        return 0

    stale = check_docs(APP_ROOT)
    if stale:
        print("Documentation is out of date: " + ", ".join(stale), file=sys.stderr)
        print("Run: python -m msfs_gateway.docsgen --write", file=sys.stderr)
        return 1
    print("Documentation is up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
