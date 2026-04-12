---
mode: agent
description: "FlatBuffers schema design — mia.fbs, code generation, cross-platform message contracts"
---

# MIA Schema & Contracts Designer Worker

You own `schemas/`, `protos/`, `contracts/`, and generated bindings in `Mia/`.

## Schema Inventory

| File | Purpose |
|------|---------|
| `schemas/mia.fbs` | Master FlatBuffers schema — all message types |
| `schemas/generate.py` | Generates Python/C++ bindings from `.fbs` |
| `Mia/` | Auto-generated Python FlatBuffers classes |
| `protos/` | Protocol Buffers definitions |
| `contracts/ble-gatt.md` | BLE GATT service/characteristic UUIDs |
| `contracts/events.md` | System event definitions |
| `contracts/topics.md` | MQTT topic registry |
| `contracts/config.schema.json` | JSON Schema for configuration |

## Current Message Types (`mia.fbs`)

```
GPIOCommand / GPIOResponse     — pin control
SensorTelemetry                — sensor readings (temp, humidity, distance, pressure, light, motion)
SystemStatus                   — uptime, memory, CPU, device count
CommandAck                     — command results with status enum
DeviceInfo                     — device registry entries
LEDState                       — LED modes (Drive/Parked/Night/Service/Emergency) + AI state
VehicleTelemetry               — OBD: RPM, speed, coolant, DPF, fuel, Eolys additive
```

## Enums

```
GPIODirection: Input | Output | PWM
SensorType: Temperature | Humidity | Distance | Pressure | Light | Motion
CommandStatus: Success | Failure | Timeout | Invalid
DeviceType: GPIO | Sensor | Actuator | Display | Network
LEDMode: Drive | Parked | Night | Service | Emergency
AIState: Listening | Speaking | Thinking | Recording | Error | Idle
DpfStatus: Normal | Regenerating | Warning | Critical
```

## Generation Pipeline

```bash
cd schemas && python generate.py    # regenerates Mia/ Python bindings
```

## When working here

1. **Never hand-edit** `Mia/` — always modify `mia.fbs` and regenerate
2. Schema changes are **cross-cutting** — notify all platform workers
3. Run `generate.py` before committing schema changes
4. New message types need root_type declarations
5. Keep enums compact — byte-sized where possible
6. `metadata: [ubyte]` fields for extensibility without schema breaks
7. Update `contracts/topics.md` when adding MQTT-bound message types
8. C++ generated headers: `apps/rpi-backend/cpp-audio/core/webgrab_generated.h`
