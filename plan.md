# MIA Implementation Plan: FlatBuffers + MCP Cognitive Architecture

Based on the architecture document and current codebase analysis, here are the concrete implementation steps organized by priority and dependency.

---

## Phase 1: Schema Hardening (Foundation — do first)

### 1.1 Add explicit field IDs to all FlatBuffers schemas
**Why:** Current schemas (`mia.fbs`, `vehicle.fbs`, `webgrab.fbs`) use implicit field ordering — two developers adding fields in different branches will cause silent wire-format corruption.

**Work:**
- Add `(id: N)` attributes to every field in every table across all 3 `.fbs` files (~50+ tables)
- Enums and structs don't need IDs (fixed layout), only `table` types
- Regenerate Python and C++ bindings via `schemas/generate.py`

**Files:** `schemas/mia.fbs`, `protos/vehicle.fbs`, `apps/rpi-backend/cpp-audio/core/webgrab.fbs`

### 1.2 Add `flatc --conform` CI check
**Why:** Only reliable guard against breaking schema changes when firmware updates lag behind app releases.

**Work:**
- Store a baseline schema snapshot in `schemas/baseline/`
- Add a CI job in `.github/workflows/ci.yml` that runs `flatc --conform schemas/baseline/mia.fbs -- schemas/mia.fbs` on every PR
- Update baseline on intentional breaking changes (manual, requires reviewer approval)

### 1.3 Add cognitive architecture schemas
**Why:** The seven-layer cognitive model needs dedicated schema types not yet in `mia.fbs`.

**New schemas (`schemas/cognitive.fbs`):**
- `CognitiveLayer` enum (Perceptual, Episodic, Semantic, Procedural, MetaCognitive, Transfer, Evaluative)
- `CognitiveMessage` envelope table (source_device, source_layer, target_layer, payload, confidence)
- `KGNode` and `KGEdge` tables for knowledge graph (with `key` attribute for sorted lookup)
- `CognitiveState` table
- `InferenceResult` table

**New schemas (`schemas/storage.fbs`):**
- Persistent storage types for episodic memory
- Working memory buffer types

### 1.4 Multi-language code generation
**Why:** Currently `generate.py` only produces Python and C++ — need Kotlin, TypeScript, and Rust.

**Work:**
- Extend `schemas/generate.py` to support `--kotlin`, `--ts`, `--rust` flags
- Add output directories: `generated/kotlin/`, `generated/ts/`, `generated/rust/`
- Add FlatBuffers version pinning (currently 24.3.25, document upgrade path to v25.x)

---

## Phase 2: Gateway Architecture (Core integration)

### 2.1 FlatBuffers-to-JSON-RPC translation gateway
**Why:** ESP32 devices speak FlatBuffers/MQTT; MCP servers speak JSON-RPC. The RPi must bridge them.

**Work:**
- New module: `orchestration/mcp/modules/flatbuffers-gateway/`
- Subscribes to MQTT topics (`{device_id}/{layer}/{data_type}`)
- Deserializes FlatBuffers messages → constructs JSON-RPC MCP calls
- Translates MCP responses back to FlatBuffers → publishes to MQTT
- Uses the `CognitiveMessage` envelope from Phase 1.3

**Key files to create:**
- `gateway.py` — main translation loop
- `fb_to_jsonrpc.py` — FlatBuffers → JSON-RPC converter
- `jsonrpc_to_fb.py` — JSON-RPC → FlatBuffers converter
- `topic_router.py` — MQTT topic ↔ MCP endpoint mapping

### 2.2 MQTT topic structure for cognitive layers
**Why:** Standardize how devices publish/subscribe by cognitive layer.

**Topic format:** `mia/{device_id}/{layer}/{data_type}`
- `mia/esp32-01/perceptual/bpm_data`
- `mia/rpi-main/episodic/interaction_log`
- `mia/android-01/evaluative/user_feedback`

**Work:**
- Define topic schema in a shared config (`orchestration/mcp/modules/shared/topics.py`)
- Update serial bridge to publish using new topic structure
- Update OBD worker to publish VehicleTelemetry on `mia/{device}/perceptual/vehicle`

### 2.3 Integrate with existing ZeroMQ broker
**Why:** MIA already has a ZMQ ROUTER-DEALER broker on port 5555. The gateway should bridge ZMQ ↔ MQTT ↔ MCP.

**Work:**
- Gateway connects as a DEALER to the existing ZMQ broker
- Translates between ZMQ internal messages and MQTT external messages
- Add MQTT client (paho-mqtt) to requirements.txt

---

## Phase 3: ESP32 BPM Detector Integration

### 3.1 ESP32 FlatBuffers struct types for ESP-NOW
**Why:** ESP-NOW has a 250-byte limit; FlatBuffers `struct` types have zero overhead.

