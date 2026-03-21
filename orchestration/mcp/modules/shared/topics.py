"""
MQTT Topic Structure for MIA Cognitive Architecture

Topic format: mia/{device_id}/{layer}/{data_type}

Layers map to CognitiveLayer enum values from cognitive.fbs:
  - perceptual:    Sensor data ingestion and feature extraction
  - episodic:      Interaction history and temporal context
  - semantic:      Knowledge graph and concept relationships
  - procedural:    Action execution and learned sequences
  - metacognitive: Self-monitoring, anomaly detection, resource awareness
  - transfer:      Cross-domain knowledge application
  - evaluative:    Outcome assessment and feedback loops
"""

# Layer name constants (match CognitiveLayer enum ordinals)
LAYER_PERCEPTUAL = "perceptual"
LAYER_EPISODIC = "episodic"
LAYER_SEMANTIC = "semantic"
LAYER_PROCEDURAL = "procedural"
LAYER_METACOGNITIVE = "metacognitive"
LAYER_TRANSFER = "transfer"
LAYER_EVALUATIVE = "evaluative"

ALL_LAYERS = [
    LAYER_PERCEPTUAL,
    LAYER_EPISODIC,
    LAYER_SEMANTIC,
    LAYER_PROCEDURAL,
    LAYER_METACOGNITIVE,
    LAYER_TRANSFER,
    LAYER_EVALUATIVE,
]

# CognitiveLayer enum ordinal -> topic layer name
LAYER_ORDINAL_MAP = {i: name for i, name in enumerate(ALL_LAYERS)}

# Standard data types per layer
STANDARD_DATA_TYPES = {
    LAYER_PERCEPTUAL: ["vehicle", "sensor", "bpm_data", "audio_features", "gpio"],
    LAYER_EPISODIC: ["interaction_log", "session", "event"],
    LAYER_SEMANTIC: ["knowledge_graph", "concept", "relation"],
    LAYER_PROCEDURAL: ["action", "sequence", "command"],
    LAYER_METACOGNITIVE: ["health", "metrics", "anomaly", "cognitive_state"],
    LAYER_TRANSFER: ["cross_domain", "adaptation"],
    LAYER_EVALUATIVE: ["user_feedback", "outcome", "performance"],
}

# Topic prefix
TOPIC_PREFIX = "mia"

# Wildcard subscriptions
SUBSCRIBE_ALL = f"{TOPIC_PREFIX}/#"
SUBSCRIBE_DEVICE = "{prefix}/{device_id}/#"
SUBSCRIBE_LAYER = "{prefix}/+/{layer}/#"


def build_topic(device_id: str, layer: str, data_type: str) -> str:
    """Build an MQTT topic string.

    Args:
        device_id: Device identifier (e.g., "esp32-01", "rpi-main", "android-01")
        layer: Cognitive layer name (use LAYER_* constants)
        data_type: Data type within the layer (e.g., "vehicle", "bpm_data")

    Returns:
        MQTT topic string like "mia/esp32-01/perceptual/bpm_data"
    """
    return f"{TOPIC_PREFIX}/{device_id}/{layer}/{data_type}"


def parse_topic(topic: str) -> dict | None:
    """Parse an MQTT topic string into components.

    Args:
        topic: MQTT topic string like "mia/esp32-01/perceptual/bpm_data"

    Returns:
        Dict with keys: prefix, device_id, layer, data_type
        None if topic doesn't match expected format
    """
    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != TOPIC_PREFIX:
        return None

    return {
        "prefix": parts[0],
        "device_id": parts[1],
        "layer": parts[2],
        "data_type": parts[3],
    }


def layer_from_ordinal(ordinal: int) -> str | None:
    """Convert CognitiveLayer enum ordinal to topic layer name."""
    return LAYER_ORDINAL_MAP.get(ordinal)


def subscribe_pattern_for_device(device_id: str) -> str:
    """Get MQTT subscription pattern for all topics from a device."""
    return f"{TOPIC_PREFIX}/{device_id}/#"


def subscribe_pattern_for_layer(layer: str) -> str:
    """Get MQTT subscription pattern for all topics in a cognitive layer."""
    return f"{TOPIC_PREFIX}/+/{layer}/#"
