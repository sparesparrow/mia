# MIA API Reference

The MIA API is a REST/WebSocket API for controlling IoT devices and receiving telemetry data.

**Base URL:** `http://<rpi-address>:8000`

**Interactive Docs:** `http://<rpi-address>:8000/docs` (Swagger UI)

## Authentication

Authentication is optional but recommended for production deployments.

### API Key Authentication

Set the `MIA_API_KEY` environment variable to enable authentication:

```bash
export MIA_API_KEY=mia_api_your_secure_key_here
```

Provide the API key via:
- **Header:** `X-API-Key: <your-api-key>`
- **Query Parameter:** `?api_key=<your-api-key>`

### Disable Authentication

For development/testing:
```bash
export MIA_AUTH_DISABLED=1
```

## Endpoints

### System Status

#### GET /
Root endpoint with API information.

**Response:**
```json
{
  "service": "MIA Raspberry Pi API",
  "version": "1.0.0",
  "status": "running",
  "auth": "enabled",
  "registry": "enabled"
}
```

#### GET /status
System health and resource usage.

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 12345,
  "uptime_human": "3:25:45",
  "memory": {
    "total": 4294967296,
    "available": 2147483648,
    "percent": 50.0,
    "used": 2147483648
  },
  "cpu": {
    "percent": 15.5,
    "count": 4
  },
  "devices_connected": 3,
  "timestamp": "2025-01-15T12:00:00"
}
```

#### GET /auth/status
Check authentication status.

**Response:**
```json
{
  "enabled": true,
  "keys_configured": 1,
  "message": "Authentication enabled"
}
```

### Device Management

#### GET /devices
List all connected devices.

**Response:**
```json
{
  "devices": [
    {
      "device_id": "gpio_worker_1",
      "device_type": "gpio",
      "name": "GPIO Controller",
      "capabilities": ["GPIO_SET", "GPIO_GET"],
      "status": "online",
      "last_seen": "2025-01-15T12:00:00",
      "is_healthy": true
    }
  ],
  "count": 1,
  "timestamp": "2025-01-15T12:00:00"
}
```

#### POST /command
Send a command to a device.

**Request:**
```json
{
  "device": "gpio_worker_1",
  "action": "GPIO_SET",
  "params": {
    "pin": 18,
    "value": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "type": "GPIO_SET_RESPONSE",
    "pin": 18,
    "value": true
  },
  "timestamp": "2025-01-15T12:00:00"
}
```

### Telemetry

#### GET /telemetry
Get latest sensor/telemetry readings.

**Response:**
```json
{
  "telemetry": {
    "vehicle": {
      "rpm": 2500.0,
      "speed_kmh": 60.0,
      "coolant_temp_c": 85.0,
      "dpf_soot_mass_g": 12.5,
      "oil_temp_c": 95.0,
      "timestamp": "2025-01-15T12:00:00"
    }
  },
  "timestamp": "2025-01-15T12:00:00"
}
```

### GPIO Control

#### POST /gpio/configure
Configure a GPIO pin.

**Request:**
```json
{
  "pin": 18,
  "direction": "output"
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "type": "GPIO_CONFIGURE_RESPONSE",
    "pin": 18,
    "direction": "output"
  }
}
```

#### POST /gpio/set
Set a GPIO pin value.

**Request:**
```json
{
  "pin": 18,
  "value": true
}
```

#### GET /gpio/{pin}
Get current value of a GPIO pin.

**Response:**
```json
{
  "success": true,
  "response": {
    "type": "GPIO_GET_RESPONSE",
    "pin": 18,
    "value": true
  }
}
```

### Device Registry

#### GET /registry/status
Get registry status summary.

**Response:**
```json
{
  "total_devices": 3,
  "online": 3,
  "offline": 0,
  "error": 0,
  "healthy": 3,
  "by_type": {
    "gpio": 1,
    "obd": 1,
    "serial": 1
  },
  "timestamp": "2025-01-15T12:00:00"
}
```

#### GET /registry/devices
List devices with optional filters.

**Query Parameters:**
- `device_type` - Filter by type (gpio, obd, serial, etc.)
- `capability` - Filter by capability
- `healthy_only` - Only return healthy devices

**Example:**
```
GET /registry/devices?device_type=gpio&healthy_only=true
```

#### GET /registry/devices/{device_id}
Get specific device by ID.

#### POST /registry/devices
Register a new device (for testing).

**Request:**
```json
{
  "device_id": "test_device_1",
  "device_type": "gpio",
  "name": "Test Device",
  "capabilities": ["GPIO_SET", "GPIO_GET"],
  "metadata": {}
}
```

#### DELETE /registry/devices/{device_id}
Unregister a device.

#### POST /registry/devices/{device_id}/heartbeat
Send a heartbeat for a device.

## WebSocket

### WS /ws
Real-time telemetry streaming.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Telemetry:', data);
};
```

**Message Format:**
```json
{
  "type": "telemetry",
  "data": {
    "vehicle": {
      "rpm": 2500.0,
      "speed_kmh": 60.0
    }
  },
  "timestamp": "2025-01-15T12:00:00"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid device type: unknown"
}
```

### 401 Unauthorized
```json
{
  "detail": "Missing or invalid API key"
}
```

### 404 Not Found
```json
{
  "detail": "Device not found: device_123"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Device registry not available"
}
```

## Code Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "your_api_key"

headers = {"X-API-Key": API_KEY}

# Get devices
response = requests.get(f"{BASE_URL}/devices", headers=headers)
print(response.json())

# Send command
response = requests.post(
    f"{BASE_URL}/command",
    headers=headers,
    json={
        "device": "gpio_worker_1",
        "action": "GPIO_SET",
        "params": {"pin": 18, "value": True}
    }
)
print(response.json())
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:8000';
const API_KEY = 'your_api_key';

// Get devices
fetch(`${BASE_URL}/devices`, {
  headers: { 'X-API-Key': API_KEY }
})
.then(res => res.json())
.then(data => console.log(data));

// WebSocket telemetry
const ws = new WebSocket(`${BASE_URL.replace('http', 'ws')}/ws`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### cURL

```bash
# Get status
curl http://localhost:8000/status

# With authentication
curl -H "X-API-Key: your_key" http://localhost:8000/devices

# Send command
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{"device": "gpio_1", "action": "GPIO_SET", "params": {"pin": 18, "value": true}}'
```
