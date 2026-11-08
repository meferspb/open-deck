"""Тесты для реестра телеметрии."""

import unittest

from msfs_gateway import telemetry


class VariableRegistryTest(unittest.TestCase):
    def test_known_variables_have_required_fields(self):
        self.assertIn("power.batteryMaster", telemetry.VARIABLES)
        self.assertIn("attitude.pitchDeg", telemetry.VARIABLES)
        self.assertIn("autopilot.headingBugDeg", telemetry.VARIABLES)

    def test_writable_flags(self):
        self.assertTrue(telemetry.is_writable("power.batteryMaster"))
        self.assertTrue(telemetry.is_writable("autopilot.headingBugDeg"))
        # У переменной без sim_event нет команды записи.
        self.assertFalse(telemetry.is_writable("attitude.pitchDeg"))

    def test_unknown_key(self):
        self.assertIsNone(telemetry.get("does.not.exist"))
        self.assertFalse(telemetry.is_known("does.not.exist"))
        self.assertIsNone(telemetry.default_value("does.not.exist"))

    def test_heading_bug_is_param_event(self):
        variable = telemetry.get("autopilot.headingBugDeg")
        self.assertIsNotNone(variable)
        self.assertTrue(variable.sim_event_param)
        self.assertEqual(variable.sim_event, "HEADING_BUG_SET")

    def test_torque_and_radio_altitude_simvars(self):
        # Официальные SimVar MSFS: процент момента и радиовысота.
        self.assertEqual(
            telemetry.get("engine.torquePct").sim_var,
            "TURB ENG MAX TORQUE PERCENT:1",
        )
        self.assertEqual(
            telemetry.get("aircraft.radioAltitudeFt").sim_var,
            "RADIO HEIGHT",
        )

    def test_localizer_and_glide_slope_use_deviation_simvars(self):
        self.assertEqual(telemetry.get("nav.localizer").sim_var, "NAV CDI:1")
        self.assertEqual(
            telemetry.get("nav.glideSlope").sim_var,
            "NAV GLIDE SLOPE ERROR",
        )
        self.assertEqual(telemetry.get("nav.locFlag").sim_var, "HSI CDI NEEDLE VALID")
        self.assertEqual(telemetry.get("nav.gsFlag").sim_var, "HSI GSI NEEDLE VALID")


class CoerceTest(unittest.TestCase):
    def test_bool_from_many_forms(self):
        key = "power.batteryMaster"
        self.assertIs(telemetry.coerce(key, True), True)
        self.assertIs(telemetry.coerce(key, False), False)
        self.assertTrue(telemetry.coerce(key, 1))
        self.assertFalse(telemetry.coerce(key, 0))
        self.assertTrue(telemetry.coerce(key, "on"))
        self.assertFalse(telemetry.coerce(key, "OFF"))
        self.assertTrue(telemetry.coerce(key, "true"))

    def test_bool_rejects_garbage(self):
        with self.assertRaises(ValueError):
            telemetry.coerce("power.batteryMaster", "maybe")

    def test_number(self):
        self.assertEqual(telemetry.coerce("speed.iasKt", 108), 108.0)
        self.assertEqual(telemetry.coerce("speed.iasKt", "108.5"), 108.5)
        with self.assertRaises(ValueError):
            telemetry.coerce("speed.iasKt", "fast")

    def test_string(self):
        self.assertEqual(telemetry.coerce("aircraft.title", "C172"), "C172")
        self.assertEqual(telemetry.coerce("aircraft.title", None), "")


class EmptySnapshotTest(unittest.TestCase):
    def test_covers_all_keys(self):
        snapshot = telemetry.empty_snapshot()
        self.assertEqual(set(snapshot), set(telemetry.VARIABLES))
        self.assertIs(snapshot["power.batteryMaster"], False)
        self.assertEqual(snapshot["speed.iasKt"], 0.0)
        self.assertEqual(snapshot["aircraft.title"], "")


class VariablesCatalogTest(unittest.TestCase):
    def test_catalog_matches_registry(self):
        catalog = telemetry.variables_catalog()
        self.assertEqual(len(catalog), len(telemetry.VARIABLES))

        by_key = {item["key"]: item for item in catalog}
        self.assertEqual(set(by_key), set(telemetry.VARIABLES))

        battery = by_key["power.batteryMaster"]
        self.assertEqual(battery["kind"], "bool")
        self.assertTrue(battery["writable"])
        self.assertEqual(battery["simEvent"], "TOGGLE_MASTER_BATTERY")

        pitch = by_key["attitude.pitchDeg"]
        self.assertFalse(pitch["writable"])

    def test_catalog_has_stable_order(self):
        first = telemetry.variables_catalog()[0]["key"]
        self.assertEqual(first, "power.batteryMaster")


if __name__ == "__main__":
    unittest.main()
