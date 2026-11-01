"""Тесты WebSocket-сервера (RFC 6455): handshake, фреймы, маскирование."""

import io
import struct
import unittest

from msfs_gateway.websocket import (
    OP_CLOSE,
    OP_PING,
    OP_PONG,
    OP_TEXT,
    WebSocketConnection,
    WebSocketError,
    accept_key,
    handshake_headers,
)


class FakeSock:
    def __init__(self):
        self.timeout = None
        self.shutdown_called = False

    def settimeout(self, value):
        self.timeout = value

    def shutdown(self, how):
        self.shutdown_called = True


def make_connection(rfile_bytes=b"", sock=None):
    sock = sock or FakeSock()
    rfile = io.BytesIO(rfile_bytes)
    wfile = io.BytesIO()
    conn = WebSocketConnection(sock, rfile, wfile, peer="test")
    return sock, rfile, wfile, conn


class HandshakeTest(unittest.TestCase):
    def test_accept_key_rfc_example(self):
        # RFC 6455 §1.3, известный тестовый вектор.
        self.assertEqual(
            accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        )

    def test_handshake_headers(self):
        headers = handshake_headers("dGhlIHNhbXBsZSBub25jZQ==")
        text = headers.decode("ascii")
        self.assertIn("101 Switching Protocols", text)
        self.assertIn("Upgrade: websocket", text)
        self.assertIn("Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=", text)


class SendTest(unittest.TestCase):
    def test_send_text_frame_layout(self):
        _, _, wfile, conn = make_connection()
        conn.send_text("Hi")
        frame = wfile.getvalue()

        self.assertEqual(frame[0] & 0x7F, OP_TEXT)
        self.assertTrue(frame[0] & 0x80, "FIN должен быть установлен")
        self.assertFalse(frame[1] & 0x80, "серверный фрейм не маскируется")
        self.assertEqual(frame[1] & 0x7F, 2, "длина 2 байта")
        self.assertEqual(frame[2:4], b"Hi")

    def test_send_text_16bit_length(self):
        _, _, wfile, conn = make_connection()
        payload = "x" * 200
        conn.send_text(payload)
        frame = wfile.getvalue()
        self.assertEqual(frame[1] & 0x7F, 126)
        self.assertEqual(struct.unpack("!H", frame[2:4])[0], 200)

    def test_close_marks_closed_and_shuts_socket(self):
        sock, _, _, conn = make_connection()
        conn.close(1000, "bye")
        self.assertTrue(sock.shutdown_called)


class RecvTest(unittest.TestCase):
    @staticmethod
    def masked_frame(opcode, payload: bytes, fin=True) -> bytes:
        mask = b"\x00\x01\x02\x03"
        first = (0x80 if fin else 0x00) | opcode
        length = len(payload)
        header = bytearray([first, 0x80 | length])
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        return bytes(header) + mask + masked

    def test_recv_text(self):
        _sock, _rfile, _wfile, conn = make_connection(self.masked_frame(OP_TEXT, b"hello"))
        self.assertEqual(conn.recv_text(), "hello")

    def test_recv_requires_mask(self):
        # Клиентский фрейм без маски запрещён.
        raw = bytearray([0x81, 0x05]) + b"hello"
        _, _, _, conn = make_connection(bytes(raw))
        with self.assertRaises(WebSocketError):
            conn.recv_text()

    def test_recv_ping_responds_pong(self):
        _sock, _rfile, wfile, conn = make_connection(
            self.masked_frame(OP_PING, b"p") + self.masked_frame(OP_CLOSE, b"")
        )
        # ping → сервер отвечает pong, затем close → None.
        result = conn.recv_text()
        self.assertIsNone(result)
        out = wfile.getvalue()
        # Первый исходящий фрейм — pong.
        self.assertEqual(out[0] & 0x7F, OP_PONG)

    def test_recv_utf8_rejected(self):
        # Байт 0xFF не является валидным UTF-8.
        _, _, _, conn = make_connection(self.masked_frame(OP_TEXT, b"\xff\xfe"))
        with self.assertRaises(WebSocketError):
            conn.recv_text()


if __name__ == "__main__":
    unittest.main()
