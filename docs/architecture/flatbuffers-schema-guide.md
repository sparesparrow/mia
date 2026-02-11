# FlatBuffers Schema Design Guide for MIA

## Quick Reference

FlatBuffers is a serialization library that enables **zero-copy** data access across C++, Python, Kotlin, and other languages. Unlike JSON, which must be parsed character-by-character, FlatBuffers keeps data in a binary format that can be accessed immediately.

## Why FlatBuffers vs JSON/MessagePack/Protobuf?

| Aspect | JSON | FlatBuffers | Protobuf |
|:---|:---|:---|:---|
| **Parse latency** | ~100µs | ~1µs (zero-copy) | ~10µs |
| **Binary size** | Large (~200B) | Compact (~30B) | Compact (~40B) |
| **Cross-platform** | Yes | Yes (all languages) | Yes |
| **Schema evolution** | Weak | Excellent (forward/backward compat) | Excellent |
| **Learning curve** | Easy | Moderate | Moderate |

**Use FlatBuffers when:** Real-time embedded systems, ARM microcontrollers, or high-throughput data streams.

---

## The MIA Protocol Schema

### File: `mia_protocol.fbs`

```flatbuffers
// Namespace ensures no collisions
namespace Mia.Protocol;

// ============================================
// Core Telemetry (From OBD2/CAN)
// ============================================

table Telemetry {
  // Vehicle state (updated every 100ms)
  speed: float;                    // km/h
  rpm: int32;                      // engine RPM
  engine_temp: float;              // °C
  gear: uint8;                     // 0=P, 1=D, 2=R, 3=N
  throttle_position: float;        // 0-100%
  
  // Electrical
  battery_voltage: float;          // 12V system
  alternator_output: float;        // Amps
  
  // Lights & Indicators
  is_lights_on: bool;
  is_high_beam: bool;
  is_blink_left: bool;
  is_blink_right: bool;
  is_brake_on: bool;
  
  // Engine status
  is_engine_running: bool;
  is_check_engine_light: bool;
  
  // Timestamps
  timestamp_ms: uint64;            // Unix milliseconds
}

// ============================================
// GPIO Commands (To Arduino/ESP32)
// ============================================

table GpioCommand {
  gpio_pin: uint16;                // GPIO pin number (BCM for RPi)
  action: uint8;                   // 0=LOW, 1=HIGH, 2=TOGGLE, 3=PWM
  value: uint16;                   // For PWM: 0-255 (duty cycle)
  duration_ms: int32;              // -1 = permanent, 0 = momentary
  callback_id: string;             // Optional tracking ID
}

// ============================================
// Voice/Intent Commands
// ============================================

table VoiceIntent {
  recognized_text: string;         // "turn on lights"
  confidence: float;               // 0.0-1.0
  command_type: string;            // "control", "query", "navigate"
  entities: [Entity];              // Extracted parameters
}

table Entity {
  key: string;                     // "light_name", "destination"
  value: string;                   // "headlights", "home"
}

// ============================================
// System Events
// ============================================

table SystemEvent {
  event_type: string;              // "startup", "shutdown", "error"
  message: string;
  severity: uint8;                 // 0=info, 1=warn, 2=error
  timestamp_ms: uint64;
}

// ============================================
// Root Type (Required)
// ============================================

root_type Telemetry;
```

---

## Generate Code for All Platforms

### C++ (ESP32/Arduino)
```bash
flatc --cpp --gen-mutable mia_protocol.fbs
# Output: mia_protocol_generated.h
```

### Python (Raspberry Pi)
```bash
flatc --python mia_protocol.fbs
# Output: Mia/Protocol/*.py
```

### Kotlin (Android)
```bash
flatc --kotlin mia_protocol.fbs
# Output: Mia/Protocol/*.kt
```

---

## Usage Examples

### 1. C++ (ESP32 Publishing OBD2 Data)

```cpp
#include "mia_protocol_generated.h"
#include <zmq.hpp>

void publish_telemetry(int rpm, float speed) {
    flatbuffers::FlatBufferBuilder builder(1024);
    
    // Build message
    auto telemetry = Mia::Protocol::CreateTelemetry(
        builder,
        speed,           // speed
        rpm,             // rpm
        85.5,            // engine_temp
        1,               // gear (Drive)
        0,               // throttle_position
        12.5,            // battery_voltage
        ...
    );
    
    builder.Finish(telemetry);
    
    // Send via ZMQ
    zmq::context_t ctx;
    zmq::socket_t socket(ctx, zmq::socket_type::pub);
    socket.bind("tcp://0.0.0.0:5555");
    
    zmq::message_t msg(builder.GetSize());
    memcpy(msg.data(), builder.GetBufferPointer(), builder.GetSize());
    
    socket.send(zmq::buffer("TELEMETRY"), zmq::send_flags::sndmore);
    socket.send(msg, zmq::send_flags::none);
}
```

