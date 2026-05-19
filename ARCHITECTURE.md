# MIA Architecture & Repository Structure

> **Audience**: Developers, architects, AI agents

## Repository Organization

MIA is a distributed vehicle telemetry and IoT control system with four key organizational layers:

### 1. Applications (`apps/`)

Runtime applications targeting specific platforms:

- **`apps/android/`** - Android companion app (Kotlin + Jetpack Compose, Hilt DI, Room, WebSocket)
- **`apps/rpi-backend/py-api/`** - Python FastAPI server on Raspberry Pi 4B (ZeroMQ broker, REST/WebSocket, MCP bridge)
- **`apps/rpi-backend/cpp-audio/`** - C++ audio processing for beat detection, FFT optimization, DSP
- **`apps/esp32/`** - ESP32 firmware (PlatformIO, sensor drivers, BLE, OBD-II emulation)

### 2. Orchestration (`orchestration/`)

Multi-agent orchestration and MCP microservices:

- **`orchestration/mia-agents/`** - AI agents configuration, agent definitions, skill orchestration
- **`orchestration/mcp/`** - MCP server definitions, microservice configurations, framework code
- **`orchestration/mcp/prompts/`** - MIA-specific prompts for voice commands, workflows, domain knowledge

Includes:
- Core orchestrator (routes user commands to specialized agents)
- Service discovery (health checks, registry)
- AI audio assistant (Whisper STT, ElevenLabs TTS, Spotify)
- Automotive bridge (OBD-II, Audi A4 B3 Cabriolet primary prototype; Citroën C4 PSA legacy)
- Hardware bridge (GPIO abstraction)
- Security scanners and platform controllers

### 3. Infrastructure (`infra/`)

Deployment, containerization, and runtime configuration:

- **`infra/docker/`** - Docker Compose (dev/prod), Dockerfiles for each service
- **`infra/systemd/`** - Systemd service files for RPi deployment
- **`infra/conan/`** - Conan profiles, cross-compilation, package recipes
- **`infra/deploy/`** - Deployment scripts (RPi, ESP32, AWS/K8s), SSH/SCP/Ansible configs

### 4. Tests & Tools (`tests/`, `tools/`)

Cross-cutting concerns:

- **`tests/unit/`** - Unit tests per platform (Android, RPi, ESP32)
- **`tests/integration/`** - Integration test scenarios and fixtures (voice→LED, OBD telemetry, etc.)
- **`tools/ci/`** - CI helper scripts, linting, validation
- **`tools/local-dev/`** - Developer scripts (build all, sync assets, flash firmware, start stack)

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Android App (apps/android/)                                 │
│ • User speaks voice command                                  │
│ • Sends intent via REST/WebSocket                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket (8000)
┌──────────────────────▼──────────────────────────────────────┐
│ RPi Python API (apps/rpi-backend/py-api/)                   │
│ • FastAPI server + ZeroMQ ROUTER broker (5555)             │
│ • Routes commands to MCP modules                            │
│ • Real-time telemetry via PUB/SUB (5556)                   │
└──────┬──────────┬──────────────┬──────────┬─────────────────┘
       │          │              │          │
   ┌───▼─┐ ┌─────▼─┐ ┌──────────▼──┐ ┌────▼────┐
   │GPIO │ │Serial │ │OBD Worker   │ │Orchestr │
   │     │ │Bridge │ │(Audi A4 B3) │ │ (MCP)   │
   └─────┘ └───┬───┘ └─────────────┘ └────┬────┘
               │                          │
        ┌──────▼─────┐              ┌─────▼──────────┐
        │ ESP32/MCU  │              │ AI Agents      │
        │ Sensors    │              │ (orchestr/     │
        │ BLE        │              │  mia-agents/)  │
        └────────────┘              └────────────────┘
