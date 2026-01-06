# MIA Schemas

This directory contains the FlatBuffers schema definitions that define the interfaces between all MIA components.

## Overview

MIA uses FlatBuffers for efficient, cross-platform serialization of messages between:
- Raspberry Pi orchestration layer
- Android companion app
- ESP32 edge devices
- Arduino peripherals

## Schema Files

### `mia.fbs`
Main MIA protocol schema containing:
- Device communication messages
- Sensor telemetry formats
- Command and control structures
- System status messages

### `vehicle.fbs`
Vehicle-specific schemas for:
- OBD-II diagnostic data
- Citroën C4 specific protocols
- Automotive telemetry formats
- Safety-critical message structures

## Usage

### Code Generation

Generate language-specific code from schemas:

```bash
# Generate Python code
flatc --python mia.fbs vehicle.fbs

# Generate Java code for Android
flatc --java mia.fbs vehicle.fbs

# Generate C++ code for ESP32
flatc --cpp mia.fbs vehicle.fbs
```

### Integration

Each component imports the generated code:

- **Raspberry Pi**: `from schemas.mia import *`
- **Android**: `import cz.mia.schemas.*`
- **ESP32**: `#include "schemas/mia_generated.h"`

## Protocol Details

### Message Flow

1. **Discovery**: Device info exchange
2. **Connection**: Handshake with capabilities
3. **Measurement**: Real-time data streaming
4. **Control**: Remote commands and configuration

### Reliability

- **Sequence numbers** for message ordering
- **CRC validation** for data integrity
- **Heartbeat messages** for connection monitoring
- **Automatic reconnection** on connection loss

## Versioning

- Schema changes maintain backward compatibility
- Version negotiation during device handshake
- Deprecated fields marked with appropriate comments