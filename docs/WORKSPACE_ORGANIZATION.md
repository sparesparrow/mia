# Workspace Organization

> Last refreshed: 2026-05-12

This document describes the workspace organization and directory structure for the MIA project.

## Directory Structure

### Repository Layout

```
mia/
├── apps/
│   ├── android/              # Kotlin/Jetpack Compose Android app
│   ├── esp32/                # ESP32 firmware (PlatformIO)
│   └── rpi-backend/
│       ├── py-api/           # FastAPI + ZMQ workers + hardware drivers
│       ├── shared/           # Shared messaging, telemetry, broker
│       └── cpp-audio/        # C++ audio/hardware server
├── orchestration/
│   └── mcp/modules/          # MCP microservices (core-orchestrator, ai-audio, automotive, etc.)
├── schemas/                  # FlatBuffers source schemas (mia.fbs, vehicle_telemetry.fbs)
├── protos/                   # Wire-format wrappers (vehicle.fbs with file_identifier)
├── Mia/                      # Auto-generated Python FlatBuffers bindings (do not hand-edit)
├── contracts/                # MQTT topics, events, BLE GATT, config schemas
├── infra/
│   ├── conan/                # Conan profiles, recipes, conanfile.py
│   ├── docker/               # Docker Compose files (dev, prod, simulation)
│   ├── systemd/              # Systemd service units for RPi deployment
│   └── deploy/               # Deployment scripts (RPi, AWS, K8s)
├── platforms/cpp/             # Cross-platform C++ (CMake)
├── mcp-cpp-bridge/           # C++ MCP SDK bridge
├── web/                      # Static web pages, voice-chat UI
├── tests/                    # pytest suite (unit, integration, hardware)
├── scripts/                  # Build, deploy, test, and utility scripts
├── agents/                   # AI agent definitions
├── arduino/                  # Arduino sketches and protocol library
├── docs/                     # Project documentation
├── monitoring/               # Grafana, Prometheus configs
└── containers/               # Container build contexts
```

### Installation Environment (`/opt/mia/`)

The installation directory mirrors the repo layout on Raspberry Pi:

```
/opt/mia/
├── apps/rpi-backend/         # Python services and hardware drivers
├── orchestration/            # MCP modules
├── schemas/                  # FlatBuffers schemas
├── Mia/                      # Generated bindings
├── contracts/                # Runtime contracts
└── infra/                    # Deployment assets
```

### System Integration

Systemd services are installed from `infra/systemd/`:

```
/etc/systemd/system/
├── zmq-broker.service          # ZMQ ROUTER:5555 + PUB:5556 (starts first)
├── mia-api.service             # FastAPI :8000 (after broker)
├── mia-serial-bridge.service   # ESP32/Arduino serial→ZMQ
├── mia-obd-worker.service      # ELM327 emulator (after serial-bridge)
├── mia-gpio-worker.service     # GPIO control via libgpiod
├── mia-citroen-bridge.service  # PSA Citroën OBD telemetry
├── mia-vag-audi-bridge.service # VAG/Audi read-only OBD (UDS disabled by default)
└── ...                         # BLE, STT, TTS, wake-word, camera, power, LED

/etc/mia/
└── environment                 # Runtime env vars (MIA_PYTHON, ports, etc.)

/var/lib/mia/
├── broker_messages.db          # ZMQ message persistence (SQLite)
└── data/                       # Persistent runtime data
```

## Path Configuration

### Configurable Paths (`config/paths.json`)

```json
{
  "project_root": ".",
  "install_prefix": "/opt/mia",
  "rpi_deploy_path": "/home/mia/mia-install"
}
```

### Path Resolution (`core/paths.py`)

The `PathConfig` class provides utilities for resolving paths across different environments:

```python
from core.paths import PathConfig

config = PathConfig()
project_root = config.get_path('project_root')
install_path = config.resolve_path('/opt/mia')
```

## Development Workflow

### Local Development
1. Clone the repository
2. Install Python dependencies: `pip3 install -r requirements-dev.txt`
3. Run tests: `pytest tests/ -m "not hardware"`
4. For RPi simulation: `docker compose -f infra/docker/docker-compose.dev.yml up`

### Deployment to Raspberry Pi
1. Run `infra/deploy/rpi/deploy.sh` to sync code to `/opt/mia/`
2. Systemd services are enabled via `infra/systemd/*.service`
3. Startup order: `zmq-broker` → `mia-api` → workers → orchestration
4. Verify: `curl http://localhost:8000/status`

### Android Development
1. Open `apps/android/` in Android Studio
2. JDK 17, Android SDK 34, Gradle 8.4
3. Build: `cd apps/android && ./gradlew assembleDebug`

## Environment Variables

Services use environment variables from `/etc/mia/environment`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MIA_PYTHON` | `/usr/local/bin/mia-python` | Bundled Python interpreter |
| `ZMQ_BROKER_URL` | `tcp://localhost:5555` | ZMQ broker address |
| `PYTHONPATH` | `/opt/mia/apps/rpi-backend/py-api:/opt/mia` | Module search |

## Key Conventions

- **Schema changes** flow through `schemas/` → `python schemas/generate.py --all` → `Mia/`
- **Never hand-edit** files under `Mia/` — they are auto-generated
- **Systemd services** are the source of truth for startup ordering
- **Contracts** (`contracts/events.md`, `contracts/topics.md`) define MQTT/event shapes
- See [ARCHITECTURE.md](../ARCHITECTURE.md) and [CLAUDE.md](../CLAUDE.md) for full details