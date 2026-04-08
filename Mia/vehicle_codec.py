"""Helpers for encoding and decoding vehicle FlatBuffers payloads."""

from __future__ import annotations

from typing import Any, Dict, Iterable

import flatbuffers

import Mia.VehicleTelemetry as VehicleTelemetry
from Mia.DpfStatus import DpfStatus


VEHICLE_FILE_IDENTIFIER = b"CTEL"

_INPUT_FIELD_ALIASES = {
    "rpm": ("rpm",),
    "speed_kmh": ("speed_kmh",),
    "coolant_temp_c": ("coolant_temp_c",),
    "dpf_soot_load_percent": ("dpf_soot_load_percent",),
    "dpf_soot_mass_g": ("dpf_soot_mass_g",),
    "dpf_regeneration_status": ("dpf_regeneration_status", "dpf_status"),
    "eolys_additive_level_percent": ("eolys_additive_level_percent", "eolys_level_pct"),
    "eolys_additive_level_l": ("eolys_additive_level_l", "eolys_level_l"),
    "battery_voltage": ("battery_voltage",),
    "oil_temperature_c": ("oil_temperature_c", "oil_temp_c"),
    "intake_air_temp_c": ("intake_air_temp_c",),
    "fuel_level_percent": ("fuel_level_percent",),
    "engine_load_percent": ("engine_load_percent",),
    "timestamp": ("timestamp",),
}


def _first_value(payload: Dict[str, Any], field_names: Iterable[str], default: Any) -> Any:
    for field_name in field_names:
        if field_name in payload and payload[field_name] is not None:
            return payload[field_name]
    return default


def _coerce_dpf_status(value: int | None) -> int:
    if value is None:
        return DpfStatus.Normal
    if value in (DpfStatus.Normal, DpfStatus.Regenerating, DpfStatus.Warning, DpfStatus.Critical):
        return value
    return DpfStatus.Warning


def _payload_float(payload: Dict[str, Any], field_name: str) -> float:
    return float(_first_value(payload, _INPUT_FIELD_ALIASES[field_name], 0.0))


def _payload_uint64(payload: Dict[str, Any], field_name: str) -> int:
    return int(_first_value(payload, _INPUT_FIELD_ALIASES[field_name], 0))


def buffer_has_vehicle_identifier(buffer: bytes) -> bool:
    return len(buffer) >= 8 and buffer[4:8] == VEHICLE_FILE_IDENTIFIER


def build_vehicle_telemetry(payload: Dict[str, Any]) -> bytes:
    """Build the live vehicle telemetry buffer from canonical or legacy keys."""
    builder = flatbuffers.Builder(1024)

    VehicleTelemetry.VehicleTelemetryStart(builder)
    VehicleTelemetry.VehicleTelemetryAddRpm(builder, _payload_float(payload, "rpm"))
    VehicleTelemetry.VehicleTelemetryAddSpeedKmh(builder, _payload_float(payload, "speed_kmh"))
    VehicleTelemetry.VehicleTelemetryAddCoolantTempC(builder, _payload_float(payload, "coolant_temp_c"))
    VehicleTelemetry.VehicleTelemetryAddDpfSootLoadPercent(builder, _payload_float(payload, "dpf_soot_load_percent"))
    VehicleTelemetry.VehicleTelemetryAddDpfSootMassG(builder, _payload_float(payload, "dpf_soot_mass_g"))
    VehicleTelemetry.VehicleTelemetryAddDpfRegenerationStatus(
        builder,
        _coerce_dpf_status(_first_value(payload, _INPUT_FIELD_ALIASES["dpf_regeneration_status"], None)),
    )
    VehicleTelemetry.VehicleTelemetryAddEolysAdditiveLevelPercent(
        builder,
        _payload_float(payload, "eolys_additive_level_percent"),
    )
    VehicleTelemetry.VehicleTelemetryAddEolysAdditiveLevelL(
        builder,
        _payload_float(payload, "eolys_additive_level_l"),
    )
    VehicleTelemetry.VehicleTelemetryAddBatteryVoltage(builder, _payload_float(payload, "battery_voltage"))
    VehicleTelemetry.VehicleTelemetryAddOilTemperatureC(builder, _payload_float(payload, "oil_temperature_c"))
    VehicleTelemetry.VehicleTelemetryAddIntakeAirTempC(builder, _payload_float(payload, "intake_air_temp_c"))
    VehicleTelemetry.VehicleTelemetryAddFuelLevelPercent(builder, _payload_float(payload, "fuel_level_percent"))
    VehicleTelemetry.VehicleTelemetryAddEngineLoadPercent(builder, _payload_float(payload, "engine_load_percent"))
    VehicleTelemetry.VehicleTelemetryAddTimestamp(builder, _payload_uint64(payload, "timestamp"))

    telemetry = VehicleTelemetry.VehicleTelemetryEnd(builder)
    builder.Finish(telemetry, file_identifier=VEHICLE_FILE_IDENTIFIER)
    return bytes(builder.Output())


