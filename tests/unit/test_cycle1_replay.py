from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
RPI_ROOT = ROOT / "apps" / "rpi-backend"
if str(RPI_ROOT) not in sys.path:
    sys.path.insert(0, str(RPI_ROOT))

from shared.telemetry.can_replay import Cycle1CANDecoder
from shared.telemetry.vehicle_envelope import build_cycle1_envelope_from_flat_payload, flatten_cycle1_envelope


def test_fixture_reconstructs_complete_envelope():
    schema = json.loads((ROOT / "schemas" / "vehicle_telemetry_envelope.schema.json").read_text())
    decoder = Cycle1CANDecoder(device_id="cycle1-test", source="replay.can", confidence=1.0)
    final = None
    for line in (ROOT / "tests" / "fixtures" / "cycle1_bench.jsonl").read_text().splitlines():
        if line and not line.startswith("#"):
            final = decoder.consume_payload(json.loads(line)) or final
    assert final is not None
    Draft202012Validator(schema).validate(final)
    assert final["signals"]["ignition"]["value"] is True
    assert final["signals"]["battery_voltage"]["value"] == 13.8
    assert final["signals"]["engine_rpm"]["value"] == 1750.0
    assert final["signals"]["coolant_temp_c"]["value"] == 86.0
    assert flatten_cycle1_envelope(final) == {
        "ignition": True,
        "battery_voltage": 13.8,
        "engine_rpm": 1750.0,
        "coolant_temp_c": 86.0,
    }


def test_flat_payload_requires_all_four_signals():
    payload = {"device_id": "simulation_0", "ignition": True, "battery_voltage": 13.8, "engine_rpm": 1750, "coolant_temp_c": 86}
    assert build_cycle1_envelope_from_flat_payload(payload, source="simulation", confidence=0.5)


def test_partial_flat_payload_is_not_promoted():
    assert build_cycle1_envelope_from_flat_payload({"device_id": "simulation_0", "engine_rpm": 1750}, source="simulation", confidence=0.5) is None
