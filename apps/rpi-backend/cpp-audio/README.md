# C++ Platform Components

This directory contains the C++ components for the MIA system, providing hardware control and message processing capabilities.

## Architecture

The C++ platform uses a hybrid approach combining:

1. **MessageQueueProcessor (MQP)**: In-process job management for downloads and GPIO operations
2. **MQTT Bridge**: Cross-process communication with Python orchestrator
3. **FlatBuffers**: Efficient serialization for all message types
4. **Conan**: Dependency management with automatic header generation

## Components

### Core Library (`webgrab_core`)
- Download management and file operations
- FlatBuffers serialization
- Thread-safe queue processing
- GPIO abstraction layer

### Hardware Control Server (`hardware-server`)
- GPIO control for Raspberry Pi
- TCP interface for direct hardware access
- MQTT integration for Python communication
- Hybrid MQP + MQTT architecture

### MCP Server (`mcp-server`)
- Model Context Protocol implementation
- MQTT transport layer
- GPIO task execution
- Download job management

## Building

### Prerequisites
- CMake 3.20+
- Conan package manager
- C++20 compiler

### Build Process
```bash
# Install dependencies and build
conan install .. --profile ../profiles/linux-release --build missing
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake
cmake --build build -j$(nproc)
```

## Dependencies

### Conan-Managed
- `flatbuffers/2.0.0`: Serialization (headers auto-generated)
- `jsoncpp/1.9.5`: JSON processing
- `libcurl/8.5.0`: HTTP client
- `libgpiod/1.6.3`: GPIO control (hardware builds)
- `mosquitto/2.0.18`: MQTT communication
- `openssl/3.0.8`: SSL/TLS support

### Build Tools
- `flatbuffers/2.0.0`: FlatBuffers compiler (flatc)

## Integration with Python

### MQTT Topics
- `hardware/gpio/+`: GPIO control commands
- `hardware/response/+`: GPIO responses
- `webgrab/download/+`: Download operations
- `webgrab/status/+`: Status queries

### Message Flow
```
Python Orchestrator → MQTT → C++ Hardware Server → GPIO/Files
                      ↓
              MQTT Response ← C++ Processing
```

### Python Bridge
See `modules/hardware-bridge/` for Python client implementations that interface with these C++ components.

## Configuration

### MQTT Settings
```cpp
HardwareControlServer server(8081, "localhost", 1883, "/tmp/webgrab");
```

### GPIO Configuration
- Automatic GPIO chip detection
- Pin mode validation
- Error handling for hardware failures

## Development

### Code Generation
FlatBuffers headers are automatically generated during the Conan build process:

```bash
conan build ..  # Generates webgrab_generated.h from webgrab.fbs
```

### Testing
```bash
# Unit tests
ctest --test-dir build

# Integration tests
python modules/hardware-bridge/test_integration.py
```

## Deployment

### Docker Integration
```dockerfile
FROM conanio/gcc11:1.59.0

# Copy and build
COPY . /src
RUN conan install /src --profile linux-release
RUN cmake -S /src/platforms/cpp -B build
RUN cmake --build build
```

### Cross-Platform
- Linux (x86_64, ARM64): Full hardware support
- Windows: Client-only (no GPIO)
- macOS: Client-only (no GPIO)

## Troubleshooting

### Common Issues
1. **flatc not found**: Ensure Conan installed FlatBuffers
2. **GPIO permissions**: Run as root or configure udev rules
3. **MQTT connection**: Verify broker is running on port 1883

### Debug Builds
```bash
conan install .. --profile linux-simulation  # No hardware deps
cmake -DCMAKE_BUILD_TYPE=Debug
```

## Architecture Decisions

### Hybrid MQP + MQTT
- **MQP**: Low-latency, in-process operations
- **MQTT**: Cross-language, distributed communication
- **Result**: Best of both worlds without breaking existing code

### FlatBuffers Integration
- Schema-driven development
- Zero-copy serialization
- Cross-language compatibility
- Automatic header generation via Conan

### Conan Dependency Management
- Reproducible builds
- Automatic tool provisioning (flatc)
- Cross-platform package management
- Integration with CMake toolchain