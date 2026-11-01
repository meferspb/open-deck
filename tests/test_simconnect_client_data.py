"""Тесты учёта областей/определений Client Data в SimConnect-бэкенде.

Сам SimConnect.dll не нужен: вызовы идут в поддельный DLL, а `run_on_dispatch`
выполняет колбэк сразу (как поток диспетчеризации).
"""

import unittest

from msfs_gateway.sim.simconnect import SimConnectClientDataBackend, SimConnectError


class FakeDll:
    def __init__(self):
        self.calls = []

    def SimConnect_MapClientDataNameToID(self, handle, name, area_id):
        self.calls.append(("map", name.decode(), area_id))
        return 0

    def SimConnect_AddToClientDataDefinition(self, handle, define_id, offset, size, epsilon, datum):
        self.calls.append(("define", define_id, size))
        return 0

    def SimConnect_RequestClientData(
        self, handle, area_id, request_id, define_id, period, flags, origin, interval, limit
    ):
        self.calls.append(("request", area_id, request_id, define_id, period))
        return 0

    def SimConnect_SetClientData(self, handle, area_id, define_id, flags, reserved, size, pointer):
        self.calls.append(("set", area_id, define_id, size))
        return 0


class FakeSim:
    def __init__(self):
        self._dll = FakeDll()
        self._handle = object()
        self.sink = None

    def set_client_data_sink(self, sink):
        self.sink = sink

    def run_on_dispatch(self, callback, wait=True, timeout=5.0):
        callback()

    @property
    def connected(self):
        return True


class BackendRegistryTest(unittest.TestCase):
    def setUp(self):
        self.sim = FakeSim()
        self.backend = SimConnectClientDataBackend(self.sim)

    def kinds(self):
        return [call[0] for call in self.sim._dll.calls]

    def test_area_and_definition_created_once(self):
        self.backend.ensure_area("MobiFlight.LVars", 272)
        self.backend.ensure_area("MobiFlight.LVars", 272)

        self.assertEqual(self.kinds(), ["map", "define"])
        self.assertEqual(self.sim._dll.calls[0][1], "MobiFlight.LVars")
        self.assertEqual(self.sim._dll.calls[1][2], 272)

    def test_new_size_adds_definition_without_remap(self):
        self.backend.ensure_area("MobiFlight.LVars", 136)
        self.backend.ensure_area("MobiFlight.LVars", 272)

        self.assertEqual(self.kinds(), ["map", "define", "define"])
        self.assertEqual(self.sim._dll.calls[2][2], 272)

    def test_request_uses_last_definition(self):
        self.backend.ensure_area("MobiFlight.LVars", 136)
        self.backend.ensure_area("MobiFlight.LVars", 272)
        self.backend.request_read("MobiFlight.LVars", 7)

        request = [call for call in self.sim._dll.calls if call[0] == "request"][-1]
        _kind, _area_id, request_id, _define_id, period = request
        self.assertEqual(request_id, 7)
        self.assertEqual(period, 1)  # SIMCONNECT_CLIENT_DATA_PERIOD_ONCE

    def test_write_sends_set_client_data(self):
        self.backend.ensure_area("MobiFlight.Command", 8)
        self.backend.write_area("MobiFlight.Command", b"abc\x00\x00\x00\x00\x00")

        set_call = [call for call in self.sim._dll.calls if call[0] == "set"][-1]
        self.assertEqual(set_call[3], 8)

    def test_payload_forwarded_to_sink(self):
        received = []
        self.backend.set_sink(lambda rid, data: received.append((rid, data)))
        self.sim.sink(42, b"payload")

        self.assertEqual(received, [(42, b"payload")])

    def test_reset_forgets_areas(self):
        self.backend.ensure_area("Area", 4)
        self.backend.reset()
        self.backend.ensure_area("Area", 4)

        maps = [call for call in self.sim._dll.calls if call[0] == "map"]
        self.assertEqual(len(maps), 2, "после reset область регистрируется заново")

    def test_request_without_area_fails(self):
        with self.assertRaises(SimConnectError):
            self.backend.request_read("Unknown.Area", 1)


if __name__ == "__main__":
    unittest.main()
