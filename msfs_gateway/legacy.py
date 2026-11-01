"""Адаптер «пиксельного» формата профилей первой итерации (v0).

Формат из ТЗ выглядит так:

    {
      "aircraft_id": "cessna_172_g1000",
      "title": "Cessna 172 Skyhawk",
      "layout": {"target_aspect_ratio": "16:10"},
      "bindings": [
        {"id": "master_battery_switch", "type": "toggle_switch",
         "sim_var": "ELECTRICAL MASTER BATTERY",
         "write_event": "TOGGLE_MASTER_BATTERY",
         "position": {"x": 120, "y": 450, "w": 40, "h": 80}}
      ]
    }

Внутри шлюза профиль живёт в другом виде: координаты — доли панели,
привязки — канонические ключи телеметрии, а связь с SimConnect/LVAR живёт
в адаптере симулятора. Так один профиль работает на трёх форм-факторах и
не зависит от конкретного моста (SimConnect / WASM / mock).

Адаптер нужен для совместимости: старые панели загружаются как есть.
При сохранении через API профиль перезаписывается уже в основном формате.
"""

from __future__ import annotations

import re
from typing import Any, Final

from . import telemetry
from .profiles import ProfileError

#: Соответствие «человеческих» типов из ТЗ внутренним типам приборов.
TYPE_ALIASES: Final[dict[str, str]] = {
    "toggle_switch": "switch.toggle",
    "switch": "switch.toggle",
    "switches": "switch.toggle",
    "canvas_gauge_attitude": "attitude",
    "attitude_indicator": "attitude",
    "gauge_attitude": "attitude",
    "canvas_gauge_radial": "gauge.radial",
    "radial_gauge": "gauge.radial",
    "gauge": "gauge.radial",
    "digital_readout": "readout",
    "readout": "readout",
    "annunciator": "annunciator",
    "lamp": "annunciator",
    "knob": "knob.rotary",
    "rotary_knob": "knob.rotary",
}

DEFAULT_CANVAS_WIDTH: Final = 1280
DEFAULT_CANVAS_HEIGHT: Final = 800
COLOR_PATTERN: Final = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def looks_legacy(profile: Any) -> bool:
    """Профиль в старом формате: список bindings вместо widgets."""
    return isinstance(profile, dict) and (
        isinstance(profile.get("bindings"), list) or "aircraft_id" in profile
    )