```

## Key Patterns

### Messaging Layer
- **Broker**: ZeroMQ ROUTER-DEALER on port 5555 (`apps/rpi-backend/shared/messaging/broker.py`)
  - Workers (GPIO, serial bridge, OBD) register as DEALER sockets
  - FastAPI connects as DEALER to relay HTTP/WebSocket requests
- **Pub/Sub**: ZeroMQ PUB/SUB on port 5556 (real-time MCU telemetry from serial bridge to subscribers)
- **MCP Modules**: Microservices under `orchestration/mcp/` handle domain logic
  - Shared framework: `orchestration/mcp/modules/shared/mcp_framework.py`

### REST/WebSocket Gateway
- `apps/rpi-backend/py-api/api/main.py` runs FastAPI on port 8000
- REST endpoints: `/devices`, `/command`, `/telemetry`, `/status`, `/gpio/*`
- WebSocket: `/ws` for real-time streaming
- API key auth in `apps/rpi-backend/py-api/api/auth/`

### MCP Modules (`orchestration/mcp/modules/`)
- **core-orchestrator** — routes user commands to appropriate modules
- **service-discovery** — service registry with health checks
- **ai-audio-assistant** — Whisper STT, ElevenLabs TTS, Spotify
- **ai-platform-controllers** — system command execution
- **automotive-mcp-bridge** / **vag-audi-bridge** — vehicle OBD-II (Audi A4 B3 primary)
- **citroen-c4-bridge** — PSA-specific PID decoding (legacy)
- **hardware-bridge** — GPIO abstraction

### Hardware Layer
- `apps/rpi-backend/py-api/hardware/gpio_worker.py` — GPIO control with simulation fallback
- `apps/rpi-backend/py-api/hardware/serial_bridge.py` — USB serial to ZeroMQ bridge for ESP32/Arduino
- `apps/rpi-backend/py-api/hardware/` — I2C/SPI sensor drivers (BME280, DHT, etc.)
- `apps/rpi-backend/cpp-audio/` — C++ audio and hardware implementations

### OBD-II Digital Twin
`apps/rpi-backend/py-api/services/obd_worker.py` implements a Digital Twin: physical potentiometers on an MCU drive an ELM327 emulator that responds to real diagnostic tools (Torque, OBD Eleven, VCDS) with mapped engine parameters. Primary target: Audi A4 B3 Cabriolet (2004).

Telemetry flow: MCU → serial bridge → ZMQ PUB → OBD worker → virtual PTY → diagnostic tool

### Serialization
FlatBuffers schemas in `schemas/` (main: `mia.fbs`) and `protos/` define message types (VehicleTelemetry, GPIOCommand, SensorTelemetry). Generated Python bindings in `Mia/`.

### Testing Strategy
- **Unit tests**: Per-platform, isolated to `tests/unit/android|rpi|esp32/` (corresponding to `apps/` platforms)
- **Integration tests**: Named by business flow (e.g., `voice_command_led_brightness/`), located in `tests/integration/scenarios/`
- **Markers**: `@pytest.mark.hardware`, `.integration`, `.slow` for selective execution

### CI/CD
- **Workflows**: Separate files per platform in `.github/workflows/`
- **Path-based triggers**: Each workflow only runs on changes to its platform
- **Artifact storage**: Test reports, coverage, build logs in `.artifacts/` (gitignored)

## Development Workflow

### Local Setup
```bash
# From repo root:
./tools/local-dev/start-dev-stack.sh      # Docker + RPi backend
./tools/ci/lint-all.sh                     # Pre-commit checks
pytest tests/ -m "not hardware"            # Run non-hardware tests
```

### Building a New Feature
1. Create feature branch: `git checkout -b feature/xyz`
2. Make changes in relevant `apps/`, `orchestration/`, or `infra/` subdirectory
3. Write tests in corresponding `tests/` location
4. Run local validation: `./tools/ci/lint-all.sh && pytest tests/`
5. Push and create PR targeting `main`
6. CI runs platform-specific jobs based on changed paths

### Deployment
- **Development**: `docker compose -f infra/docker/docker-compose.dev.yml up`
- **Production RPi**: `./infra/deploy/rpi/deploy.sh` (copies to `/opt/mia/`, starts systemd services)
- **ESP32**: `./infra/deploy/esp32/flash.sh` (uses platformio to upload firmware)

## Migration Notes

This structure was established to support:
- Clear separation of concerns (runtime vs. orchestration vs. infrastructure)
- Scalability (easy to add new platforms, devices, or regions)
- CI/CD path-based triggering (changes in `apps/android/` don't trigger full C++ rebuild)
- Multi-team development (frontend, backend, embedded, infrastructure teams each own clear domains)

Legacy files still being consolidated:
- Old `core/`, `services/`, `rpi/` directories being merged into `apps/rpi-backend/`
- Old `platforms/cpp/` moving to `apps/rpi-backend/cpp-audio/`
- Old `docker/`, `deploy/` being consolidated under `infra/`
- `modules/` becoming `orchestration/mcp/` (preserving hyphenated module names)
