"""Тесты TCP-фолбэка SimConnect (без настоящего DLL)."""

import os
import unittest
from pathlib import Path

from msfs_gateway.sim import simconnect as sc


def _bare_sim(host="127.0.0.1", port=19999):
    sim = object.__new__(sc.SimConnectSim)
    sim._host = host
    sim._port = port
    return sim


class GeneratedConfigTest(unittest.TestCase):
    def test_generates_cfg_in_temporary_cwd(self):
        sim = _bare_sim(port=19999)
        seen = {}

        def fake_open():
            seen["cwd"] = os.getcwd()
            seen["cfg"] = Path("SimConnect.cfg").read_text(encoding="ascii")

        sim._open = fake_open
        original = os.getcwd()

        self.assertTrue(sim._open_via_generated_config())
        self.assertEqual(os.getcwd(), original)
        self.assertNotEqual(seen["cwd"], original)
        self.assertIn("Protocol=IPv4", seen["cfg"])
        self.assertIn("Port=19999", seen["cfg"])
        self.assertIn("Address=127.0.0.1", seen["cfg"])

    def test_failure_returns_false_and_restores_cwd(self):
        sim = _bare_sim()

        def fake_open():
            raise sc.SimConnectError("нет связи")

        sim._open = fake_open
        original = os.getcwd()

        self.assertFalse(sim._open_via_generated_config())
        self.assertEqual(os.getcwd(), original)

    def test_custom_host_and_port_land_in_cfg(self):
        sim = _bare_sim(host="192.168.1.50", port=5000)
        seen = {}
        sim._open = lambda: seen.update(cfg=Path("SimConnect.cfg").read_text(encoding="ascii"))

        self.assertTrue(sim._open_via_generated_config())
        self.assertIn("Address=192.168.1.50", seen["cfg"])
        self.assertIn("Port=5000", seen["cfg"])


if __name__ == "__main__":
    unittest.main()
