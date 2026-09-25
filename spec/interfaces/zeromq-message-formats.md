# ZeroMQ Message Formats

This document describes the message formats used in the MIA ZeroMQ messaging system.

## Architecture Overview

The MIA system uses ZeroMQ for inter-process communication:
- **Broker**: ROUTER socket on port 5555 (command/control)
- **Telemetry**: PUB/SUB sockets on port 5556 (telemetry data)
- **Workers**: DEALER sockets connecting to broker
- **Clients**: DEALER sockets connecting to broker

## Message Format

All messages are JSON-encoded strings sent over ZeroMQ sockets.

### General Message Structure

```json
{
  "type": "MESSAGE_TYPE",
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "optional-request-id",
  ...message-specific-fields
}
```

## Broker Messages (Port 5555)

### Worker Registration

**Type**: `WORKER_REGISTER`

**Direction**: Worker → Broker

**Payload**:
```json
{
  "type": "WORKER_REGISTER",
  "worker_type": "GPIO|OBD|BLE_OBD|SERIAL_BRIDGE",
  "capabilities": ["CAPABILITY1", "CAPABILITY2"],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**: None (acknowledged by broker accepting connection)

### GPIO Control Messages

#### Configure GPIO Pin

**Type**: `GPIO_CONFIGURE`

**Direction**: Client → Broker → GPIO Worker

**Payload**:
```json
{
  "type": "GPIO_CONFIGURE",
  "pin": 18,
  "direction": "input|output",
  "request_id": "req-123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**:
```json
{
  "type": "GPIO_CONFIGURE_RESPONSE",
  "pin": 18,
  "status": "success|error",
  "message": "Pin configured",
  "request_id": "req-123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Set GPIO Pin Value

**Type**: `GPIO_SET`

**Direction**: Client → Broker → GPIO Worker

**Payload**:
```json
{
  "type": "GPIO_SET",
  "pin": 18,
  "value": true,
  "request_id": "req-124",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**:
```json
{
  "type": "GPIO_SET_RESPONSE",
  "pin": 18,
  "value": true,
  "status": "success|error",
  "request_id": "req-124",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Get GPIO Pin Value

**Type**: `GPIO_GET`

**Direction**: Client → Broker → GPIO Worker

**Payload**:
```json
{
  "type": "GPIO_GET",
  "pin": 18,
  "request_id": "req-125",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**:
```json
{
  "type": "GPIO_GET_RESPONSE",
  "pin": 18,
  "value": true,
  "status": "success|error",
  "request_id": "req-125",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## OBD Messages

### OBD Status Request

**Type**: `OBD_STATUS`

**Direction**: Client → Broker → OBD Worker

**Payload**:
```json
{
  "type": "OBD_STATUS",
  "request_id": "req-126",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**:
```json
{
  "type": "OBD_STATUS_RESPONSE",
  "status": "running|stopped|error",
  "rpm": 2500,
  "speed": 60,
  "coolant_temp": 85,
  "request_id": "req-126",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### OBD PID Query

**Type**: `OBD_PID_QUERY`

**Direction**: Client → Broker → OBD Worker

**Payload**:
```json
{
  "type": "OBD_PID_QUERY",
  "pid": "010C",
  "request_id": "req-127",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**:
```json
{
  "type": "OBD_PID_QUERY_RESPONSE",
  "pid": "010C",
  "value": 2500,
  "unit": "rpm",
  "status": "success|error",
  "request_id": "req-127",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### OBD Command (via BLE)

**Type**: `OBD_COMMAND`

**Direction**: BLE Service → Broker → OBD Worker

**Payload**:
```json
{
  "type": "OBD_COMMAND",
  "command": "010C",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response**:
```json
{
  "type": "OBD_RESPONSE",
  "response": "41 0C 27 10",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Telemetry Messages (Port 5556)

Telemetry uses PUB/SUB pattern with topic-based filtering.

### MCU Telemetry

**Topic**: `mcu/telemetry`

**Publisher**: Serial Bridge

**Message Format**:
```json
{
  "pot1": 512,
  "pot2": 256,
  "throttle": 45,
  "coolant": 85,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### OBD Telemetry

**Topic**: `obd/telemetry`

**Publisher**: OBD Worker

**Message Format**:
```json
{
  "rpm": 2500,
  "speed": 60,
  "coolant_temp": 85,
  "load": 45,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Error Messages

All error responses follow this format:

```json
{
  "type": "ERROR",
  "error": "Error message description",
  "request_id": "req-123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Message Flow Examples

### GPIO Pin Toggle

```
1. Client → Broker: GPIO_CONFIGURE {pin: 18, direction: "output"}
2. Broker → GPIO Worker: GPIO_CONFIGURE {pin: 18, direction: "output"}
3. GPIO Worker → Broker: GPIO_CONFIGURE_RESPONSE {status: "success"}
4. Broker → Client: GPIO_CONFIGURE_RESPONSE {status: "success"}

5. Client → Broker: GPIO_SET {pin: 18, value: true}
6. Broker → GPIO Worker: GPIO_SET {pin: 18, value: true}
7. GPIO Worker → Broker: GPIO_SET_RESPONSE {status: "success"}
8. Broker → Client: GPIO_SET_RESPONSE {status: "success"}
```

### OBD Data Query via BLE

```
1. Android App → BLE Service: BLE Write "010C\r"
2. BLE Service → Broker: OBD_COMMAND {command: "010C"}
3. Broker → OBD Worker: OBD_COMMAND {command: "010C"}
4. OBD Worker → Broker: OBD_RESPONSE {response: "41 0C 27 10"}
5. Broker → BLE Service: OBD_RESPONSE {response: "41 0C 27 10"}
6. BLE Service → Android App: BLE Notify "41 0C 27 10\r>"
```

### Telemetry Subscription

```
1. Client → Telemetry PUB: Subscribe to topic "obd/telemetry"
2. OBD Worker → Telemetry PUB: Publish {topic: "obd/telemetry", data: {...}}
3. Telemetry PUB → Client: {topic: "obd/telemetry", data: {...}}
```

## Implementation Notes

### ZeroMQ Socket Types

- **ROUTER (Broker)**: Routes messages between clients and workers
- **DEALER (Workers/Clients)**: Connects to ROUTER for bidirectional communication
- **PUB (Telemetry Publisher)**: Broadcasts telemetry data
- **SUB (Telemetry Subscriber)**: Subscribes to telemetry topics

### Message Routing

The broker uses worker identity (set via `zmq.IDENTITY`) to route responses back to the correct client.

### Error Handling

- All messages should include a `request_id` for correlation
- Workers should respond with error messages for invalid requests
- Timeouts should be implemented on the client side (5-10 seconds)

### Performance Considerations

- Telemetry messages are sent at 10Hz (100ms intervals)
- Command/control messages are synchronous (request/response)
- Use async I/O for handling multiple concurrent requests

## Python Example

```python
import zmq
import json

# Connect to broker
context = zmq.Context()
socket = context.socket(zmq.DEALER)
socket.setsockopt_string(zmq.IDENTITY, "client-1")
socket.connect("tcp://localhost:5555")

# Send GPIO configure request
request = {
    "type": "GPIO_CONFIGURE",
    "pin": 18,
    "direction": "output",
    "request_id": "req-1",
    "timestamp": "2025-01-15T10:30:00Z"
}
socket.send_json(request)

# Wait for response
response = socket.recv_json()
print(f"Response: {response}")
```

## JavaScript/TypeScript Example

```typescript
import zmq from 'zeromq';

const socket = new zmq.Dealer();
socket.identity = 'client-1';
socket.connect('tcp://localhost:5555');

const request = {
  type: 'GPIO_CONFIGURE',
  pin: 18,
  direction: 'output',
  request_id: 'req-1',
  timestamp: new Date().toISOString()
};

socket.send(JSON.stringify(request));

socket.on('message', (msg) => {
  const response = JSON.parse(msg.toString());
  console.log('Response:', response);
});
```
