# The MIA Nervous System: Lean Architecture with ZeroMQ & FlatBuffers

## Overview

This document describes an alternative, **lightweight architecture** optimized for a **single Raspberry Pi deployment** with optional Android/iOS companion app and optional hardware modules (ESP32, Arduino). This approach prioritizes simplicity, low CPU overhead, and native Android integration while maintaining type safety and performance.

### Why Not ROS2?

For a **single-vehicle** deployment (not a robot fleet), ROS2 introduces unnecessary complexity:
- **DDS discovery overhead** (5-10% CPU just for middleware)
- **Learning curve** (`.msg` files, `colcon` build system)
- **Weak Android integration** (requires rosbridge_suite workarounds)
- **Dependency on Debian/Ubuntu** (Raspberry Pi OS support is "Tier 3")

**ROS2 is worth it when:** You need Lidar SLAM, trajectory planning, or fleet management. For an infotainment + voice + GPIO system, it's overkill.

---

## Architecture: "The MIA Nervous System"

### Core Design Pattern

**ZeroMQ (pub/sub) + FlatBuffers (serialization) + FastAPI (REST API for Android)**

```
┌─────────────────────────────────────────────────────────────┐
│                      Raspberry Pi 4B                          │
│                   (Ubuntu Server 24.04)                      │
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐           │
│  │   FastAPI HTTP   │◄───────►│  Android App     │           │
│  │   REST Server    │◄───────►│   (WebSocket)    │           │
│  │   (Port 8000)    │         │   (Optional)     │           │
│  └────────┬─────────┘         └──────────────────┘           │
│           │                                                   │
│  ┌────────▼─────────────────────────────────────────┐       │
│  │        ZeroMQ PUB/SUB (Internal IPC)             │       │
│  │   (Inproc + TCP for local network)               │       │
│  └────────┬─────────────────────────────────────────┘       │
│           │                                                   │
│  ┌────────┴────────────────────────────────────────┐        │
│  │                  Python Workers                 │        │
│  │  ┌──────────────┐  ┌──────────────┐             │        │
│  │  │ voice_worker │  │ gpio_worker  │ ...         │        │
│  │  │ (Whisper)    │  │ (RPi GPIO)   │             │        │
│  │  └──────────────┘  └──────────────┘             │        │
│  └────────┬─────────────────────────────────────────┘       │
│           │                                                   │
│     ┌─────┴─────────────────────────┐                       │
│     │   Hardware Bridges             │                       │
│     │  ┌──────────────────────────┐ │                       │
│     │  │ Serial Gateway (ESP32)   │ │                       │
│     │  │ GPIO Controller (Arduino)│ │                       │
│     │  └──────────────────────────┘ │                       │
│     └─────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
        │                    │
        │                    │
    ┌───▼───┐            ┌───▼────┐
    │ ESP32 │            │Arduino │
    │ OBD2  │            │ LED    │
    │ Cam   │            │ Sensors│
    └───────┘            └────────┘
```

---

## Key Components

### 1. **FastAPI HTTP Server** (RPi, Port 8000)

**Purpose:** Exposes car state and commands via REST + WebSocket.

**Endpoints:**
```python
GET  /api/telemetry          # Returns Flatbuffers-serialized car state
POST /api/command            # Execute command (lock, lights, etc.)
WS   /api/ws                 # WebSocket for real-time updates
```

**Responsibilities:**
- Listen for HTTP requests from Android app
- Serialize responses using FlatBuffers
- Forward commands to ZeroMQ workers
- Cache recent telemetry for quick response

**Key advantage:** Android has native HTTP/WebSocket support. Zero custom ROS libraries needed.

---

### 2. **ZeroMQ Backbone** (Internal IPC)

**Why ZeroMQ instead of MQTT?**
- No broker = No single point of failure
- Faster latency (microsecond range for local)
- Peer-to-peer, but with topics (similar to MQTT)
- Works perfectly on single machine

**Topology:**
```
voice_worker   ──┐
                 ├──► ZMQ PUB (All publish here)
gpio_worker    ──┤
esp32_gateway  ──┘

                   ↓

voice_worker   ◄──┐
                  ├──► ZMQ SUB (All subscribe)
gpio_worker    ◄──┤
ui_server      ◄──┘
```

