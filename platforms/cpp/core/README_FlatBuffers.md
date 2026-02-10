# MIA FlatBuffers Message Protocol Schema

## Overview

This document describes the FlatBuffers message protocol schema used by the MIA (AI Service with MCP and Hardware Control) system. The schema provides a unified, efficient, and strongly-typed messaging system for all MIA components.

## Key Features

- **Efficient Binary Serialization**: FlatBuffers provides zero-copy deserialization and compact binary format
- **Strongly Typed**: Compile-time type safety with schema validation
- **Extensible**: Easy to add new message types without breaking existing code
- **Multi-Transport**: Works with TCP, MQTT, WebSockets, and other transports
- **Cross-Language**: Generated code available for C++, Python, JavaScript, and more

## Architecture

### Message Structure

```
Message Envelope (MQTTEnvelope)
├── Metadata (source, target, timestamp, message_id)
└── Payload (Message)
    ├── Request Union (polymorphic requests)
    └── Response Union (polymorphic responses)
```

### Transport Layers

1. **MQTT**: For pub/sub communication between distributed services
2. **TCP**: For direct client-server communication
3. **WebSockets**: For web-based interfaces
4. **FlatBuffers**: For efficient serialization

## Message Categories

### 1. Legacy Messages (Download & GPIO)

- **Download Operations**: File download management
- **GPIO Control**: Hardware pin control
- **System Status**: Basic system monitoring

### 2. Voice Control Messages

- **VoiceCommandRequest/Response**: Voice command processing
- **AudioProcessRequest/Response**: Speech-to-text processing
- **AudioStream***: Streaming audio support
- **WakeWordDetected**: Wake word detection events

### 3. AI Agent Messages

- **AIAgentRequest/Response**: AI agent interactions
- **AIContextUpdate**: Conversation context management
- **AIMemoryQuery/Result**: AI memory and recall operations

### 4. MCP (Model Context Protocol) Messages

- **MCPToolCall/Result**: Tool execution requests and results
- **MCPMessage**: Generic MCP message envelope

### 5. Advanced Hardware Control

- **HardwareConfig**: Device configuration
- **HardwareEvent**: Hardware event notifications

### 6. Service Coordination

- **ServiceAnnouncement**: Service discovery
- **ServiceQuery/List**: Service discovery queries

### 7. Security & Authentication

- **AuthenticationRequest/Response**: User authentication
- **AuthorizationRequest/Response**: Permission checking

### 8. Plugin & Extension System

- **PluginLoadRequest/Response**: Dynamic plugin loading
- **PluginUnloadRequest**: Plugin unloading
- **PluginMessage**: Plugin-specific messaging

### 9. Configuration Management

- **ConfigurationUpdate**: Runtime configuration changes
- **ConfigurationSnapshot**: Full configuration retrieval

### 10. Advanced Monitoring

- **MetricReport**: Real-time metrics and telemetry
- **HealthReport**: Comprehensive health checking

### 11. Event-Driven Architecture

- **EventSubscription**: Subscribe to system events
- **EventPublication**: Publish events to subscribers
- **EventAcknowledgment**: Event delivery confirmation

### 12. Workflow Orchestration

- **WorkflowStartRequest**: Start complex workflows
- **WorkflowStatusResponse**: Workflow progress tracking
- **WorkflowControlRequest**: Workflow lifecycle management

### 13. AI/ML Integration

- **ModelLoadRequest/Response**: Dynamic model loading
- **InferenceRequest/Response**: AI model inference
- **AIMemoryQuery/Result**: AI memory and recall

### 14. Distributed Coordination

- **LockRequest/Response**: Distributed locking
- **UnlockRequest**: Lock release

## Schema Evolution Strategy

The schema is designed for backward compatibility:

1. **Additive Changes**: New message types can be added to unions
2. **Optional Fields**: New fields should be optional with defaults
3. **Version Negotiation**: Use capabilities negotiation for feature detection
4. **Deprecation Path**: Old message types can be deprecated gradually

## Performance Characteristics

- **Zero-Copy Deserialization**: Direct memory access without copying
- **Compact Binary Format**: Typically 30-50% smaller than JSON
- **Type Safety**: Compile-time validation prevents runtime errors
- **Cross-Language**: Consistent APIs across C++, Python, JavaScript

## Usage Examples

### Voice Command Flow

```cpp
// Client sends voice command
flatbuffers::FlatBufferBuilder builder;
auto command = builder.CreateString("turn on the lights");
auto session_id = builder.CreateString("session_123");
auto request = CreateVoiceCommandRequest(builder, command, 0.95f,
                                       builder.CreateString("en-US"), session_id);
auto message = CreateMessage(builder, Request_VoiceCommandRequest, request.Union());
builder.Finish(message);

// Server processes and responds
auto response = CreateVoiceCommandResponse(builder,
                                         builder.CreateString("Lights activated"),
                                         0, // actions vector
                                         session_id,
                                         builder.CreateString("success"));
```

### AI Agent Interaction

