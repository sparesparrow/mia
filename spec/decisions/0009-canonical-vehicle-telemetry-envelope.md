# 0009. Canonical vehicle telemetry envelope v1

- Status: Accepted
- Date: 2026-09-25
- Requirements: REQ-AUTO-010, REQ-AUTO-011, REQ-AUTO-013, REQ-AND-012

## Context
Cycle 1 needs one shape for vehicle signals from bench replay, the ESP32 and simulation,
consumed by the Pi API and the Android app. Consumers must know where each value came from
and how far to trust it.

## Decision
- A JSON envelope, `message_type: vehicle.telemetry`, `schema_version: 1`, defined by
  `schemas/vehicle_telemetry_envelope.schema.json`.
- Cycle 1 carries four signals: ignition, battery_voltage, engine_rpm, coolant_temp_c.
- Every signal carries `unit`, `source` and `confidence`; the envelope carries its own
  `source` and `confidence`.
- Only complete, validated envelopes are published or cached; partial data is not promoted.

## Consequences
- New signals or fields need a schema version bump and consumer updates.
- Flat legacy telemetry fields stay alongside the envelope until consumers migrate.

## Sources
`apps/rpi-backend/shared/telemetry/vehicle_envelope.py`, `spec/architecture/cycle1-passive-telemetry.md`, PR #111.
