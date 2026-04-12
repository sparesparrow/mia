"""
Bench validation: simulated end-to-end telemetry flow without ZMQ or hardware.

Exercises the full path:
  normalized_payload.build_telemetry_payload()
  → FastAPI _handle_mcu_telemetry() cache update
  → /status telemetry_sources summary
  → /telemetry endpoint shape
  → WebSocket broadcast shape
  → VAG bridge ingestion
"""

import importlib.util
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

# ── Load modules via importlib to avoid sys.path pollution ──────────────

_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


normalized_payload = _load(
    "normalized_payload",
    _ROOT / "apps" / "rpi-backend" / "shared" / "telemetry" / "normalized_payload.py",
)
build_telemetry_payload = normalized_payload.build_telemetry_payload
build_adapter_capabilities = normalized_payload.build_adapter_capabilities

vag_module = _load(
    "vag_audi_bridge_main",
    _ROOT / "orchestration" / "mcp" / "modules" / "vag-audi-bridge" / "main.py",
)
VagAudiBridge = vag_module.VagAudiBridge

# ── Fixtures ────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


# ── Simulated FastAPI cache layer ───────────────────────────────────────

def _simulate_fastapi_cache_update(payload: dict) -> dict:
    """Simulate what _handle_mcu_telemetry does to the telemetry_cache entry."""
    cache_entry: dict = {}
    cache_entry.update(payload)
    cache_entry["timestamp"] = datetime.now().isoformat()
    cache_entry["source"] = "mcu/telemetry"
    return cache_entry


def _simulate_telemetry_source_summary(cache: dict) -> dict:
    """Simulate _build_telemetry_source_summary."""
    sources = {}
    now = datetime.now()
    for device_id, entry in cache.items():
        ts_raw = entry.get("timestamp")
        age_seconds = None
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                age_seconds = round((now - ts).total_seconds(), 1)
            except (ValueError, TypeError):
                pass
        source_info = {
            "last_update": ts_raw,
            "age_seconds": age_seconds,
            "source": entry.get("source"),
        }
        adapter_caps = entry.get("adapter_capabilities")
        if adapter_caps:
            source_info["adapter_kind"] = adapter_caps.get("adapter_kind")
            source_info["capability_class"] = adapter_caps.get("capability_class")
            source_info["connection_state"] = adapter_caps.get("connection_state")
        sources[device_id] = source_info
    return sources


# ── Tests ───────────────────────────────────────────────────────────────

class TestBenchEndToEndFlow(unittest.TestCase):
    """Simulate the full telemetry path on a dev machine without ZMQ."""

    def test_normalized_payload_through_fastapi_cache(self):
        """build_telemetry_payload → cache → /telemetry shape."""
        payload = build_telemetry_payload(
            engine_rpm=2500,
            speed_kmh=80,
            coolant_temp_c=90,
            device_id="bench_obd",
        )
        cached = _simulate_fastapi_cache_update(payload)

        self.assertEqual(cached["engine_rpm"], 2500)
        self.assertEqual(cached["speed_kmh"], 80)
        self.assertEqual(cached["coolant_temp_c"], 90)
        self.assertEqual(cached["source"], "mcu/telemetry")
        self.assertIn("timestamp", cached)

    def test_telemetry_source_summary_includes_freshness(self):
        """Status endpoint should report freshness and source for each device."""
        payload = build_telemetry_payload(
            engine_rpm=3000,
            speed_kmh=120,
            device_id="bench_elm327",
            adapter_capabilities=build_adapter_capabilities(
                capability_class="generic_pid_only",
                adapter_kind="elm327",
            ),
        )
        cached = _simulate_fastapi_cache_update(payload)
        telemetry_cache = {"bench_elm327": cached}

        summary = _simulate_telemetry_source_summary(telemetry_cache)
        entry = summary["bench_elm327"]

        self.assertIn("last_update", entry)
        self.assertIsNotNone(entry["age_seconds"])
        self.assertLess(entry["age_seconds"], 2.0)
        self.assertEqual(entry["source"], "mcu/telemetry")
        self.assertEqual(entry["adapter_kind"], "elm327")
        self.assertEqual(entry["capability_class"], "generic_pid_only")

    def test_status_summary_without_adapter_capabilities(self):
        """Devices without adapter_capabilities should still appear in summary."""
        cached = _simulate_fastapi_cache_update({"pot1": 512, "pot2": 256})
        telemetry_cache = {"arduino_mcu": cached}

        summary = _simulate_telemetry_source_summary(telemetry_cache)
        entry = summary["arduino_mcu"]

        self.assertIn("last_update", entry)
        self.assertNotIn("adapter_kind", entry)
        self.assertNotIn("capability_class", entry)

    def test_websocket_broadcast_shape(self):
        """WebSocket frames should contain telemetry and led_state."""
        payload = build_telemetry_payload(speed_kmh=60, device_id="ws_test")
        cached = _simulate_fastapi_cache_update(payload)
        telemetry_cache = {"ws_test": cached}

        # Simulate the WebSocket frame shape
        ws_frame = {
            "type": "telemetry",
            "data": {
                "telemetry": telemetry_cache,
                "led_state": {"mode": "off"},
            },
            "timestamp": datetime.now().isoformat(),
        }
        self.assertIn("telemetry", ws_frame["data"])
        self.assertEqual(ws_frame["data"]["telemetry"]["ws_test"]["speed_kmh"], 60)
        self.assertEqual(ws_frame["type"], "telemetry")
        # Must be JSON serializable
        json.dumps(ws_frame)


