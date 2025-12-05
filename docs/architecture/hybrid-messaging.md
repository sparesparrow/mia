# Hybrid Messaging Architecture: MQP + MQTT Integration

## Overview

The MIA system implements a hybrid messaging architecture that combines the **Message Queue Processor (MQP)** for in-process operations with **MQTT** for cross-process communication. This approach provides optimal performance for local operations while enabling distributed communication.

## Architecture Flow

### Primary Communication Path
```
Python AI Assistant → MQTT → MQP → C++ Hardware Server → MQP → GPIO Control
```

### Detailed Flow

1. **Python Orchestrator** (AI Assistant)
   - Receives voice commands or API requests
   - Translates to MCP protocol messages
   - Publishes to MQTT topics

2. **MQTT Transport Layer**
   - Topic-based routing: `hardware/gpio/control`, `webgrab/download/request`
   - QoS 1 (at least once delivery) for reliability
   - Retained messages for state synchronization

3. **C++ Message Queue Processor (MQP)**
   - Receives MQTT messages via MQTTReader
   - Processes requests through existing MQP job queue
   - Manages GPIO operations and download jobs
   - Thread-safe, low-latency processing

4. **Hardware Control Server**
   - Executes GPIO operations via libgpiod
   - Manages download jobs and file operations
   - Sends responses back through MQP → MQTT

## Component Integration

### MessageQueueProcessor (MQP) Enhancements

```cpp
class MessageQueueProcessor : public IRequestReader, public IResponseWriter {
public:
    // MQTT integration
    void enableMQTT(bool enable = true);
    bool isMQTTEnabled() const;

    // Existing MQP interface maintained
    bool next(RequestEnvelope& out) override;
    bool write(const DownloadResponse& resp) override;

private:
    std::unique_ptr<MQTTReader> mqtt_reader_;
    std::unique_ptr<MQTTWriter> mqtt_writer_;
    std::thread mqtt_processor_thread_;
};
```

### MQTT Bridge Implementation

```cpp
class MQTTBridge {
public:
    MQTTBridge(const std::string& host, int port, const std::string& client_id);
    bool publish(const std::string& topic, const std::string& payload);
    void setMessageCallback(MessageCallback callback);
};
```

### FlatBuffers Schema Extensions

```fbs
// GPIO Control Messages
table GPIOConfigureRequest {
  pin:int32;
  direction:string;
}

table GPIOStatusResponse {
  pins:[GPIOPinStatus];
}

// MQTT Transport Envelope
table MQTTEnvelope {
  message_id:string;
  timestamp:uint64;
  source:string;
  target:string;
  payload:Message;
}
```

## Benefits of Hybrid Approach

### Performance Optimization
- **MQP**: Microsecond latency for in-process operations
- **MQTT**: Millisecond latency for cross-process communication
- **Combined**: Optimal performance for each use case

### Backward Compatibility
- Existing MQP code unchanged
- TCP interface still available for direct hardware access
- Gradual migration path

### Reliability
- **MQP**: Guaranteed delivery within process
- **MQTT**: QoS levels for network communication
- **Combined**: End-to-end reliability

### Scalability
- **MQP**: Efficient for high-frequency operations
- **MQTT**: Scales across multiple processes/machines
- **Combined**: Handles both local and distributed workloads

## Implementation Details

### MQTT Topic Structure
```
hardware/
├── gpio/
│   ├── control      # GPIO commands from Python
│   ├── response/+   # GPIO responses to Python
│   └── status       # GPIO status broadcasts
├── download/
│   ├── request      # Download commands
│   ├── response/+   # Download status responses
│   └── abort/+      # Abort download commands
webgrab/
├── status           # System status queries
└── control          # System control commands
```

### Message Processing Pipeline

1. **MQTT Message Reception**
   ```cpp
   void MQTTReader::handle_message(const std::string& topic, const std::string& payload) {
       // Parse JSON payload
       // Create appropriate RequestEnvelope
       // Queue for MQP processing
   }
   ```

2. **MQP Job Processing**
   ```cpp
   void MessageQueueProcessor::enqueueJob(const std::string& url, IResponseWriter* writer) {
       // Create DownloadJob
       // Add to thread-safe queue
       // Process asynchronously
   }
   ```

3. **Response Routing**
   ```cpp
   void MQTTWriter::write(const GPIOStatusResponse& resp) {
       // Serialize to JSON
       // Publish to appropriate MQTT topic
   }
   ```

## Configuration

### MQTT Settings
```cpp
// Hardware server configuration
HardwareControlServer server(
    8081,  // TCP port
    "localhost",  // MQTT host
    1883   // MQTT port
);
```

### Python Client Configuration
```python
# Hardware bridge configuration
bridge = MCPBridge(
    mqtt_broker="localhost",
    mqtt_port=1883,
    hardware_host="localhost",
    hardware_port=8081
)
```

## Testing Strategy

### Unit Tests
- MQP functionality (existing tests)
- MQTT message parsing/serialization
- GPIO operation validation

### Integration Tests
```python
def test_hybrid_messaging():
    # Start C++ hardware server with MQTT
    # Send MQTT command from Python
    # Verify GPIO state via MQP
    # Check MQTT response
    pass
```

### Performance Benchmarks
- MQP latency: < 100μs
- MQTT round-trip: < 5ms
- Combined operations: < 10ms

## Deployment Considerations

### Single Machine
- All components on same host
- MQTT over localhost
- Direct memory sharing where possible

### Distributed Deployment
- Hardware server on edge device (Raspberry Pi)
- Python orchestrator on main server
- MQTT over network with TLS

### Docker Integration
```yaml
services:
  hardware-server:
    image: ai-servis-cpp:latest
    devices:
      - /dev/gpiomem
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1883

  python-orchestrator:
    environment:
      - MQTT_BROKER=mosquitto
      - HARDWARE_HOST=hardware-server
```

## Future Extensions

### WebSocket Transport
- Alternative to MQTT for web clients
- Lower latency for browser-based interfaces

### Protocol Buffers
- Alternative to FlatBuffers for specific use cases
- Better language support for some platforms

### Advanced Routing
- Message filtering and transformation
- Load balancing across multiple hardware servers
- Geographic routing for distributed deployments

## Monitoring and Debugging

### MQTT Debugging
```bash
# Subscribe to all messages
mosquitto_sub -h localhost -t "#" -v

# Publish test message
mosquitto_pub -h localhost -t "hardware/gpio/control" -m '{"pin":17,"direction":"output"}'
```

### MQP Debugging
- Thread-safe logging integration
- Job queue status monitoring
- Performance profiling hooks

This hybrid architecture provides the foundation for scalable, reliable communication between the Python AI orchestrator and C++ hardware components while maintaining optimal performance and backward compatibility.