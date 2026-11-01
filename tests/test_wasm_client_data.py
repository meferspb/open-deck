"""Тесты WASM-моста поверх Client Data Area (эмуляция MobiFlight)."""

import unittest

from msfs_gateway.sim.client_data import ClientDataChannel, LoopbackClientDataBackend
from msfs_gateway.sim.wasm_bridge import (
    COMMAND_AREA,
    LVAR_AREA,
    LVAR_ENTRY_BYTES,
    RESPONSE_AREA,
    WasmBridge,
    decode_lvar_block,
    decode_response,
    encode_command,
    encode_lvar_block,
)

LVARS = {"PMDG_FUEL_LBS": 1200.0, "PMDG_APU_ON": 1.0}
RPN_ANSWER = "17.5"


def mobiflight_transform(area: str, data: bytes) -> bytes:
    """Эмулирует WASM-модуль: заполняет LVAR значениями и отвечает на RPN."""
    if area == LVAR_AREA:
        count = len(data) // LVAR_ENTRY_BYTES
        requested = decode_lvar_block(data, count) if count else {}
        return encode_lvar_block([(name, LVARS.get(name, 0.0)) for name in requested])
    if area == RESPONSE_AREA:
        return encode_command(RPN_ANSWER)
    return data


class ChannelTransport:
    """Адаптер `WasmTransport` над каналом Client Data."""

    available = True

    def __init__(self, channel: ClientDataChannel) -> None:
        self.channel = channel

    def read_area(self, area: str, size: int) -> bytes | None:
        return self.channel.read_area(area, size)

    def write_area(self, area: str, payload: bytes) -> None:
        self.channel.write_area(area, payload)


class WasmOverClientDataTest(unittest.TestCase):
    def setUp(self):
        self.backend = LoopbackClientDataBackend(transform=mobiflight_transform)
        self.channel = ClientDataChannel(self.backend)
        self.bridge = WasmBridge(ChannelTransport(self.channel))

    def test_read_lvars_through_client_data(self):
        values = self.bridge.read_lvars(["PMDG_FUEL_LBS", "PMDG_APU_ON"])
        self.assertEqual(values["PMDG_FUEL_LBS"], 1200.0)
        self.assertEqual(values["PMDG_APU_ON"], 1.0)

    def test_unknown_lvar_reads_zero(self):
        values = self.bridge.read_lvars(["NOPE"])
        self.assertEqual(values["NOPE"], 0.0)

    def test_write_lvar_sends_rpn_command(self):
        self.bridge.write_lvar("PMDG_FUEL_LBS", 250.0)

        command = decode_response(self.backend.areas[COMMAND_AREA])
        self.assertIn(">L:PMDG_FUEL_LBS", command)
        self.assertTrue(command.startswith("250"))

    def test_read_specs_mixed(self):
        values = self.bridge.read_specs(
            [
                {"key": "custom.fuel", "kind": "number", "source": "lvar", "name": "PMDG_FUEL_LBS"},
                {"key": "custom.apu", "kind": "bool", "source": "lvar", "name": "PMDG_APU_ON"},
                {"key": "custom.rpn", "kind": "number", "source": "rpn", "expression": "1 2 +"},
            ]
        )
        self.assertEqual(values["custom.fuel"], 1200.0)
        self.assertIs(values["custom.apu"], True)
        self.assertEqual(values["custom.rpn"], 17.5)

    def test_empty_payload_yields_no_values(self):
        # Область отвечает пустым буфером: ключей быть не должно,
        # подставлять выдуманные нули нельзя.
        backend = LoopbackClientDataBackend(transform=lambda area, data: b"")
        channel = ClientDataChannel(backend, timeout=0.05)
        bridge = WasmBridge(ChannelTransport(channel))

        self.assertEqual(bridge.read_lvars(["X"]), {})


if __name__ == "__main__":
    unittest.main()