def build_citroen_telemetry(payload: Dict[str, Any]) -> bytes:
    """Backward-compatible wrapper for the live Citroen telemetry payload."""
    return build_vehicle_telemetry(payload)


def parse_vehicle_telemetry(buffer: bytes, *, require_identifier: bool = False) -> Dict[str, Any]:
    """Parse the live vehicle telemetry buffer using canonical schema field names."""
    if require_identifier and not buffer_has_vehicle_identifier(buffer):
        raise ValueError("Expected a VehicleTelemetry FlatBuffer with file identifier CTEL")

    telemetry = VehicleTelemetry.VehicleTelemetry.GetRootAs(buffer, 0)
    return {
        "rpm": round(telemetry.Rpm(), 1),
        "speed_kmh": round(telemetry.SpeedKmh(), 1),
        "coolant_temp_c": round(telemetry.CoolantTempC(), 1),
        "dpf_soot_load_percent": round(telemetry.DpfSootLoadPercent(), 2),
        "dpf_soot_mass_g": round(telemetry.DpfSootMassG(), 2),
        "dpf_regeneration_status": telemetry.DpfRegenerationStatus(),
        "eolys_additive_level_percent": round(telemetry.EolysAdditiveLevelPercent(), 1),
        "eolys_additive_level_l": round(telemetry.EolysAdditiveLevelL(), 2),
        "battery_voltage": round(telemetry.BatteryVoltage(), 2),
        "oil_temperature_c": round(telemetry.OilTemperatureC(), 1),
        "intake_air_temp_c": round(telemetry.IntakeAirTempC(), 1),
        "fuel_level_percent": round(telemetry.FuelLevelPercent(), 1),
        "engine_load_percent": round(telemetry.EngineLoadPercent(), 1),
        "timestamp": telemetry.Timestamp(),
    }


def parse_citroen_telemetry(buffer: bytes, *, require_identifier: bool = False) -> Dict[str, Any]:
    """Parse the live vehicle telemetry buffer using the legacy payload field names."""
    telemetry = parse_vehicle_telemetry(buffer, require_identifier=require_identifier)
    return {
        "rpm": telemetry["rpm"],
        "speed_kmh": telemetry["speed_kmh"],
        "coolant_temp_c": telemetry["coolant_temp_c"],
        "dpf_soot_load_percent": telemetry["dpf_soot_load_percent"],
        "dpf_soot_mass_g": telemetry["dpf_soot_mass_g"],
        "dpf_status": telemetry["dpf_regeneration_status"],
        "eolys_level_pct": telemetry["eolys_additive_level_percent"],
        "eolys_level_l": telemetry["eolys_additive_level_l"],
        "battery_voltage": telemetry["battery_voltage"],
        "oil_temp_c": telemetry["oil_temperature_c"],
        "intake_air_temp_c": telemetry["intake_air_temp_c"],
        "fuel_level_percent": telemetry["fuel_level_percent"],
        "engine_load_percent": telemetry["engine_load_percent"],
        "timestamp": telemetry["timestamp"],
    }