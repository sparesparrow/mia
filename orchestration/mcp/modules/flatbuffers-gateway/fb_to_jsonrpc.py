"""
FlatBuffers to JSON-RPC translator.

Deserializes FlatBuffers binary payloads from MQTT messages
and constructs JSON-RPC 2.0 method calls for MCP servers.
"""

import json
import uuid
import logging

from .topic_router import route_topic

logger = logging.getLogger(__name__)

# Map FlatBuffers type names to deserialization functions.
# Each function takes raw bytes and returns a dict.
# We use a registry pattern so new types can be added without modifying core logic.
_FB_DESERIALIZERS = {}


def register_deserializer(type_name: str):
    """Decorator to register a FlatBuffers deserializer for a type name."""
    def decorator(func):
        _FB_DESERIALIZERS[type_name] = func
        return func
    return decorator


def _try_import_fb_type(module_path: str, class_name: str):
    """Attempt to import a generated FlatBuffers class.

    Returns the class or None if not available.
    """
    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name, None)
    except ImportError:
        return None


def _deserialize_generic(data: bytes, type_name: str) -> dict:
    """Attempt to deserialize FlatBuffers data using generated bindings.

    Falls back to base64-encoding the raw bytes if bindings aren't available.
    """
    # Check registered custom deserializers first
    if type_name in _FB_DESERIALIZERS:
        return _FB_DESERIALIZERS[type_name](data)

    # Try importing from Mia namespace (generated Python bindings)
    # Type names follow pattern: Mia.SomeType or Mia.Sub.SomeType
    parts = type_name.split(".")
    if len(parts) >= 2:
        module_path = ".".join(parts[:-1]) + "." + parts[-1]
        cls = _try_import_fb_type(module_path, parts[-1])
        if cls and hasattr(cls, 'GetRootAs'):
            try:
                obj = cls.GetRootAs(data, 0)
                return _fb_object_to_dict(obj)
            except Exception as e:
                logger.warning("Failed to deserialize %s: %s", type_name, e)

    # Fallback: return raw bytes as base64
    import base64
    return {"_raw_base64": base64.b64encode(data).decode("ascii"), "_type": type_name}


def _fb_object_to_dict(obj) -> dict:
    """Convert a FlatBuffers object to a dict by inspecting its accessor methods."""
    result = {}
    for attr_name in dir(obj):
        if attr_name.startswith('_') or attr_name in ('Init', 'GetRootAs', 'GetRootAsWithOffset'):
            continue
        if attr_name.endswith('Length') or attr_name.endswith('IsNone'):
            continue
        try:
            val = getattr(obj, attr_name)
            if callable(val):
                val = val()
            if isinstance(val, bytes):
                val = val.decode('utf-8', errors='replace')
            result[attr_name] = val
        except (TypeError, Exception):
            continue
    return result


def translate_fb_to_jsonrpc(topic: str, payload: bytes, payload_type: str = "") -> dict | None:
    """Translate a FlatBuffers MQTT message to a JSON-RPC 2.0 request.

    Args:
        topic: MQTT topic string
        payload: FlatBuffers binary payload
        payload_type: Optional FlatBuffers type name for deserialization hint

    Returns:
        JSON-RPC 2.0 request dict, or None if topic cannot be routed
    """
    route = route_topic(topic)
    if not route:
        logger.warning("No route for topic: %s", topic)
        return None

    # Deserialize the FlatBuffers payload
    if payload_type:
        data = _deserialize_generic(payload, payload_type)
    else:
        # Try to infer type from topic data_type
        data = {"_raw_payload_size": len(payload)}
        try:
            # Attempt JSON fallback (some devices send JSON on MQTT)
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            import base64
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
