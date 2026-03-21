"""
JSON-RPC to FlatBuffers translator.

Converts JSON-RPC 2.0 responses from MCP servers back to
FlatBuffers binary for publishing on MQTT response topics.
"""

import json
import logging

logger = logging.getLogger(__name__)


def translate_jsonrpc_to_fb(response: dict, target_type: str = "") -> bytes:
    """Translate a JSON-RPC 2.0 response to FlatBuffers binary.

    Args:
        response: JSON-RPC 2.0 response dict
        target_type: FlatBuffers type name for serialization

    Returns:
        Serialized bytes (FlatBuffers if bindings available, JSON otherwise)
    """
    if "error" in response:
        return _serialize_error_response(response["error"])

    result = response.get("result", {})

    if target_type:
        fb_bytes = _try_serialize_fb(result, target_type)
        if fb_bytes is not None:
            return fb_bytes

    # Fallback: JSON-encode the response
    return json.dumps(result).encode("utf-8")


def _serialize_error_response(error: dict) -> bytes:
    """Serialize an error response."""
    return json.dumps({
        "error": True,
        "code": error.get("code", -1),
        "message": error.get("message", "Unknown error"),
    }).encode("utf-8")


def _try_serialize_fb(data: dict, type_name: str) -> bytes | None:
    """Attempt to serialize data as FlatBuffers using generated bindings.

    Returns None if bindings aren't available or serialization fails.
    """
    try:
        import importlib
        parts = type_name.split(".")
        if len(parts) < 2:
            return None

        module_path = ".".join(parts[:-1]) + "." + parts[-1]
        module = importlib.import_module(module_path)
        cls_name = parts[-1]

        # Use the builder pattern: Start, Add*, End
        import flatbuffers
        builder = flatbuffers.Builder(1024)

        start_fn = getattr(module, f"{cls_name}Start", None)
        end_fn = getattr(module, f"{cls_name}End", None)
        if not start_fn or not end_fn:
            return None

        # Pre-create strings
        string_offsets = {}
        for key, value in data.items():
            if isinstance(value, str):
                string_offsets[key] = builder.CreateString(value)

        start_fn(builder)

        for key, value in data.items():
            # Convert key to PascalCase for FlatBuffers accessor
            add_fn_name = f"{cls_name}Add{''.join(w.capitalize() for w in key.split('_'))}"
            add_fn = getattr(module, add_fn_name, None)
            if add_fn:
                if key in string_offsets:
                    add_fn(builder, string_offsets[key])
                elif isinstance(value, (int, float, bool)):
                    add_fn(builder, value)

        offset = end_fn(builder)
        builder.Finish(offset)
        return bytes(builder.Output())

    except (ImportError, AttributeError, Exception) as e:
        logger.debug("Cannot serialize as %s: %s", type_name, e)
        return None
