"""Тесты строковых датумов SimConnect (TITLE / ATC MODEL)."""

import ctypes
import threading
import unittest

from msfs_gateway.sim import simconnect as sc


def _make_sim(values=None):
    sim = object.__new__(sc.SimConnectSim)
    sim._values = dict(values or {})
    sim._lock = threading.RLock()
    sim._data_keys = []
    sim._last_data_at = 0.0
    return sim


def _dispatch(sim, define_id, payload, count=1, extra_offset=0):
    total = sc._DATA_OFFSET + extra_offset + len(payload)
    buffer = ctypes.create_string_buffer(total)
    message = sc._RecvSimObjectData.from_buffer(buffer)
    message.dwID = sc.SIMCONNECT_RECV_ID_SIMOBJECT_DATA
    message.dwRequestID = 1
    message.dwDefineID = define_id
    message.dwDefineCount = count
    ctypes.memmove(
        ctypes.addressof(buffer) + sc._DATA_OFFSET + extra_offset,
        payload,
        len(payload),
    )
    sim._handle_data(ctypes.cast(buffer, ctypes.POINTER(sc._Recv)), total)


class DecodeStringTest(unittest.TestCase):
    def test_stops_at_nul(self):
        self.assertEqual(sc.decode_string(b"Cessna Skyhawk SP\x00\x00\x00"), "Cessna Skyhawk SP")

    def test_strips_spaces(self):
        self.assertEqual(sc.decode_string(b"  C172  \x00"), "C172")

    def test_empty(self):
        self.assertEqual(sc.decode_string(b""), "")
        self.assertEqual(sc.decode_string(b"\x00\x00"), "")

    def test_non_utf8_falls_back(self):
        # Кириллица в кодировке Windows-1251 не должна ронять разбор.
        self.assertEqual(sc.decode_string(b"\xcf\xf3\xeb\xea\xee\xe2\xee\x00"), "Пулково")


class HandleStringDatumTest(unittest.TestCase):
    def test_title_is_stored(self):
        sim = _make_sim()
        _dispatch(sim, sc._TITLE_DEFINE_ID, b"Airbus A320neo\x00")
        self.assertEqual(sim._values["aircraft.title"], "Airbus A320neo")
        self.assertEqual(sim.aircraft_title, "Airbus A320neo")

    def test_atc_model_is_stored(self):
        sim = _make_sim()
        _dispatch(sim, sc._ATC_DEFINE_ID, b"C172\x00")
        self.assertEqual(sim._values["aircraft.atcModel"], "C172")
        self.assertEqual(sim.atc_model, "C172")

    def test_empty_string_is_ignored(self):
        sim = _make_sim()
        _dispatch(sim, sc._TITLE_DEFINE_ID, b"\x00\x00\x00")
        self.assertNotIn("aircraft.title", sim._values)

    def test_padding_after_string_is_ignored(self):
        sim = _make_sim()
        # Строка 256 байт с мусором после NUL — берём только текст до NUL.
        _dispatch(sim, sc._TITLE_DEFINE_ID, b"Cessna\x00garbage", count=1)
        self.assertEqual(sim._values["aircraft.title"], "Cessna")


class NumericDatumStillWorksTest(unittest.TestCase):
    def test_speed_is_parsed(self):
        sim = _make_sim()
        sim._data_keys = ["speed.iasKt"]
        sim._values = {"speed.iasKt": 0.0}
        payload = ctypes.c_double(108.5)
        raw = bytes(memoryview(payload).cast("B"))
        _dispatch(sim, sc._DEFINE_ID, raw, count=1)
        self.assertAlmostEqual(sim._values["speed.iasKt"], 108.5, places=3)
        self.assertGreater(sim._last_data_at, 0.0)


if __name__ == "__main__":
    unittest.main()