**Message Types** (Flatbuffers-serialized):
- `TELEMETRY` → Engine speed, temperature, etc.
- `GPIO_COMMAND` → Set LED, unlock door
- `VOICE_INTENT` → Recognized text from speech
- `AUDIO_FRAME` → Raw PCM for streaming
- `SYSTEM_EVENT` → Startup, shutdown, error

---

### 3. **FlatBuffers Serialization**

Instead of JSON (slow to parse), use **FlatBuffers** (zero-copy, typed).

**Example Schema** (`mia_protocol.fbs`):
```flatbuffers
namespace Mia.Protocol;

table Telemetry {
  speed: float;           // km/h
  rpm: int;               // engine RPM
  engine_temp: float;     // Celsius
  gear: int;              // 0=Park, 1=Drive, 2=Reverse, 3=Neutral
  is_lights_on: bool;
  is_engine_running: bool;
  battery_voltage: float; // 12V system
}

table GpioCommand {
  gpio_pin: int;
  state: bool;            // 0 = LOW, 1 = HIGH
  duration_ms: int;       // -1 = permanent
}

root_type Telemetry;
```

**Codegen** (One-time setup):
```bash
# C++ (ESP32)
flatc --cpp mia_protocol.fbs

# Python (RPi)
flatc --python mia_protocol.fbs

# Kotlin (Android)
flatc --kotlin mia_protocol.fbs
```

**Usage in Python:**
```python
import Mia.Protocol.Telemetry

# Create
builder = flatbuffers.Builder(1024)
Mia.Protocol.TelemetryStart(builder)
Mia.Protocol.TelemetryAddSpeed(builder, 65.0)
Mia.Protocol.TelemetryAddRpm(builder, 2500)
telemetry = Mia.Protocol.TelemetryEnd(builder)
builder.Finish(telemetry)

# Send via ZMQ (binary buffer)
zmq_socket.send(b"TELEMETRY", zmq.SNDMORE)
zmq_socket.send(builder.Output())

# Receive & Parse
msg_type = zmq_socket.recv()
data = zmq_socket.recv()
tel = Mia.Protocol.Telemetry.GetRootAsTelemetry(data, 0)
print(tel.Speed(), tel.Rpm())  # Zero-copy access!
```

---

## Worker Architecture

### `voice_worker.py` - Speech Processing

```python
import zmq
import whisper
import Mia.Protocol

ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
pub.bind("ipc:///tmp/mia-zmq")

model = whisper.load_model("base")

while True:
    audio_chunk = mic.read(1024)
    result = model.transcribe(audio_chunk)
    
    # Build Flatbuffers message
    intent_text = result["text"]
    
    # Publish
    pub.send(b"VOICE_INTENT", zmq.SNDMORE)
    pub.send(intent_text.encode())  # or Flatbuffers binary
```

### `gpio_worker.py` - Hardware Control

```python
import RPi.GPIO as GPIO
import zmq

ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("ipc:///tmp/mia-zmq")
sub.subscribe(b"GPIO_COMMAND")

GPIO.setmode(GPIO.BCM)

while True:
    msg_type, data = sub.recv_multipart()
    
    # Parse Flatbuffers
    cmd = Mia.Protocol.GpioCommand.GetRootAsGpioCommand(data, 0)
    pin = cmd.GpioPin()
    state = cmd.State()
    
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, state)
```

### `esp32_gateway.py` - Serial Bridge

```python
import serial
import zmq
import json

ser = serial.Serial("/dev/ttyUSB0", 115200)
zmq_pub = ctx.socket(zmq.PUB)

while True:
    line = ser.readline()
    msg = json.loads(line)  # ESP32 sends JSON (simple protocol)
    
    # Convert to Flatbuffers & re-publish
    zmq_pub.send(b"TELEMETRY", zmq.SNDMORE)
    zmq_pub.send(serialize_telemetry(msg))
```

---

## Android Integration

### Android App Architecture

