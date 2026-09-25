# Project Guidelines

## Architecture

- The repository has three parts ([spec/README.md](../spec/README.md)): requirements and design decisions in `spec/`, production code in `apps/`, `orchestration/`, `schemas/`, `infra/`, `web/` and `agents/`, and tests in `tests/`. Open work lives in GitHub Issues, not in files.
- Runtime applications live in `apps/`, MCP orchestration lives in `orchestration/`, deployment assets live in `infra/`, and shared contracts live in `schemas/` (FlatBuffers and JSON schemas, with generated bindings under `schemas/generated/`). Interface specs live in `spec/interfaces/`.
- The main runtime boundary is the Raspberry Pi backend in `apps/rpi-backend/py-api/`: FastAPI provides HTTP/WebSocket access, ZeroMQ handles worker messaging, and hardware/vehicle integrations hang off that boundary.
- Android work lives in `apps/android/`. ESP32 and Arduino work lives under `apps/esp32/` and `apps/arduino/`. Keep changes localized to one platform unless the task explicitly crosses contracts.
- Treat schema and messaging changes as cross-cutting: if you change FlatBuffers definitions in `schemas/`, regenerate bindings instead of hand-editing generated files in `schemas/generated/python/Mia/`.
- Hardware-facing code must keep non-hardware development paths working. Preserve simulation or fallback behavior for Raspberry Pi and serial integrations.

## Build and Test

- Python setup: `pip3 install -r requirements-dev.txt`
- Python validation: `pytest tests/ -m "not hardware"`
- Python formatting/lint: `black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503`
- Requirement traceability: `pytest tests/ -m "not hardware" --req-report=req-report.json && python tools/ci/traceability.py check --pytest-report req-report.json`
- Android build: `cd apps/android && ./gradlew assembleDebug`
- C++ build: `cmake -S apps/rpi-backend/cpp-audio -B build/cpp -DWITH_HARDWARE=OFF && cmake --build build/cpp`
- Docker dev stack: `docker compose -f infra/docker/docker-compose.dev.yml up`
- In CI or lightweight environments, prefer `requirements-ci.txt` over the full `requirements.txt`.

## Conventions

- Use the pytest markers defined in `pytest.ini` exactly: `hardware`, `slow`, `integration`, `unit`, `automotive`, `android` and `req`.
- New behaviour needs a requirement in `spec/requirements/`, and every test names the requirements it checks with `@pytest.mark.req("REQ-...")` (or a `// @req` comment in Kotlin). A requirement may claim only the evidence its tests and `spec/evidence/` records support (ADR-0010).
- Python services in this repo commonly return structured `status` and `message` payloads. Match the surrounding code instead of introducing a different response shape in existing service layers.
- Service startup order matters for deployed systems. Check the broker, API, and worker dependencies before changing ZeroMQ ports, worker registration, or systemd service names.
- Do not hand-edit generated artifacts unless the task is explicitly about generation output. Update the source schema, config, or generator instead.
- Prefer targeted changes inside the owning area of the repo rather than broad reorganization. This codebase is large and spans multiple platforms.

## Key References

- General development commands and deployment notes: [CLAUDE.md](../CLAUDE.md)
- Repository structure and system overview: [spec/architecture/README.md](../spec/architecture/README.md)
- Test markers and pytest defaults: [pytest.ini](../pytest.ini)
- Android-specific architecture and Gradle workflows: [apps/android/README.md](../apps/android/README.md)
- Deployment and environment setup details: [docs/PRODUCTION_DEPLOYMENT.md](../docs/PRODUCTION_DEPLOYMENT.md), [docs/RASPBERRY_PI_SETUP.md](../docs/RASPBERRY_PI_SETUP.md), [docs/conan-setup.md](../docs/conan-setup.md)
- Troubleshooting and operational guidance: [docs/troubleshooting.md](../docs/troubleshooting.md)