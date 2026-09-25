# MIA BLE GATT Specification v1.0

## Overview
Bluetooth Low Energy (BLE) GATT services for ESP32 to Android communication in MIA system.

## Service UUIDs
- **Telemetry Service**: `0xFFF0`
- **Command Service**: `0xFFF1`
- **Configuration Service**: `0xFFF2`
- **OTA Service**: `0xFFF3`

## Service 0xFFF0 - Telemetry Service

### Characteristic 0xFFF1 - Telemetry Data (Notify)
- **UUID**: `0xFFF1`
- **Properties**: Notify
- **Format**: CBOR encoded telemetry data
- **Max Size**: 512 bytes
- **Update Frequency**: 1Hz (configurable)

**Payload Structure**:
```cbor
{
  "fuel_level": 23,
  "engine_rpm": 2100,
  "vehicle_speed": 87,
  "coolant_temp": 95,
  "engine_load": 45,
  "dtc_codes": ["P0420"],
  "timestamp": 1642234567
}
```

### Characteristic 0xFFF2 - Device Status (Read/Notify)
- **UUID**: `0xFFF2`
- **Properties**: Read, Notify
- **Format**: JSON
- **Update Frequency**: 30 seconds

**Payload Structure**:
```json
{
  "rssi": -45,
  "battery_level": 85,
  "fw_version": "1.2.3",
  "uptime": 86400,
  "connection_quality": "excellent"
}
```

## Service 0xFFF1 - Command Service

### Characteristic 0xFFF3 - IO Commands (Write)
- **UUID**: `0xFFF3`
- **Properties**: Write
- **Format**: JSON commands
- **Max Size**: 128 bytes

**Command Examples**:
```json
{
  "command": "set_led",
  "parameters": {
    "led_id": 1,
    "color": "green",
    "pattern": "solid"
  }
}
```

```json
{
  "command": "set_relay",
  "parameters": {
    "relay_id": 1,
    "state": "on",
    "duration": 5000
  }
}
```

### Characteristic 0xFFF4 - System Commands (Write)
- **UUID**: `0xFFF4`
- **Properties**: Write
- **Format**: JSON system commands

**Command Examples**:
```json
{
  "command": "restart",
  "parameters": {
    "reason": "ota_update"
  }
}
```

```json
{
  "command": "factory_reset",
  "parameters": {
    "confirm": true
  }
}
```

## Service 0xFFF2 - Configuration Service

### Characteristic 0xFFF5 - Device Config (Read/Write)
- **UUID**: `0xFFF5`
- **Properties**: Read, Write
- **Format**: JSON configuration
- **Max Size**: 1024 bytes

**Configuration Structure**:
```json
{
  "device_name": "MIA-OBD-001",
  "telemetry_interval": 1000,
  "obd_pids": ["05", "0C", "0D", "11", "15"],
  "alert_thresholds": {
    "fuel_low": 20,
    "temp_high": 105,
    "rpm_max": 6000
  },
  "privacy_settings": {
    "data_retention_hours": 72,
    "anpr_enabled": true,
    "cloud_sync": false
  }
}
```

### Characteristic 0xFFF6 - Watchlist (Read/Write)
- **UUID**: `0xFFF6`
- **Properties**: Read, Write
- **Format**: JSON array of hashed plates
- **Max Size**: 2048 bytes

**Watchlist Structure**:
```json
{
  "plates": [
    "a1b2c3d4e5f6...",
    "b2c3d4e5f6a1..."
  ],
  "version": 1,
  "last_updated": 1642234567
}
```

## Service 0xFFF3 - OTA Service

### Characteristic 0xFFF7 - OTA Control (Write)
- **UUID**: `0xFFF7`
- **Properties**: Write
- **Format**: JSON OTA commands

**OTA Command Structure**:
```json
{
  "command": "start_ota",
  "parameters": {
    "firmware_url": "https://ota.ai-servis.cz/firmware.bin",
    "firmware_size": 1048576,
    "firmware_hash": "sha256-hash",
    "firmware_version": "1.2.4"
  }
}
```

### Characteristic 0xFFF8 - OTA Progress (Notify)
- **UUID**: `0xFFF8`
- **Properties**: Notify
- **Format**: JSON progress updates

**Progress Structure**:
```json
{
  "status": "downloading",
  "progress": 45,
  "bytes_received": 471859,
  "total_bytes": 1048576,
  "estimated_time": 30
}
```

## Connection Parameters
- **Connection Interval**: 7.5ms - 4s (configurable)
- **Slave Latency**: 0-499
- **Supervision Timeout**: 4s
- **MTU Size**: 512 bytes (negotiated)

## Security
- **Pairing**: Just Works (for initial setup)
- **Bonding**: Required for production
- **Encryption**: AES-128 (when bonded)
- **Authentication**: Device certificates (optional)

## Power Management
- **Advertising Interval**: 100ms (when disconnected)
- **Connection Interval**: 1000ms (when idle)
- **Connection Interval**: 100ms (when active)
- **Sleep Mode**: Deep sleep when possible

## Error Handling
- **Connection Loss**: Automatic reconnection
- **Data Corruption**: CRC validation
- **Timeout**: 30-second command timeout
- **Retry Logic**: 3 attempts for critical commands

