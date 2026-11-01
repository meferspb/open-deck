"""HTTP-проверки API ассистента (mock-провайдер, без MSFS)."""

import http.client
import json
import tempfile
import time
import unittest
from pathlib import Path

from msfs_gateway.app import GatewayApplication
from msfs_gateway.settings import DEFAULT_WEB_DIR, Settings


class AssistHttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            host="127.0.0.1",
            port=0,
            web_dir=DEFAULT_WEB_DIR,
            profile_dir=Path(self.tmp.name),
            sim="mock",
            discovery=False,
            wasm=False,
            auth_path=Path(self.tmp.name) / "auth.json",
        )
        self.app = GatewayApplication(self.settings, check_integrity=False)
        self.app.start_background()
        self.port = self.app.httpd.server_address[1]
        # Даём потоку ассистента снять первый снимок телеметрии.
        time.sleep(0.3)

    def tearDown(self):
        self.app.shutdown()
        self.tmp.cleanup()

    def call(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = None
        headers = {}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            data = response.read()
            return response.status, json.loads(data) if data else None
        finally:
            conn.close()

    def test_status_reports_telemetry_and_limits(self):
        status, payload = self.call("GET", "/api/assist")
        self.assertEqual(status, 200)
        self.assertIn("telemetry", payload)
        self.assertIn("taxi", payload)
        self.assertIn("landing", payload)
        self.assertIn("limits", payload)
        self.assertIn("onGround", payload["telemetry"])
        self.assertIn("phase", payload["landing"])

    def test_taxi_refuses_airborne_mock(self):
        status, payload = self.call("POST", "/api/assist/taxi", {"action": "engage"})
        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertIn("земле", payload["message"])

    def test_taxi_speed_and_stop(self):
        status, payload = self.call("POST", "/api/assist/taxi", {"action": "speed", "value": 15})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertAlmostEqual(payload["status"]["taxi"]["targetSpeedKt"], 15.0)

        status, payload = self.call("POST", "/api/assist/taxi", {"action": "stop"})
        self.assertEqual(status, 200)
        self.assertIn("СТОП", payload["message"])
        time.sleep(0.3)  # снимок телеметрии обновляется потоком ассистента
        status, payload = self.call("GET", "/api/assist")
        self.assertTrue(payload["telemetry"]["parkingBrake"])

    def test_landing_arm_in_mock(self):
        status, payload = self.call("POST", "/api/assist/landing", {"action": "arm"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"]["landing"]["phase"], "armed")

        status, payload = self.call("POST", "/api/assist/landing", {"action": "toga"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"]["landing"]["phase"], "toga")

    def test_unknown_action_rejected(self):
        status, payload = self.call("POST", "/api/assist/taxi", {"action": "fly"})
        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
