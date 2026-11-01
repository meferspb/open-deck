"""Тесты ассистента посадки и руления (без MSFS)."""

import unittest

from msfs_gateway.assist import (
    FLARE_START_FT,
    TAXI_SPEED_MAX_KT,
    TAXI_SPEED_MIN_KT,
    AssistManager,
    AssistSnapshot,
    LandingAssist,
    TaxiAssist,
    wrap180,
)


class Sink:
    def __init__(self):
        self.commands = []

    def __call__(self, key, value):
        self.commands.append((key, value))
        return True

    def last(self, key):
        for name, value in reversed(self.commands):
            if name == key:
                return value
        return None


def base_values(**overrides):
    values = {
        "aircraft.onGround": True,
        "aircraft.radioAltitudeFt": 0.0,
        "groundSpeed.kt": 0.0,
        "speed.iasKt": 0.0,
        "heading.magneticDeg": 90.0,
        "nav.localizer": 0.0,
        "nav.glideSlope": 0.0,
        "nav.locFlag": False,
        "nav.gsFlag": False,
        "autopilot.master": False,
        "autopilot.approach": False,
        "controls.throttlePct": 0.0,
        "controls.rudder": 0.0,
        "brakes.parking": False,
        "verticalSpeed.fpm": 0.0,
    }
    values.update(overrides)
    return values


class WrapTest(unittest.TestCase):
    def test_wrap180(self):
        self.assertEqual(wrap180(0), 0)
        self.assertEqual(wrap180(190), -170)
        self.assertEqual(wrap180(-190), 170)
        self.assertEqual(wrap180(360), 0)


class TaxiTest(unittest.TestCase):
    def setUp(self):
        self.sink = Sink()
        self.taxi = TaxiAssist(self.sink)

    def test_engage_requires_ground(self):
        ok, message = self.taxi.engage(base_values(**{"aircraft.onGround": False}))
        self.assertFalse(ok)
        self.assertIn("не на земле", message)

    def test_engage_requires_parking_brake_off(self):
        ok, message = self.taxi.engage(base_values(**{"brakes.parking": True}))
        self.assertFalse(ok)
        self.assertIn("тормоз", message)

    def test_engage_sets_heading(self):
        ok, _ = self.taxi.engage(base_values(**{"heading.magneticDeg": "bad"}))
        self.assertTrue(ok)
        self.assertEqual(self.taxi.status.target_heading_deg, 0.0)

    def test_speed_limits(self):
        self.taxi.set_speed(1)
        self.assertEqual(self.taxi.status.target_speed_kt, TAXI_SPEED_MIN_KT)
        self.taxi.set_speed(100)
        self.assertEqual(self.taxi.status.target_speed_kt, TAXI_SPEED_MAX_KT)
        ok, _ = self.taxi.set_speed("abc")
        self.assertFalse(ok)

    def test_heading_nudge_wraps(self):
        self.taxi.status.target_heading_deg = 355
        self.taxi.nudge_heading(10)
        self.assertEqual(self.taxi.status.target_heading_deg, 5.0)

    def test_update_emits_throttle_and_rudder(self):
        self.taxi.engage(base_values())
        self.taxi.status.target_speed_kt = 12
        self.taxi.status.target_heading_deg = 120
        self.taxi.update(0.1, base_values(heading=90.0))
        throttle = self.sink.last("controls.throttlePct")
        rudder = self.sink.last("controls.rudder")
        self.assertIsNotNone(throttle)
        self.assertGreater(throttle, 0)
        self.assertIsNotNone(rudder)
        self.assertGreater(rudder, 0)  # курс правее — руль вправо
        # Значения в разумных пределах.
        self.assertLessEqual(throttle, 55)
        self.assertLessEqual(abs(rudder), 70)

    def test_disengages_when_airborne(self):
        self.taxi.engage(base_values())
        self.taxi.update(0.1, base_values(**{"aircraft.onGround": False}))
        self.assertFalse(self.taxi.status.engaged)
        self.assertEqual(self.sink.last("controls.throttlePct"), 0)

    def test_disengages_on_overspeed(self):
        self.taxi.engage(base_values())
        self.taxi.update(0.1, base_values(**{"groundSpeed.kt": 50.0}))
        self.assertFalse(self.taxi.status.engaged)

    def test_stop_applies_parking_brake(self):
        self.taxi.engage(base_values())
        ok, _ = self.taxi.stop()
        self.assertTrue(ok)
        self.assertFalse(self.taxi.status.engaged)
        self.assertEqual(self.sink.last("controls.throttlePct"), 0)
        self.assertTrue(self.sink.last("brakes.parking"))


