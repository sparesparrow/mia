# CLAUDE.md

> **Audience**: AI agents (Claude Code, GitHub Copilot) working with this repository

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIA is a distributed vehicle telemetry and IoT control system targeting Raspberry Pi 4B, with ESP32/Arduino microcontrollers and an Android companion app. Primary prototype vehicle: Audi A4 Cabriolet 8H (2004). Core capabilities: OBD-II vehicle telemetry (standard PIDs + VAG/Audi read-only UDS), GPIO/sensor control, AI voice assistant, and a mobile interface with BLE/ANPR/DVR. Legacy Citroën C4 PSA bridge is maintained but secondary.

## Repository Layout

The repository has three parts ([spec/README.md](spec/README.md), ADR-0002):

1. **Requirements and design** in `spec/`:
   - `requirements/*.yaml`: the registry of `REQ-<AREA>-NNN` entries with their evidence state
   - `decisions/`: the ADRs
   - `architecture/`
   - `interfaces/`: MQTT, events, BLE GATT and ZeroMQ formats
   - `evidence/`: bench, hardware and vehicle validation records
2. **Production code** in `apps/`, `orchestration/`, `schemas/`, `infra/`, `web/` and `agents/`.
   `tools/` holds developer tooling.
3. **Tests** in `tests/`:
   - `unit/<area>/`, `integration/` and `e2e/`
   - `fixtures/`
   - `env/`: the simulated test environment

Android and C++ tests sit beside their builds.

Open work (to-dos, ideas, validation and test gaps) lives in GitHub Issues with `backlog:*` and `area:*` labels, never in TODO files (ADR-0001).

## Build & Test Commands

### Python

```bash
# Install dependencies
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt

# Run all tests
pytest tests/

# Run one area or one file
pytest tests/unit/rpi_backend
pytest tests/unit/rpi_backend/test_cycle1_api.py

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m "not hardware"          # skip hardware-dependent tests
pytest -m "not hardware and not slow"

# Coverage (what is measured and the fail_under gate are set in .coveragerc)
pytest tests/ -m "not hardware" --cov

# Requirement traceability (what CI runs)
pytest tests/ -m "not hardware" --req-report=req-report.json
python tools/ci/traceability.py check --pytest-report req-report.json

# Lint & format
black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503

# Pre-commit (runs black, isort, flake8, bandit, yaml checks, schema drift)
pre-commit run --all-files
```

What blocks a merge in CI (`.github/workflows/ci.yml`): the pytest run, the `.coveragerc` gate, the traceability check, and the strict voice schema drift check. The flake8/black/isort steps run with `continue-on-error`. There is no `pyproject.toml`, so the pre-commit black hook uses black's default line length (88), while CI's black check uses `--line-length 120`. Don't reformat files you aren't changing.

### C++ (Conan + CMake)

```bash
cmake -S apps/rpi-backend/cpp-audio -B build/cpp -DWITH_HARDWARE=OFF && cmake --build build/cpp
```

The ARM64 Conan recipe (`infra/conan/`) does not build yet; see issue #125.

### Android

```bash
cd apps/android && ./gradlew assembleDebug
```

### Docker

```bash
docker compose -f infra/docker/docker-compose.yml up          # full stack (orchestrator, MQTT, Postgres, Redis, Grafana)
docker compose -f infra/docker/docker-compose.dev.yml up      # dev mode with volume mounts
```

## Architecture

> For complete architecture, data flow diagrams, and component details, see [spec/architecture/README.md](spec/architecture/README.md).

Key runtime boundaries (quick reference for AI agents):
- **ZeroMQ broker**: port 5555 — ROUTER-DEALER control plane (`apps/rpi-backend/shared/messaging/broker.py`)
- **Telemetry PUB/SUB**: port 5556 — real-time MCU data fan-out
- **FastAPI**: port 8000 — REST/WebSocket gateway (`apps/rpi-backend/py-api/api/main.py`)
- **MCP modules**: `orchestration/mcp/modules/` — domain microservices (automotive, audio, hardware)
- **OBD Digital Twin**: `apps/rpi-backend/py-api/services/obd_worker.py` — ELM327 emulator for the Audi A4 Cabriolet 8H
- **Voice**: `services/voice_command_router.py` (started with `VOICE_FSM=1`) owns the live `VoiceMachine` for the production voice pipeline. In router mode, `mia-api` relays `/ws/voice` to it through the router's loopback ZeroMQ ROUTER endpoint at `127.0.0.1:5565` (`VOICE_CONSOLE_PORT`). The console defaults to `VOICE_CONSOLE_BACKEND=sim`; with `VOICE_CONSOLE=1`, that mode creates a separate simulation-only machine in `mia-api`, outside the live voice pipeline. There is no wake word by default: a console or steering-wheel Wake is the push-to-talk route (ADR-0011, ADR-0020)

