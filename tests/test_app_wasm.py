"""Тесты сборки приложения: подключение WASM-моста к шине телеметрии."""

import tempfile
import unittest
from pathlib import Path

from msfs_gateway.app import GatewayApplication
from msfs_gateway.settings import Settings


class FakeBridge:
    def __init__(self):
        self.calls = 0

    def read_specs(self, specs):
        self.calls += 1
        return {}


class FakeSimWithBridge:
    name = "fake-simconnect"

    def __init__(self):
        self.bridge = FakeBridge()
        self.connected = True
        self.aircraft_title = "Fake"
        self.profile_id = None
        self.started = False

    # --- SimProvider ---
    def start(self):
        self.started = True

    def stop(self):
        pass

    def read(self):
        return {}

    def apply_command(self, key, value):
        return None

    # --- WASM ---
    def wasm_bridge(self):
        return self.bridge


class WasmWiringTest(unittest.TestCase):
    def _app(self, *, wasm=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        settings = Settings(profile_dir=Path(tmp.name), sim="mock", wasm=wasm)
        app = GatewayApplication(settings, check_integrity=False)
        self.addCleanup(app.sim.stop)
        return app

    def test_mock_provider_has_no_wasm(self):
        app = self._app()
        app._setup_wasm()
        self.assertIsNone(app.wasm_bridge)
        self.assertIsNone(app.hub._custom_reader)

    def test_provider_bridge_is_wired_into_hub(self):
        app = self._app()
        fake = FakeSimWithBridge()
        app.sim = fake

        app._setup_wasm()

        self.assertIs(app.wasm_bridge, fake.bridge)
        self.assertIsNotNone(app.hub._custom_reader)
        # Читатель действительно вызывает мост.
        app.hub._custom_reader([{"key": "custom.x", "source": "lvar", "name": "X"}])
        self.assertEqual(fake.bridge.calls, 1)

    def test_no_wasm_disables_bridge(self):
        app = self._app(wasm=False)
        fake = FakeSimWithBridge()
        app.sim = fake

        app._setup_wasm()

        self.assertIsNone(app.wasm_bridge)
        self.assertIsNone(app.hub._custom_reader)


if __name__ == "__main__":
    unittest.main()
