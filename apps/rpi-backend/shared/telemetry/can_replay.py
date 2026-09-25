"""Synthetic/recorded CAN replay support for Cycle 1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .vehicle_envelope import build_cycle1_envelope

OBD_RESPONSE_ID = 0x7E8
BENCH_IGNITION_ID = 0x100


@dataclass(frozen=True)
class CANFrame:
    timestamp_ms: int
    can_id: int
    data: bytes
    bus: str = "powertrain"


def _data(value: bytes | str) -> bytes:
    if isinstance(value, bytes):
        return value
    compact = "".join(str(value).split())
    if len(compact) % 2:
        raise ValueError("CAN data must contain an even number of hex digits")
    return bytes.fromhex(compact)


def parse_frame(payload: Mapping[str, Any]) -> CANFrame:
    can_id = payload["can_id"]
    return CANFrame(
        timestamp_ms=int(payload.get("timestamp_ms", 0)),
        can_id=int(can_id, 0) if isinstance(can_id, str) else int(can_id),
        data=_data(payload["data"]),
        bus=str(payload.get("bus", "powertrain")),
    )


def _obd(frame: CANFrame) -> Optional[tuple[str, float, str]]:
    if frame.can_id != OBD_RESPONSE_ID or len(frame.data) < 4 or frame.data[1] != 0x41:
        return None
    pid = frame.data[2]
    if pid == 0x0C and len(frame.data) >= 5:
        return "engine_rpm", (frame.data[3] * 256 + frame.data[4]) / 4.0, "can:0x7E8/0x0C"
    if pid == 0x05:
        return "coolant_temp_c", frame.data[3] - 40.0, "can:0x7E8/0x05"
    if pid == 0x42 and len(frame.data) >= 5:
        return "battery_voltage", (frame.data[3] * 256 + frame.data[4]) / 1000.0, "can:0x7E8/0x42"
    return None


class Cycle1CANDecoder:
    def __init__(self, *, device_id: str, source: str = "replay.can", confidence: float = 1.0) -> None:
        self.device_id = device_id
        self.source = source
        self.confidence = confidence
        self._signals: dict[str, dict[str, Any]] = {}

    def consume(self, frame: CANFrame) -> Optional[dict[str, Any]]:
        if frame.can_id == BENCH_IGNITION_ID and frame.data:
            update = ("ignition", bool(frame.data[0] & 0x01), "replay:bench:kl15-frame")
        else:
            update = _obd(frame)
        if update is None:
            return None
        name, value, source = update
        self._signals[name] = {
            "value": value,
            "source": source,
            "confidence": self.confidence,
        }
        if len(self._signals) != 4:
            return None
        return build_cycle1_envelope(
            device_id=self.device_id,
            signals=self._signals,
            source=self.source,
            confidence=self.confidence,
        )

    def consume_payload(self, payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        return self.consume(parse_frame(payload))
