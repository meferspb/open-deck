"""Мост к WASM-модулю (MobiFlight / SimBridge): LVAR и RPN.

Зачем: стандартные SimVar покрывают дефолтные самолёты, но PMDG, Fenix,
FlyByWire и iniBuilds держат состояние в собственных LVAR/HVAR/BVAR. Доступ
к ним даёт WASM-модуль внутри MSFS, который обменивается с хостом через
SimConnect Client Data Area.

Этот модуль — транспортно-независимый слой протокола:

  * кодирование/декодирование блоков LVAR (имя 128 байт + double);
  * команды RPN через область `MobiFlight.Command` и ответ в
    `MobiFlight.Response`;
  * `WasmBridge` — чтение LVAR, запись LVAR через RPN, выполнение RPN;
  * `MockWasmTransport` — полностью рабочий in-memory транспорт для демо и
    автотестов (позволяет прогнать всю цепочку без MSFS).

Реальный транспорт поверх SimConnect Client Data Area подключается отдельно
(см. docs/architecture.md, раздел «WASM-мост»): имена областей и ID сообщений
сверяются с версией WASM-модуля, поэтому они не зашиты в этот файл.
"""

from __future__ import annotations

import logging
import re
import struct
import threading
import time
from collections.abc import Iterable, Sequence
from typing import Any, Final, Protocol

#: Раскладка блока LVAR в Client Data Area.
LVAR_NAME_BYTES: Final = 128
LVAR_VALUE_FORMAT: Final = "<d"
LVAR_VALUE_BYTES: Final = 8
LVAR_ENTRY_BYTES: Final = LVAR_NAME_BYTES + LVAR_VALUE_BYTES

#: Имена областей по документации MobiFlight WASM.
LVAR_AREA: Final = "MobiFlight.LVars"
COMMAND_AREA: Final = "MobiFlight.Command"
RESPONSE_AREA: Final = "MobiFlight.Response"

COMMAND_BYTES: Final = 1024
RESPONSE_BYTES: Final = 1024
#: Сколько LVAR тянуть за один запрос. 56 × 136 = 7616 байт: вместе с
#: заголовком пакета это меньше MaxRecvData/MaxSendData = 8192 из
#: генерируемого SimConnect.cfg (64 элемента уже не помещались).
MAX_LVARS_PER_BLOCK: Final = 56

_SET_LVAR_PATTERN: Final = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*\(\s*>\s*L\s*:\s*([^,]+?)\s*,\s*[A-Za-z]+\s*\)\s*$"
)


class WasmBridgeError(RuntimeError):
    """WASM-мост недоступен или вернул ошибку."""


# ----------------------------------------------------------------------
# Кодирование протокола (чистые функции — их же проверяют тесты)
# ----------------------------------------------------------------------
def pack_lvar_name(name: str) -> bytes:
    """Имя LVAR фиксированной длины 128 байт, UTF-8, с NUL-заполнением."""
    if not isinstance(name, str) or not name:
        raise ValueError("Имя LVAR должно быть непустой строкой")
    encoded = name.encode("utf-8")
    if len(encoded) >= LVAR_NAME_BYTES:
        raise ValueError(f"Имя LVAR длиннее {LVAR_NAME_BYTES - 1} байт: {name!r}")
    return encoded.ljust(LVAR_NAME_BYTES, b"\x00")


def unpack_lvar_name(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("utf-8", "replace")


def encode_lvar_block(pairs: Iterable[tuple[str, float]]) -> bytes:
    """Блок «имя + значение» в том порядке, в котором перечислены пары."""
    parts: list[bytes] = []
    for name, value in pairs:
        parts.append(pack_lvar_name(name))
        parts.append(struct.pack(LVAR_VALUE_FORMAT, float(value)))
    return b"".join(parts)


def decode_lvar_block(data: bytes, count: int | None = None) -> dict[str, float]:
    """Разбирает блок LVAR. Неполный хвост данных игнорируется."""
    if not data:
        return {}
    available = len(data) // LVAR_ENTRY_BYTES
    entries = available if count is None else min(available, max(0, int(count)))

    values: dict[str, float] = {}
    for index in range(entries):
        offset = index * LVAR_ENTRY_BYTES
        name = unpack_lvar_name(data[offset : offset + LVAR_NAME_BYTES])
        (value,) = struct.unpack(
            LVAR_VALUE_FORMAT,
            data[offset + LVAR_NAME_BYTES : offset + LVAR_ENTRY_BYTES],
        )
        if name:
            values[name] = value
    return values


def encode_command(text: str) -> bytes:
    """Команда RPN: UTF-8 строка с завершающим NUL, дополненная до буфера."""
    raw = text.encode("utf-8")
    if len(raw) >= COMMAND_BYTES:
        raise ValueError(f"Команда RPN длиннее {COMMAND_BYTES - 1} байт")
    return raw.ljust(COMMAND_BYTES, b"\x00")


def decode_response(data: bytes) -> str:
    return data.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()


def coerce_custom_value(raw: Any, kind: str) -> Any:
    """Приводит значение из WASM к типу переменной профиля."""
    if kind == "bool":
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "on", "yes"}
        return bool(raw)
    if kind == "number":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0
    return "" if raw is None else str(raw)


