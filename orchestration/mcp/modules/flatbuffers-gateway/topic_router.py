"""
MQTT topic to MCP method routing.

Maps cognitive layer topics to MCP server endpoints and tool names.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.topics import (
    LAYER_PERCEPTUAL, LAYER_EPISODIC, LAYER_SEMANTIC,
    LAYER_PROCEDURAL, LAYER_METACOGNITIVE, LAYER_TRANSFER,
    LAYER_EVALUATIVE, parse_topic,
)

# Map cognitive layers to MCP service names
LAYER_TO_SERVICE = {
    LAYER_PERCEPTUAL: "hardware-bridge",
    LAYER_EPISODIC: "episodic-memory",
    LAYER_SEMANTIC: "core-orchestrator",
    LAYER_PROCEDURAL: "ai-platform-controllers",
    LAYER_METACOGNITIVE: "service-discovery",
    LAYER_TRANSFER: "core-orchestrator",
    LAYER_EVALUATIVE: "core-orchestrator",
}

# Map (layer, data_type) to MCP tool names
TOPIC_TO_TOOL = {
    (LAYER_PERCEPTUAL, "vehicle"): "ingest_vehicle_telemetry",
    (LAYER_PERCEPTUAL, "sensor"): "ingest_sensor_data",
    (LAYER_PERCEPTUAL, "bpm_data"): "ingest_bpm_data",
    (LAYER_PERCEPTUAL, "audio_features"): "ingest_audio_features",
    (LAYER_PERCEPTUAL, "gpio"): "handle_gpio_event",
    (LAYER_EPISODIC, "interaction_log"): "store_interaction",
    (LAYER_EPISODIC, "session"): "manage_session",
    (LAYER_EPISODIC, "event"): "store_event",
    (LAYER_PROCEDURAL, "command"): "execute_command",
    (LAYER_PROCEDURAL, "action"): "execute_action",
    (LAYER_METACOGNITIVE, "health"): "report_health",
    (LAYER_METACOGNITIVE, "metrics"): "report_metrics",
    (LAYER_METACOGNITIVE, "cognitive_state"): "update_cognitive_state",
    (LAYER_EVALUATIVE, "user_feedback"): "process_feedback",
    (LAYER_EVALUATIVE, "outcome"): "evaluate_outcome",
}


def route_topic(topic: str) -> dict | None:
    """Route an MQTT topic to an MCP service and tool.

    Args:
        topic: MQTT topic string like "mia/esp32-01/perceptual/bpm_data"

    Returns:
        Dict with keys: service, tool, device_id, layer, data_type
        None if topic cannot be routed
    """
    parsed = parse_topic(topic)
    if not parsed:
        return None

    layer = parsed["layer"]
    data_type = parsed["data_type"]

    service = LAYER_TO_SERVICE.get(layer)
    if not service:
        return None

    tool = TOPIC_TO_TOOL.get((layer, data_type))
    if not tool:
        # Default tool name based on layer and data type
        tool = f"handle_{layer}_{data_type}"

    return {
        "service": service,
        "tool": tool,
        "device_id": parsed["device_id"],
        "layer": layer,
        "data_type": data_type,
    }
