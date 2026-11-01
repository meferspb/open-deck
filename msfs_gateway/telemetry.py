"""Каноническая модель телеметрии.

Единственный источник правды о переменных: имена, типы, единицы и то, как
они читаются из MSFS (SimConnect) и как меняются командами клиентов.
Профили панелей ссылаются только на эти ключи, поэтому переименование
переменной — правка в одном месте, а не по всему проекту.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal

ValueKind = Literal["bool", "number", "string"]
CommandAction = Literal["set", "toggle"]


@dataclass(frozen=True, slots=True)
class Variable:
    """Описание одной величины телеметрии."""

    key: str
    kind: ValueKind
    label: str
    unit: str = ""
    # Сторона SimConnect: как прочитать значение.
    sim_var: str | None = None
    sim_unit: str | None = None
    # Сторона SimConnect: каким событием (K-event) менять значение.
    sim_event: str | None = None
    #: Событие принимает числовой параметр (например, HEADING_BUG_SET).
    sim_event_param: bool = False

    @property
    def writable(self) -> bool:
        return self.sim_event is not None


_VARIABLES: Final[tuple[Variable, ...]] = (
    # --- Электрика -------------------------------------------------------
    Variable(
        "power.batteryMaster",
        "bool",
        "Master battery",
        sim_var="ELECTRICAL MASTER BATTERY",
        sim_unit="bool",
        sim_event="TOGGLE_MASTER_BATTERY",
    ),
    Variable(
        "power.avionicsMaster",
        "bool",
        "Avionics master",
        sim_var="AVIONICS MASTER SWITCH",
        sim_unit="bool",
        sim_event="TOGGLE_AVIONICS_MASTER",
    ),
    Variable(
        "power.busVolts",
        "number",
        "Main bus voltage",
        unit="V",
        sim_var="ELECTRICAL MAIN BUS VOLTAGE",
        sim_unit="volts",
    ),
    # --- Силовая установка ----------------------------------------------
    Variable(
        "engine.rpm",
        "number",
        "Engine RPM",
        unit="RPM",
        sim_var="GENERAL ENG RPM:1",
        sim_unit="rpm",
    ),
    Variable(
        "engine.fuelFlowGph",
        "number",
        "Fuel flow",
        unit="GPH",
        sim_var="ENG FUEL FLOW GPH:1",
        sim_unit="gallons per hour",
    ),
    # --- Турбовинтовые / реактивные --------------------------------------
    Variable(
        "engine.torquePct",
        "number",
        "Engine torque",
        unit="%",
        sim_var="TURB ENG MAX INDICATED TORQUE:1",
        sim_unit="percent",
    ),
    Variable(
        "engine.ittC",
        "number",
        "Interstage turbine temperature",
        unit="°C",
        sim_var="TURB ENG ITT:1",
        sim_unit="celsius",
    ),
    Variable(
        "engine.propRpm",
        "number",
        "Propeller RPM",
        unit="RPM",
        sim_var="PROP RPM:1",
        sim_unit="rpm",
    ),
    Variable(
        "engine.n1Pct",
        "number",
        "N1 (engine 1)",
        unit="%",
        sim_var="TURB ENG N1:1",
        sim_unit="percent",
    ),
    Variable(
        "engine.n1Pct2",
        "number",
        "N1 (engine 2)",
        unit="%",
        sim_var="TURB ENG N1:2",
        sim_unit="percent",
    ),
    # --- Пространственное положение -------------------------------------
    Variable(
        "attitude.pitchDeg",
        "number",
        "Pitch",
        unit="°",
        sim_var="PLANE PITCH DEGREES",
        sim_unit="degrees",
    ),
    Variable(
        "attitude.bankDeg",
        "number",
        "Bank",
        unit="°",
        sim_var="PLANE BANK DEGREES",
        sim_unit="degrees",
    ),
    Variable(
        "heading.magneticDeg",
        "number",
        "Magnetic heading",
        unit="°",
        sim_var="PLANE HEADING DEGREES MAGNETIC",
        sim_unit="degrees",
    ),
    Variable(
        "altitude.indicatedFt",
        "number",
        "Indicated altitude",
        unit="FT",
        sim_var="INDICATED ALTITUDE",
        sim_unit="feet",
    ),
    Variable(
        "verticalSpeed.fpm",
        "number",
        "Vertical speed",
        unit="FPM",
        sim_var="VERTICAL SPEED",
        sim_unit="feet per minute",
    ),
    Variable(
        "speed.iasKt",
        "number",
        "Indicated airspeed",
        unit="KT",
        sim_var="AIRSPEED INDICATED",
        sim_unit="knots",
    ),
    Variable(
        "autopilot.headingBugDeg",
        "number",
        "Heading bug",
        unit="°",
        sim_var="AUTOPILOT HEADING LOCK DIR",
        sim_unit="degrees",
        sim_event="HEADING_BUG_SET",
        sim_event_param=True,
    ),
    Variable(
        "autopilot.master",
        "bool",
        "Autopilot master",
        sim_var="AUTOPILOT MASTER",
        sim_unit="bool",
        sim_event="AP_MASTER",
    ),
    # --- Механизация и топливо ------------------------------------------
    Variable(
        "flaps.percent",
        "number",
        "Flaps position",
        unit="%",
        sim_var="TRAILING EDGE FLAPS LEFT PERCENT",
        sim_unit="percent",
    ),
    Variable(
        "fuel.leftGal",
        "number",
        "Left tank",
        unit="GAL",
        sim_var="FUEL LEFT QUANTITY",
        sim_unit="gallons",
    ),
    Variable(
        "fuel.rightGal",
        "number",
        "Right tank",
        unit="GAL",
        sim_var="FUEL RIGHT QUANTITY",
        sim_unit="gallons",
    ),
    # Сумма баков: в SimConnect такого датума нет, провайдеры считают её сами.
    Variable("fuel.totalGal", "number", "Total fuel", unit="GAL"),
    # --- Служебное -------------------------------------------------------
    Variable("aircraft.title", "string", "Aircraft title", sim_var="TITLE", sim_unit=""),
)

VARIABLES: Final[dict[str, Variable]] = {item.key: item for item in _VARIABLES}


def get(key: str) -> Variable | None:
    return VARIABLES.get(key)


def is_known(key: str) -> bool:
    return key in VARIABLES


def is_writable(key: str) -> bool:
    variable = VARIABLES.get(key)
    return bool(variable and variable.writable)


def default_value(key: str) -> Any:
    """Значение-заглушка, пока от симулятора не пришло реальное."""
    variable = VARIABLES.get(key)
    if variable is None:
        return None
    if variable.kind == "bool":
        return False
    if variable.kind == "number":
        return 0.0
    return ""


def coerce(key: str, raw: Any) -> Any:
    """Приводит произвольное значение к типу переменной.

    Используется и для команд от клиента, и для данных из SimConnect,
    где логические величины приходят числами 0/1.
    """
    variable = VARIABLES.get(key)
    if variable is None:
        raise ValueError(f"Неизвестная переменная телеметрии: {key!r}")

    if variable.kind == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return raw != 0
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"1", "true", "on", "yes"}:
                return True
            if normalized in {"0", "false", "off", "no"}:
                return False
        raise ValueError(f"{key}: ожидалось логическое значение, получено {raw!r}")

    if variable.kind == "number":
        if isinstance(raw, bool):
            return float(raw)
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key}: ожидалось число, получено {raw!r}") from exc

    if raw is None:
        return ""
    return str(raw)


def empty_snapshot() -> dict[str, Any]:
    """Заглушка «все переменные известны, данных нет»."""
    return {key: default_value(key) for key in VARIABLES}


def variables_catalog() -> list[dict[str, Any]]:
    """Каталог переменных для редактора панелей и нативных клиентов.

    Возвращает список (а не словарь), чтобы порядок объявления был стабилен.
    """
    catalog: list[dict[str, Any]] = []
    for variable in _VARIABLES:
        catalog.append(
            {
                "key": variable.key,
                "label": variable.label,
                "kind": variable.kind,
                "unit": variable.unit,
                "writable": variable.writable,
                "simVar": variable.sim_var,
                "simEvent": variable.sim_event,
            }
        )
    return catalog
