# 0017. One MQTT topic contract: `spec/interfaces/topics.md`

- Status: Proposed
- Date: 2026-10-25
- Requirements: REQ-AND-006, REQ-HW-007, REQ-ORCH-004, REQ-ORCH-009, REQ-AUTO-012

## Context
ADR-0003 keeps MQTT at the edges, for devices and external systems that need it. Over time four naming schemes
grew up side by side, and no document says which one a new publisher should use:

| Prefix | Who publishes or subscribes | Where |
|---|---|---|
| `vehicle/telemetry/{vin}/obd`, `vehicle/alerts/{vin}`, `vehicle/events/{vin}/anpr` | Android app; the legacy Docker stack's simulators | `apps/android/.../core/background/MQTTTopics.kt`, `infra/edge/pi-gateway/services/` |
| `system/session/{id}`, `system/health/{device-id}` | Android (session); legacy health publisher | `MQTTTopics.kt`, `infra/edge/pi-gateway/services/health-publisher/` |
| `device/health/{vin}`, `device/metrics/{vin}` | Android | `MQTTTopics.kt` |
| `mia/{device_id}/{layer}/{data_type}` (cognitive layers) | FlatBuffers-to-JSON-RPC gateway | `orchestration/mcp/modules/shared/topics.py`, `orchestration/mcp/modules/flatbuffers-gateway/` |
| `mia/telemetry/…`, `mia/alerts/{fuel,coolant,rpm}` | ESP32 OBD firmware | `apps/esp32/firmware-obd/main/main.c`, `components/ai_servis_obd/ai_servis_obd.c` |
| `mia/camera/service/health` | USB camera service | `apps/rpi-backend/py-api/services/usb_camera_service.py` |
| `hardware/arduino/led/*` | Hardware bridge LED controller | `orchestration/mcp/modules/hardware-bridge/arduino_led_controller.py` |

`spec/interfaces/topics.md` already specifies the first two rows and `device/state/{node-id}`, but nothing ties
the code to it, and the Android health topic does not match it.

## Decision
- `spec/interfaces/topics.md` is the single contract for MQTT topics that cross a device or process boundary
  (phone, ESP32, Pi, any external broker). Vehicle data is keyed by VIN under `vehicle/…`; device state under
  `device/state/{node-id}`; system health and sessions under `system/…`.
- A new MQTT publisher or subscriber uses a topic from that file, or adds one there in the same change.
- The other prefixes in the table above are legacy. They keep working until each is migrated; a migration
  changes the producer and its consumers together and updates `topics.md`.
- ZeroMQ topics (`mcu/telemetry`, `mia/voice/*` and the like) are not MQTT and are out of scope; the voice ones
  are specified in `spec/interfaces/voice.md`.

## Consequences
- A reader can tell from one file which topics are contract and which are legacy.
- Migrating the legacy producers is work: the ESP32 alerts, the cognitive-layer gateway, the camera health topic,
  the LED controller and the Android health/metrics topics. It is tracked in #191, not done by this ADR.
- No code changes with this decision.

## Sources
`spec/decisions/0003-zeromq-control-plane-and-telemetry.md`, `spec/interfaces/topics.md` and the files in the table.
