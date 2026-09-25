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
