"""Ассистент посадки и руления.

Два независимых контура поверх телеметрии MSFS:

* **Руление** — удерживает заданную путевую скорость (3–25 уз) и курс:
  тяга и руль направления считаются простыми ПИ/П-регуляторами. Пилот
  задаёт курс кнопками «левее/правее» и скорость ползунком, «СТОП» даёт
  тягу 0 и стояночный тормоз.
* **Посадка** — включает автопилот и режим APR, следит за радио altitude:
  на 60–15 футах плавно убирает тягу, на касании выключает AP и даёт
  тягу 0. Полное управление рулями высоты не выполняется: заход и
  выравнивание остаются за автопилотом/пилотом.

Оба контура — *ассистенты*, а не автопилот сертифицированного уровня.
Пилот обязан контролировать полёт и может выключить ассистент в любой
момент. Все внешние команды проходят через `Hub.apply_assist_command`,
поэтому валидация переменных и ошибки SimConnect остаются в одном месте.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

LOGGER = logging.getLogger("msfs_gateway.assist")

CommandSink = Callable[[str, Any], bool]

#: Границы задания скорости руления.
TAXI_SPEED_MIN_KT = 3.0
TAXI_SPEED_MAX_KT = 25.0
#: Выше этой скорости ассистент руления выключается (страховка).
TAXI_HARD_LIMIT_KT = 35.0
#: Высота начала выравнивания и полного сброса тяги, футы.
FLARE_START_FT = 60.0
FLARE_IDLE_FT = 15.0
#: Минимальная приборная скорость для включения ассистента посадки.
LANDING_MIN_IAS_KT = 40.0


def clamp(value: float, low: float, high: float) -> float:
    """Ограничивает значение диапазоном."""
    return max(low, min(high, value))


def wrap180(degrees: float) -> float:
    """Приводит угол к диапазону (-180, 180]."""
    return (float(degrees) + 180.0) % 360.0 - 180.0


def _optional_number(values: dict[str, Any], key: str) -> float | None:
    """Число или None, если значение отсутствует/некорректно.

    Для ассистента важно отличать «ноль» от «данных нет»: подстановка 0.0
    при пропаже радиоaltitude могла бы преждевременно убрать тягу.
    """
    raw = values.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    if math.isnan(raw) or math.isinf(raw):
        return None
    return float(raw)


def _optional_flag(values: dict[str, Any], key: str) -> bool | None:
    """Булево значение или None, если телеметрия его не дала."""
    if key not in values:
        return None
    raw = values[key]
    return None if raw is None else bool(raw)


def _rounded(values: dict[str, Any], key: str, digits: int) -> float | None:
    value = _optional_number(values, key)
    return None if value is None else round(value, digits)


def _flag(values: dict[str, Any], key: str) -> bool:
    return bool(values.get(key))


@dataclass
class TaxiStatus:
    """Состояние ассистента руления."""

    engaged: bool = False
    target_speed_kt: float = 12.0
    target_heading_deg: float = 0.0
    throttle_pct: float = 0.0
    rudder_pct: float = 0.0
    message: str = ""


class TaxiAssist:
    """Удержание скорости и курса на рулении."""

    def __init__(self, send: CommandSink) -> None:
        self._send = send
        self.status = TaxiStatus()
        self._integral = 0.0
        self._last_throttle = -1000.0
        self._last_rudder = -1000.0

    # --- управление ---------------------------------------------------
    def engage(self, values: dict[str, Any]) -> tuple[bool, str]:
        """Включает ассистент руления с проверками безопасности."""
        on_ground = _optional_flag(values, "aircraft.onGround")
        if on_ground is None:
            return False, "Нет данных о положении самолёта — руление недоступно"
        if not on_ground:
            return False, "Самолёт не на земле — руление недоступно"
        parking = _optional_flag(values, "brakes.parking")
        if parking is None:
            return False, "Нет данных о стояночном тормозе — руление недоступно"
        if parking:
            return False, "Снимите стояночный тормоз"
        heading_value = _optional_number(values, "heading.magneticDeg")
        if heading_value is None:
            return False, "Нет данных о курсе — руление недоступно"
        heading = heading_value
        self.status = TaxiStatus(
            engaged=True,
            target_speed_kt=self.status.target_speed_kt,
            target_heading_deg=heading % 360.0,
        )
        self._integral = 0.0
        self._last_throttle = -1000.0
        self._last_rudder = -1000.0
        return True, "Ассистент руления включён"

    def disengage(self, reason: str = "Ассистент руления выключен") -> None:
        """Выключает ассистент и обнуляет тягу/руль."""
        if self.status.engaged:
            self._send("controls.throttlePct", 0)
            self._send("controls.rudder", 0)
        self.status.engaged = False
        self.status.throttle_pct = 0.0
        self.status.rudder_pct = 0.0
        self.status.message = reason

    def set_speed(self, value: Any) -> tuple[bool, str]:
        """Задаёт скорость руления в допустимых пределах."""
        try:
            speed = float(value)
        except (TypeError, ValueError):
            return False, "Скорость должна быть числом"
        if not math.isfinite(speed):
            return False, "Скорость должна быть числом"
        self.status.target_speed_kt = clamp(speed, TAXI_SPEED_MIN_KT, TAXI_SPEED_MAX_KT)
        return True, f"Скорость руления: {self.status.target_speed_kt:.0f} уз"

    def nudge_heading(self, delta: float) -> tuple[bool, str]:
        """Поворачивает заданный курс на delta градусов."""
        self.status.target_heading_deg = (self.status.target_heading_deg + delta) % 360.0
        return True, f"Курс: {self.status.target_heading_deg:.0f}°"

    def stop(self) -> tuple[bool, str]:
        """Останавливает поток ассистента."""
        sent = self._send("controls.throttlePct", 0)
        sent = self._send("controls.rudder", 0) and sent
        sent = self._send("brakes.parking", True) and sent
        self.status.engaged = False
        self.status.throttle_pct = 0.0
        self.status.rudder_pct = 0.0
        self.status.message = (
            "СТОП: тяга 0, стояночный тормоз"
            if sent
            else "СТОП: команды не отправлены (нет связи с MSFS)"
        )
        return sent, self.status.message

    # --- контур -------------------------------------------------------
    def update(self, dt: float, values: dict[str, Any]) -> None:
        """Один шаг контура по свежей телеметрии."""
        if not self.status.engaged:
            return
        if dt <= 0:
            return
        reason = self._safety(values)
        if reason:
            self.disengage(reason)
            return

        ground_speed = _optional_number(values, "groundSpeed.kt")
        heading = _optional_number(values, "heading.magneticDeg")
        if ground_speed is None or heading is None:
            self.disengage("Нет данных телеметрии — руление выключено")
            return
        error = self.status.target_speed_kt - ground_speed

        # ПИ по скорости: I ограничен, чтобы тяга не «накапливалась» на стоянке.
        self._integral = clamp(self._integral + error * dt * 0.8, 0.0, 22.0)
        throttle = 9.0 + 1.7 * error + self._integral
        if error < -3.0:
            throttle = 0.0
        throttle = clamp(throttle, 0.0, 55.0)

        heading_error = wrap180(self.status.target_heading_deg - heading)
        rudder = clamp(heading_error * 1.6, -70.0, 70.0)

        self.status.throttle_pct = round(throttle, 1)
        self.status.rudder_pct = round(rudder, 1)
        self._emit(throttle, rudder)

    def _safety(self, values: dict[str, Any]) -> str | None:
        on_ground = _optional_flag(values, "aircraft.onGround")
        if on_ground is None:
            return "Нет данных о положении самолёта — руление выключено"
        if not on_ground:
            return "Самолёт оторвался от земли — руление выключено"
        parking = _optional_flag(values, "brakes.parking")
        if parking is None:
            return "Нет данных о стояночном тормозе — руление выключено"
        if parking:
            return "Включён стояночный тормоз — руление выключено"
        speed = _optional_number(values, "groundSpeed.kt")
        if speed is None:
            return "Нет данных о путевой скорости — руление выключено"
        if speed > TAXI_HARD_LIMIT_KT:
            return "Скорость выше 35 уз — руление выключено"
        if _optional_number(values, "heading.magneticDeg") is None:
            return "Нет данных о курсе — руление выключено"
        return None

    def _emit(self, throttle: float, rudder: float) -> None:
        if abs(throttle - self._last_throttle) >= 0.6:
            self._send("controls.throttlePct", round(throttle, 1))
            self._last_throttle = throttle
        if abs(rudder - self._last_rudder) >= 2.0:
            self._send("controls.rudder", round(rudder, 1))
            self._last_rudder = rudder


@dataclass
class LandingStatus:
    """Состояние ассистента посадки."""

    phase: str = "off"  # off | armed | approach | flare | rollout | done | toga
    message: str = ""
    throttle_pct: float = 0.0

    @property
    def active(self) -> bool:
        """Активен ли контур."""
        return self.phase in {"armed", "approach", "flare", "rollout"}


class LandingAssist:
    """Заход по ILS и сброс тяги на выравнивании."""

    def __init__(self, send: CommandSink) -> None:
        self._send = send
        self.status = LandingStatus()
        self._last_throttle = -1000.0

    @property
    def active(self) -> bool:
        """Активен ли контур."""
        return self.status.phase in {"armed", "approach", "flare", "rollout"}

    def arm(self, values: dict[str, Any]) -> tuple[bool, str]:
        """Включает AP и APR с проверкой условий захода."""
        on_ground = _optional_flag(values, "aircraft.onGround")
        if on_ground is None:
            return False, "Нет данных о положении самолёта — заход не включён"
        if on_ground:
            return False, "Самолёт уже на земле"
        speed = _optional_number(values, "speed.iasKt")
        if speed is None:
            return False, "Нет данных о приборной скорости — заход не включён"
        if speed < LANDING_MIN_IAS_KT:
            return False, "Скорость ниже 40 уз — заход не включён"
        self._last_throttle = -1000.0
        if not self._send("autopilot.master", True):
            self.status.phase = "off"
            self.status.message = "Не удалось включить автопилот (нет связи с MSFS)"
            return False, self.status.message
        if not self._send("autopilot.approachHold", True):
            # Не оставляем AP включённым, если APR включить не удалось.
            self._send("autopilot.master", False)
            self.status.phase = "off"
            self.status.message = "Не удалось включить режим APR (нет связи с MSFS)"
            return False, self.status.message
        self.status.phase = "armed"
        self.status.message = "Заход: AP и APR включены"
        return True, self.status.message

    def disarm(self, reason: str = "Ассистент посадки выключен") -> tuple[bool, str]:
        """Выключает ассистент посадки."""
        self.status.phase = "off"
        self.status.message = reason
        return True, reason

    def toga(self) -> tuple[bool, str]:
        """Уход на второй круг: полная тяга, AP выключен."""
        self._send("autopilot.master", False)
        self._send("autopilot.approachHold", False)
        sent = self._send("controls.throttlePct", 100)
        self.status.phase = "toga"
        self.status.throttle_pct = 100.0 if sent else 0.0
        self.status.message = (
            "TOGA: полная тяга, автопилот выключен"
            if sent
            else "TOGA: тяга не отправлена (нет связи с MSFS)"
        )
        return sent, self.status.message

    def update(self, dt: float, values: dict[str, Any]) -> None:
        """Один шаг контура по свежей телеметрии."""
        if not self.active:
            return
        if dt <= 0:
            return

        on_ground = _optional_flag(values, "aircraft.onGround")
        radio_alt = _optional_number(values, "aircraft.radioAltitudeFt")
        ias = _optional_number(values, "speed.iasKt")
        ground_speed = _optional_number(values, "groundSpeed.kt")

        if self.status.phase in {"armed", "approach", "flare"} and on_ground is True:
            self.status.phase = "rollout"
            self.status.message = "Касание: тяга 0, автопилот выключен"
            self._send("autopilot.master", False)
            self._send("autopilot.approachHold", False)
            self._set_throttle(0.0)

        if self.status.phase == "rollout":
            self._set_throttle(0.0)
            if on_ground is True and ground_speed is not None and ground_speed < 5.0:
                self.status.phase = "done"
                self.status.message = "Пробег завершён, ассистент выключен"
            return

        if on_ground is False and ias is not None and ias < LANDING_MIN_IAS_KT:
            self.status.phase = "off"
            self.status.message = "Скорость ниже 40 уз — ассистент посадки выключен"
            return

        if self.status.phase == "armed" and _flag(values, "autopilot.approach"):
            self.status.phase = "approach"
            self.status.message = "APR захвачен, следим за глиссадой"

        if (
            self.status.phase == "approach"
            and radio_alt is not None
            and radio_alt <= FLARE_START_FT
        ):
            self.status.phase = "flare"
            self.status.message = "Выравнивание: убираем тягу"

        if self.status.phase == "flare":
            if radio_alt is None:
                # Не подставляем 0.0: иначе пропавшая телеметрия выглядела бы
                # как касание и ассистент убрал бы тягу в воздухе.
                self.status.message = "Нет данных о высоте — выравнивание приостановлено"
                return
            span = FLARE_START_FT - FLARE_IDLE_FT
            ratio = clamp((radio_alt - FLARE_IDLE_FT) / span, 0.0, 1.0)
            self._set_throttle(round(45.0 * ratio, 1))

    def _set_throttle(self, value: float) -> None:
        self.status.throttle_pct = value
        if abs(value - self._last_throttle) >= 0.6:
            self._send("controls.throttlePct", value)
            self._last_throttle = value


@dataclass
class AssistSnapshot:
    """Последние значения телеметрии и состояния контуров."""

    values: dict[str, Any] = field(default_factory=dict)
    updated_at: float = 0.0


class AssistManager:
    """Поток 10 Гц: обновляет контуры и отдаёт статус по HTTP."""

    def __init__(self, hub: Any, *, hz: float = 10.0) -> None:
        self._hub = hub
        self._hz = max(1.0, hz)
        self._send = self._command
        self.taxi = TaxiAssist(self._send)
        self.landing = LandingAssist(self._send)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot = AssistSnapshot()

    # --- жизнь --------------------------------------------------------
    def start(self) -> None:
        """Запускает поток ассистента."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="assist", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает поток ассистента."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=5.0)
            if thread.is_alive():
                LOGGER.warning("Поток ассистента не завершился за 5 с")

    def _command(self, key: str, value: Any) -> bool:
        try:
            self._hub.apply_assist_command(key, value)
            return True
        except Exception as exc:
            LOGGER.debug("Команда ассистента %s=%r отклонена: %s", key, value, exc)
            return False

    def _loop(self) -> None:
        period = 1.0 / self._hz
        last = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            dt = min(0.5, max(0.0, now - last))
            last = now
            try:
                values = self._hub.sim.read()
            except Exception as exc:
                LOGGER.debug("Телеметрия для ассистента недоступна: %s", exc)
                values = {}
            connected = bool(getattr(self._hub.sim, "connected", True))
            with self._lock:
                self._snapshot = AssistSnapshot(values=values, updated_at=now)
                if connected:
                    self.taxi.update(dt, values)
                    self.landing.update(dt, values)
                else:
                    # Без живой связи не продолжаем выдавать уставки:
                    # последние значения могли устареть.
                    if self.taxi.status.engaged:
                        self.taxi.disengage("Нет связи с MSFS — руление выключено")
                    if self.landing.active:
                        self.landing.disarm("Нет связи с MSFS — ассистент посадки выключен")
            self._stop.wait(period)

    # --- действия -----------------------------------------------------
    def taxi_action(self, payload: dict[str, Any]) -> tuple[bool, str]:
        """Выполняет действие API для руления."""
        action = str(payload.get("action") or "").strip().lower()
        with self._lock:
            if action == "engage":
                return self.taxi.engage(self._snapshot.values)
            if action == "disengage":
                self.taxi.disengage()
                return True, "Ассистент руления выключен"
            if action == "stop":
                return self.taxi.stop()
            if action == "speed":
                return self.taxi.set_speed(payload.get("value"))
            if action == "heading":
                if "delta" in payload:
                    try:
                        delta = float(payload["delta"])
                    except (TypeError, ValueError):
                        return False, "delta должен быть числом"
                    return self.taxi.nudge_heading(delta)
                return False, "Нужен параметр delta"
        return False, f"Неизвестное действие: {action or '—'}"

    def landing_action(self, payload: dict[str, Any]) -> tuple[bool, str]:
        """Выполняет действие API для посадки."""
        action = str(payload.get("action") or "").strip().lower()
        with self._lock:
            if action == "arm":
                return self.landing.arm(self._snapshot.values)
            if action == "disarm":
                return self.landing.disarm()
            if action == "toga":
                return self.landing.toga()
        return False, f"Неизвестное действие: {action or '—'}"

    def status(self) -> dict[str, Any]:
        """Сериализуемое состояние ассистента для API."""
        with self._lock:
            values = dict(self._snapshot.values)
            taxi = self.taxi.status
            landing = self.landing.status
            return {
                "telemetry": {
                    "onGround": _optional_flag(values, "aircraft.onGround"),
                    "radioAltitudeFt": _rounded(values, "aircraft.radioAltitudeFt", 1),
                    "groundSpeedKt": _rounded(values, "groundSpeed.kt", 1),
                    "iasKt": _rounded(values, "speed.iasKt", 1),
                    "verticalSpeedFpm": _rounded(values, "verticalSpeed.fpm", 0),
                    "headingDeg": _rounded(values, "heading.magneticDeg", 1),
                    "localizerDeg": _rounded(values, "nav.localizer", 3),
                    "glideSlopeDeg": _rounded(values, "nav.glideSlope", 3),
                    "locValid": _optional_flag(values, "nav.locFlag"),
                    "gsValid": _optional_flag(values, "nav.gsFlag"),
                    "autopilotMaster": _optional_flag(values, "autopilot.master"),
                    "approach": _optional_flag(values, "autopilot.approach"),
                    "throttlePct": _rounded(values, "controls.throttlePct", 1),
                    "rudderPct": _rounded(values, "controls.rudder", 1),
                    "parkingBrake": _optional_flag(values, "brakes.parking"),
                },
                "taxi": {
                    "engaged": taxi.engaged,
                    "targetSpeedKt": round(taxi.target_speed_kt, 1),
                    "targetHeadingDeg": round(taxi.target_heading_deg, 1),
                    "throttlePct": taxi.throttle_pct,
                    "rudderPct": taxi.rudder_pct,
                    "message": taxi.message,
                },
                "landing": {
                    "phase": landing.phase,
                    "message": landing.message,
                    "throttlePct": landing.throttle_pct,
                    "active": landing.active,
                },
                "limits": {
                    "taxiSpeedMinKt": TAXI_SPEED_MIN_KT,
                    "taxiSpeedMaxKt": TAXI_SPEED_MAX_KT,
                    "flareStartFt": FLARE_START_FT,
                    "flareIdleFt": FLARE_IDLE_FT,
                },
            }
