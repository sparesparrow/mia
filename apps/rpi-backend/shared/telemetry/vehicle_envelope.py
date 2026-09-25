"""Canonical Cycle 1 vehicle telemetry envelope."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

SCHEMA_VERSION = 1
MESSAGE_TYPE = "vehicle.telemetry"
SIGNAL_DEFINITIONS = {
    "ignition": {"unit": "bool"},
    "battery_voltage": {"unit": "V"},
    "engine_rpm": {"unit": "rpm"},
    "coolant_temp_c": {"unit": "°C"},
}
_ALIASES = {
    "ignition": ("ignition", "kl15", "ignition_on"),
    "battery_voltage": ("battery_voltage", "vehicle_voltage", "voltage"),
    "engine_rpm": ("engine_rpm", "rpm"),
    "coolant_temp_c": ("coolant_temp_c", "coolant_temp", "coolant"),
}


class VehicleEnvelopeValidationError(ValueError):
    """Raised when the Cycle 1 runtime contract is invalid."""


def _timestamp(value: Optional[str | datetime]) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _coerce(name: str, value: Any) -> bool | float:
    if name == "ignition":
        if not isinstance(value, bool):
            raise VehicleEnvelopeValidationError("ignition must be boolean")
        return value
    if isinstance(value, bool):
        raise VehicleEnvelopeValidationError(f"{name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise VehicleEnvelopeValidationError(f"{name} must be numeric") from exc


def _signal(name: str, raw: Any, source: str, confidence: float) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        value = raw.get("value")
        unit = str(raw.get("unit", SIGNAL_DEFINITIONS[name]["unit"]))
        signal_source = str(raw.get("source", source))
        signal_confidence = float(raw.get("confidence", confidence))
    else:
        value = raw
        unit = SIGNAL_DEFINITIONS[name]["unit"]
        signal_source = source
        signal_confidence = confidence
    if not signal_source or not 0 <= signal_confidence <= 1:
        raise VehicleEnvelopeValidationError(f"invalid provenance for {name}")
    return {
        "value": _coerce(name, value),
        "unit": unit,
        "source": signal_source,
        "confidence": signal_confidence,
    }


def build_cycle1_envelope(
    *,
    device_id: str,
    signals: Mapping[str, Any],
    timestamp: Optional[str | datetime] = None,
    source: str = "unknown",
    confidence: float = 0.0,
) -> dict[str, Any]:
    if not device_id or not source:
        raise VehicleEnvelopeValidationError("device_id and source are required")
    if not 0 <= confidence <= 1:
        raise VehicleEnvelopeValidationError("confidence must be in [0, 1]")
    missing = set(SIGNAL_DEFINITIONS) - set(signals)
    if missing:
        raise VehicleEnvelopeValidationError(
            "complete Cycle 1 telemetry is missing: " + ", ".join(sorted(missing))
        )
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "message_type": MESSAGE_TYPE,
        "device_id": device_id,
        "timestamp": _timestamp(timestamp),
        "source": source,
        "confidence": float(confidence),
        "signals": {
            name: _signal(name, signals[name], source, confidence)
            for name in SIGNAL_DEFINITIONS
        },
    }
    validate_cycle1_envelope(envelope)
    return envelope


def build_cycle1_envelope_from_flat_payload(
    payload: Mapping[str, Any], *, source: str, confidence: float,
    device_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    values: dict[str, Any] = {}
    for canonical, aliases in _ALIASES.items():
        for key in aliases:
            if key in payload and payload[key] is not None:
                values[canonical] = payload[key]
                break
    if set(values) != set(SIGNAL_DEFINITIONS):
        return None
    return build_cycle1_envelope(
        device_id=device_id or str(payload.get("device_id") or "unknown"),
        signals=values,
        timestamp=payload.get("timestamp"),
        source=source,
        confidence=confidence,
    )


def validate_cycle1_envelope(envelope: Mapping[str, Any]) -> None:
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise VehicleEnvelopeValidationError("unsupported schema_version")
    if envelope.get("message_type") != MESSAGE_TYPE:
        raise VehicleEnvelopeValidationError("unsupported message_type")
    if not envelope.get("device_id") or not envelope.get("source"):
        raise VehicleEnvelopeValidationError("device_id and source are required")
    try:
        confidence = float(envelope["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise VehicleEnvelopeValidationError("confidence is required and numeric") from exc
    if not 0 <= confidence <= 1:
        raise VehicleEnvelopeValidationError("confidence must be in [0, 1]")
    timestamp = envelope.get("timestamp")
    if not timestamp:
        raise VehicleEnvelopeValidationError("timestamp is required")
    try:
        datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError as exc:
        raise VehicleEnvelopeValidationError("timestamp must be ISO-8601") from exc
    signals = envelope.get("signals")
    if not isinstance(signals, Mapping):
        raise VehicleEnvelopeValidationError("signals must be an object")
    missing = set(SIGNAL_DEFINITIONS) - set(signals)
    if missing:
        raise VehicleEnvelopeValidationError(
            "complete Cycle 1 telemetry is missing: " + ", ".join(sorted(missing))
        )
    for name, signal in signals.items():
        if name not in SIGNAL_DEFINITIONS:
            raise VehicleEnvelopeValidationError(f"unknown Cycle 1 signal: {name}")
        if not isinstance(signal, Mapping):
            raise VehicleEnvelopeValidationError(f"{name} must be an object")
        for key in ("value", "unit", "source", "confidence"):
            if key not in signal:
                raise VehicleEnvelopeValidationError(f"{name} signal missing {key}")
        _coerce(name, signal["value"])
        signal_confidence = float(signal["confidence"])
        if not signal["source"] or not 0 <= signal_confidence <= 1:
            raise VehicleEnvelopeValidationError(f"invalid provenance for {name}")


def flatten_cycle1_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    validate_cycle1_envelope(envelope)
    return {name: envelope["signals"][name]["value"] for name in SIGNAL_DEFINITIONS}
