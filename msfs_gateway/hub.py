"""Шина телеметрии: подключение клиентов, рассылка состояния, приём команд.

Один поток-«тикер» собирает снимок состояния у провайдера и рассылает его
всем WebSocket-клиентам. Запись в сокеты сериализуется блокировкой, поэтому
рассылка не мешает обработке входящих сообщений в потоках HTTP-сервера.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final

from . import __version__, telemetry
from .profiles import ProfileStore, custom_variable_specs
from .sim.base import SimCommandError, SimProvider
from .websocket import WebSocketConnection, WebSocketError

#: Не больше стольких команд в секунду от одного клиента: тумблер не должен
#: превращаться в генератор событий при залипании касания.
COMMANDS_PER_SECOND: Final = 30

#: Пользовательские переменные (LVAR/RPN) опрашиваются не каждый тик:
#: обращение к WASM дороже, чем чтение кэша провайдера.
CUSTOM_REFRESH_SECONDS: Final = 0.25


@dataclass(slots=True)
class ClientInfo:
    connection: WebSocketConnection
    client_id: str
    user_agent: str = ""
    connected_at: float = field(default_factory=time.monotonic)
    command_times: deque[float] = field(
        default_factory=lambda: deque(maxlen=COMMANDS_PER_SECOND * 2)
    )
    commands_total: int = 0


class Hub:
    """Реестр клиентов + цикл рассылки."""

    def __init__(
        self,
        sim: SimProvider,
        profiles: ProfileStore,
        *,
        hz: float = 20.0,
        logger: logging.Logger | None = None,
    ) -> None:
        self.sim = sim
        self.profiles = profiles
        self.hz = hz
        self.logger = logger or logging.getLogger("msfs_gateway.hub")

        self._lock = threading.RLock()
        self._clients: dict[int, ClientInfo] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seq = 0
        self._started_at = time.monotonic()
        #: Правила автоопределения борта: (profile_id, поле, шаблон).
        self._match_rules: list[tuple[str, str, str]] = []
        self._last_message: dict[str, Any] = {}
        #: Пользовательские переменные профилей (LVAR/RPN), ключ → спецификации.
        self._custom_specs: dict[str, list[dict[str, Any]]] = {}
        self._custom_reader: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None
        #: (profile_id, момент чтения, значения) — кэш между кадрами.
        self._custom_cache: tuple[str | None, float, dict[str, Any]] = (None, 0.0, {})
        #: Ручной выбор борта, пока самолёт в симуляторе не сменился.
        self._override_profile: str | None = None
        self._override_identity: tuple[str | None, str | None] = (None, None)
        self._custom_error_logged = False
        self._read_error_logged = False
        self.refresh_profile_index()

    # ------------------------------------------------------------------
    # Профили
    # ------------------------------------------------------------------
    def refresh_profile_index(self) -> None:
        """Кэширует шаблоны `sim.match.*` и пользовательские переменные."""
        rules: list[tuple[str, str, str]] = []
        custom: dict[str, list[dict[str, Any]]] = {}
        for summary in self.profiles.list_summaries():
            try:
                profile = self.profiles.get(summary["id"])
            except Exception:
                continue
            match = profile.get("sim", {}).get("match", {})
            if isinstance(match, dict):
                for field_name in ("title", "atcModel"):
                    pattern = match.get(field_name)
                    if isinstance(pattern, str) and pattern:
                        rules.append((summary["id"], field_name, pattern))
            specs = custom_variable_specs(profile)
            if specs:
                custom[summary["id"]] = specs
        with self._lock:
            self._match_rules = rules
            self._custom_specs = custom
            self._custom_cache = (None, 0.0, {})

    def set_custom_reader(
        self, reader: Callable[[list[dict[str, Any]]], dict[str, Any]] | None
    ) -> None:
        """Подключает источник значений пользовательских переменных.

        Обычно это `WasmBridge.read_specs`. Без него переменные LVAR/RPN
        остаются незаполненными (виджеты покажут «--»).
        """
        with self._lock:
            self._custom_reader = reader
            self._custom_cache = (None, 0.0, {})

    def _match_profile(self, title: str | None, atc_model: str | None = None) -> str | None:
        """Ищет профиль по названию борта и/или модели ATC (шаблоны с `*`)."""
        candidates = {
            "title": (title or "").strip().lower(),
            "atcModel": (atc_model or "").strip().lower(),
        }
        if not any(candidates.values()):
            return None
        with self._lock:
            rules = list(self._match_rules)
        for profile_id, field_name, pattern in rules:
            value = candidates.get(field_name, "")
            if value and fnmatch.fnmatchcase(value, pattern.lower()):
                return profile_id
        return None

    def set_profile_override(self, profile_id: str | None) -> None:
        """Запоминает ручной выбор борта (когда симулятор не умеет его менять).

        Действует, пока в симуляторе не сменится самолёт: как только
        заголовок/модель ATC станут другими, приоритет снова у автоопределения.
        """
        with self._lock:
            self._override_profile = profile_id
            self._override_identity = (
                self.sim.aircraft_title,
                getattr(self.sim, "atc_model", None),
            )

    def _active_profile_id(self, values: dict[str, Any]) -> str | None:
        if self.sim.profile_id:
            return self.sim.profile_id

        title = values.get("aircraft.title") or self.sim.aircraft_title
        atc_model = values.get("aircraft.atcModel") or getattr(self.sim, "atc_model", None)
        identity = (title or None, atc_model or None)

        with self._lock:
            override = self._override_profile
            if override is not None:
                if identity != self._override_identity and any(identity):
                    # В симуляторе загрузили другой борт — ручной выбор снимается.
                    self._override_profile = None
                    override = None
                else:
                    return override

        return self._match_profile(title, atc_model)

    # ------------------------------------------------------------------
    # Клиенты
    # ------------------------------------------------------------------
    def attach(self, connection: WebSocketConnection, user_agent: str = "") -> ClientInfo:
        client = ClientInfo(
            connection=connection, client_id=uuid.uuid4().hex[:8], user_agent=user_agent
        )
        with self._lock:
            self._clients[id(connection)] = client
            total = len(self._clients)
        self.logger.info(
            "Клиент %s подключился (%s), всего: %d", client.client_id, connection.peer, total
        )

        # Первое сообщение — полный контекст, чтобы клиент не ждал тика.
        hello = {
            "type": "hello",
            "clientId": client.client_id,
            "server": {
                "name": "RUD Panel Gateway",
                "version": __version__,
                "telemetryHz": self.hz,
                "uptimeSec": round(time.monotonic() - self._started_at, 1),
            },
            "profiles": self.profiles.list_summaries(),
            "state": self.build_message(),
        }
        connection.send_text(json.dumps(hello, ensure_ascii=False, separators=(",", ":")))
        return client

    def detach(self, connection: WebSocketConnection) -> None:
        with self._lock:
            client = self._clients.pop(id(connection), None)
            total = len(self._clients)
        if client is not None:
            self.logger.info("Клиент %s отключился, всего: %d", client.client_id, total)

    def close_all(self) -> None:
        with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            client.connection.close(1001, "gateway shutdown")

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    # ------------------------------------------------------------------
    # Цикл рассылки
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="telemetry-broadcast", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def _loop(self) -> None:
        period = 1.0 / self.hz
        deadline = time.perf_counter()
        while not self._stop.is_set():
            try:
                message = self.build_message()
                self._last_message = message
                self._broadcast_text(json.dumps(message, ensure_ascii=False, separators=(",", ":")))
            except Exception:
                self.logger.exception("Ошибка цикла телеметрии")

            deadline += period
            delay = deadline - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            else:
                deadline = time.perf_counter()

    def _broadcast_text(self, text: str) -> None:
        with self._lock:
            clients = list(self._clients.values())
        for client in clients:
            try:
                # send_telemetry не блокирует шину: у каждого клиента своя
                # очередь и поток-отправитель.
                client.connection.send_telemetry(text)
            except (WebSocketError, OSError):
                self.detach(client.connection)

    def broadcast(self, message: dict[str, Any]) -> None:
        self._broadcast_text(json.dumps(message, ensure_ascii=False, separators=(",", ":")))

    # ------------------------------------------------------------------
    # Состояние
    # ------------------------------------------------------------------
    def build_message(self) -> dict[str, Any]:
        try:
            values = self.sim.read()
        except Exception as exc:
            if not self._read_error_logged:
                self.logger.warning("Провайдер не отдал значения: %s", exc)
                self._read_error_logged = True
            values = {}
        else:
            self._read_error_logged = False

        # Гарантируем полный набор встроенных ключей: клиент не должен
        # проверять наличие. Пользовательские (LVAR/RPN) добавляются ниже.
        clean: dict[str, Any] = {}
        for key in telemetry.VARIABLES:
            value = values.get(key, telemetry.default_value(key))
            if isinstance(value, float):
                clean[key] = round(value, 3)
            elif isinstance(value, (int, str, bool)):
                clean[key] = value
            else:
                clean[key] = telemetry.default_value(key)

        # Провайдер может вернуть переменные профиля (например, mock) —
        # пропускаем их как есть, чтобы виджеты могли на них ссылаться.
        for key, value in values.items():
            if key in clean:
                continue
            if isinstance(value, float):
                clean[key] = round(value, 3)
            elif isinstance(value, (int, str, bool)):
                clean[key] = value

        title = clean.get("aircraft.title") or self.sim.aircraft_title
        if title and not clean.get("aircraft.title"):
            clean["aircraft.title"] = title

        profile_id = self._active_profile_id(clean)
        clean.update(self._custom_values(profile_id))

        with self._lock:
            self._seq += 1
            seq = self._seq

        return {
            "type": "telemetry",
            "seq": seq,
            "ts": int(time.time() * 1000),
            "sim": {
                "provider": self.sim.name,
                "connected": bool(self.sim.connected),
                "aircraftTitle": title or None,
                "atcModel": clean.get("aircraft.atcModel") or getattr(self.sim, "atc_model", None),
                "profileId": profile_id,
            },
            "values": clean,
        }

    def _custom_values(self, profile_id: str | None) -> dict[str, Any]:
        """Значения LVAR/RPN активного профиля с кэшем на CUSTOM_REFRESH_SECONDS."""
        if profile_id is None:
            return {}
        with self._lock:
            specs = self._custom_specs.get(profile_id) or []
            reader = self._custom_reader
        if not specs or reader is None:
            return {}

        now = time.monotonic()
        with self._lock:
            # Кэш привязан к профилю: при смене борта старые значения не
            # должны попасть в кадр нового.
            cached_profile, cached_at, cached_values = self._custom_cache
            if cached_profile == profile_id and now - cached_at < CUSTOM_REFRESH_SECONDS:
                return dict(cached_values)

        try:
            values = reader(specs)
            if not isinstance(values, dict):
                values = {}
            self._custom_error_logged = False
        except Exception as exc:
            if not self._custom_error_logged:
                self.logger.warning("Не удалось прочитать переменные профиля: %s", exc)
                self._custom_error_logged = True
            values = {}

        with self._lock:
            self._custom_cache = (profile_id, now, dict(values))
        return dict(values)

    def latest_message(self) -> dict[str, Any]:
        message = self._last_message
        return message if message else self.build_message()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "uptimeSec": round(time.monotonic() - self._started_at, 1),
            "clients": self.client_count,
            "telemetryHz": self.hz,
            "sim": {
                "provider": self.sim.name,
                "connected": bool(self.sim.connected),
                "aircraftTitle": self.sim.aircraft_title,
                "atcModel": getattr(self.sim, "atc_model", None),
                "profileId": self.sim.profile_id,
            },
        }

    def announce_profiles(self) -> None:
        self.refresh_profile_index()
        self.broadcast({"type": "profiles", "profiles": self.profiles.list_summaries()})

    def announce_aircraft(self) -> None:
        # ВАЖНО: именно свежий кадр, а не latest_message(): кэш последнего тика
        # ещё содержит старый борт, и клиент переключился бы обратно.
        message = self.build_message()
        self.broadcast(
            {
                "type": "aircraft",
                "profileId": message.get("sim", {}).get("profileId"),
                "aircraftTitle": message.get("sim", {}).get("aircraftTitle"),
            }
        )

    # ------------------------------------------------------------------
    # Команды
    # ------------------------------------------------------------------
    def handle_command(
        self,
        key: Any,
        value: Any,
        request_id: Any = None,
        client: ClientInfo | None = None,
    ) -> dict[str, Any]:
        """Единая точка входа для команд из WebSocket и REST."""
        if not isinstance(key, str) or not key:
            return self._nack(request_id, key, "invalid_key", "Не указан ключ команды")
        if not telemetry.is_writable(key):
            return self._nack(
                request_id, key, "not_writable", f"Переменная {key!r} не принимает команды"
            )

        if client is not None and not self._allow_command(client):
            return self._nack(
                request_id, key, "rate_limited", "Слишком много команд, попробуйте позже"
            )

        try:
            self.sim.apply_command(key, value)
        except ValueError as exc:
            return self._nack(request_id, key, "invalid_value", str(exc))
        except SimCommandError as exc:
            return self._nack(request_id, key, "sim_rejected", str(exc))
        except Exception as exc:
            self.logger.exception("Команда %s не выполнена", key)
            return self._nack(request_id, key, "sim_error", f"Симулятор не выполнил команду: {exc}")

        if client is not None:
            client.commands_total += 1
        self.logger.debug("Команда %s=%r принята", key, value)

        # Не ждём следующего тика: сразу сообщаем клиенту актуальное значение.
        # Чтение после записи не должно превращать успешную команду в 500.
        try:
            values = self.sim.read()
        except Exception as exc:
            self.logger.warning("Команда применена, но значение прочитать не удалось: %s", exc)
            values = {}
        return {
            "type": "ack",
            "id": request_id,
            "key": key,
            "ok": True,
            "value": values.get(key),
        }

    def _allow_command(self, client: ClientInfo) -> bool:
        now = time.monotonic()
        window = client.command_times
        while window and now - window[0] > 1.0:
            window.popleft()
        if len(window) >= COMMANDS_PER_SECOND:
            self.logger.warning("Клиент %s превысил лимит команд", client.client_id)
            return False
        window.append(now)
        return True

    @staticmethod
    def _nack(request_id: Any, key: Any, code: str, message: str) -> dict[str, Any]:
        return {
            "type": "ack",
            "id": request_id,
            "key": key,
            "ok": False,
            "code": code,
            "error": message,
        }
