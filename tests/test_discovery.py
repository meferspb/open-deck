"""Тесты автообнаружения хоста (UDP broadcast)."""

import json
import socket
import threading
import unittest

from msfs_gateway.discovery import (
    BEACON_TYPE,
    PROTOCOL_VERSION,
    DiscoveryBeacon,
    listen_once,
)


class _FakeProfiles:
    def __init__(self, summaries):
        self.summaries = summaries

    def list_summaries(self):
        return self.summaries


class PayloadTest(unittest.TestCase):
    def test_payload_fields(self):
        beacon = DiscoveryBeacon(
            http_port=8760,
            telemetry_hz=30.0,
            profiles_provider=_FakeProfiles(
                [{"id": "cessna-172-skyhawk"}, {"id": "piper-pa28-archer-ii"}]
            ).list_summaries,
        )
        payload = beacon.payload()
        self.assertEqual(payload["type"], BEACON_TYPE)
        self.assertEqual(payload["protocol"], PROTOCOL_VERSION)
        self.assertEqual(payload["httpPort"], 8760)
        self.assertEqual(payload["telemetryHz"], 30.0)
        self.assertEqual(payload["profiles"], ["cessna-172-skyhawk", "piper-pa28-archer-ii"])
        self.assertIn("name", payload)
        self.assertIn("ts", payload)

    def test_payload_without_provider(self):
        beacon = DiscoveryBeacon(http_port=8760)
        self.assertEqual(beacon.payload()["profiles"], [])

    def test_payload_is_json_serializable_and_small(self):
        beacon = DiscoveryBeacon(http_port=8760)
        raw = json.dumps(beacon.payload(), ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.assertLessEqual(len(raw), 1400)


class ListenOnceTest(unittest.TestCase):
    def test_receives_broadcast_on_loopback(self):
        port = 8871
        received = []

        def listener():
            payload = listen_once(timeout=4.0, port=port)
            received.append(payload)

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()

        # Даём слушателю занять порт, затем шлём бикон вручную на loopback.
        import time

        time.sleep(0.2)
        beacon = DiscoveryBeacon(http_port=8760, port=port)
        data = json.dumps(beacon.payload(), separators=(",", ":")).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(data, ("127.0.0.1", port))
        finally:
            sock.close()

        thread.join(timeout=5.0)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], BEACON_TYPE)
        self.assertEqual(received[0]["httpPort"], 8760)


if __name__ == "__main__":
    unittest.main()
