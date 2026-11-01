"""Тесты WASM-моста: кодирование протокола и in-memory транспорт."""

import struct
import unittest

from msfs_gateway.sim.wasm_bridge import (
    COMMAND_BYTES,
    LVAR_ENTRY_BYTES,
    LVAR_NAME_BYTES,
    LVAR_VALUE_BYTES,
    MAX_LVARS_PER_BLOCK,
    MockWasmTransport,
    NullWasmTransport,
    WasmBridge,
    WasmBridgeError,
    coerce_custom_value,
    decode_lvar_block,
    decode_response,
    encode_command,
    encode_lvar_block,
    pack_lvar_name,
    unpack_lvar_name,
)


class ProtocolEncodingTest(unittest.TestCase):
    def test_layout_constants(self):
        self.assertEqual(LVAR_NAME_BYTES, 128)
        self.assertEqual(LVAR_VALUE_BYTES, 8)
        self.assertEqual(LVAR_ENTRY_BYTES, 136)

    def test_pack_name_is_fixed_size_and_nul_padded(self):
        raw = pack_lvar_name("PMDG_FUEL")
        self.assertEqual(len(raw), LVAR_NAME_BYTES)
        self.assertTrue(raw.endswith(b"\x00"))
        self.assertEqual(unpack_lvar_name(raw), "PMDG_FUEL")

    def test_pack_name_rejects_overlong(self):
        with self.assertRaises(ValueError):
            pack_lvar_name("X" * LVAR_NAME_BYTES)

    def test_pack_name_rejects_empty(self):
        with self.assertRaises(ValueError):
            pack_lvar_name("")

    def test_encode_decode_block_roundtrip(self):
        pairs = [("LVAR_A", 1.5), ("LVAR_B", -42.25)]
        block = encode_lvar_block(pairs)
        self.assertEqual(len(block), 2 * LVAR_ENTRY_BYTES)

        decoded = decode_lvar_block(block)
        self.assertEqual(decoded, {"LVAR_A": 1.5, "LVAR_B": -42.25})

    def test_decode_block_ignores_truncated_tail(self):
        block = encode_lvar_block([("LVAR_A", 1.0)]) + b"\x00\x01\x02"
        self.assertEqual(decode_lvar_block(block), {"LVAR_A": 1.0})

    def test_decode_block_respects_count(self):
        block = encode_lvar_block([("A", 1.0), ("B", 2.0)])
        self.assertEqual(decode_lvar_block(block, count=1), {"A": 1.0})

    def test_command_and_response(self):
        payload = encode_command("1 (>L:TEST, number)")
        self.assertEqual(len(payload), COMMAND_BYTES)
        self.assertTrue(payload.endswith(b"\x00"))
        self.assertEqual(decode_response(payload), "1 (>L:TEST, number)")

    def test_command_rejects_overlong(self):
        with self.assertRaises(ValueError):
            encode_command("x" * COMMAND_BYTES)

    def test_coerce_custom_value(self):
        self.assertEqual(coerce_custom_value("42.5", "number"), 42.5)
        self.assertEqual(coerce_custom_value("bad", "number"), 0.0)
        self.assertIs(coerce_custom_value(1, "bool"), True)
        self.assertIs(coerce_custom_value("off", "bool"), False)
        self.assertEqual(coerce_custom_value(5, "string"), "5")
        self.assertEqual(coerce_custom_value(None, "string"), "")


class MockTransportTest(unittest.TestCase):
    def test_bridge_reads_lvars(self):
        transport = MockWasmTransport(lvars={"PMDG_FUEL": 1234.5, "PMDG_DOOR": 1.0})
        bridge = WasmBridge(transport)

        values = bridge.read_lvars(["PMDG_FUEL", "PMDG_DOOR", "MISSING"])
        self.assertEqual(values["PMDG_FUEL"], 1234.5)
        self.assertEqual(values["PMDG_DOOR"], 1.0)
        # Неизвестный LVAR модуль отдаёт как 0.0 — отличить «нет данных»
        # на уровне протокола нельзя, это описано в docstring read_lvars.
        self.assertEqual(values["MISSING"], 0.0)

    def test_bridge_writes_lvar_via_rpn(self):
        transport = MockWasmTransport()
        bridge = WasmBridge(transport)

        bridge.write_lvar("PMDG_FUEL", 250.0)
        self.assertEqual(transport.lvars["PMDG_FUEL"], 250.0)
        self.assertTrue(transport.commands)
        self.assertIn(">L:PMDG_FUEL", transport.commands[-1])

    def test_read_specs_mixed_sources(self):
        transport = MockWasmTransport(
            lvars={"DOOR": 1.0},
            rpn_handler=lambda script: "17.5" if "ALT" in script else "",
        )
        bridge = WasmBridge(transport)

        values = bridge.read_specs(
            [
                {"key": "custom.door", "kind": "bool", "source": "lvar", "name": "DOOR"},
                {
                    "key": "custom.cabinAlt",
                    "kind": "number",
                    "source": "rpn",
                    "expression": "(A:CABIN ALT, feet)",
                },
            ]
        )
        self.assertIs(values["custom.door"], True)
        self.assertEqual(values["custom.cabinAlt"], 17.5)

    def test_read_specs_skips_failed_rpn(self):
        def broken(script):
            raise RuntimeError("нет ответа")

        bridge = WasmBridge(MockWasmTransport(rpn_handler=broken))
        values = bridge.read_specs(
            [{"key": "custom.x", "kind": "number", "source": "rpn", "expression": "BOOM"}]
        )
        self.assertEqual(values, {})

    def test_chunking_respects_limit(self):
        names = [f"LVAR_{index}" for index in range(MAX_LVARS_PER_BLOCK + 5)]
        transport = MockWasmTransport(
            lvars={name: float(index) for index, name in enumerate(names)}
        )
        bridge = WasmBridge(transport)

        values = bridge.read_lvars(names)
        self.assertEqual(len(values), len(names))
        self.assertEqual(values["LVAR_0"], 0.0)
        self.assertEqual(values[f"LVAR_{MAX_LVARS_PER_BLOCK + 4}"], float(MAX_LVARS_PER_BLOCK + 4))

    def test_null_transport_unavailable(self):
        bridge = WasmBridge(NullWasmTransport())
        self.assertFalse(bridge.available)
        with self.assertRaises(WasmBridgeError):
            bridge.execute_rpn("1 2 +")
        with self.assertRaises(WasmBridgeError):
            bridge.write_lvar("X", 1.0)


class BlockSizeGuardTest(unittest.TestCase):
    def test_block_size_matches_entries(self):
        payload = encode_lvar_block([(f"L{index}", float(index)) for index in range(3)])
        self.assertEqual(len(payload), 3 * LVAR_ENTRY_BYTES)
        # Каждая запись — ровно 128 байт имени и 8 байт double.
        first_value = struct.unpack("<d", payload[LVAR_NAME_BYTES:LVAR_ENTRY_BYTES])[0]
        self.assertEqual(first_value, 0.0)


if __name__ == "__main__":
    unittest.main()
