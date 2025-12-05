# MIA Events Specification v1.0

## Overview
Canonical events for MIA system communication between Android app, ESP32 modules, and optional Pi gateway.

## Event Format
All events use JSON format with the following structure:
```json
{
  "event_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "source": "device-id",
  "event_type": "event.category",
  "payload": {},
  "metadata": {
    "version": "1.0",
    "priority": "low|normal|high|critical"
  }
}
```

## Vehicle Telemetry Events

### OBD Data Event
```json
{
  "event_type": "vehicle.telemetry.obd",
  "payload": {
    "vin": "vehicle-identification-number",
    "fuel_level": 45,
    "engine_rpm": 2100,
    "vehicle_speed": 87,
    "coolant_temp": 95,
    "engine_load": 45,
    "dtc_codes": ["P0420"],
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### ANPR Detection Event
```json
{
  "event_type": "vehicle.events.anpr",
  "payload": {
    "plate_hash": "hmac-sha256-hash",
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

### Vehicle Alert Event
```json
{
  "event_type": "vehicle.alerts",
  "payload": {
    "severity": "warning|error|critical",
    "code": "FUEL_LOW|ENGINE_OVERHEAT|DTC_DETECTED",
    "message": "Palivo dochází. Nejbližší čerpačka 4km.",
    "action_required": true,
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

## Device Control Events

### IO Command Event
```json
{
  "event_type": "vehicle.cmd.io",
  "payload": {
    "relay_1": "on|off",
    "led_status": "green|yellow|red|off",
    "buzzer": "short|long|off",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Device State Event
```json
{
  "event_type": "device.state",
  "payload": {
    "node_id": "esp32-obd-001",
    "rssi": -45,
    "battery_level": 85,
    "fw_version": "1.2.3",
    "uptime": 86400,
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

## Privacy & Security Events

### Data Retention Event
```json
{
  "event_type": "privacy.retention",
  "payload": {
    "data_type": "anpr|telemetry|clips",
    "retention_hours": 72,
    "records_deleted": 150,
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Security Audit Event
```json
{
  "event_type": "security.audit",
  "payload": {
    "action": "pairing|unpairing|access_denied",
    "device_id": "android-phone-001",
    "ip_address": "192.168.1.100",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

## Event Priorities
- **Critical**: Engine overheating, critical DTCs, security violations
- **High**: Fuel low, ANPR watchlist match, device failures
- **Normal**: Regular telemetry, device state updates
- **Low**: Debug logs, non-critical status updates

## Event Retention
- Critical/High: 30 days
- Normal: 7 days  
- Low: 24 hours
- All events are hashed for privacy compliance