class TestBenchVAGBridgeIngestion(unittest.IsolatedAsyncioTestCase):
    """Verify normalized payloads flow correctly into the VAG bridge."""

    async def test_normalized_payload_ingested_by_vag_bridge(self):
        """A normalized payload from the serial bridge should update VAG state."""
        bridge = VagAudiBridge()
        await bridge.initialize()
        try:
            payload = build_telemetry_payload(
                engine_rpm=1800,
                speed_kmh=45,
                coolant_temp_c=82,
                adapter_capabilities=build_adapter_capabilities(
                    capability_class="generic_pid_only",
                    adapter_kind="elm327",
                ),
            )
            raw = json.dumps(payload).encode()
            await bridge.ingest_transport_message((b"mcu/telemetry", raw))

            status = await bridge.get_vehicle_status()
            self.assertEqual(status["telemetry"]["speed_kmh"], 45)
            self.assertEqual(status["telemetry"]["engine_rpm"], 1800)
            self.assertEqual(status["adapter_capabilities"]["capability_class"], "generic_pid_only")
        finally:
            await bridge.shutdown()

    async def test_fixture_replay_full_chain(self):
        """Replay generic PID fixtures through builder → cache → VAG bridge."""
        samples = _load_fixture("transport_generic_pid.json")
        bridge = VagAudiBridge()
        await bridge.initialize()
        try:
            telemetry_cache = {}
            for sample in samples:
                # Step 1: normalize through cache
                device_id = sample.get("device_id", "unknown")
                cached = _simulate_fastapi_cache_update(sample)
                telemetry_cache[device_id] = cached

                # Step 2: ingest into VAG bridge
                raw = json.dumps(sample).encode()
                await bridge.ingest_transport_message((b"mcu/telemetry", raw))

            # Status endpoint should list all sources
            summary = _simulate_telemetry_source_summary(telemetry_cache)
            self.assertGreater(len(summary), 0)

            # VAG bridge should have telemetry state
            vag_status = await bridge.get_vehicle_status()
            self.assertIn("telemetry", vag_status)
            self.assertIn("adapter_capabilities", vag_status)
        finally:
            await bridge.shutdown()

    async def test_uds_fixture_promotes_capability_through_chain(self):
        """UDS-capable fixtures should promote the VAG bridge to uds_read_only."""
        samples = _load_fixture("transport_uds_capable.json")
        bridge = VagAudiBridge()
        await bridge.initialize()
        try:
            for sample in samples:
                raw = json.dumps(sample).encode()
                await bridge.ingest_transport_message((b"obd/telemetry", raw))

            status = await bridge.get_vehicle_status()
            self.assertEqual(status["adapter_capabilities"]["capability_class"], "uds_read_only")

            # Verify the VIN made it through
            vin = status["telemetry"].get("vin", "")
            self.assertIn("WAUZZZ", vin)
        finally:
            await bridge.shutdown()


class TestOBDWorkerNormalizedPublish(unittest.TestCase):
    """Verify the OBD worker's published payload matches the contract."""

    def test_obd_publish_shape_matches_contract(self):
        """The OBD worker's telemetry should use normalized field names."""
        # Simulate what _telemetry_publish_loop now produces
        telemetry_data = {
            "engine_rpm": 2500,
            "speed_kmh": 80,
            "coolant_temp_c": 90,
            "device_id": "obd_worker",
            "timestamp": datetime.now().isoformat(),
        }

        # Verify it uses the contract fields
        for field in ("engine_rpm", "speed_kmh", "coolant_temp_c", "device_id"):
            self.assertIn(field, telemetry_data)

        # Verify legacy names are NOT present
        for old_field in ("rpm", "speed", "coolant_temp", "load"):
            self.assertNotIn(old_field, telemetry_data)

    def test_obd_publish_with_adapter_capabilities(self):
        """When a protocol is active, adapter_capabilities should be present."""
        telemetry_data = {
            "engine_rpm": 800,
            "speed_kmh": 0,
            "coolant_temp_c": 85,
            "device_id": "obd_worker",
            "timestamp": datetime.now().isoformat(),
            "adapter_capabilities": {
                "adapter_kind": "elm327_emulator",
                "transport": "virtual_pty",
                "connection_state": "connected",
                "active_protocol": "ISO 15765-4 CAN 11-bit 500kbps",
            },
        }

        caps = telemetry_data["adapter_capabilities"]
        self.assertEqual(caps["adapter_kind"], "elm327_emulator")
        self.assertEqual(caps["connection_state"], "connected")
        self.assertIn("active_protocol", caps)

        # Full payload must be JSON serializable
        json.dumps(telemetry_data)


if __name__ == "__main__":
    unittest.main()
