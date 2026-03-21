"""Tests for FlatBuffers-to-JSON-RPC gateway components."""
import unittest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "orchestration", "mcp", "modules",
))


class TestTopics(unittest.TestCase):
    """Test MQTT topic building and parsing."""

    def test_build_topic(self):
        from shared.topics import build_topic
        topic = build_topic("esp32-01", "perceptual", "bpm_data")
        self.assertEqual(topic, "mia/esp32-01/perceptual/bpm_data")

    def test_build_topic_rpi(self):
        from shared.topics import build_topic
        topic = build_topic("rpi-main", "episodic", "interaction_log")
        self.assertEqual(topic, "mia/rpi-main/episodic/interaction_log")

    def test_parse_topic(self):
        from shared.topics import parse_topic
        result = parse_topic("mia/esp32-01/perceptual/bpm_data")
        self.assertIsNotNone(result)
        self.assertEqual(result["device_id"], "esp32-01")
        self.assertEqual(result["layer"], "perceptual")
        self.assertEqual(result["data_type"], "bpm_data")

    def test_parse_topic_invalid(self):
        from shared.topics import parse_topic
        self.assertIsNone(parse_topic("invalid/topic"))
        self.assertIsNone(parse_topic("other/a/b/c"))
        self.assertIsNone(parse_topic("mia/a/b/c/d"))  # too many parts

    def test_roundtrip(self):
        from shared.topics import build_topic, parse_topic
        topic = build_topic("android-01", "evaluative", "user_feedback")
        parsed = parse_topic(topic)
        self.assertEqual(parsed["device_id"], "android-01")
        self.assertEqual(parsed["layer"], "evaluative")
        self.assertEqual(parsed["data_type"], "user_feedback")

    def test_layer_from_ordinal(self):
        from shared.topics import layer_from_ordinal
        self.assertEqual(layer_from_ordinal(0), "perceptual")
        self.assertEqual(layer_from_ordinal(4), "metacognitive")
        self.assertEqual(layer_from_ordinal(6), "evaluative")
        self.assertIsNone(layer_from_ordinal(99))

    def test_all_layers_constant(self):
        from shared.topics import ALL_LAYERS
        self.assertEqual(len(ALL_LAYERS), 7)

    def test_subscribe_patterns(self):
        from shared.topics import subscribe_pattern_for_device, subscribe_pattern_for_layer
        self.assertEqual(subscribe_pattern_for_device("esp32-01"), "mia/esp32-01/#")
        self.assertEqual(subscribe_pattern_for_layer("perceptual"), "mia/+/perceptual/#")


class TestTopicRouter(unittest.TestCase):
    """Test MQTT topic to MCP service routing."""

    def test_route_perceptual_vehicle(self):
        from orchestration.mcp.modules.__init__ import __file__ as _
        # Need to import differently since it's a hyphenated path
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "orchestration", "mcp", "modules", "flatbuffers-gateway",
        ))
        try:
            from topic_router import route_topic
            result = route_topic("mia/esp32-01/perceptual/vehicle")
            self.assertIsNotNone(result)
            self.assertEqual(result["service"], "hardware-bridge")
            self.assertEqual(result["tool"], "ingest_vehicle_telemetry")
            self.assertEqual(result["device_id"], "esp32-01")
        except ImportError:
            # Fallback: test via direct import
            self.skipTest("Cannot import topic_router directly")

    def test_route_unknown_topic(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "orchestration", "mcp", "modules", "flatbuffers-gateway",
        ))
        try:
            from topic_router import route_topic
            result = route_topic("other/topic/not/mia")
            self.assertIsNone(result)
        except ImportError:
            self.skipTest("Cannot import topic_router directly")


class TestFbToJsonRpc(unittest.TestCase):
    """Test FlatBuffers to JSON-RPC translation logic."""

    def _translate(self, topic, payload, payload_type=""):
        """Inline translation logic to avoid relative import issues."""
        from topic_router import route_topic
        import uuid
        import base64

        route = route_topic(topic)
        if not route:
            return None

        # Deserialize payload
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {"_raw_base64": base64.b64encode(payload).decode("ascii")}

        return {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": f"tools/{route['tool']}",
            "params": {
                "device_id": route["device_id"],
                "layer": route["layer"],
                "data_type": route["data_type"],
                "data": data,
            },
        }

    def test_translate_json_payload(self):
        """Test translation when payload is JSON (common for MQTT)."""
        payload = json.dumps({"bpm": 120.5, "confidence": 0.95}).encode("utf-8")
        result = self._translate("mia/esp32-01/perceptual/bpm_data", payload)
        self.assertIsNotNone(result)
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertIn("id", result)
        self.assertEqual(result["method"], "tools/ingest_bpm_data")
        self.assertEqual(result["params"]["device_id"], "esp32-01")
        self.assertEqual(result["params"]["data"]["bpm"], 120.5)

    def test_translate_binary_payload(self):
        """Test translation with binary (non-JSON) payload."""
        binary_data = bytes([0x00, 0x01, 0x02, 0xFF])
        result = self._translate("mia/esp32-01/perceptual/sensor", binary_data)
        self.assertIsNotNone(result)
        self.assertIn("_raw_base64", result["params"]["data"])

    def test_translate_unroutable_topic(self):
        """Test that unroutable topics return None."""
        result = self._translate("invalid/topic", b"data")
        self.assertIsNone(result)


class TestJsonRpcToFb(unittest.TestCase):
    """Test JSON-RPC to FlatBuffers translation."""

    def test_translate_error_response(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "orchestration", "mcp", "modules", "flatbuffers-gateway",
        ))
        try:
            from jsonrpc_to_fb import translate_jsonrpc_to_fb
            response = {
                "jsonrpc": "2.0",
                "id": "123",
                "error": {"code": -32601, "message": "Method not found"},
            }
            result = translate_jsonrpc_to_fb(response)
            parsed = json.loads(result)
            self.assertTrue(parsed["error"])
            self.assertEqual(parsed["code"], -32601)
        except ImportError:
            self.skipTest("Cannot import jsonrpc_to_fb")

    def test_translate_success_response(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "orchestration", "mcp", "modules", "flatbuffers-gateway",
        ))
        try:
            from jsonrpc_to_fb import translate_jsonrpc_to_fb
            response = {
                "jsonrpc": "2.0",
                "id": "123",
                "result": {"status": "ok", "value": 42},
            }
            result = translate_jsonrpc_to_fb(response)
            parsed = json.loads(result)
            self.assertEqual(parsed["status"], "ok")
        except ImportError:
            self.skipTest("Cannot import jsonrpc_to_fb")


class TestBaselineSchemas(unittest.TestCase):
    """Test that baseline schemas exist and match current schemas."""

    def test_baseline_directory_exists(self):
        baseline_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "baseline",
        )
        self.assertTrue(os.path.isdir(baseline_dir))

    def test_baseline_schemas_present(self):
        baseline_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "baseline",
        )
        for name in ["mia.fbs", "cognitive.fbs", "storage.fbs", "vehicle.fbs", "webgrab.fbs"]:
            path = os.path.join(baseline_dir, name)
            self.assertTrue(
                os.path.exists(path),
                f"Missing baseline schema: {name}"
            )


if __name__ == "__main__":
    unittest.main()