def _slug(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        return fallback
    if not text[0].isalnum():
        text = f"w-{text}"
    return text[:64]


def _reverse_maps() -> tuple[dict[str, str], dict[str, str]]:
    by_var: dict[str, str] = {}
    by_event: dict[str, str] = {}
    for key, variable in telemetry.VARIABLES.items():
        if variable.sim_var:
            by_var[variable.sim_var.upper()] = key
        if variable.sim_event:
            by_event[variable.sim_event.upper()] = key
    return by_var, by_event


def _map_variable(name: Any, by_var: dict[str, str], where: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ProfileError(f"{where}: не указана переменная SimConnect")
    key = by_var.get(name.strip().upper())
    if key is None:
        raise ProfileError(
            f"{where}: переменная {name!r} не зарегистрирована в msfs_gateway/telemetry.py"
        )
    return key


def _canvas(profile: dict[str, Any]) -> tuple[float, float]:
    layout = profile.get("layout")
    if isinstance(layout, dict):
        canvas = layout.get("canvas")
        if isinstance(canvas, dict):
            width, height = canvas.get("width"), canvas.get("height")
            if all(isinstance(v, (int, float)) and v > 0 for v in (width, height)):
                return float(width), float(height)

        ratio = layout.get("target_aspect_ratio")
        if isinstance(ratio, str) and ":" in ratio:
            try:
                left, right = ratio.split(":", 1)
                value = float(left) / float(right)
                if value > 0:
                    return float(DEFAULT_CANVAS_WIDTH), float(DEFAULT_CANVAS_WIDTH) / value
            except (ValueError, ZeroDivisionError):
                pass

    return float(DEFAULT_CANVAS_WIDTH), float(DEFAULT_CANVAS_HEIGHT)


def _rect(position: Any, width: float, height: float, where: str) -> dict[str, float]:
    if not isinstance(position, dict):
        raise ProfileError(f"{where}.position: ожидался объект {{x, y, w, h}}")

    values: dict[str, float] = {}
    for name in ("x", "y", "w", "h"):
        raw = position.get(name)
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            raise ProfileError(f"{where}.position.{name}: ожидалось число пикселей")
        values[name] = float(raw)

    if values["w"] <= 0 or values["h"] <= 0:
        raise ProfileError(f"{where}.position: ширина и высота должны быть больше нуля")

    x = min(1.0, max(0.0, values["x"] / width))
    y = min(1.0, max(0.0, values["y"] / height))
    w = min(1.0 - x, values["w"] / width)
    h = min(1.0 - y, values["h"] / height)
    if w <= 0 or h <= 0:
        raise ProfileError(f"{where}.position: прибор выходит за пределы панели")
    return {"x": round(x, 5), "y": round(y, 5), "w": round(w, 5), "h": round(h, 5)}


def _attitude_bindings(
    binding: dict[str, Any], by_var: dict[str, str], where: str
) -> dict[str, str]:
    sim_vars = binding.get("sim_vars")
    sim_vars = sim_vars if isinstance(sim_vars, dict) else {}
    pitch = sim_vars.get("pitch") or binding.get("sim_var_pitch")
    bank = sim_vars.get("bank") or binding.get("sim_var_bank")
    if pitch is None or bank is None:
        raise ProfileError(f"{where}: для авиагоризонта нужны pitch и bank")
    return {
        "pitch": _map_variable(pitch, by_var, f"{where}.pitch"),
        "bank": _map_variable(bank, by_var, f"{where}.bank"),
    }


def _value_binding(
    binding: dict[str, Any], by_var: dict[str, str], where: str, role: str = "value"
) -> dict[str, str]:
    sim_vars = binding.get("sim_vars")
    sim_vars = sim_vars if isinstance(sim_vars, dict) else {}
    name = binding.get("sim_var") or sim_vars.get(role)
    return {role: _map_variable(name, by_var, where)}


def _switch_widget(
    binding: dict[str, Any],
    by_var: dict[str, str],
    by_event: dict[str, str],
    where: str,
) -> tuple[dict[str, str], dict[str, str]]:
    bindings = _value_binding(binding, by_var, where, role="state")
    event = binding.get("write_event")
    key = by_event.get(str(event).strip().upper()) if isinstance(event, str) else None
    if key is None:
        # Если событие не указано, но переменная сама записываемая — используем её.
        candidate = bindings["state"]
        key = candidate if telemetry.is_writable(candidate) else None
    if key is None:
        raise ProfileError(f"{where}: не удалось определить команду записи (write_event={event!r})")
    return bindings, {"key": key, "action": "set"}


def _options_for(binding: dict[str, Any], widget_type: str) -> dict[str, Any]:
    options = dict(binding.get("options") or {}) if isinstance(binding.get("options"), dict) else {}
    if isinstance(binding.get("label"), str) and binding["label"]:
        options.setdefault("caption", binding["label"])

    for name in ("min", "max", "step", "redline", "unit", "decimals", "wrap"):
        if name in binding:
            options.setdefault(name, binding[name])

    if widget_type == "gauge.radial":
        options.setdefault("min", 0)
        options.setdefault("max", 100)
    elif widget_type == "knob.rotary":
        options.setdefault("min", 0)
        options.setdefault("max", 359)
        options.setdefault("wrap", True)
        options.setdefault("step", 1)
    elif widget_type == "annunciator":
        options.setdefault("tone", "danger")
        options.setdefault("invert", bool(binding.get("invert", False)))

    return options


def adapt(profile: dict[str, Any]) -> dict[str, Any]:
    """Преобразует профиль v0 во внутренний формат."""
    bindings = profile.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ProfileError("bindings: ожидался непустой массив")

    canvas_width, canvas_height = _canvas(profile)
    by_var, by_event = _reverse_maps()

    widgets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, binding in enumerate(bindings):
        where = f"bindings[{index}]"
        if not isinstance(binding, dict):
            raise ProfileError(f"{where}: ожидался объект")

        raw_type = str(binding.get("type", "")).strip().lower()
        widget_type = TYPE_ALIASES.get(raw_type)
        if widget_type is None:
            supported = ", ".join(sorted(set(TYPE_ALIASES)))
            raise ProfileError(f"{where}.type: тип {raw_type!r} не поддержан ({supported})")

        widget_id = _slug(binding.get("id") or f"widget-{index}", f"widget-{index}")
        if widget_id in seen:
            widget_id = f"{widget_id}-{index}"
        seen.add(widget_id)

        widget: dict[str, Any] = {
            "id": widget_id,
            "type": widget_type,
            "label": str(binding.get("label") or binding.get("id") or widget_id),
            "layout": {"base": _rect(binding.get("position"), canvas_width, canvas_height, where)},
            "options": _options_for(binding, widget_type),
        }

        if widget_type == "attitude":
            widget["bindings"] = _attitude_bindings(binding, by_var, where)
        elif widget_type == "switch.toggle":
            widget["bindings"], widget["command"] = _switch_widget(binding, by_var, by_event, where)
        elif widget_type == "annunciator":
            widget["bindings"] = _value_binding(binding, by_var, where, role="active")
        else:
            widget["bindings"] = _value_binding(binding, by_var, where)

        widgets.append(widget)

    layout = profile.get("layout") if isinstance(profile.get("layout"), dict) else {}
    background = profile.get("background") or layout.get("background_color") or "#0b1117"
    if not isinstance(background, str) or not COLOR_PATTERN.match(background):
        background = "#0b1117"

    title = str(profile.get("title") or profile.get("name") or "Legacy aircraft").strip()
    adapted: dict[str, Any] = {
        "schemaVersion": 1,
        "id": _slug(profile.get("aircraft_id") or profile.get("id"), "legacy-aircraft"),
        "name": title or "Legacy aircraft",
        "revision": 1,
        "description": "Импортировано из формата v0 (пиксельные координаты).",
        "panel": {"background": background},
        "widgets": widgets,
        "meta": {
            "sourceFormat": "legacy-v0",
            "version": profile.get("version"),
            "canvas": {"width": canvas_width, "height": canvas_height},
        },
    }
    if title:
        adapted["sim"] = {"match": {"title": f"*{title}*"}}
    return adapted


def adapt_if_needed(profile: Any) -> Any:
    return adapt(profile) if looks_legacy(profile) else profile
