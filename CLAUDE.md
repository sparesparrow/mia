# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIA is a distributed vehicle telemetry and IoT control system targeting Raspberry Pi 4B, with ESP32/Arduino microcontrollers and an Android companion app. Core capabilities: OBD-II vehicle telemetry (Citroën C4 PSA-specific PIDs), GPIO/sensor control, AI voice assistant, and a mobile interface with BLE/ANPR/DVR.

## Build & Test Commands

### Python

```bash
# Install dependencies
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt

# Run all tests
pytest tests/

# Run a single test file
pytest tests/unit/test_something.py

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m "not hardware"          # skip hardware-dependent tests
pytest -m "not hardware and not slow"

# Coverage
pytest tests/ --cov=modules --cov=rpi --cov-report=term-missing

# Lint & format
black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503

# Pre-commit (runs black, isort, flake8, bandit, yaml checks)
pre-commit run --all-files
```

### C++ (Conan + CMake)

```bash
conan create . --build=missing
cd platforms/cpp && cmake -B build && cmake --build build
```

### Android

```bash
cd android && ./gradlew assembleDebug
```

### Docker

```bash
docker compose -f infra/docker/docker-compose.yml up          # full stack (orchestrator, MQTT, Postgres, Redis, Grafana)
docker compose -f infra/docker/docker-compose.dev.yml up      # dev mode with volume mounts
```

## Architecture

### Messaging Layer (ZeroMQ)

The central nervous system is a ZeroMQ ROUTER-DEALER broker (`apps/rpi-backend/shared/messaging/broker.py`) on port 5555. Workers (GPIO, serial bridge, OBD) connect as DEALER sockets. The FastAPI server also connects as a DEALER to relay HTTP/WebSocket requests.

A separate PUB/SUB channel on port 5556 distributes real-time MCU telemetry from the serial bridge to subscribers (OBD worker, etc.).

### REST/WebSocket Gateway

`apps/rpi-backend/py-api/api/main.py` runs FastAPI on port 8000 with REST endpoints for GPIO control, device listing, telemetry, and a WebSocket endpoint (`/ws`) for real-time streaming. API key auth in `apps/rpi-backend/py-api/api/auth/`.

### MCP Modules (`orchestration/mcp/modules/`)

Each subdirectory is an MCP (Model Context Protocol) microservice:
- **core-orchestrator** - Routes user commands to appropriate MCP modules
- **service-discovery** - Service registry with health checks
- **ai-audio-assistant** - Whisper STT, ElevenLabs TTS, Spotify integration
- **ai-platform-controllers** - System command execution
- **automotive-mcp-bridge** / **citroen-c4-bridge** - Vehicle OBD-II interface
- **hardware-bridge** - Hardware abstraction

The shared MCP framework lives in `orchestration/mcp/modules/shared/mcp_framework.py`. Note: copies still exist in individual module directories (known duplication being consolidated).

### Hardware Layer

- `apps/rpi-backend/py-api/hardware/gpio_worker.py` - GPIO control with simulation fallback when RPi.GPIO unavailable
- `apps/rpi-backend/py-api/hardware/serial_bridge.py` - USB serial to ZeroMQ bridge for ESP32/Arduino
- `apps/rpi-backend/py-api/hardware/` - I2C/SPI sensor drivers (BME280, DHT, etc.)
- `apps/rpi-backend/cpp-audio/` - C++ audio and hardware implementations for RPi

### OBD-II Digital Twin

`apps/rpi-backend/py-api/services/obd_worker.py` implements a Digital Twin: physical potentiometers on an MCU drive an ELM327 emulator that responds to real OBD-II diagnostic tools with mapped engine parameters. Telemetry flows: MCU -> serial bridge -> ZMQ PUB -> OBD worker -> virtual PTY -> diagnostic tool.

### Android App (`apps/android/`)

Kotlin + Jetpack Compose with Hilt DI, Room DB, Retrofit/OkHttp, WebSocket. Features: BLE scanning, ANPR, dashboard recording, real-time telemetry charts.

### Serialization

FlatBuffers schemas in `schemas/` (main: `mia.fbs`) and `protos/` define message types (VehicleTelemetry, GPIOCommand, SensorTelemetry, etc.). Generated Python bindings in `Mia/`.

## Key Configuration

- **Python**: 3.12.7, **Conan**: 2.3.2 (see `.tool-versions`)
- **pytest.ini**: asyncio_mode=auto, strict markers, test discovery in `tests/`
- **Flake8**: max-line-length=120, extends E203/W503 ignored
- **Black + isort**: isort uses `--profile black`
- **Pre-commit excludes**: `.backups/`, `exported-assets/`, `apps/android/`, `platforms/cpp/` from Python linters

## Deployment

Production target is `/opt/mia/` on Raspberry Pi. Systemd services defined in `infra/systemd/*.service` (zmq-broker, mia-api, mia-gpio-worker, mia-serial-bridge, mia-obd-worker, mia-citroen-bridge, etc.). Deploy with `infra/deploy/rpi/deploy.sh`. The ZMQ broker must start before other services.

## Conventions

- Hardware-dependent code must have simulation fallbacks for CI and non-RPi development
- Test markers: `@pytest.mark.hardware` for tests requiring physical hardware, `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.automotive`
- MCP modules follow initialize/shutdown lifecycle pattern
- Error handling returns structured dicts with `status` and `message` keys
- Environment config via `.env` (see `.env.example`)