```cpp
// Query AI agent
auto query = builder.CreateString("What's the weather like?");
auto agent_id = builder.CreateString("weather_agent");
auto request = CreateAIAgentRequest(builder, agent_id, query,
                                  builder.CreateString(""), 0, // parameters
                                  session_id);

// Response with actions
auto action = CreateAIAgentAction(builder,
                                builder.CreateString("execute_command"),
                                10, // priority
                                parameters_vector,
                                5000); // timeout
auto response = CreateAIAgentResponse(builder, agent_id,
                                    builder.CreateString("It's sunny"),
                                    builder.CreateVector(&action, 1),
                                    0.89f, session_id,
                                    builder.CreateString("success"));
```

### Authentication Flow

```cpp
// Authenticate user
auto auth_req = CreateAuthenticationRequest(builder,
                                          builder.CreateString("username"),
                                          builder.CreateString("password"),
                                          builder.CreateString("basic"),
                                          builder.CreateString("client_123"));

auto auth_resp = CreateAuthenticationResponse(builder,
                                            true, // success
                                            builder.CreateString("jwt_token_here"),
                                            1640995200ULL, // expires_at
                                            builder.CreateString("user_123"),
                                            permissions_vector,
                                            builder.CreateString("")); // no error
```

### Plugin System

```cpp
// Load a plugin
auto plugin_req = CreatePluginLoadRequest(builder,
                                        builder.CreateString("speech_processor"),
                                        builder.CreateString("1.0.0"),
                                        config_vector);

auto plugin_resp = CreatePluginLoadResponse(builder,
                                          builder.CreateString("speech_processor"),
                                          true, // success
                                          builder.CreateString(""), // no error
                                          capabilities_vector);
```

### Workflow Orchestration

```cpp
// Start a complex workflow
auto workflow_req = CreateWorkflowStartRequest(builder,
                                             builder.CreateString("data_processing_pipeline"),
                                             builder.CreateString("ETL Pipeline"),
                                             params_vector,
                                             5); // high priority

auto workflow_status = CreateWorkflowStatusResponse(builder,
                                                  builder.CreateString("workflow_123"),
                                                  builder.CreateString("running"),
                                                  0.75f, // 75% complete
                                                  builder.CreateString("Data Validation"),
                                                  3, // steps completed
                                                  4, // total steps
                                                  builder.CreateString("{}"), // partial result
                                                  builder.CreateString("")); // no error
```

### Real-time Telemetry

```cpp
// Report system metrics
auto metric = CreateMetricReport(builder,
                               builder.CreateString("cpu_usage"),
                               builder.CreateString("gauge"),
                               85.5f, // 85.5% CPU usage
                               labels_vector,
                               getCurrentTimestamp());

// Health check
auto health = CreateHealthReport(builder,
                               builder.CreateString("web_server"),
                               builder.CreateString("healthy"),
                               health_checks_vector,
                               getCurrentTimestamp());
```

## Code Generation

Generate C++ headers:
```bash
flatc --cpp --gen-mutable webgrab.fbs
```

Generate Python classes:
```bash
flatc --python webgrab.fbs
```

## Best Practices

### Message Design

1. **Use Unions for Polymorphism**: Allows handling different message types uniformly
2. **Include Session IDs**: For tracking conversations and requests
3. **Add Timestamps**: For debugging and ordering
4. **Version Fields**: For protocol versioning
5. **Optional Fields**: Use FlatBuffers' optional semantics

### Error Handling

1. **ErrorResponse**: Generic error message for failed operations
2. **Status Fields**: Include success/failure indicators
3. **Detailed Messages**: Provide actionable error descriptions

### Performance

1. **Reuse Builders**: FlatBufferBuilder instances can be reused
2. **Zero-Copy**: Access data without copying when possible
3. **Streaming**: Use streaming for large data (audio, telemetry)
4. **Compression**: Consider compression for network transport

## Schema Evolution

When adding new message types:

1. **Add to Unions**: Include in Request/Response unions
2. **Add Root Types**: For independent serialization
3. **Update Documentation**: Keep this document current
4. **Version Compatibility**: Ensure backward compatibility

## Integration Points

### Python Orchestrator
- Uses generated Python classes for message handling
- MQTT pub/sub for inter-service communication
- REST API translation layer

### C++ Services
- Direct FlatBuffers usage for performance
- Hardware control interfaces
- Audio processing pipelines

### Web Interface
- WebSocket transport with FlatBuffers
- JavaScript code generation
- Real-time dashboard updates

## Security Considerations

1. **Message Validation**: Always validate incoming messages
2. **Authentication**: Use transport-layer authentication
3. **Authorization**: Check permissions for hardware access
4. **Rate Limiting**: Prevent message flooding
5. **Encryption**: Use TLS for sensitive data

## Future Extensions

- **Video Streaming**: Add video message types
- **File Transfer**: Large file handling
- **Real-time Telemetry**: High-frequency sensor data
- **Distributed Coordination**: Service mesh integration
- **Plugin Architecture**: Dynamic message type loading