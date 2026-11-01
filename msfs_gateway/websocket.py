"""Минимальный сервер WebSocket (RFC 6455) на стандартной библиотеке.

Реализовано ровно то, что нужно шлюзу: текстовые сообщения, ping/pong и
корректное закрытие. Расширения (например, permessage-deflate) не нужны —
трафик идёт по локальной сети, а лишняя сложность усложняет аудит кода.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import logging
import queue
import socket
import struct
import threading
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:  # pragma: no cover - только для типизации
    from typing import BinaryIO

WS_GUID: Final = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_CONTINUATION: Final = 0x0
OP_TEXT: Final = 0x1
OP_BINARY: Final = 0x2
OP_CLOSE: Final = 0x8
OP_PING: Final = 0x9
OP_PONG: Final = 0xA

#: Защита от «злого» клиента, который пришлёт гигантский фрейм.
MAX_MESSAGE_BYTES: Final = 256 * 1024
#: Сколько кадров телеметрии держим в очереди на медленного клиента.
OUTBOX_FRAMES: Final = 8


class WebSocketError(Exception):
    """Нарушение протокола или обрыв соединения."""


def accept_key(client_key: str) -> str:
    """Вычисляет Sec-WebSocket-Accept по ключу клиента."""
    digest = hashlib.sha1((client_key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def handshake_headers(client_key: str) -> bytes:
    """Готовый блок заголовков ответа 101 Switching Protocols."""
    return (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept_key(client_key)}\r\n"
        "\r\n"
    ).encode("ascii")


class WebSocketConnection:
    """Одно клиентское соединение.

    Чтение выполняет поток HTTP-обработчика. Телеметрию пишет отдельный
    поток-отправитель с ограниченной очередью: медленный клиент не должен
    останавливать рассылку остальным.
    """

    def __init__(
        self,
        sock: socket.socket,
        rfile: BinaryIO,
        wfile: BinaryIO,
        peer: str,
        logger: logging.Logger | None = None,
        read_timeout: float = 90.0,
    ) -> None:
        self._sock = sock
        self._rfile = rfile
        self._wfile = wfile
        self.peer = peer
        self.logger = logger or logging.getLogger("msfs_gateway.ws")
        self._send_lock = threading.Lock()
        self._closed = False
        self.last_seen = 0.0
        self._outbox: queue.Queue[str | None] = queue.Queue(maxsize=OUTBOX_FRAMES)
        self._writer: threading.Thread | None = None
        self._writer_lock = threading.Lock()
        with contextlib.suppress(OSError):  # сокет мог быть уже закрыт
            self._sock.settimeout(read_timeout)

    # ------------------------------------------------------------------
    # Чтение
    # ------------------------------------------------------------------
    def recv_text(self) -> str | None:
        """Читает следующее текстовое сообщение. None — клиент закрыл соединение."""
        buffer = bytearray()
        message_opcode: int | None = None

        while True:
            fin, opcode, payload = self._read_frame()

            if opcode == OP_CLOSE:
                self._send_frame(OP_CLOSE, payload[:2])
                self._closed = True
                return None
            if opcode == OP_PING:
                self._send_frame(OP_PONG, payload)
                continue
            if opcode == OP_PONG:
                continue
            if opcode == OP_BINARY:
                raise WebSocketError("бинарные сообщения не поддерживаются")

            if opcode in (OP_TEXT, OP_CONTINUATION):
                if opcode == OP_TEXT:
                    if message_opcode is not None:
                        raise WebSocketError("новое сообщение внутри фрагментированного")
                    message_opcode = OP_TEXT
                    buffer = bytearray(payload)
                else:
                    if message_opcode is None:
                        raise WebSocketError("продолжение без начала сообщения")
                    buffer.extend(payload)
                if len(buffer) > MAX_MESSAGE_BYTES:
                    raise WebSocketError("сообщение слишком большое")
                if fin:
                    try:
                        return buffer.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise WebSocketError("сообщение не является корректным UTF-8") from exc
                continue

            raise WebSocketError(f"неизвестный opcode: {opcode}")

    def _read_frame(self) -> tuple[bool, int, bytes]:
        header = self._read_exact(2)
        first, second = header[0], header[1]

        if first & 0x70:
            raise WebSocketError("RSV-биты не поддерживаются")

        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]

        if length > MAX_MESSAGE_BYTES:
            raise WebSocketError("фрейм слишком большой")
        if opcode in (OP_CLOSE, OP_PING, OP_PONG):
            # RFC 6455, 5.5: управляющие фреймы не фрагментируются и
            # несут не больше 125 байт полезной нагрузки.
            if not fin:
                raise WebSocketError("управляющий фрейм не может быть фрагментирован")
            if length > 125:
                raise WebSocketError("управляющий фрейм слишком большой")
        if not masked:
            # Клиентские фреймы обязаны быть маскированными (RFC 6455, 5.1).
            raise WebSocketError("клиентский фрейм обязан быть маскированным")

        mask = self._read_exact(4)
        payload = self._read_exact(length) if length else b""
        if payload:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return fin, opcode, payload

    def _read_exact(self, size: int) -> bytes:
        """Читает ровно `size` байт.

        Используется буферизованный `rfile` обработчика: он мог заранее
        прочитать часть первого фрейма вместе с HTTP-заголовками, поэтому
        обращаться напрямую к сокету нельзя.
        """
        if size == 0:
            return b""
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self._rfile.read(size - len(chunks))
            if not chunk:
                raise WebSocketError("соединение закрыто во время чтения фрейма")
            chunks.extend(chunk)
        return bytes(chunks)

    # ------------------------------------------------------------------
    # Запись
    # ------------------------------------------------------------------
    def send_text(self, text: str) -> None:
        self._send_frame(OP_TEXT, text.encode("utf-8"))

    def send_ping(self, payload: bytes = b"") -> None:
        self._send_frame(OP_PING, payload)

    def send_telemetry(self, text: str) -> None:
        """Ставит кадр телеметрии в очередь и не блокирует вызывающий поток.

        Если клиент не успевает читать, старые кадры выбрасываются: пропустить
        кадр лучше, чем остановить рассылку телеметрии всем клиентам.
        """
        if self._closed:
            return
        try:
            self._outbox.put_nowait(text)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                self._outbox.get_nowait()
            with contextlib.suppress(queue.Full):
                self._outbox.put_nowait(text)
        self._ensure_writer()

    def _ensure_writer(self) -> None:
        with self._writer_lock:
            if self._writer is not None and self._writer.is_alive():
                return
            self._writer = threading.Thread(
                target=self._writer_loop,
                name=f"ws-out-{self.peer}",
                daemon=True,
            )
            self._writer.start()

    def _writer_loop(self) -> None:
        while True:
            text = self._outbox.get()
            if text is None:
                return
            try:
                self._send_frame(OP_TEXT, text.encode("utf-8"))
            except (WebSocketError, OSError):
                self._closed = True
                return

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        with self._send_lock:
            self._write_frame(opcode, payload)

    def _write_frame(self, opcode: int, payload: bytes) -> None:
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))

        frame = bytes(header) + payload
        if self._closed:
            raise WebSocketError("соединение уже закрыто")
        try:
            self._wfile.write(frame)
            self._wfile.flush()
        except (OSError, ValueError) as exc:
            self._closed = True
            raise WebSocketError("не удалось отправить фрейм") from exc

    def close(self, code: int = 1000, reason: str = "") -> None:
        """Идемпотентное закрытие: отправляет close-фрейм и гасит сокет.

        Если отправитель занят (клиент не читает), ждём не дольше секунды:
        иначе остановка шлюза могла бы зависнуть на каждом «зависшем» клиенте.
        """
        if self._closed:
            return
        payload = struct.pack("!H", code) + reason.encode("utf-8")[:120]
        locked = self._send_lock.acquire(timeout=1.0)
        try:
            if locked and not self._closed:
                with contextlib.suppress(WebSocketError, OSError):
                    self._write_frame(OP_CLOSE, payload)
        finally:
            if locked:
                self._send_lock.release()
        self._closed = True
        # Будим отправителя, чтобы он завершил поток.
        try:
            self._outbox.put_nowait(None)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                self._outbox.get_nowait()
            with contextlib.suppress(queue.Full):
                self._outbox.put_nowait(None)
        with contextlib.suppress(OSError):
            self._sock.shutdown(socket.SHUT_RDWR)
