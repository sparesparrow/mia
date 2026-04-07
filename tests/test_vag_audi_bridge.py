"""Tests for the VAG Audi bridge scaffold."""

import importlib.util
import sys
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "orchestration"
    / "mcp"
    / "modules"
    / "vag-audi-bridge"
    / "main.py"
)


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("vag_audi_bridge_main", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bridge_module = load_bridge_module()
VagAudiBridge = bridge_module.VagAudiBridge


class TestVagAudiBridge(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bridge = VagAudiBridge()
        await self.bridge.initialize()

    async def asyncTearDown(self):
        await self.bridge.shutdown()

    async def test_default_config_is_read_only_and_passive(self):
        self.assertTrue(self.bridge.config["read_only"])
        self.assertTrue(self.bridge.config["enable_passive_monitoring"])
        self.assertFalse(self.bridge.config["enable_uds_polling"])
        self.assertFalse(self.bridge.config["allow_write_services"])
        self.assertFalse(self.bridge.config["allow_extended_session"])
        self.assertFalse(self.bridge.config["allow_security_access"])

    async def test_status_shape_is_stable_without_transport_data(self):
        status = await self.bridge.get_vehicle_status()

        self.assertEqual(status["current_state"], "passive_monitoring")
        self.assertEqual(status["vehicle_info"]["brand"], "Audi")
        self.assertIn("telemetry", status)
        self.assertIn("diagnostics", status)
        self.assertEqual(status["diagnostics"]["dtc_codes"], [])
        self.assertEqual(status["diagnostics"]["did_values"], {})
        self.assertTrue(status["capabilities"]["read_only"])
        self.assertFalse(status["capabilities"]["write_operations"])

    async def test_read_data_identifiers_returns_disabled_when_uds_is_off(self):
        result = await self.bridge.read_data_identifiers(["f190"])

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["identifiers"], ["F190"])
        self.assertEqual(result["values"], {})

    async def test_decode_transport_message_accepts_plain_json_payload(self):
        topic, payload = self.bridge._decode_transport_message('{"speed_kmh": 48, "engine_rpm": 1250}')

        self.assertIsNone(topic)
        self.assertEqual(payload["speed_kmh"], 48)
        self.assertEqual(payload["engine_rpm"], 1250)

    async def test_decode_transport_message_accepts_multipart_payload(self):
        topic, payload = self.bridge._decode_transport_message(
            (b"obd/telemetry", b'{"coolant_temp_c": 89, "vin": "WAUZZZ8V0FA000001"}')
        )

        self.assertEqual(topic, "obd/telemetry")
        self.assertEqual(payload["coolant_temp_c"], 89)
        self.assertEqual(payload["vin"], "WAUZZZ8V0FA000001")

    async def test_ingest_transport_message_updates_base_telemetry(self):
        await self.bridge.ingest_transport_message(
            (b"obd/telemetry", b'{"speed_kmh": 52, "engine_rpm": 1350, "battery_voltage": 12.4}')
        )

        status = await self.bridge.get_vehicle_status()
        self.assertEqual(status["current_state"], "ready")
        self.assertEqual(status["telemetry"]["speed_kmh"], 52)
        self.assertEqual(status["telemetry"]["engine_rpm"], 1350)
        self.assertEqual(status["telemetry"]["battery_voltage"], 12.4)


if __name__ == "__main__":
    unittest.main()