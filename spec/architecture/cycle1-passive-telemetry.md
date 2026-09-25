# Cycle 1 — Passive Telemetry Vertical Slice

Cycle 1 proves a read-only telemetry path before diagnostics, actuation, or
vehicle-specific comfort-bus mapping.

~~~mermaid
flowchart LR
    CAN["bench / replay / ESP32 CAN"] --> D["Cycle1CANDecoder"]
    D --> E["VehicleTelemetryEnvelope"]
    E --> Z["Pi serial / ZMQ"]
    Z --> API["FastAPI /ws/telemetry"]
    API --> A["Android dashboard"]
~~~

The safety boundary is explicit: the passive firmware build contains no
executable twai_transmit call, and the vehicle transceiver TXD line must also
remain physically disconnected. The synthetic 0x100 ignition mapping is a
test-harness convention, not an Audi 8H claim.

Replay the vector with:

~~~bash
tools/vehicle-replay/run_cycle1.sh
~~~

The expected synthetic values are ignition=true, battery_voltage=13.8 V,
engine_rpm=1750 and coolant_temp_c=86 °C. They are not vehicle measurements.

## Requirements and evidence

The slice is specified as REQ-AUTO-010 (envelope), REQ-AUTO-011 (replay harness),
REQ-AUTO-012 (ESP32 passive capture), REQ-AUTO-013 (Pi normalisation and exposure) and
REQ-AND-012 (Android card), under the passive-access rule REQ-NFR-002. Their evidence states,
and what each has not proven yet, live in `spec/requirements/`; the design decision is
[ADR-0009](../decisions/0009-canonical-vehicle-telemetry-envelope.md).