# ----------------------------------------------------------------------
# Транспорт
# ----------------------------------------------------------------------
class WasmTransport(Protocol):
    """Минимальный интерфейс обмена с Client Data Area."""

    available: bool

    def read_area(self, area: str, size: int) -> bytes | None:
        """Прочитать область; None — данных нет/область не готова."""

    def write_area(self, area: str, payload: bytes) -> None:
        """Записать область целиком."""


class NullWasmTransport:
    """Заглушка: моста нет, все операции — ошибка."""

    available = False

    def read_area(self, area: str, size: int) -> bytes | None:
        return None

    def write_area(self, area: str, payload: bytes) -> None:
        raise WasmBridgeError("WASM-мост не подключён")


class MockWasmTransport:
    """In-memory транспорт: эмуляция WASM для демо и тестов.

    Хранит значения LVAR и минимально разбирает команды вида
    ``42 (>L:SOME_LVAR, number)``. Ответ RPN можно подменить через
    ``rpn_handler`` — это нужно, чтобы проверить чтение через RPN.
    """

    available = True

    def __init__(
        self,
        lvars: dict[str, float] | None = None,
        rpn_handler: Any = None,
    ) -> None:
        self.lvars: dict[str, float] = dict(lvars or {})
        self.areas: dict[str, bytes] = {}
        self.commands: list[str] = []
        self._rpn_handler = rpn_handler

    def read_area(self, area: str, size: int) -> bytes | None:
        if size <= 0:
            return b""
        if area == LVAR_AREA:
            return self._lvar_block(size)
        data = self.areas.get(area)
        if data is None:
            return None
        return data[:size].ljust(size, b"\x00")

    def write_area(self, area: str, payload: bytes) -> None:
        self.areas[area] = bytes(payload)
        if area != COMMAND_AREA:
            return

        script = decode_response(payload)
        self.commands.append(script)
        match = _SET_LVAR_PATTERN.match(script)
        if match:
            self.lvars[match.group(2).strip()] = float(match.group(1))

        response = ""
        if self._rpn_handler is not None:
            # Ошибку обработчика не глотаем: для тестов важно видеть отказ.
            response = str(self._rpn_handler(script) or "")
        self.areas[RESPONSE_AREA] = encode_command(response)

    def _lvar_block(self, size: int) -> bytes:
        """Отвечает на последний записанный блок имён их значениями."""
        request = self.areas.get(LVAR_AREA, b"")
        count = min(size // LVAR_ENTRY_BYTES, len(request) // LVAR_ENTRY_BYTES)
        block = bytearray()
        for index in range(count):
            offset = index * LVAR_ENTRY_BYTES
            name = unpack_lvar_name(request[offset : offset + LVAR_NAME_BYTES])
            value = float(self.lvars.get(name, 0.0))
            block += pack_lvar_name(name)
            block += struct.pack(LVAR_VALUE_FORMAT, value)
        return bytes(block)


# ----------------------------------------------------------------------
# Мост
# ----------------------------------------------------------------------
class WasmBridge:
    """Высокоуровневые операции над WASM-модулем."""

    def __init__(
        self,
        transport: WasmTransport,
        logger: logging.Logger | None = None,
    ) -> None:
        self._transport = transport
        self.logger = logger or logging.getLogger("msfs_gateway.wasm")
        self._lock = threading.RLock()
        self._last_error: str | None = None
        self._last_success_at: float | None = None

    @property
    def available(self) -> bool:
        return bool(getattr(self._transport, "available", False))

    @property
    def transport(self) -> WasmTransport:
        return self._transport

    def status(self) -> dict[str, Any]:
        """Диагностика моста для /api/diagnostics и UI."""
        with self._lock:
            return {
                "available": self.available,
                "transport": type(self._transport).__name__,
                "lastError": self._last_error,
                "lastSuccessAt": self._last_success_at,
            }

    def probe(self) -> bool:
        """Проверяет, отвечает ли установленный WASM-модуль."""
        if not self.available:
            self._last_error = "WASM-мост не подключён"
            return False
        payload = encode_lvar_block([("__open_deck_probe__", 0.0)])
        try:
            with self._lock:
                self._transport.write_area(LVAR_AREA, payload)
                data = self._transport.read_area(LVAR_AREA, len(payload))
            if data is None:
                self._last_error = "WASM-модуль не ответил на пробный запрос"
                return False
            self._last_success_at = time.monotonic()
            self._last_error = None
            return True
        except Exception as exc:
            self._last_error = str(exc)
            return False

    def read_lvars(self, names: Sequence[str]) -> dict[str, float]:
        """Читает значения LVAR по именам (пачками, чтобы не превысить буфер).

        Неизвестный модулю LVAR приходит как 0.0: протокол не передаёт
        признак «переменная не найдена», поэтому нулевое значение нельзя
        считать достоверным без сверки с документацией ВС.
        """
        if not self.available:
            self._last_error = "WASM-мост не подключён"
            raise WasmBridgeError("WASM-мост не подключён")

        unique = [name for name in dict.fromkeys(names) if name]
        result: dict[str, float] = {}
        for start in range(0, len(unique), MAX_LVARS_PER_BLOCK):
            chunk = unique[start : start + MAX_LVARS_PER_BLOCK]
            request = encode_lvar_block([(name, 0.0) for name in chunk])
            with self._lock:
                self._transport.write_area(LVAR_AREA, request)
                data = self._transport.read_area(LVAR_AREA, len(request))
            if data:
                result.update(decode_lvar_block(data, len(chunk)))
        if result:
            self._last_success_at = time.monotonic()
            self._last_error = None
        return result

    def write_lvar(self, name: str, value: float) -> None:
        """Пишет LVAR через RPN: `(<значение>) (>L:NAME, number)`."""
        if not self.available:
            raise WasmBridgeError("WASM-мост не подключён")
        self.execute_rpn(f"{float(value):g} (>L:{name}, number)")

    def execute_rpn(self, script: str) -> str:
        """Выполняет RPN-скрипт и возвращает ответ модуля."""
        if not self.available:
            self._last_error = "WASM-мост не подключён"
            raise WasmBridgeError("WASM-мост не подключён")
        with self._lock:
            self._transport.write_area(COMMAND_AREA, encode_command(script))
            data = self._transport.read_area(RESPONSE_AREA, RESPONSE_BYTES)
        self._last_error = None
        self._last_success_at = time.monotonic()
        return decode_response(data or b"")

    def read_specs(self, specs: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Читает набор пользовательских переменных профиля.

        Поддерживаются источники `lvar` (одним блоком) и `rpn` (по одному
        запросу). Ошибки отдельных записей не роняют остальные.
        """
        if not self.available:
            # Мост отключён или предохранитель Client Data открыт: не тратим
            # время на таймауты, приборы просто покажут «--».
            return {}

        values: dict[str, Any] = {}

        lvar_specs = [spec for spec in specs if spec.get("source") == "lvar"]
        if lvar_specs:
            try:
                raw = self.read_lvars([str(spec["name"]) for spec in lvar_specs])
            except WasmBridgeError:
                raise
            except Exception as exc:
                self.logger.debug("Чтение LVAR не удалось: %s", exc)
                raw = {}
            for spec in lvar_specs:
                name = str(spec["name"])
                if name in raw:
                    values[spec["key"]] = coerce_custom_value(raw[name], spec.get("kind", "number"))

        for spec in specs:
            if spec.get("source") != "rpn":
                continue
            if not self.available:
                break
            try:
                response = self.execute_rpn(str(spec.get("expression", "")))
            except Exception as exc:
                self.logger.debug("RPN %r не выполнен: %s", spec.get("expression"), exc)
                continue
            # Пустой ответ означает, что модуль ничего не вернул —
            # подставлять 0.0 было бы враньём.
            if not response:
                continue
            values[spec["key"]] = coerce_custom_value(response, spec.get("kind", "number"))

        return {key: value for key, value in values.items() if key}