**Work:**
- Add `AudioFeatures` struct to `schemas/mia.fbs` (bpm, beat_confidence, dominant_freq, rms_energy, timestamp_ms)
- Add `BeatEvent` struct for real-time beat broadcasting
- Document the `#undef STRUCT_END` workaround for ESP-IDF conflict

### 3.2 PlatformIO project skeleton for BPM detector
**Why:** The `apps/esp32/` directory needs a PlatformIO project configured for FlatBuffers.

**Work:**
- Create `apps/esp32/platformio.ini` with ESP32 board config, FlatBuffers lib dependency
- Create `apps/esp32/src/main.cpp` with FreeRTOS task skeleton (audio capture, DSP, comms)
- Create `apps/esp32/lib/flatbuffers/` with generated C++ headers
- Add ESP-NOW and MQTT communication tasks

---

## Phase 4: Cognitive Layer Implementation on RPi

### 4.1 Perceptual layer — sensor data ingestion
**Already partially implemented** in `hardware/serial_bridge.py` and sensor drivers.

**Work:**
- Wrap existing sensor data in `CognitiveMessage` envelopes with `source_layer: Perceptual`
- Publish to MQTT via the gateway

### 4.2 Episodic layer — interaction history
**Why:** Store timestamped interaction records for context-aware responses.

**Work:**
- New module: `orchestration/mcp/modules/episodic-memory/`
- SQLite-backed storage for interaction events
- MCP resource endpoint: `episodic://interactions/{time_range}`
- FlatBuffers serialization for storage (using storage.fbs types)

### 4.3 Procedural layer — action execution
**Already partially implemented** in `ai-platform-controllers` MCP module.

**Work:**
- Tag existing platform controller actions with `CognitiveLayer.Procedural`
- Add procedural memory (learned action sequences) to episodic store

### 4.4 MetaCognitive layer — system self-monitoring
**Why:** Health checks, anomaly detection, resource awareness.

**Work:**
- Extend existing `HealthReport`/`MetricReport` FlatBuffers types
- Add system load awareness to core-orchestrator decision-making
- Expose as MCP tools: `get_system_health`, `get_cognitive_state`

---

## Phase 5: Android Integration

### 5.1 Kotlin FlatBuffers bindings
**Work:**
- Add `flatc --kotlin` to `generate.py`
- Create Gradle module `apps/android/schemas/` with generated Kotlin code
- Add `com.google.flatbuffers:flatbuffers-java` dependency

### 5.2 Android MCP client
**Work:**
- WebSocket connection to RPi MCP gateway (Streamable HTTP)
- Expose clipboard, camera, microphone as MCP resources
- Consume cognitive state as MCP resource for dashboard display

---

## Phase 6: CI/CD Enhancements

### 6.1 Schema generation CI job
**Why:** All platform builds must consume generated code from a single `flatc` invocation.

**Work:**
- Add `schemas` job to `.github/workflows/ci.yml` that:
  1. Installs `flatc` (pinned version)
  2. Runs `flatc --conform` against baseline
  3. Generates Python, C++, Kotlin, TypeScript, Rust code
  4. Uploads generated artifacts
- Make `python-test`, `cpp-build`, `android-build`, `esp32-build` jobs depend on `schemas`

### 6.2 Schema version tracking
**Work:**
- Add `schema_version` field to root message types
- Add version compatibility matrix documentation
- Automated compatibility test: old schema can read new data (forward compat)

---

## Dependency Graph

```
Phase 1.1 (field IDs) ──→ Phase 1.2 (CI conform) ──→ Phase 6.1 (schema CI)
     │
     ├──→ Phase 1.3 (cognitive schemas) ──→ Phase 2.1 (gateway)
     │                                          │
     │                                          ├──→ Phase 4.x (RPi layers)
     │                                          └──→ Phase 3.x (ESP32)
     │
     └──→ Phase 1.4 (multi-lang codegen) ──→ Phase 5.1 (Kotlin bindings)
                                                  └──→ Phase 5.2 (Android MCP)
```

## Recommended Starting Order

1. **Phase 1.1** — Add explicit field IDs (prevents future corruption, no dependencies)
2. **Phase 1.3** — Add cognitive schemas (enables all downstream work)
3. **Phase 1.2** — Add `flatc --conform` CI (safety net before schema proliferates)
4. **Phase 2.1** — Build the gateway (central integration piece)
5. **Phase 2.2** — MQTT topic structure
6. **Phase 4.2** — Episodic memory (first new cognitive capability)
7. **Phase 3.1** — ESP32 struct types
8. **Phase 6.1** — Schema generation CI
9. Remaining phases as capacity allows
