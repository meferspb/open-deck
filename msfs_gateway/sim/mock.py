"""Mock-провайдер: процедурный «полёт» без MSFS.

Нужен для трёх вещей: разработки клиента без установленного симулятора,
демонстрации на презентации и автотестов. Модель намеренно простая, но
значения меняются непрерывно, поэтому видно, что телеметрия живая.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any

from .. import telemetry
from ..profiles import ProfileStore, custom_variable_specs
from .base import SimCommandError, SimProvider


def _initial_value(spec: dict[str, Any]) -> Any:
    """Стартовое значение пользовательской переменной для демо-режима."""
    raw = spec.get("initial")
    kind = spec.get("kind", "number")
    if kind == "bool":
        return bool(raw)
    if kind == "number":
        try:
            return float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            return 0.0
    return "" if raw is None else str(raw)


class MockSim(SimProvider):
    """Процедурный провайдер для демо и тестов."""

    name = "mock"

    #: Частота внутренней модели; клиенту уходит с частотой шлюза (30 Гц).
    TICK_HZ = 60.0

    def __init__(self, store: ProfileStore) -> None:
        self._store = store
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self._values: dict[str, Any] = telemetry.empty_snapshot()
        self._values.update(
            {
                "power.batteryMaster": False,
                "power.avionicsMaster": False,
                "power.busVolts": 0.0,
                "engine.rpm": 2380.0,
                "engine.fuelFlowGph": 8.4,
                "engine.torquePct": 84.0,
                "engine.ittC": 720.0,
                "engine.propRpm": 1980.0,
                "engine.n1Pct": 91.0,
                "engine.n1Pct2": 90.0,
                "autopilot.master": True,
                "attitude.pitchDeg": 2.5,
                "attitude.bankDeg": -6.0,
                "heading.magneticDeg": 274.0,
                "autopilot.headingBugDeg": 290.0,
                "altitude.indicatedFt": 4520.0,
                "speed.iasKt": 108.0,
                "flaps.percent": 0.0,
                "fuel.leftGal": 17.3,
                "fuel.rightGal": 16.9,
                "fuel.totalGal": 34.2,
            }
        )

        self._profile_id: str | None = None
        self._time = 0.0
        self._last_tick = time.perf_counter()
        #: Ключи пользовательских переменных активного профиля.
        self._custom_keys: set[str] = set()
        self._select_initial_profile()

    # ------------------------------------------------------------------
    # Профиль / борт
    # ------------------------------------------------------------------
    def _select_initial_profile(self) -> None:
        summaries = self._store.list_summaries()
        if summaries:
            # Демо начинаем с «народной» Cessna, а не с первого по алфавиту.
            preferred = next(
                (item for item in summaries if item["id"] == "cessna-172-skyhawk"),
                summaries[0],
            )
            try:
                self.select_aircraft(preferred["id"])
            except Exception:
                self._values["aircraft.title"] = "Demo aircraft"
        else:
            self._values["aircraft.title"] = "Demo aircraft"

    @property
    def profile_id(self) -> str | None:
        return self._profile_id

    @property
    def aircraft_title(self) -> str | None:
        return self._values.get("aircraft.title") or None

    @property
    def atc_model(self) -> str | None:
        return self._values.get("aircraft.atcModel") or None

    def select_aircraft(self, profile_id: str) -> None:
        """Выбирает профиль и стартовые LVAR."""
        profile = self._store.get(profile_id)
        with self._lock:
            # Снимаем переменные прошлого борта, чтобы не тянуть их в кадр.
            for key in self._custom_keys:
                self._values.pop(key, None)
            self._custom_keys = set()

            self._profile_id = profile["id"]
            self._values["aircraft.title"] = profile["name"]
            self._values["aircraft.atcModel"] = profile.get("icao") or ""

            # Пользовательские переменные (LVAR/RPN) в mock не симулируются:
            # берём `initial` из профиля, чтобы панель ожила без MSFS.
            for spec in custom_variable_specs(profile):
                self._values[spec["key"]] = _initial_value(spec)
                self._custom_keys.add(spec["key"])

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Запускает поток модели."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._last_tick = time.perf_counter()
        self._thread = threading.Thread(target=self._loop, name="mock-sim", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает поток модели."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    @property
    def connected(self) -> bool:
        return True

    def read(self) -> dict[str, Any]:
        """Снимок значений."""
        with self._lock:
            return dict(self._values)

    # ------------------------------------------------------------------
    # Команды
    # ------------------------------------------------------------------
    def apply_command(self, key: str, value: Any) -> None:
        """Применяет команду."""
        variable = telemetry.get(key)
        if variable is None or not variable.writable:
            raise SimCommandError(f"Переменная {key!r} не принимает команды")
        target = telemetry.coerce(key, value)
        with self._lock:
            if key == "autopilot.headingBugDeg":
                target = float(target) % 360.0
            self._values[key] = target

    # ------------------------------------------------------------------
    # Модель полёта
    # ------------------------------------------------------------------
    def _loop(self) -> None:
        period = 1.0 / self.TICK_HZ
        deadline = time.perf_counter()
        while not self._stop.is_set():
            now = time.perf_counter()
            dt = min(0.2, max(0.0, now - self._last_tick))
            self._last_tick = now
            self._advance(dt)

            deadline += period
            delay = deadline - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            else:
                deadline = time.perf_counter()

    def _advance(self, dt: float) -> None:
        """Интегрирует простую модель: плавный вираж с набором высоты."""
        if dt <= 0.0:
            return
        with self._lock:
            self._time += dt
            t = self._time
            values = self._values

            bank_target = 14.0 * math.sin(t * 0.11) + 4.0 * math.sin(t * 0.37)
            bank = float(values["attitude.bankDeg"])
            bank += (bank_target - bank) * min(1.0, dt * 2.5)
            values["attitude.bankDeg"] = bank

            pitch_target = 2.5 + 1.4 * math.sin(t * 0.19) + 0.4 * math.sin(t * 0.73)
            pitch = float(values["attitude.pitchDeg"])
            pitch += (pitch_target - pitch) * min(1.0, dt * 3.0)
            values["attitude.pitchDeg"] = pitch

            heading = float(values["heading.magneticDeg"]) + bank * 0.12 * dt
            values["heading.magneticDeg"] = heading % 360.0

            altitude_target = 4520.0 + 45.0 * math.sin(t * 0.05)
            previous_altitude = float(values["altitude.indicatedFt"])
            altitude = previous_altitude + (altitude_target - previous_altitude) * min(
                1.0, dt * 0.15
            )
            values["altitude.indicatedFt"] = altitude
            values["verticalSpeed.fpm"] = (altitude - previous_altitude) / dt * 60.0

            ias_target = 108.0 + 4.0 * math.sin(t * 0.13) - abs(bank) * 0.06
            ias = float(values["speed.iasKt"])
            ias += (ias_target - ias) * min(1.0, dt * 1.5)
            values["speed.iasKt"] = ias

            rpm_target = 2380.0 + 90.0 * math.sin(t * 0.07)
            rpm = float(values["engine.rpm"])
            rpm += (rpm_target - rpm) * min(1.0, dt * 1.2)
            values["engine.rpm"] = rpm

            # Турбовинтовые/реактивные параметры: живут даже на поршневом демо,
            # чтобы панели TBM и A320 выглядели правдоподобно.
            values["engine.torquePct"] = 84.0 + 3.0 * math.sin(t * 0.09)
            values["engine.ittC"] = 720.0 + 12.0 * math.sin(t * 0.05)
            values["engine.propRpm"] = 1980.0 + 25.0 * math.sin(t * 0.06)
            values["engine.n1Pct"] = 91.0 + 1.6 * math.sin(t * 0.08)
            values["engine.n1Pct2"] = 90.0 + 1.4 * math.sin(t * 0.08 + 0.4)

            fuel_flow = 8.4 + 0.35 * math.sin(t * 0.31)
            values["engine.fuelFlowGph"] = fuel_flow

            # Расход топлива: 8.4 GPH на два бака, поэтому стрелки «живут».
            burn = fuel_flow / 3600.0 * dt
            left = max(0.0, float(values["fuel.leftGal"]) - burn / 2.0)
            right = max(0.0, float(values["fuel.rightGal"]) - burn / 2.0)
            values["fuel.leftGal"] = left
            values["fuel.rightGal"] = right
            values["fuel.totalGal"] = left + right

            if values["power.batteryMaster"]:
                values["power.busVolts"] = 24.2 + 0.15 * math.sin(t * 0.9)
            else:
                values["power.busVolts"] = 0.0
