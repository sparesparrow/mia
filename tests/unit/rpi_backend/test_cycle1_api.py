"""Cycle 1: the canonical envelope reaches /telemetry/cycle1 and /ws/telemetry."""

import asyncio
import copy
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", "apps", "rpi-backend", "py-api"))

from api import main as api_main  # noqa: E402
from fastapi import WebSocketDisconnect  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.rpi_backend.shared.telemetry.can_replay import Cycle1CANDecoder  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "cycle1_bench.jsonl"


@pytest.fixture
def client():
    api_main.telemetry_cache.clear()
    yield TestClient(api_main.app)
    api_main.telemetry_cache.clear()


def _replayed_envelope():
    decoder = Cycle1CANDecoder(device_id="cycle1-api", source="replay.can", confidence=1.0)
    envelope = None
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            envelope = decoder.consume_payload(json.loads(line)) or envelope
    assert envelope is not None
    return envelope


def test_envelope_module_is_wired_into_the_api():
    assert api_main.validate_cycle1_envelope is not None
    assert api_main.flatten_cycle1_envelope is not None


def test_valid_envelope_is_served_and_flattened(client):
    envelope = _replayed_envelope()
    api_main._handle_mcu_telemetry({"device_id": "esp32-obd-001", "vehicle_telemetry": envelope})

    body = client.get("/telemetry/cycle1").json()
    assert body["available"] is True
    assert body["telemetry"] == envelope

    cached = client.get("/telemetry").json()["telemetry"]["esp32-obd-001"]
    assert cached["engine_rpm"] == 1750.0
    assert cached["ignition"] is True


def test_invalid_envelope_never_replaces_the_last_good_one(client):
    envelope = _replayed_envelope()
    api_main._handle_mcu_telemetry({"device_id": "esp32-obd-001", "vehicle_telemetry": envelope})

    broken = copy.deepcopy(envelope)
    del broken["signals"]["engine_rpm"]
    api_main._handle_mcu_telemetry({"device_id": "esp32-obd-001", "vehicle_telemetry": broken})

    assert client.get("/telemetry/cycle1").json()["telemetry"] == envelope


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda env: "not-an-object",
        lambda env: {
            **env,
            "signals": {**env["signals"], "engine_rpm": {**env["signals"]["engine_rpm"], "confidence": None}},
        },
    ],
    ids=["non-object", "null-signal-confidence"],
)
def test_malformed_envelope_keeps_legacy_fields(client, corrupt):
    api_main._handle_mcu_telemetry(
        {"device_id": "esp32-obd-001", "adc_value": 512, "vehicle_telemetry": corrupt(_replayed_envelope())}
    )

    assert client.get("/telemetry/cycle1").json()["available"] is False
    assert client.get("/telemetry").json()["telemetry"]["esp32-obd-001"]["adc_value"] == 512


def test_invalid_first_envelope_is_not_served(client):
    broken = copy.deepcopy(_replayed_envelope())
    broken["schema_version"] = 99
    api_main._handle_mcu_telemetry({"device_id": "esp32-obd-001", "vehicle_telemetry": broken})

    body = client.get("/telemetry/cycle1").json()
    assert body["available"] is False
    assert body["telemetry"] is None


class _OneTickAsyncio:
    """Stand-in for api.main's asyncio: the second sleep ends the 10 Hz send loop."""

    def __init__(self):
        self._ticks = 0

    def __getattr__(self, name):
        return getattr(asyncio, name)

    async def sleep(self, delay):
        self._ticks += 1
        if self._ticks > 1:
            raise WebSocketDisconnect()


def test_telemetry_websocket_carries_the_envelope(client, monkeypatch):
    envelope = _replayed_envelope()
    api_main._handle_mcu_telemetry({"device_id": "esp32-obd-001", "vehicle_telemetry": envelope})
    monkeypatch.setattr(api_main, "asyncio", _OneTickAsyncio())

    with client.websocket_connect("/ws/telemetry") as websocket:
        message = websocket.receive_json()
    assert message["vehicle_telemetry"] == envelope
