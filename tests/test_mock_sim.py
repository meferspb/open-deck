"""Тесты mock-провайдера: команды и пользовательские переменные профиля."""

import json
import tempfile
import unittest
from pathlib import Path

from msfs_gateway.profiles import ProfileStore
from msfs_gateway.sim.base import SimCommandError
from msfs_gateway.sim.mock import MockSim

PROFILE = {
    "schemaVersion": 1,
    "id": "lvar-demo",
    "name": "LVAR Demo",
    "panel": {"background": "#0b1117"},
    "variables": [
        {
            "key": "custom.fuelLbs",
            "kind": "number",
            "source": "lvar",
            "name": "PMDG_FUEL_LBS",
            "initial": 1200,
        },
        {
            "key": "custom.apuOn",
            "kind": "bool",
            "source": "lvar",
            "name": "PMDG_APU_ON",
            "initial": True,
        },
    ],
    "widgets": [
        {
            "id": "fuel",
            "type": "readout",
            "bindings": {"value": "custom.fuelLbs"},
            "layout": {"base": {"x": 0, "y": 0, "w": 0.2, "h": 0.1}},
        }
    ],
}

SECOND_PROFILE = {
    "schemaVersion": 1,
    "id": "plain-demo",
    "name": "Plain Demo",
    "panel": {"background": "#0b1117"},
    "widgets": [
        {
            "id": "ias",
            "type": "readout",
            "bindings": {"value": "speed.iasKt"},
            "layout": {"base": {"x": 0, "y": 0, "w": 0.2, "h": 0.1}},
        }
    ],
}


class MockCustomVariablesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "lvar-demo.json").write_text(json.dumps(PROFILE), encoding="utf-8")
        (root / "plain-demo.json").write_text(json.dumps(SECOND_PROFILE), encoding="utf-8")
        self.store = ProfileStore(root)
        self.sim = MockSim(self.store)

    def tearDown(self):
        self.sim.stop()
        self.tmp.cleanup()

    def test_initial_values_available(self):
        values = self.sim.read()
        self.assertEqual(values["custom.fuelLbs"], 1200.0)
        self.assertIs(values["custom.apuOn"], True)

    def test_switching_aircraft_drops_custom_keys(self):
        self.sim.select_aircraft("plain-demo")
        values = self.sim.read()
        self.assertNotIn("custom.fuelLbs", values)
        self.assertNotIn("custom.apuOn", values)
        self.assertIn("speed.iasKt", values)

    def test_commands_still_work(self):
        self.sim.apply_command("power.batteryMaster", True)
        self.assertIs(self.sim.read()["power.batteryMaster"], True)

    def test_non_writable_rejected(self):
        with self.assertRaises(SimCommandError):
            self.sim.apply_command("speed.iasKt", 100)


if __name__ == "__main__":
    unittest.main()
