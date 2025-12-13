# MIA Raspberry Pi API Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `http://<raspberry-pi-ip>:8000`

## Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://<raspberry-pi-ip>:8000/docs`
- **ReDoc**: `http://<raspberry-pi-ip>:8000/redoc`
- **OpenAPI Schema**: `http://<raspberry-pi-ip>:8000/openapi.json`

## Authentication

Currently, the API does not require authentication. For production deployments, implement authentication using API keys or JWT tokens.

## Endpoints

### Root

#### `GET /`

Get API information and status.

**Response**:
```json
{
  "service": "MIA Raspberry Pi API",
  "version": "1.0.0",
  "status": "running"
}
```

---

### Devices

#### `GET /devices`

List all connected devices.

**Response**:
```json
{
  "devices": [
    {
      "id": "device-1",
      "type": "GPIO",
      "status": "connected"
    }
  ],
  "count": 1,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### Commands

#### `POST /command`

Send command to a device.

**Request Body**:
```json
{
  "device": "led1",
  "action": "toggle",
  "params": {
    "brightness": 50
  }
}
```

**Response**:
```json
{
  "success": true,
  "response": {
    "status": "success",
    "message": "Command executed"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Command timeout - no response from device",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### Telemetry

#### `GET /telemetry`

Fetch latest sensor readings.

**Query Parameters**:
- `devices` (optional): Filter by device IDs (comma-separated)
- `sensors` (optional): Filter by sensor types (comma-separated)

**Example**: `GET /telemetry?devices=device-1,device-2`

**Response**:
```json
{
  "telemetry": {
    "device-1": {
      "temperature": 25.5,
      "humidity": 60.0,
      "timestamp": "2025-01-15T10:30:00Z"
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### System Status

#### `GET /status`

Get system health and uptime information.

**Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 86400,
  "uptime_human": "1 day, 0:00:00",
  "memory": {
    "total": 4294967296,
    "available": 2147483648,
    "percent": 50.0,
    "used": 2147483648
  },
  "cpu": {
    "percent": 25.5,
    "count": 4
  },
  "devices_connected": 3,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

### GPIO Control

#### `POST /gpio/configure`

Configure a GPIO pin.

**Request Body**:
```json
{
  "pin": 18,
  "direction": "output"
}
```

**Response**:
```json
{
  "success": true,
  "response": {
    "type": "GPIO_CONFIGURE_RESPONSE",
    "pin": 18,
    "status": "success",
    "message": "Pin configured"
  }
}
```

#### `POST /gpio/set`

Set GPIO pin value.

**Request Body**:
```json
{
  "pin": 18,
  "value": true
}
```

**Response**:
```json
{
  "success": true,
  "response": {
    "type": "GPIO_SET_RESPONSE",
    "pin": 18,
    "value": true,
    "status": "success"
  }
}
```

#### `GET /gpio/{pin}`

Get GPIO pin value.

**Path Parameters**:
- `pin` (integer): GPIO pin number

**Example**: `GET /gpio/18`

**Response**:
```json
{
  "success": true,
  "response": {
    "type": "GPIO_GET_RESPONSE",
    "pin": 18,
    "value": true,
    "status": "success"
  }
}
```

---

### WebSocket

#### `WS /ws`

WebSocket endpoint for real-time telemetry streaming.

**Connection**: `ws://<raspberry-pi-ip>:8000/ws`

**Message Format** (Server → Client):
```json
{
  "type": "telemetry",
  "data": {
    "device-1": {
      "temperature": 25.5,
      "humidity": 60.0
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Update Frequency**: 10Hz (100ms intervals)

**Example (JavaScript)**:
```javascript
const ws = new WebSocket('ws://192.168.1.100:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Telemetry:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

**Example (Python)**:
```python
import asyncio
import websockets
import json

async def listen_telemetry():
    uri = "ws://192.168.1.100:8000/ws"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Telemetry: {data}")

asyncio.run(listen_telemetry())
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Server error

Error responses follow this format:
```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

Currently, there is no rate limiting implemented. For production, consider implementing rate limiting to prevent abuse.

## CORS

CORS is enabled for all origins (`*`). For production, restrict CORS to specific domains.

## Examples

### cURL Examples

**Get system status**:
```bash
curl http://192.168.1.100:8000/status
```

**Configure GPIO pin**:
```bash
curl -X POST http://192.168.1.100:8000/gpio/configure \
  -H "Content-Type: application/json" \
  -d '{"pin": 18, "direction": "output"}'
```

**Set GPIO pin**:
```bash
curl -X POST http://192.168.1.100:8000/gpio/set \
  -H "Content-Type: application/json" \
  -d '{"pin": 18, "value": true}'
```

**Get telemetry**:
```bash
curl http://192.168.1.100:8000/telemetry
```

### Python Examples

```python
import requests

BASE_URL = "http://192.168.1.100:8000"

# Get status
response = requests.get(f"{BASE_URL}/status")
print(response.json())

# Configure GPIO
response = requests.post(
    f"{BASE_URL}/gpio/configure",
    json={"pin": 18, "direction": "output"}
)
print(response.json())

# Set GPIO
response = requests.post(
    f"{BASE_URL}/gpio/set",
    json={"pin": 18, "value": True}
)
print(response.json())
```

### JavaScript/TypeScript Examples

```typescript
const BASE_URL = 'http://192.168.1.100:8000';

// Get status
const status = await fetch(`${BASE_URL}/status`).then(r => r.json());
console.log(status);

// Configure GPIO
const configResponse = await fetch(`${BASE_URL}/gpio/configure`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pin: 18, direction: 'output' })
});
console.log(await configResponse.json());

// Set GPIO
const setResponse = await fetch(`${BASE_URL}/gpio/set`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pin: 18, value: true })
});
console.log(await setResponse.json());
```

## Integration with ZeroMQ

The API acts as a bridge between HTTP/REST and the ZeroMQ messaging system. All commands are forwarded to the ZeroMQ broker, which routes them to appropriate workers.

See [ZeroMQ Message Formats](./ZEROMQ_MESSAGE_FORMATS.md) for details on the underlying message protocol.

## Versioning

Current API version: **1.0.0**

API versioning will be implemented using URL path versioning (e.g., `/v1/`, `/v2/`) in future releases.

## Changelog

### v1.0.0 (2025-01-15)
- Initial API release
- GPIO control endpoints
- Telemetry endpoints
- WebSocket support
- System status endpoint
