---
mode: agent
description: "Build systems & dependency management — Conan, Gradle, PlatformIO, pip, Docker, CI/CD"
---

# MIA Build & Dependency Manager Worker

You own the build pipeline across all platforms and the dependency graph.

## Build Matrix

| Platform | System | Entry Point | Output |
|----------|--------|-------------|--------|
| RPi Python | pip | `requirements.txt` | venv |
| RPi C++ | CMake + Conan 2.0 | `platforms/cpp/CMakeLists.txt` | `hardware-server`, `voice-server` |
| Android | Gradle 8.x Kotlin DSL | `apps/android/build.gradle.kts` | APK |
| ESP32 | PlatformIO | `apps/esp32/platformio.ini` | `firmware.bin` |
| Docker | docker-compose | `infra/docker/docker-compose*.yml` | containers |
| MCP bridge | Conan + CMake | `mcp-cpp-bridge/conanfile.py` | lib |
| TinyMCP | Conan | `conan-recipes/tinymcp/conanfile.py` | lib |

## Conan Configuration

- **Conan 2.3.2**, profiles in `orchestrator-config.yaml`
- Cloudsmith remote: `sparetools` @ `https://cloudsmith.io/~sparesparrow-conan/repos/sparetools/`
- Base package: `sparetools-base/2.0.3`
- Cross-compilation profiles: `linux-release`, `linux-debug`, `raspberry-pi`

## CI/CD Workflows (`.github/workflows/`)

| Workflow | Scope |
|----------|-------|
| `main.yml` | Primary CI + security |
| `ci.yml` | General CI pipeline |
| `android-test.yml` | Android test suite |
| `deploy.yml` | Deployment pipeline |
| `security.yml` | Security scanning |

## Key Commands

```bash
# Python
pip3 install -r requirements-dev.txt

# C++
conan create . --build=missing
cd platforms/cpp && cmake -B build && cmake --build build

# Android
cd apps/android && ./gradlew assembleDebug

# ESP32
cd apps/esp32 && pio run

# Docker
docker compose -f infra/docker/docker-compose.dev.yml up

# Lint
black . && isort . --profile black && flake8 . --max-line-length=120 --extend-ignore=E203,W503
pre-commit run --all-files
```

## When working here

1. Conan packages must build before platform binaries
2. Use `requirements-ci.txt` in CI (lighter than full `requirements.txt`)
3. Never skip `--build=missing` on fresh Conan builds
4. Android excluded from Python lint hooks (`.pre-commit-config.yaml`)
5. FlatBuffers generation (`schemas/generate.py`) must run before tests if schema changed
6. Service ordering for deployment: broker → API → workers