### 2. Python (Raspberry Pi - Receiving & Processing)

```python
import zmq
import Mia.Protocol.Telemetry as Telemetry

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://esp32.local:5555")
sub.subscribe(b"TELEMETRY")

while True:
    msg_type, data = sub.recv_multipart()
    
    # Zero-copy access (no parsing!)
    tel = Telemetry.Telemetry.GetRootAsTelemetry(data, 0)
    
    speed = tel.Speed()
    rpm = tel.Rpm()
    temp = tel.EngineTemp()
    
    print(f"Speed: {speed} km/h, RPM: {rpm}, Temp: {temp}°C")
    
    # Publish processed data to Android via HTTP
    publish_to_http({
        "speed": speed,
        "rpm": rpm,
        "temperature": temp
    })
```

### 3. Kotlin (Android - Display Telemetry)

```kotlin
import Mia.Protocol.Telemetry
import java.nio.ByteBuffer

class MiaCarStateViewModel {
    private val client = MiaHttpClient("http://raspberrypi.local:8000")
    
    fun observeTelemetry() {
        viewModelScope.launch {
            while (isActive) {
                val response = client.getTelemetry()
                val telemetry = Telemetry.getRootAsTelemetry(
                    ByteBuffer.wrap(response.body)
                )
                
                updateUI(
                    speed = telemetry.speed(),
                    rpm = telemetry.rpm(),
                    engineTemp = telemetry.engineTemp()
                )
                
                delay(500)
            }
        }
    }
    
    private fun updateUI(speed: Float, rpm: Int, engineTemp: Float) {
        speedLiveData.value = "${speed.toInt()} km/h"
        rpmLiveData.value = "$rpm RPM"
        tempLiveData.value = "${engineTemp.toInt()}°C"
    }
}
```

---

## Schema Evolution (Forward Compatibility)

**Problem:** You add `fuel_level` to Telemetry. Old Android app doesn't know about it.

**Solution:** FlatBuffers handles this automatically:

```flatbuffers
// v2: Added new field
table Telemetry {
  speed: float;
  rpm: int32;
  engine_temp: float;
  fuel_level: float;  // NEW (old clients ignore it)
}
```

**Old Python code:**
```python
tel = Telemetry.GetRootAsTelemetry(data, 0)
print(tel.Speed())  # Works fine
print(tel.FuelLevel())  # Returns 0.0 if not present
```

No crashes, no version mismatch errors. It "just works."

---

## Best Practices

1. **Always use a namespace** → Prevents collisions
2. **Use descriptive names** → `is_lights_on` not `lights`
3. **Add comments** → Include units (°C, km/h, Amps)
4. **Use proper types** → `uint8` for values 0-255, not `int32`
5. **Include timestamps** → Essential for debugging
6. **Keep schemas versioned** → git-track your `.fbs` files
7. **Test cross-platform** → Serialize on C++, deserialize on Python/Kotlin

---

## Directory Structure

```
mia/
├── schema/
│   ├── mia_protocol.fbs           # Main schema
│   └── generated/
│       ├── cpp/
│       │   └── mia_protocol_generated.h
│       ├── python/
│       │   └── Mia/Protocol/
│       │       ├── __init__.py
│       │       └── Telemetry.py
│       └── kotlin/
│           └── Mia/Protocol/Telemetry.kt
├── esp32/
│   └── obd2_reader.cpp            # Uses generated C++
├── modules/
│   └── telemetry.py               # Uses generated Python
└── android/
    └── app/src/main/kotlin/
        └── MiaCarState.kt         # Uses generated Kotlin
```

---

## Debugging Tips

### Inspect Binary Message

```python
import binascii

data = zmq_socket.recv()
print(f"Hex dump: {binascii.hexlify(data)}")
print(f"Size: {len(data)} bytes")

# Verify header (first 4 bytes point to table root)
root_offset = int.from_bytes(data[0:4], byteorder='little')
print(f"Root offset: {root_offset}")
```

### Verify Schema Version

```python
# Before sending: log schema hash
import hashlib
with open("mia_protocol.fbs", "rb") as f:
    schema_hash = hashlib.sha256(f.read()).hexdigest()
print(f"Schema: {schema_hash[:8]}")

# Include in telemetry for verification
table Telemetry {
    schema_hash: string;  // "abc12345"
    ...
}
```

---

## Further Reading

- [FlatBuffers Official Docs](https://google.github.io/flatbuffers/)
- [FlatBuffers GitHub](https://github.com/google/flatbuffers)
- Cross-language serialization best practices

See also: [lean-architecture.md](./lean-architecture.md) for system integration patterns.
