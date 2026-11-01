"""Протокол Client Data Area: синхронный фасад над обменом «площадками».

Зачем отдельный слой: WASM-модули (MobiFlight, SimBridge) публикуют данные
через SimConnect Client Data Area. Работа с ними асинхронная — запрос уходит
в симулятор, ответ приходит в колбэк `SIMCONNECT_RECV_CLIENT_DATA`. Этот
модуль превращает её в понятные синхронные `read_area` / `write_area`,
которые можно вызывать из потока шины телеметрии.

Транспорт (`ClientDataBackend`) абстрагирован: в реальном полёте это
SimConnect, в тестах и демо — `LoopbackClientDataBackend` в памяти.
Так протокол (корреляция запросов, таймауты, размеры областей) проверяется
без MSFS.
"""

from __future__ import annotations

import itertools
import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


class ClientDataError(RuntimeError):
    """Обмен с Client Data Area невозможен."""


class ClientDataTimeout(ClientDataError):
    """Ответ на запрос чтения не пришёл вовремя."""


@runtime_checkable
class ClientDataBackend(Protocol):
    """Минимальный транспорт, который умеет работать с областями."""

    def ensure_area(self, name: str, size: int) -> None:
        """Зарегистрировать область нужного размера (идемпотентно)."""

    def request_read(self, name: str, request_id: int) -> None:
        """Запросить чтение области; ответ придёт в `ClientDataChannel.deliver`."""

    def write_area(self, name: str, payload: bytes) -> None:
        """Записать область целиком."""


class _Pending:
    __slots__ = ("error", "event", "payload")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.payload: bytes | None = None
        self.error: str | None = None


class ClientDataChannel:
    """Синхронные чтение/запись Client Data Area поверх асинхронного транспорта."""

    def __init__(
        self,
        backend: ClientDataBackend,
        *,
        timeout: float = 1.5,
        logger: logging.Logger | None = None,
    ) -> None:
        self._backend = backend
        self._timeout = timeout
        self.logger = logger or logging.getLogger("msfs_gateway.clientdata")

        self._lock = threading.Lock()
        self._pending: dict[int, _Pending] = {}
        self._ids = itertools.count(1)
        #: Размер, с которым область уже зарегистрирована.
        self._areas: dict[str, int] = {}
        #: Чтобы не спамить лог при отсутствующем WASM-модуле.
        self._timeout_logged: set[str] = set()

        sink: Any = getattr(backend, "set_sink", None)
        if callable(sink):
            sink(self.deliver)

    # ------------------------------------------------------------------
    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def _ensure(self, name: str, size: int) -> None:
        known = self._areas.get(name)
        if known is not None and known >= size:
            return
        self._backend.ensure_area(name, size)
        self._areas[name] = size

    def read_area(self, name: str, size: int, timeout: float | None = None) -> bytes | None:
        """Читает область. None — ответ не пришёл (например, нет WASM-модуля)."""
        if size <= 0:
            return b""
        if not name:
            raise ClientDataError("Пустое имя области")

        self._ensure(name, size)
        request_id = next(self._ids)
        pending = _Pending()
        with self._lock:
            self._pending[request_id] = pending

        try:
            self._backend.request_read(name, request_id)
        except Exception as exc:
            with self._lock:
                self._pending.pop(request_id, None)
            raise ClientDataError(f"{name}: запрос не отправлен ({exc})") from exc

        wait_for = self._timeout if timeout is None else max(0.0, timeout)
        if not pending.event.wait(wait_for):
            with self._lock:
                self._pending.pop(request_id, None)
            if name not in self._timeout_logged:
                self._timeout_logged.add(name)
                self.logger.warning(
                    "Client Data «%s»: нет ответа за %.2f с (WASM-модуль не подключён?)",
                    name,
                    wait_for,
                )
            return None

        if pending.error:
            raise ClientDataError(f"{name}: {pending.error}")

        data = pending.payload or b""
        self._timeout_logged.discard(name)
        return data[:size]

    def write_area(self, name: str, payload: bytes) -> None:
        if not name:
            raise ClientDataError("Пустое имя области")
        data = bytes(payload)
        self._ensure(name, len(data))
        self._backend.write_area(name, data)

    # ------------------------------------------------------------------
    # Колбэки транспорта
    # ------------------------------------------------------------------
    def deliver(self, request_id: int, data: bytes) -> None:
        """Ответ на чтение: вызывается из потока SimConnect или теста."""
        with self._lock:
            pending = self._pending.pop(int(request_id), None)
        if pending is None:
            # Поздний ответ на уже истёкший запрос — штатная ситуация.
            return
        pending.payload = bytes(data)
        pending.event.set()

    def fail(self, request_id: int, reason: str) -> None:
        with self._lock:
            pending = self._pending.pop(int(request_id), None)
        if pending is None:
            return
        pending.error = reason
        pending.event.set()

    def fail_all(self, reason: str = "соединение потеряно") -> None:
        """Сбрасывает все ожидающие запросы (например, при разрыве с MSFS)."""
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for item in pending:
            item.error = reason
            item.event.set()

    def reset(self) -> None:
        """Забыть размеры областей: после переподключения их регистрируют заново."""
        with self._lock:
            self._areas.clear()
            self._timeout_logged.clear()


class LoopbackClientDataBackend:
    """In-memory транспорт: области лежат в словаре, чтение отдаёт содержимое.

    `transform(area, data) -> bytes` позволяет эмулировать WASM: например,
    подставить значения LVAR в блок или записать ответ на RPN-команду.
    """

    def __init__(
        self,
        transform: Callable[[str, bytes], bytes] | None = None,
        *,
        synchronous: bool = True,
    ) -> None:
        self.transform = transform
        self.synchronous = synchronous
        self.areas: dict[str, bytes] = {}
        self.reads = 0
        self.writes = 0
        self._sink: Callable[[int, bytes], None] | None = None
        self._lock = threading.Lock()

    def set_sink(self, sink: Callable[[int, bytes], None]) -> None:
        self._sink = sink

    def ensure_area(self, name: str, size: int) -> None:
        with self._lock:
            current = self.areas.get(name, b"")
            if len(current) < size:
                self.areas[name] = current.ljust(size, b"\x00")

    def request_read(self, name: str, request_id: int) -> None:
        with self._lock:
            data = self.areas.get(name, b"")
            self.reads += 1
        if self.transform is not None:
            data = self.transform(name, data)

        def answer() -> None:
            sink = self._sink
            if sink is not None:
                sink(request_id, data)

        if self.synchronous:
            answer()
        else:
            threading.Thread(target=answer, daemon=True).start()

    def write_area(self, name: str, payload: bytes) -> None:
        with self._lock:
            self.areas[name] = bytes(payload)
            self.writes += 1