class LandingTest(unittest.TestCase):
    def setUp(self):
        self.sink = Sink()
        self.landing = LandingAssist(self.sink)

    def test_arm_refuses_on_ground(self):
        ok, message = self.landing.arm(base_values(**{"aircraft.onGround": True}))
        self.assertFalse(ok)
        self.assertIn("на земле", message)

    def test_arm_refuses_low_speed(self):
        ok, message = self.landing.arm(
            base_values(**{"aircraft.onGround": False, "speed.iasKt": 20.0})
        )
        self.assertFalse(ok)
        self.assertIn("40", message)

    def test_arm_sends_ap_and_apr(self):
        ok, _ = self.landing.arm(base_values(**{"aircraft.onGround": False, "speed.iasKt": 120.0}))
        self.assertTrue(ok)
        self.assertEqual(self.landing.status.phase, "armed")
        self.assertTrue(self.sink.last("autopilot.master"))
        self.assertTrue(self.sink.last("autopilot.approachHold"))

    def test_approach_and_flare(self):
        values = base_values(
            **{
                "aircraft.onGround": False,
                "speed.iasKt": 120.0,
                "aircraft.radioAltitudeFt": 400.0,
            }
        )
        self.landing.arm(values)
        self.landing.update(0.1, {**values, "autopilot.approach": True})
        self.assertEqual(self.landing.status.phase, "approach")

        self.landing.update(0.1, {**values, "aircraft.radioAltitudeFt": FLARE_START_FT - 5})
        self.assertEqual(self.landing.status.phase, "flare")
        self.assertGreater(self.landing.status.throttle_pct, 0)

        self.landing.update(0.1, {**values, "aircraft.radioAltitudeFt": 5})
        self.assertEqual(self.landing.status.throttle_pct, 0)

    def test_touchdown_turns_off_ap_and_throttle(self):
        values = base_values(
            **{
                "aircraft.onGround": False,
                "speed.iasKt": 120.0,
                "aircraft.radioAltitudeFt": 40.0,
            }
        )
        self.landing.arm(values)
        self.landing.update(0.1, values)
        self.landing.update(
            0.1,
            {
                **values,
                "aircraft.onGround": True,
                "aircraft.radioAltitudeFt": 0,
                "groundSpeed.kt": 20.0,
            },
        )
        self.assertEqual(self.landing.status.phase, "rollout")
        self.assertFalse(self.sink.last("autopilot.master"))
        self.assertEqual(self.sink.last("controls.throttlePct"), 0)

    def test_rollout_finishes(self):
        values = base_values(**{"aircraft.onGround": True, "speed.iasKt": 0})
        self.landing.status.phase = "rollout"
        self.landing.update(0.1, {**values, "groundSpeed.kt": 2.0})
        self.assertEqual(self.landing.status.phase, "done")

    def test_toga(self):
        self.landing.arm(base_values(**{"aircraft.onGround": False, "speed.iasKt": 120.0}))
        ok, _ = self.landing.toga()
        self.assertTrue(ok)
        self.assertEqual(self.landing.status.phase, "toga")
        self.assertEqual(self.sink.last("controls.throttlePct"), 100)
        self.assertFalse(self.sink.last("autopilot.master"))


class FakeSim:
    def __init__(self, values):
        self.values = values

    def read(self):
        return dict(self.values)


class FakeHub:
    def __init__(self, values):
        self.sim = FakeSim(values)
        self.commands = []

    def apply_assist_command(self, key, value):
        self.commands.append((key, value))


class ManagerTest(unittest.TestCase):
    def setUp(self):
        self.hub = FakeHub(base_values())
        self.manager = AssistManager(self.hub)
        self.manager._snapshot = AssistSnapshot(values=base_values())

    def test_taxi_actions(self):
        ok, _ = self.manager.taxi_action({"action": "engage"})
        self.assertTrue(ok)
        ok, _ = self.manager.taxi_action({"action": "speed", "value": 15})
        self.assertTrue(ok)
        self.assertAlmostEqual(self.manager.status()["taxi"]["targetSpeedKt"], 15.0)
        ok, _ = self.manager.taxi_action({"action": "heading", "delta": 10})
        self.assertTrue(ok)
        ok, _ = self.manager.taxi_action({"action": "stop"})
        self.assertTrue(ok)
        self.assertIn(("brakes.parking", True), self.hub.commands)

    def test_unknown_action(self):
        ok, message = self.manager.taxi_action({"action": "fly"})
        self.assertFalse(ok)
        self.assertIn("Неизвестное", message)

    def test_landing_actions(self):
        values = base_values(**{"aircraft.onGround": False, "speed.iasKt": 120.0})
        self.manager._snapshot = AssistSnapshot(values=values)
        ok, _ = self.manager.landing_action({"action": "arm"})
        self.assertTrue(ok)
        self.assertEqual(self.manager.status()["landing"]["phase"], "armed")
        ok, _ = self.manager.landing_action({"action": "toga"})
        self.assertTrue(ok)

    def test_status_shape(self):
        status = self.manager.status()
        self.assertIn("telemetry", status)
        self.assertIn("taxi", status)
        self.assertIn("landing", status)
        self.assertIn("limits", status)


if __name__ == "__main__":
    unittest.main()
