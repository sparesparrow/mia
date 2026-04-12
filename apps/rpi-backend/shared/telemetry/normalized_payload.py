"""
Normalized vehicle telemetry payload contract.

Every transport producer (serial bridge, OBD worker, transport agent) should
emit payloads compatible with ``build_telemetry_payload`` so that downstream
consumers (FastAPI cache, WebSocket, VAG/Audi bridge, Android) stay
protocol-agnostic.

The shape is intentionally flat with well-known top-level keys so JSON
consumers never need to know whether the source was a serial line, an ELM327
adapter, or a SocketCAN interface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


# ── Well-known telemetry field names ──────────────────────────────────────

GENERIC_PID_FIELDS = frozenset({
    "speed_kmh",
    "engine_rpm",
    "coolant_temp_c",
    "fuel_level_percent",
    "battery_voltage",
    "vin",
})

ADAPTER_CAPABILITY_FIELDS = frozenset({
    "capability_class",
    "capability_source",
    "adapter_kind",
    "transport",
    "device_path_or_address",
    "connection_state",
    "active_protocol",
    "supports_uds",
})

VALID_CAPABILITY_CLASSES = frozenset({
    "unknown",
    "generic_pid_only",
    "uds_read_only",
})


def build_telemetry_payload(
    *,
    speed_kmh: Optional[float] = None,
    engine_rpm: Optional[float] = None,
    coolant_temp_c: Optional[float] = None,
    fuel_level_percent: Optional[float] = None,
    battery_voltage: Optional[float] = None,
    vin: Optional[str] = None,
    dtc_codes: Optional[list[str]] = None,
    did_values: Optional[dict[str, Any]] = None,
    device_id: Optional[str] = None,
    adapter_capabilities: Optional[dict[str, Any]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a normalized telemetry payload for ZeroMQ publication.

    All fields are optional.  Transport producers should populate whatever
    they have and leave the rest ``None``.  Consumers tolerate missing keys.
    """
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if device_id is not None:
        payload["device_id"] = device_id

    if speed_kmh is not None:
        payload["speed_kmh"] = speed_kmh
    if engine_rpm is not None:
        payload["engine_rpm"] = engine_rpm
    if coolant_temp_c is not None:
        payload["coolant_temp_c"] = coolant_temp_c
    if fuel_level_percent is not None:
        payload["fuel_level_percent"] = fuel_level_percent
    if battery_voltage is not None:
        payload["battery_voltage"] = battery_voltage
    if vin is not None:
        payload["vin"] = vin

    if dtc_codes:
        payload["dtc_codes"] = list(dtc_codes)
    if did_values:
        payload["did_values"] = dict(did_values)

    if adapter_capabilities:
        payload["adapter_capabilities"] = dict(adapter_capabilities)

    if extra:
        payload.update(extra)

    return payload


def build_adapter_capabilities(
    *,
    capability_class: str = "unknown",
    capability_source: str = "unknown",
    adapter_kind: str = "unknown",
    transport: str = "unknown",
    device_path_or_address: Optional[str] = None,
    connection_state: str = "initializing",
    active_protocol: Optional[str] = None,
    supports_uds: Optional[bool] = None,
) -> dict[str, Any]:
    """Build an adapter capability block suitable for embedding in a telemetry payload."""
    caps: dict[str, Any] = {
        "capability_class": capability_class if capability_class in VALID_CAPABILITY_CLASSES else "unknown",
        "capability_source": capability_source,
        "adapter_kind": adapter_kind,
        "transport": transport,
        "connection_state": connection_state,
    }

    if device_path_or_address is not None:
        caps["device_path_or_address"] = device_path_or_address
    if active_protocol is not None:
        caps["active_protocol"] = active_protocol
    if supports_uds is not None:
        caps["supports_uds"] = supports_uds

    return caps