### Schemas and generated code

FlatBuffers sources live in `schemas/*.fbs`. Never hand-edit the generated bindings: `schemas/generated/python/`, `schemas/generated/cpp/`, and the Kotlin copy in `apps/android/app/src/main/generated/kotlin/MiaVoice/`. Regenerate them with `python schemas/generate.py --all` (needs `flatc`), plus `python tools/schemas/extract_enums.py` for the firmware enum header. CI regenerates `voice.fbs` and fails on any diff; drift in the other schemas only raises a warning. `schemas/baseline/voice.fbs` is the compatibility baseline (ADR-0004). When a schema changes, update `spec/interfaces/` (`events.md`, `topics.md`, `voice.md`) in the same PR.

## Key Configuration

- **Python**: 3.12.7, **Conan**: 2.3.2 (see `.tool-versions`)
- **pytest.ini**: asyncio_mode=auto, strict markers, test discovery in `tests/`
- **Flake8**: max-line-length=120, extends E203/W503 ignored
- **Black + isort**: isort uses `--profile black`
- **Coverage**: `.coveragerc` (source `apps/rpi-backend`, `orchestration`, `schemas`, `tools`; `fail_under` is a ratchet)
- **Pre-commit excludes**: `.backups/`, `exported-assets/`, `apps/android/` and `schemas/generated/` are excluded from the Python linters (`.pre-commit-config.yaml`)

## Deployment

Production target is `/opt/mia/` on Raspberry Pi. Systemd services defined in `infra/systemd/*.service` (zmq-broker, mia-api, mia-gpio-worker, mia-serial-bridge, mia-obd-worker, etc.). There are two entry points. `sudo ./tools/scripts/deploy-production-rpi.sh` runs on the Pi (see `docs/PRODUCTION_DEPLOYMENT.md`). `./tools/scripts/deploy-mia-rpi.sh [RPI_HOST] [RPI_USER]` runs from a dev machine: it finds the Pi on the LAN, syncs the code and installs the full voice stack, and its `MIA_*` environment toggles are listed in its header. `mia-power-monitor` stays off unless `MIA_ENABLE_POWER_MONITOR=1`, because the ignition stage is not bench-tested yet (#202). Consolidating the overlapping deploy scripts is issue #132. The ZMQ broker must start before other services.

## Conventions

- New behaviour needs a requirement in `spec/requirements/<area>.yaml`; a lasting design choice needs an ADR in `spec/decisions/`
- Every test names the requirements it checks: `pytestmark = pytest.mark.req("REQ-AUTO-010")` in Python, a `// @req REQ-AND-012` comment in Kotlin. An unknown ID stops the pytest run
- A requirement claims only the evidence that exists (ADR-0010). CI can support up to `simulation_tested`; bench, hardware and vehicle states need a record in `spec/evidence/<REQ-ID>/`
- Pull requests end with Claim / Proof / Not proven / Safety / Next owner (`.github/pull_request_template.md`)
- Reusable briefs live in the `mcp-prompts` server (`.mcp.json`): `list_prompts` with tag `mia-dev`, then `apply_template`. `mia-subagent-pr-brief` briefs a PR subagent; `mia-pr-merge-gate` is the checklist to run before any merge. The server is the global `@sparesparrow/mcp-prompts` package (GitHub Packages, needs `read:packages`); the runtime must not depend on it
- Hardware-dependent code must have simulation fallbacks for CI and non-RPi development
- Test markers are strict (`--strict-markers`): `req(...)` (see above), `hardware` (physical hardware; only in `tests/e2e/`, never run in CI), `slow`, `integration`, and the grouping-only `unit`, `automotive`, `android` and `meta_harness`
- Test file basenames must be unique across `tests/`, because pytest imports them by base name. `tests/conftest.py` puts the source roots on `sys.path`. Hyphenated directories (`rpi-backend`, `py-api`) can't be imported normally, so load them with `importlib` the way neighbouring tests do. See `tests/README.md`
- Work follows the Orchestrator / Evaluator / Executor split in `agents/` (`spec/README.md`): each PR is one approved slice and touches nothing outside it
- Path-scoped area guidance lives in `.github/instructions/*.instructions.md`; each file's `applyTo` lists the paths it covers. Claude Code doesn't load these files automatically, so read the matching one before changing code in its area
- MCP modules follow initialize/shutdown lifecycle pattern
- Error handling returns structured dicts with `status` and `message` keys
- Environment config via `.env` (see `.env.example`)
