"""Тесты валидации профилей и загрузки встроенных профилей."""

import unittest
from pathlib import Path

from msfs_gateway.legacy import adapt, looks_legacy
from msfs_gateway.profiles import (
    ProfileError,
    ProfileStore,
    custom_variable_specs,
    validate_profile,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "profiles"


def _minimal_profile(**overrides):
    profile = {
        "schemaVersion": 1,
        "id": "test-aircraft",
        "name": "Test Aircraft",
        "panel": {"background": "#0b1117"},
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
    profile.update(overrides)
    return profile


class ValidateProfileTest(unittest.TestCase):
    def test_minimal_is_valid(self):
        self.assertEqual(validate_profile(_minimal_profile()), [])

    def test_rejects_unknown_widget_type(self):
        errors = validate_profile(
            _minimal_profile(
                widgets=[
                    {
                        "id": "bad-widget",
                        "type": "flux_capacitor",
                        "bindings": {"value": "speed.iasKt"},
                        "layout": {"base": {"x": 0, "y": 0, "w": 0.1, "h": 0.1}},
                    },
                ]
            )
        )
        self.assertTrue(any("type" in e for e in errors))

    def test_rejects_unknown_binding_key(self):
        errors = validate_profile(
            _minimal_profile(
                widgets=[
                    {
                        "id": "bad-binding",
                        "type": "readout",
                        "bindings": {"value": "nope.missing"},
                        "layout": {"base": {"x": 0, "y": 0, "w": 0.1, "h": 0.1}},
                    },
                ]
            )
        )
        self.assertTrue(any("bindings.value" in e for e in errors))

    def test_rejects_non_writable_command(self):
        errors = validate_profile(
            _minimal_profile(
                widgets=[
                    {
                        "id": "bad-command",
                        "type": "switch.toggle",
                        "bindings": {"state": "power.batteryMaster"},
                        "command": {"key": "attitude.pitchDeg", "action": "set"},
                        "layout": {"base": {"x": 0, "y": 0, "w": 0.1, "h": 0.1}},
                    },
                ]
            )
        )
        self.assertTrue(any("command.key" in e for e in errors))

    def test_rejects_rect_out_of_bounds(self):
        errors = validate_profile(
            _minimal_profile(
                widgets=[
                    {
                        "id": "bad-rect",
                        "type": "readout",
                        "bindings": {"value": "speed.iasKt"},
                        "layout": {"base": {"x": 0.9, "y": 0.9, "w": 0.5, "h": 0.5}},
                    },
                ]
            )
        )
        self.assertTrue(any("layout.base" in e for e in errors))

    def test_requires_attitude_pitch_bank(self):
        errors = validate_profile(
            _minimal_profile(
                widgets=[
                    {
                        "id": "bad-attitude",
                        "type": "attitude",
                        "bindings": {"pitch": "attitude.pitchDeg"},
                        "layout": {"base": {"x": 0, "y": 0, "w": 0.1, "h": 0.1}},
                    },
                ]
            )
        )
        self.assertTrue(any("bank" in e for e in errors))


class BundledProfilesTest(unittest.TestCase):
    def test_bundled_profiles_load_and_validate(self):
        store = ProfileStore(PROFILES_DIR)
        summaries = store.list_summaries()
        self.assertGreaterEqual(len(summaries), 2)

        ids = {summary["id"] for summary in summaries}
        self.assertIn("cessna-172-skyhawk", ids)
        self.assertIn("piper-pa28-archer-ii", ids)

        for summary in summaries:
            profile = store.get(summary["id"])
            self.assertEqual(validate_profile(profile), [])
            self.assertGreaterEqual(len(profile["widgets"]), 3)


class CustomVariablesTest(unittest.TestCase):
    def _profile(self, variables, widgets=None):
        return _minimal_profile(
            variables=variables,
            widgets=widgets
            or [
                {
                    "id": "custom-readout",
                    "type": "readout",
                    "bindings": {"value": "custom.fuelLbs"},
                    "layout": {"base": {"x": 0, "y": 0, "w": 0.2, "h": 0.1}},
                }
            ],
        )

    def test_valid_lvar_variable_and_binding(self):
        profile = self._profile(
            [
                {
                    "key": "custom.fuelLbs",
                    "kind": "number",
                    "source": "lvar",
                    "name": "PMDG_FUEL_LBS",
                    "unit": "lbs",
                    "initial": 1200,
                }
            ]
        )
        self.assertEqual(validate_profile(profile), [])

    def test_valid_rpn_variable(self):
        profile = self._profile(
            [
                {
                    "key": "custom.fuelLbs",
                    "kind": "number",
                    "source": "rpn",
                    "expression": "(A:CABIN ALTITUDE, feet)",
                }
            ]
        )
        self.assertEqual(validate_profile(profile), [])

    def test_binding_to_unknown_key_still_rejected(self):
        profile = self._profile(
            [{"key": "custom.fuelLbs", "kind": "number", "source": "lvar", "name": "FUEL"}],
            widgets=[
                {
                    "id": "bad",
                    "type": "readout",
                    "bindings": {"value": "custom.unknown"},
                    "layout": {"base": {"x": 0, "y": 0, "w": 0.2, "h": 0.1}},
                }
            ],
        )
        self.assertTrue(any("bindings.value" in error for error in validate_profile(profile)))

    def test_duplicate_key_rejected(self):
        profile = self._profile(
            [
                {"key": "custom.fuelLbs", "kind": "number", "source": "lvar", "name": "A"},
                {"key": "custom.fuelLbs", "kind": "number", "source": "lvar", "name": "B"},
            ]
        )
        self.assertTrue(any("повторяется" in error for error in validate_profile(profile)))

    def test_key_collision_with_builtin_rejected(self):
        profile = self._profile(
            [{"key": "power.batteryMaster", "kind": "bool", "source": "lvar", "name": "A"}]
        )
        self.assertTrue(any("занят" in error for error in validate_profile(profile)))

    def test_bad_key_rejected(self):
        profile = self._profile(
            [{"key": "Custom Key", "kind": "number", "source": "lvar", "name": "A"}]
        )
        self.assertTrue(any("variables[0].key" in error for error in validate_profile(profile)))

    def test_bad_source_rejected(self):
        profile = self._profile([{"key": "custom.x", "kind": "number", "source": "magic"}])
        self.assertTrue(any("source" in error for error in validate_profile(profile)))

    def test_lvar_requires_name_and_rpn_requires_expression(self):
        lvar = self._profile([{"key": "custom.x", "kind": "number", "source": "lvar"}])
        rpn = self._profile([{"key": "custom.y", "kind": "number", "source": "rpn"}])
        self.assertTrue(any("name" in error for error in validate_profile(lvar)))
        self.assertTrue(any("expression" in error for error in validate_profile(rpn)))

    def test_initial_type_must_match_kind(self):
        profile = self._profile(
            [
                {
                    "key": "custom.x",
                    "kind": "number",
                    "source": "lvar",
                    "name": "A",
                    "initial": "nope",
                }
            ]
        )
        self.assertTrue(any("initial" in error for error in validate_profile(profile)))

    def test_specs_normalized(self):
        profile = self._profile(
            [
                {
                    "key": "custom.fuelLbs",
                    "kind": "number",
                    "source": "lvar",
                    "name": "FUEL",
                    "initial": 10,
                },
                {"key": "custom.cabinAlt", "kind": "number", "source": "rpn", "expression": "X"},
            ]
        )
        specs = custom_variable_specs(profile)
        self.assertEqual(len(specs), 2)
        self.assertEqual(
            specs[0],
            {
                "key": "custom.fuelLbs",
                "kind": "number",
                "source": "lvar",
                "initial": 10,
                "name": "FUEL",
            },
        )
        self.assertEqual(specs[1]["expression"], "X")


class LegacyAdapterTest(unittest.TestCase):
    def test_detects_legacy(self):
        self.assertTrue(looks_legacy({"aircraft_id": "x", "bindings": []}))
        self.assertFalse(looks_legacy(_minimal_profile()))

    def test_adapts_battery_switch(self):
        legacy = {
            "aircraft_id": "cessna_172",
            "title": "Cessna 172 Skyhawk",
            "layout": {"canvas": {"width": 1000, "height": 1000}},
            "bindings": [
                {
                    "id": "master_battery",
                    "type": "toggle_switch",
                    "sim_var": "ELECTRICAL MASTER BATTERY",
                    "write_event": "TOGGLE_MASTER_BATTERY",
                    "position": {"x": 100, "y": 200, "w": 100, "h": 200},
                }
            ],
        }
        adapted = adapt(legacy)
        self.assertEqual(adapted["schemaVersion"], 1)
        self.assertEqual(adapted["widgets"][0]["type"], "switch.toggle")
        self.assertEqual(adapted["widgets"][0]["bindings"]["state"], "power.batteryMaster")
        self.assertEqual(adapted["widgets"][0]["command"]["key"], "power.batteryMaster")
        rect = adapted["widgets"][0]["layout"]["base"]
        self.assertAlmostEqual(rect["x"], 0.1)
        self.assertAlmostEqual(rect["y"], 0.2)
        self.assertAlmostEqual(rect["w"], 0.1)
        self.assertAlmostEqual(rect["h"], 0.2)

    def test_adapt_rejects_unknown_simvar(self):
        legacy = {
            "aircraft_id": "x",
            "bindings": [
                {
                    "id": "b",
                    "type": "toggle_switch",
                    "sim_var": "NOT A REAL SIMVAR",
                    "position": {"x": 0, "y": 0, "w": 10, "h": 10},
                },
            ],
        }
        with self.assertRaises(ProfileError):
            adapt(legacy)


if __name__ == "__main__":
    unittest.main()
