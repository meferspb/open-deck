"""Тесты шины телеметрии (hub): кадр, команды, rate-limit."""

import json
import tempfile
import unittest
from pathlib import Path

from msfs_gateway import telemetry
from msfs_gateway.hub import COMMANDS_PER_SECOND, ClientInfo, Hub
from msfs_gateway.profiles import ProfileStore
from msfs_gateway.sim.base import SimProvider


class FakeSim(SimProvider):
    name = "fake"

    def __init__(self):
        self._values = telemetry.empty_snapshot()
        self._values["power.batteryMaster"] = False
        self.commands = []
        self.title = "Fake Aircraft"
        self.atc = None
        self.profile_ref = None

    @property
    def connected(self):
        return True

    @property
    def aircraft_title(self):
        return self.title

    @property
    def atc_model(self):
        return self.atc

    @property
    def profile_id(self):
        return self.profile_ref

    def start(self):
        pass

    def stop(self):
        pass

    def read(self):
        return dict(self._values)

    def apply_command(self, key, value):
        self.commands.append((key, value))
        self._values[key] = telemetry.coerce(key, value)


class BuildMessageTest(unittest.TestCase):
    def setUp(self):
        self.sim = FakeSim()
        with tempfile.TemporaryDirectory() as tmp:
            self.store = ProfileStore(Path(tmp))
            self.hub = Hub(self.sim, self.store, hz=30.0)

    def test_message_has_full_values_and_meta(self):
        message = self.hub.build_message()
        self.assertEqual(message["type"], "telemetry")
        self.assertEqual(message["sim"]["provider"], "fake")
        self.assertIn("seq", message)
        self.assertIn("ts", message)
        # Полный набор ключей независимо от провайдера.
        self.assertEqual(set(message["values"]), set(telemetry.VARIABLES))

    def test_seq_increments(self):
        first = self.hub.build_message()["seq"]
        second = self.hub.build_message()["seq"]
        self.assertEqual(second, first + 1)


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.sim = FakeSim()
        with tempfile.TemporaryDirectory() as tmp:
            self.store = ProfileStore(Path(tmp))
            self.hub = Hub(self.sim, self.store, hz=30.0)

    def test_valid_command_applies(self):
        ack = self.hub.handle_command("power.batteryMaster", True, "id-1")
        self.assertTrue(ack["ok"])
        self.assertIs(ack["value"], True)
        self.assertEqual(self.sim.commands, [("power.batteryMaster", True)])

    def test_unknown_key_nack(self):
        ack = self.hub.handle_command("nope.missing", 1, "id-2")
        self.assertFalse(ack["ok"])
        self.assertEqual(
            ack["code"], "not_writable" if not telemetry.is_known("nope.missing") else "invalid_key"
        )

    def test_not_writable_nack(self):
        ack = self.hub.handle_command("attitude.pitchDeg", 5, "id-3")
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["code"], "not_writable")

    def test_invalid_value_nack(self):
        ack = self.hub.handle_command("power.batteryMaster", "maybe", "id-4")
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["code"], "invalid_value")

    def test_rate_limit(self):
        client = ClientInfo(connection=object(), client_id="test-client")  # type: ignore[arg-type]
        # Первые COMMANDS_PER_SECOND команд проходят.
        for i in range(COMMANDS_PER_SECOND):
            ack = self.hub.handle_command("power.batteryMaster", True, f"r{i}", client=client)
            self.assertTrue(ack["ok"])
        # Следующая — отказ.
        ack = self.hub.handle_command("power.batteryMaster", True, "overflow", client=client)
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["code"], "rate_limited")


CUSTOM_PROFILE = {
    "schemaVersion": 1,
    "id": "custom-aircraft",
    "name": "Custom Aircraft",
    "sim": {"match": {"title": "Custom Aircraft*"}},
    "panel": {"background": "#0b1117"},
    "variables": [
        {
            "key": "custom.fuelLbs",
            "kind": "number",
            "source": "lvar",
            "name": "FUEL_LBS",
            "initial": 100,
        }
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


class CustomVariablesHubTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.tmp.name))
        self.store.save(CUSTOM_PROFILE)
        self.sim = FakeSim()
        self.sim.title = "Custom Aircraft - Test"
        self.hub = Hub(self.sim, self.store, hz=30.0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reader_values_merged_into_frame(self):
        calls = []

        def reader(specs):
            calls.append(specs)
            return {"custom.fuelLbs": 4321.5}

        self.hub.set_custom_reader(reader)
        message = self.hub.build_message()

        self.assertIsNotNone(message["sim"]["profileId"])
        self.assertEqual(message["values"]["custom.fuelLbs"], 4321.5)
        self.assertEqual(len(calls), 1)

    def test_reader_is_throttled(self):
        calls = []

        def reader(specs):
            calls.append(1)
            return {"custom.fuelLbs": 1.0}

        self.hub.set_custom_reader(reader)
        self.hub.build_message()
        self.hub.build_message()
        self.hub.build_message()
        self.assertEqual(len(calls), 1, "повторные кадры берут значение из кэша")

    def test_reader_errors_do_not_break_frame(self):
        def broken(specs):
            raise RuntimeError("мост недоступен")

        self.hub.set_custom_reader(broken)
        message = self.hub.build_message()
        self.assertIn("values", message)
        self.assertNotIn("custom.fuelLbs", message["values"])

    def test_provider_extra_keys_pass_through(self):
        self.sim._values["custom.providerValue"] = 7.5
        message = self.hub.build_message()
        self.assertEqual(message["values"]["custom.providerValue"], 7.5)


class AnnounceAircraftTest(unittest.TestCase):
    """Регрессия: announce_aircraft не должен отдавать закэшированный старый борт."""

    class _Connection:
        peer = "test"

        def __init__(self):
            self.messages = []

        def send_text(self, text):
            self.messages.append(json.loads(text))

        def close(self, *args, **kwargs):
            pass

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.tmp.name))
        self.sim = FakeSim()
        self.hub = Hub(self.sim, self.store, hz=30.0)
        self.connection = self._Connection()
        self.hub.attach(self.connection)  # hello

    def tearDown(self):
        self.tmp.cleanup()

    def test_aircraft_message_carries_new_profile(self):
        self.sim.profile_ref = "old-aircraft"
        self.hub.build_message()  # прогреваем кэш последнего кадра
        self.assertEqual(self.hub.latest_message()["sim"]["profileId"], "old-aircraft")

        self.sim.profile_ref = "new-aircraft"
        self.hub.announce_aircraft()

        aircraft = [m for m in self.connection.messages if m["type"] == "aircraft"]
        self.assertTrue(aircraft)
        self.assertEqual(aircraft[-1]["profileId"], "new-aircraft")


