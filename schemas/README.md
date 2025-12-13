# MIA FlatBuffers Schemas

This directory contains the FlatBuffers schema definitions for the Modular IoT Assistant (MIA) system. FlatBuffers provides efficient, cross-platform serialization for high-performance messaging between system components.

## Schema Overview

### Core Message Types

#### GPIO Control Messages
- `GPIOCommand` - Configure GPIO pins (direction, value)
- `GPIOResponse` - GPIO operation responses

#### Sensor Telemetry
- `SensorTelemetry` - Generic sensor data (temperature, humidity, distance, pressure, etc.)
- `SensorType` - Enumeration of supported sensor types

#### System Status
- `SystemStatus` - System health and resource usage information

#### Command Acknowledgments
- `CommandAck` - Response to commands with success/failure status
- `CommandStatus` - Enumeration of possible command outcomes

#### Device Management
- `DeviceInfo` - Device registration and capability information
- `DeviceType` - Enumeration of device categories

#### LED Control (Phase 4.4)
- `LEDState` - LED display state and mode control
- `LEDMode` - Different system modes (Drive, Parked, Night, Service)
- `AIState` - AI assistant states for LED feedback

#### Vehicle Telemetry
- `VehicleTelemetry` - Comprehensive vehicle sensor data (expanded from original CitroenTelemetry)
- `DpfStatus` - Diesel Particulate Filter regeneration states

## Usage

### Generating Bindings

Run the generation script to create language-specific bindings:

```bash
# Generate both Python and C++ bindings
python schemas/generate.py

# Generate only Python bindings
python schemas/generate.py --cpp=false

# Generate only C++ bindings
python schemas/generate.py --python=false

# Specify custom output directory
python schemas/generate.py --output-dir /custom/path
```

### Python Usage Example

```python
import Mia.GPIOCommand as GPIOCommand
import Mia.SensorTelemetry as SensorTelemetry
import flatbuffers

# Create a GPIO command
builder = flatbuffers.Builder(1024)
pin = builder.CreateString("GPIO17")
GPIOCommand.GPIOCommandStart(builder)
GPIOCommand.GPIOCommandAddPin(builder, 17)
GPIOCommand.GPIOCommandAddDirection(builder, GPIOCommand.GPIODirection.Output)
GPIOCommand.GPIOCommandAddValue(builder, True)
GPIOCommand.GPIOCommandAddTimestamp(builder, int(time.time() * 1000000))
cmd = GPIOCommand.GPIOCommandEnd(builder)
builder.Finish(cmd)
buf = builder.Output()

# Parse received message
received = GPIOCommand.GPIOCommand.GetRootAs(buf, 0)
print(f"GPIO Pin: {received.Pin()}")
print(f"Direction: {received.Direction()}")
print(f"Value: {received.Value()}")
```

### C++ Usage Example

```cpp
#include "Mia/GPIOCommand.h"
#include "Mia/SensorTelemetry.h"

flatbuffers::FlatBufferBuilder builder(1024);

// Create GPIO command
auto cmd = Mia::CreateGPIOCommand(builder, 17, Mia::GPIODirection_Output, true, timestamp);
builder.Finish(cmd);

// Parse received message
auto received = Mia::GetGPIOCommand(buffer);
std::cout << "Pin: " << received->pin() << std::endl;
```

## Schema Evolution

When modifying schemas:

1. **Additive Changes**: Adding new fields or tables is safe (backward compatible)
2. **Breaking Changes**: Removing fields or changing types requires careful migration
3. **Versioning**: Consider adding version fields to messages for compatibility checks

## Integration Points

The schemas integrate with:

- **API Layer** (`api/main.py`) - REST endpoints and WebSocket streaming
- **Hardware Workers** (`hardware/gpio_worker.py`, `services/obd_worker.py`) - Device communication
- **Message Broker** (`core/messaging/broker.py`) - Inter-process communication
- **Android App** - Mobile device control and telemetry display

## Performance Characteristics

- **Zero-copy deserialization** - Direct access to serialized data
- **Cross-platform compatibility** - Works across Python, C++, Android, Arduino
- **Compact binary format** - Efficient network transmission
- **Type safety** - Compile-time schema validation

## Testing

Generated bindings include comprehensive tests. Run the test suite:

```bash
# Python tests
pytest tests/test_flatbuffers_*.py

# C++ tests (if applicable)
cd build && make test
```