"""Integration-focused tests for VAG Audi bridge wiring in automotive MCP bridge."""

import importlib.util
import json
import sys
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "orchestration"
    / "mcp"
    / "modules"
    / "automotive-mcp-bridge"
    / "main.py"
)


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("automotive_mcp_bridge_main", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bridge_module = load_bridge_module()
AutomotiveMCPBridge = bridge_module.AutomotiveMCPBridge
AutomotiveCommand = bridge_module.AutomotiveCommand


class TestAutomotiveMCPBridgeVag(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bridge = AutomotiveMCPBridge(
            {
                "enable_citroen_integration": False,
                "enable_vag_audi_integration": True,
                "vag_audi_config": {
                    "model_hint": "Audi A3 8V MQB",
                    "model_year": 2017,
                },
            }
        )

    async def test_vag_bridge_is_instantiated_with_safe_defaults(self):
        self.assertIsNotNone(self.bridge.vag_audi_bridge)
        self.assertTrue(self.bridge.metrics["vag_audi_bridge_active"])
        self.assertEqual(self.bridge.vag_audi_bridge.config["default_identifiers"], ["F190"])
        self.assertFalse(self.bridge.vag_audi_bridge.config["enable_uds_polling"])

    async def test_system_status_exposes_vag_bridge_section(self):
        status = await self.bridge.get_system_status()

        self.assertIn("vag_audi", status)
        self.assertTrue(status["vag_audi"]["bridge_active"])
        self.assertEqual(status["vag_audi"]["vehicle_info"]["brand"], "Audi")
        self.assertIn("adapter_capabilities", status["vag_audi"])
        self.assertEqual(status["vag_audi"]["adapter_capabilities"]["capability_class"], "unknown")
        self.assertTrue(status["vag_audi"]["capabilities"]["read_only"])
        self.assertEqual(status["vehicle_state"]["context"], "parked")
        self.assertIsInstance(status["vehicle_state"]["last_update"], str)
        json.dumps(status)

    async def test_system_status_tracks_vag_adapter_capability_after_telemetry(self):
        await self.bridge.vag_audi_bridge.ingest_transport_message(
            (b"obd/telemetry", b'{"speed_kmh": 44, "engine_rpm": 1500}')
        )

        status = await self.bridge.get_system_status()

        self.assertEqual(status["vag_audi"]["adapter_capabilities"]["capability_class"], "generic_pid_only")
        self.assertEqual(status["vag_audi"]["adapter_capabilities"]["connection_state"], "connected")

    async def test_audi_read_vin_command_routes_to_vag_bridge(self):
        command = AutomotiveCommand(
            command_id="cmd-1",
            text="read audi vin",
            intent="audi_read_vin",
        )

        result = await self.bridge._execute_automotive_command(command)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["identifiers"], ["F190"])

    async def test_vag_sync_updates_generic_vehicle_state(self):
        await self.bridge.vag_audi_bridge.ingest_transport_message(
            (b"obd/telemetry", b'{"speed_kmh": 61, "engine_rpm": 2100, "battery_voltage": 12.7}')
        )

        await self.bridge._sync_from_vag_audi_bridge()

        self.assertEqual(self.bridge.vehicle_state.speed_kmh, 61)
        self.assertEqual(self.bridge.vehicle_state.engine_rpm, 2100)
        self.assertEqual(self.bridge.vehicle_state.battery_voltage, 12.7)

    async def test_generic_mcp_request_context_is_json_serializable(self):
        self.bridge.vag_audi_bridge = None
        self.bridge.mcp_servers["navigation"] = {"connected": True, "tools": ["navigate_to"]}

        captured_request = {}

        async def fake_execute(server, request, timeout):
            captured_request["request"] = request
            json.dumps(request)
            return {"status": "ok"}

        self.bridge._simulate_mcp_execution = fake_execute

        command = AutomotiveCommand(
            command_id="cmd-2",
            text="navigate home",
            intent="navigate_to",
            entities={"destination": "home"},
        )

        result = await self.bridge._execute_automotive_command(command)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            captured_request["request"]["params"]["automotive_context"]["vehicle_state"]["context"],
            "parked",
        )

    async def test_main_requires_aiohttp_for_http_server_entrypoint(self):
        original_aiohttp = bridge_module.aiohttp
        bridge_module.aiohttp = None

        try:
            with self.assertRaisesRegex(RuntimeError, "aiohttp is required"):
                await bridge_module.main()
        finally:
            bridge_module.aiohttp = original_aiohttp


if __name__ == "__main__":
    unittest.main()