```kotlin
// Minimal Android client
class MiaClient(val baseUrl: String) {
    suspend fun getTelemetry(): Telemetry {
        val response = httpClient.get("$baseUrl/api/telemetry")
        val bytes = response.body<ByteArray>()
        return Telemetry.getRootAsTelemetry(ByteBuffer.wrap(bytes))
    }
    
    suspend fun setLight(pin: Int, state: Boolean) {
        httpClient.post("$baseUrl/api/command") {
            contentType(ContentType.Application.Json)
            setBody("""{"action": "gpio", "pin": $pin, "state": $state}""")
        }
    }
}

// UI Layer
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        viewLifecycleOwner.lifecycleScope.launch {
            val client = MiaClient("http://raspberrypi.local:8000")
            while (isActive) {
                val tel = client.getTelemetry()
                speedView.text = "${tel.speed()} km/h"
                rpmView.text = "${tel.rpm()} RPM"
                delay(500)
            }
        }
    }
}
```

**Key point:** No ROS libraries, no custom message definitions. Just HTTP and FlatBuffers codegen.

---

## Comparison: Architectures

| Aspect | MIA (ROS2 Option) | **Lean (Recommended)** | Current MIA |
| :--- | :--- | :--- | :--- |
| **Control Plane** | Centralized RPi | Distributed ZMQ | Custom MQTT |
| **Communication** | DDS (broker) | ZeroMQ (peer-to-peer) | MQTT broker |
| **Serialization** | CDR (opaque) | **FlatBuffers (transparent)** | JSON |
| **Android Support** | rosbridge_suite (web) | Native HTTP + FlatBuffers | Custom protocol |
| **CPU overhead** | 5-10% (middleware) | <1% (ZMQ) | Variable |
| **Latency** | ~50ms | ~5ms (local) | ~10ms |
| **OS Support** | Ubuntu only | Raspberry Pi OS, Ubuntu | Any Linux |
| **Type Safety** | Yes (.msg) | **Yes (FB schema)** | Weak (JSON) |

---

## Performance Targets

- **Voice response:** <200ms (Whisper + TTS)
- **GPIO command:** <50ms (ZMQ + GPIO)
- **Telemetry update:** <20ms
- **Android UI refresh:** 500ms (network latency)
- **Memory footprint:** ~200MB (Python + Whisper model)

---

## Migration Path

### Phase 1: Add FastAPI Layer
```bash
pip install fastapi uvicorn
# Create rest_server.py
python rest_server.py
```

### Phase 2: Introduce ZeroMQ
```bash
pip install zmq
# Refactor workers to publish/subscribe
python voice_worker.py &
python gpio_worker.py &
python rest_server.py
```

### Phase 3: Migrate to FlatBuffers
```bash
pip install flatbuffers
# Generate Python code
flatc --python mia_protocol.fbs
# Update message passing
```

### Phase 4: Add Android App
- Use existing Android tooling (Kotlin/Java)
- Call REST endpoints
- No custom middleware

---

## Advantages

✅ **Simple:** No new languages or paradigms to learn  
✅ **Performant:** ZMQ is blazing fast  
✅ **Private:** No cloud, no telemetry  
✅ **Type-safe:** FlatBuffers enforces schema contracts  
✅ **Portable:** Works on Raspberry Pi OS (not just Ubuntu)  
✅ **Android-native:** Standard HTTP + WebSocket  
✅ **Modular:** Add/remove workers without recompilation  

---

## Disadvantages

❌ **No SLAM/Lidar support** (out of scope for this phase)  
❌ **Manual node discovery** (vs. ROS2 auto-discovery)  
❌ **Less ecosystem** (vs. ROS2's prebuilt libraries)  

---

## Next Steps

1. Start with **FastAPI server** exposing GPIO and CAN data
2. Add **ZeroMQ workers** for voice and telemetry
3. Define **FlatBuffers schema** for all messages
4. Build **Android UI** with Kotlin + gRPC or HTTP
5. Optional: Add **micro-ROS on ESP32** if OBD2 module is needed

See also: [flatbuffers-schema-guide.md](./flatbuffers-schema-guide.md) for detailed schema design patterns.