class FailingSim(FakeSim):
    """Провайдер, который падает как SimConnect: не SimCommandError."""

    def read(self):
        raise RuntimeError("SimConnect недоступен")

    def apply_command(self, key, value):
        raise OSError("TransmitClientEvent failed")


class ResilienceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.tmp.name))
        self.hub = Hub(FailingSim(), self.store, hz=30.0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_message_survives_provider_failure(self):
        message = self.hub.build_message()
        self.assertIn("values", message)
        # Кадр всё равно содержит полный набор встроенных ключей.
        self.assertEqual(set(message["values"]), set(telemetry.VARIABLES))

    def test_command_failure_returns_nack(self):
        ack = self.hub.handle_command("power.batteryMaster", True, "boom")
        self.assertFalse(ack["ok"])
        self.assertEqual(ack["code"], "sim_error")


def _write_profile(directory, profile_id, name, match):
    payload = {
        "schemaVersion": 1,
        "id": profile_id,
        "name": name,
        "sim": {"match": match},
        "panel": {"background": "#000000"},
        "widgets": [
            {
                "id": "battery",
                "type": "switch.toggle",
                "bindings": {"state": "power.batteryMaster"},
                "command": {"key": "power.batteryMaster", "action": "set"},
                "layout": {"base": {"x": 0, "y": 0, "w": 0.2, "h": 0.2}},
            }
        ],
    }
    (Path(directory) / f"{profile_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


class AutoDetectTest(unittest.TestCase):
    """Автоопределение профиля по TITLE и ATC MODEL."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        _write_profile(
            self.tmp.name,
            "cessna",
            "Cessna 172",
            {"title": "Cessna Skyhawk*", "atcModel": "C172"},
        )
        _write_profile(self.tmp.name, "piper", "Piper PA-28", {"title": "Piper PA-28*"})
        self.store = ProfileStore(Path(self.tmp.name))
        self.sim = FakeSim()
        self.hub = Hub(self.sim, self.store, hz=30.0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_match_by_title(self):
        self.assertEqual(self.hub._match_profile("Cessna Skyhawk SP", None), "cessna")

    def test_match_by_atc_model(self):
        self.assertEqual(self.hub._match_profile("Some livery", "C172"), "cessna")

    def test_match_unknown_aircraft(self):
        self.assertIsNone(self.hub._match_profile("Boeing 737", "B738"))

    def test_telemetry_reports_detected_profile(self):
        self.sim.title = "Piper PA-28-181 Archer II"
        message = self.hub.build_message()
        self.assertEqual(message["sim"]["profileId"], "piper")
        self.assertEqual(message["sim"]["aircraftTitle"], "Piper PA-28-181 Archer II")

    def test_override_pins_manual_choice(self):
        self.sim.title = "Cessna Skyhawk SP"
        self.hub.set_profile_override("piper")
        self.assertEqual(self.hub.build_message()["sim"]["profileId"], "piper")

    def test_override_cleared_when_aircraft_changes(self):
        self.sim.title = "Cessna Skyhawk SP"
        self.hub.set_profile_override("piper")
        self.assertEqual(self.hub.build_message()["sim"]["profileId"], "piper")

        # Загрузили другой борт — ручной выбор уступает автоопределению.
        self.sim.title = "Cessna Skyhawk 172N"
        self.assertEqual(self.hub.build_message()["sim"]["profileId"], "cessna")

    def test_telemetry_carries_atc_model(self):
        self.sim.atc = "C172"
        self.sim.title = "Some livery"
        message = self.hub.build_message()
        self.assertEqual(message["sim"]["atcModel"], "C172")
        self.assertEqual(message["sim"]["profileId"], "cessna")


if __name__ == "__main__":
    unittest.main()
