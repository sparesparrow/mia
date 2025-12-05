# MIA MQTT Topics Specification v1.0

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
- All topics require authentication
- Device-specific topics use device certificates
- Sensitive data is encrypted in transit
- Topic access is controlled by device roles

