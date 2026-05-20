# CLAUDE.md

> **Audience**: AI agents (Claude Code, GitHub Copilot) working with this repository

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIA is a distributed vehicle telemetry and IoT control system targeting Raspberry Pi 4B, with ESP32/Arduino microcontrollers and an Android companion app. Primary prototype vehicle: Audi A4 B3 Cabriolet (2004). Core capabilities: OBD-II vehicle telemetry (standard PIDs + VAG/Audi read-only UDS), GPIO/sensor control, AI voice assistant, and a mobile interface with BLE/ANPR/DVR. Legacy Citroën C4 PSA bridge is maintained but secondary.

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

> For complete architecture, data flow diagrams, and component details, see [ARCHITECTURE.md](ARCHITECTURE.md).

Key runtime boundaries (quick reference for AI agents):
- **ZeroMQ broker**: port 5555 — ROUTER-DEALER control plane (`apps/rpi-backend/shared/messaging/broker.py`)
- **Telemetry PUB/SUB**: port 5556 — real-time MCU data fan-out
- **FastAPI**: port 8000 — REST/WebSocket gateway (`apps/rpi-backend/py-api/api/main.py`)
- **MCP modules**: `orchestration/mcp/modules/` — domain microservices (automotive, audio, hardware)
- **OBD Digital Twin**: `apps/rpi-backend/py-api/services/obd_worker.py` — ELM327 emulator for Audi A4 B3

## Key Configuration

- **Python**: 3.12.7, **Conan**: 2.3.2 (see `.tool-versions`)
- **pytest.ini**: asyncio_mode=auto, strict markers, test discovery in `tests/`
- **Flake8**: max-line-length=120, extends E203/W503 ignored
- **Black + isort**: isort uses `--profile black`
- **Pre-commit excludes**: `.backups/`, `exported-assets/`, `apps/android/`, `platforms/cpp/` from Python linters

## Deployment

Production target is `/opt/mia/` on Raspberry Pi. Systemd services defined in `infra/systemd/*.service` (zmq-broker, mia-api, mia-gpio-worker, mia-serial-bridge, mia-obd-worker, etc.). Deploy with `infra/deploy/rpi/deploy.sh`. The ZMQ broker must start before other services.

## Conventions

- Hardware-dependent code must have simulation fallbacks for CI and non-RPi development
- Test markers: `@pytest.mark.hardware` for tests requiring physical hardware, `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.automotive`
- MCP modules follow initialize/shutdown lifecycle pattern
- Error handling returns structured dicts with `status` and `message` keys
- Environment config via `.env` (see `.env.example`)
