# MIA MQTT Topics Specification v1.0

> This file is the single MQTT topic contract ([ADR-0017](../decisions/0017-mqtt-topic-namespace.md)). A new
> publisher or subscriber uses a topic from here, or adds it here in the same change.
>
> Legacy publishers that do not follow it yet (to be migrated, #191):
> `device/health/{vin}` and `device/metrics/{vin}` (Android), `mia/{device_id}/{layer}/{data_type}`
> (FlatBuffers gateway), `mia/telemetry/…` and `mia/alerts/…` (ESP32 OBD firmware),
> `mia/camera/service/health` (USB camera service), `hardware/arduino/led/*` (hardware bridge).

## Topic Structure
All topics follow the pattern: `{domain}/{action}/{device-id}`

## Vehicle Telemetry Topics

### OBD Data Stream
```
vehicle/telemetry/{vin}/obd
```
- **QoS**: 1 (At least once delivery)
- **Retained**: false
- **Payload**: JSON with OBD-II PIDs
- **Frequency**: 10Hz for critical parameters

### ANPR Detection Events
```
vehicle/events/{vin}/anpr
```
- **QoS**: 2 (Exactly once delivery)
- **Retained**: false
- **Payload**: License plate detection results
- **Trigger**: On plate detection

### Vehicle Alerts
```
vehicle/alerts/{vin}
```
- **QoS**: 2 (Exactly once delivery)
- **Retained**: true (for offline devices)
- **Payload**: Alert notifications
- **Priority**: Based on severity

## Device Control Topics

### IO Commands
```
vehicle/cmd/{vin}/io
```
- **QoS**: 1
- **Retained**: false
- **Payload**: Relay/LED/Buzzer commands
- **Direction**: Android → ESP32

### Device State Updates
```
device/state/{node-id}
```
- **QoS**: 1
- **Retained**: true
- **Payload**: Device health and status
- **Frequency**: Every 30 seconds

## Privacy & Security Topics

### Data Retention Commands
```
privacy/retention/{device-id}
```
- **QoS**: 2
- **Retained**: false
- **Payload**: Retention policy updates
- **Direction**: Android → All devices

### Security Audit Log
```
security/audit/{device-id}
```
- **QoS**: 1
- **Retained**: true
- **Payload**: Security events
- **Retention**: 30 days

## System Management Topics

### Device Discovery
```
system/discovery/{device-type}
```
- **QoS**: 0
- **Retained**: false
- **Payload**: Device advertisement
- **Frequency**: On startup, every 5 minutes

### OTA Updates
```
system/ota/{device-id}
```
- **QoS**: 2
- **Retained**: false
- **Payload**: Firmware update commands
- **Direction**: Android → ESP32/Pi

### Health Monitoring
```
system/health/{device-id}
```
- **QoS**: 1
- **Retained**: true
- **Payload**: Health metrics
- **Frequency**: Every 60 seconds

### Session Events
```
system/session/{session-id}
```
- **QoS**: 1
- **Retained**: false
- **Payload**: Session state changes (created, handoff, resumed, ended)
- **Direction**: RPi → all clients

## Home Lights and the Phone Assistant

These topics drive the home lights through the light engine (OpenClaw home-auto, outside this
repository) and zigbee2mqtt. The phone assistant (android-assistant `mqtt_publish`) and the
voice pipeline's light feedback publish them. They keep their `mia/lights/…` names: no MIA
service publishes or reads them, and renaming would break the light engine.

| Topic | Payload | Publisher | Consumer | Safety class |
|---|---|---|---|---|
| `mia/lights/mood` | `{"mood": "<name>"}`, names from the mcp-prompts prompt `openclaw-home-command-interpreter` | phone assistant | light engine | `direct` |
| `mia/lights/effect` | `{"effect": "rainbow\|pulse\|breathe\|flash\|wave", "duration": <s>}` | phone assistant | light engine | `direct` |
| `mia/lights/off` | empty | phone assistant | light engine | `direct` |
| `mia/lights/sound` | `{"enabled": <bool>, "mode": "<name>", "sensitivity": <0..1>}` | phone assistant | light engine | `direct` |
| `zigbee2mqtt/{ieee-address}/set` | zigbee2mqtt set payload, e.g. `{"state": "ON", "brightness": 200}` | phone assistant | zigbee2mqtt | `confirm` |
| `vehicle/cmd/{vin}/io` | see IO Commands | Pi backend only | ESP32 | `confirm`, never from the phone |

- **QoS**: 0 for lights (a lost light change is harmless and the next one replaces it)
- **Retained**: false

## Command Safety Classes

Every topic that makes something happen has one class. Clients that act on natural language
(the phone assistant, voice) must follow it:

- **`direct`**: harmless and idempotent; publish without asking. Only the four `mia/lights/…`
  topics above.
- **`confirm`**: needs a human yes for that exact topic and payload first. Every other command
  topic, including `zigbee2mqtt/…/set` and any other `mia/…` topic.

The phone assistant publishes `direct` topics right away and `confirm` topics only with a
one-time confirmation token. Anything outside `mia/…` and `zigbee2mqtt/…` is refused. On the
secure broker the ACL goes further ([ADR-0026](../decisions/0026-mqtt-broker-users-and-topic-acl.md)):
the `phone-assistant` user may write only `mia/lights/#`. A confirmed command for the car goes
through the Pi API, which alone may publish `vehicle/cmd/{vin}/io`. Tests check that the ACL
and this table agree: `tests/unit/infra/test_topic_safety_classes.py`.

## Topic Examples

### OBD Data Example
```json
{
  "topic": "vehicle/telemetry/WBA3B5C50ED123456/obd",
  "payload": {
    "fuel_level": 23,
    "engine_rpm": 2100,
    "vehicle_speed": 87,
    "coolant_temp": 95,
    "engine_load": 45,
    "dtc_codes": [],
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### ANPR Event Example
```json
{
  "topic": "vehicle/events/WBA3B5C50ED123456/anpr",
  "payload": {
    "plate_hash": "a1b2c3d4e5f6...",
    "confidence": 0.92,
    "snapshot_id": "uuid-v4",
    "location": {
      "lat": 49.1951,
      "lng": 16.6068
    },
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Alert Example
```json
{
  "topic": "vehicle/alerts/WBA3B5C50ED123456",
  "payload": {
    "severity": "warning",
    "code": "FUEL_LOW",
    "message": "Palivo dochází. Nejbližší čerpačka 4km.",
    "action_required": true,
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

## QoS Guidelines
- **QoS 0**: Discovery, non-critical status updates
- **QoS 1**: Telemetry data, device state
- **QoS 2**: Commands, alerts, security events

## Security Considerations
- The secure broker (`SECURE=1`, ADR-0026) refuses anonymous clients and gives each client
  role only its topics (`infra/edge/pi-gateway/services/mosquitto/acl`). The development
  brokers (`infra/containers/mosquitto`, the default gateway config, `mia-sim`) still allow
  anonymous clients; the authentication decision is #139.
- Device-specific topics use device certificates (planned)
- Sensitive data is encrypted in transit (planned: TLS listener)
- Command topics carry a safety class (see Command Safety Classes)

