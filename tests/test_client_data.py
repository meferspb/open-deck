"""Тесты канала Client Data Area (корреляция запросов, таймауты, запись)."""

import threading
import unittest

from msfs_gateway.sim.client_data import (
    ClientDataChannel,
    ClientDataError,
    LoopbackClientDataBackend,
)


class RecordingBackend(LoopbackClientDataBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ensured: list[tuple[str, int]] = []

    def ensure_area(self, name, size):
        self.ensured.append((name, size))
        super().ensure_area(name, size)


class SilentBackend:
    """Транспорт, который принимает запрос и никогда не отвечает."""

    def __init__(self):
        self.requests: list[tuple[str, int]] = []

    def ensure_area(self, name, size):
        pass

    def request_read(self, name, request_id):
        self.requests.append((name, request_id))

    def write_area(self, name, payload):
        pass


class HappyPathTest(unittest.TestCase):
    def test_write_then_read(self):
        backend = LoopbackClientDataBackend()
        channel = ClientDataChannel(backend)

        channel.write_area("MobiFlight.Command", b"1 (>L:X, number)\x00")
        data = channel.read_area("MobiFlight.Command", 25)

        self.assertIsNotNone(data)
        self.assertTrue(data.startswith(b"1 (>L:X, number)"))
        self.assertEqual(backend.writes, 1)
        self.assertEqual(backend.reads, 1)

    def test_read_zero_size_is_empty(self):
        channel = ClientDataChannel(LoopbackClientDataBackend())
        self.assertEqual(channel.read_area("Area", 0), b"")

    def test_area_grows_only_when_needed(self):
        backend = RecordingBackend()
        channel = ClientDataChannel(backend)

        channel.write_area("Area", b"1234")
        channel.write_area("Area", b"1234")
        channel.write_area("Area", b"12345678")

        self.assertEqual(backend.ensured, [("Area", 4), ("Area", 8)])

    def test_multiple_sequential_reads(self):
        backend = LoopbackClientDataBackend()
        channel = ClientDataChannel(backend)
        backend.areas["A"] = b"one"
        backend.areas["B"] = b"two"

        self.assertEqual(channel.read_area("A", 3), b"one")
        self.assertEqual(channel.read_area("B", 3), b"two")
        self.assertEqual(channel.pending_count, 0)


class TimeoutTest(unittest.TestCase):
    def test_no_answer_returns_none(self):
        backend = SilentBackend()
        channel = ClientDataChannel(backend, timeout=0.05)

        self.assertIsNone(channel.read_area("MobiFlight.LVars", 136))
        self.assertEqual(channel.pending_count, 0)
        self.assertEqual(len(backend.requests), 1)

    def test_late_answer_is_ignored(self):
        backend = SilentBackend()
        channel = ClientDataChannel(backend, timeout=0.05)

        self.assertIsNone(channel.read_area("Area", 4))
        request_id = backend.requests[0][1]
        # Поздний ответ не должен падать и не должен оставлять «висяков».
        channel.deliver(request_id, b"late")
        self.assertEqual(channel.pending_count, 0)

    def test_circuit_opens_after_timeouts(self):
        backend = SilentBackend()
        channel = ClientDataChannel(backend, timeout=0.01, failure_threshold=2, cooldown=60.0)

        self.assertIsNone(channel.read_area("MobiFlight.LVars", 136))
        self.assertIsNone(channel.read_area("MobiFlight.LVars", 136))
        self.assertFalse(channel.available)

        # Пока предохранитель открыт, запросы не уходят в транспорт.
        self.assertIsNone(channel.read_area("MobiFlight.LVars", 136))
        self.assertEqual(len(backend.requests), 2)

    def test_success_resets_circuit(self):
        backend = LoopbackClientDataBackend()
        backend.areas["Area"] = b"ok"
        channel = ClientDataChannel(backend, timeout=0.01, failure_threshold=2)
        self.assertEqual(channel.read_area("Area", 2), b"ok")
        self.assertTrue(channel.available)

    def test_fail_all_releases_waiter(self):
        backend = SilentBackend()
        channel = ClientDataChannel(backend, timeout=2.0)
        errors: list[BaseException] = []

        def reader():
            try:
                channel.read_area("Area", 4)
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=reader)
        thread.start()
        while not backend.requests:
            threading.Event().wait(0.01)

        channel.fail_all("соединение закрыто")
        thread.join(timeout=2.0)

        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ClientDataError)


class RequestErrorsTest(unittest.TestCase):
    def test_transport_error_wrapped(self):
        class Broken(SilentBackend):
            def request_read(self, name, request_id):
                raise OSError("нет связи")

        channel = ClientDataChannel(Broken())
        with self.assertRaises(ClientDataError):
            channel.read_area("Area", 4)

    def test_empty_name_rejected(self):
        channel = ClientDataChannel(LoopbackClientDataBackend())
        with self.assertRaises(ClientDataError):
            channel.read_area("", 4)
        with self.assertRaises(ClientDataError):
            channel.write_area("", b"x")


if __name__ == "__main__":
    unittest.main()
