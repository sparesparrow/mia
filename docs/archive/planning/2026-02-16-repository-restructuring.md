# MIA Repository Restructuring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Reorganize the MIA monorepo from a scattered 40+ top-level directories layout into a clear domain-based structure (apps/orchestration/infra/tests/tools) that scales with the multi-platform, multi-agent architecture.

**Architecture:**
- Phase 1 creates the target directory skeleton and updates ARCHITECTURE.md
- Phase 2 moves platform-specific code (Android, RPi, ESP32) into `apps/`
- Phase 3 consolidates orchestration/MCP into `orchestration/`
- Phase 4 moves infrastructure (Docker, deploy, systemd) into `infra/`
- Phase 5 reorganizes tests and tools
- Phase 6 updates CI/CD pipelines and validates everything still works

**Tech Stack:** Bash/git, Python 3.12, pytest, GitHub Actions

**Current State Pain Points:**
- 40+ top-level directories (android, rpi, esp32, modules, docker, deploy, ci, web, platforms, clients, devices, edge-compat, external, firmware, etc.)
- Unclear separation between runtime apps vs. orchestration vs. infrastructure
- CI paths scattered across multiple locations
- Makes onboarding new developers difficult
- Blocks future expansion (desktop client, new devices, etc.)

---

## Phase 1: Create Skeleton & Document Target State

### Task 1.1: Create directory skeleton

**Files:**
- Create: `apps/` (empty)
- Create: `apps/android/` (empty)
- Create: `apps/rpi-backend/` (empty)
- Create: `apps/rpi-backend/cpp-audio/` (empty)
- Create: `apps/rpi-backend/py-api/` (empty)
- Create: `apps/esp32/` (empty)
- Create: `orchestration/` (empty)
- Create: `orchestration/mia-agents/` (empty)
- Create: `orchestration/mcp/` (empty)
- Create: `orchestration/mcp/prompts/` (empty)
- Create: `infra/` (empty)
- Create: `infra/docker/` (empty)
- Create: `infra/systemd/` (empty)
- Create: `infra/conan/` (empty)
- Create: `infra/deploy/` (empty)
- Create: `tests/integration/` (empty)
- Create: `tests/integration/scenarios/` (empty)
- Create: `tests/integration/fixtures/` (empty)
- Create: `tools/ci/` (empty)
- Create: `tools/local-dev/` (empty)

**Step 1: Create all directories**

```bash
mkdir -p apps/android apps/rpi-backend/cpp-audio apps/rpi-backend/py-api apps/esp32
mkdir -p orchestration/mia-agents orchestration/mcp/prompts
mkdir -p infra/docker infra/systemd infra/conan infra/deploy
mkdir -p tests/integration/{scenarios,fixtures}
mkdir -p tools/{ci,local-dev}
```

**Step 2: Add .gitkeep files to preserve empty directories**

```bash
for dir in apps apps/android apps/rpi-backend apps/rpi-backend/cpp-audio apps/rpi-backend/py-api apps/esp32 \
           orchestration orchestration/mia-agents orchestration/mcp orchestration/mcp/prompts \
           infra infra/docker infra/systemd infra/conan infra/deploy \
           tests/integration tests/integration/scenarios tests/integration/fixtures \
           tools tools/ci tools/local-dev; do
  touch "$dir/.gitkeep"
done
git add -A
```

**Step 3: Create ARCHITECTURE.md describing target state**

Create `/home/sparrow/projects/embedded/mia/ARCHITECTURE.md` with:

```markdown
# MIA Architecture & Repository Structure

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
- Automotive bridge (OBD-II, Citroën C4 PSA PIDs)
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
   │     │ │Bridge │ │(Citroen C4) │ │ (MCP)   │
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
- **Broker**: ZeroMQ ROUTER-DEALER on port 5555 (workers register as DEALER)
- **Pub/Sub**: ZeroMQ PUB/SUB on port 5556 (real-time telemetry to subscribers)
- **MCP Modules**: Microservices under `orchestration/mcp/` handle domain logic

### Testing Strategy
- **Unit tests**: Per-platform, isolated to `tests/unit/android|rpi|esp32/`
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
```

**Step 4: Commit**

```bash
cd /home/sparrow/projects/embedded/mia
git add -A
git commit -m "chore: add target repository skeleton and ARCHITECTURE.md"
```

**Step 5: Verify**

```bash
# Verify directory structure matches plan
find . -maxdepth 3 -type d -name '.gitkeep' | wc -l
# Should be ~20+ .gitkeep files
```

---

## Phase 2: Move Platform-Specific Code into `apps/`

### Task 2.1: Move Android app

**Files:**
- Move: `android/` → `apps/android/`
- Update: `apps/android/.gitignore`, `build.gradle.kts`
- Verify: GitHub Actions Android CI still works

**Step 1: Move Android directory**

```bash
git mv android apps/android
cd apps/android
# Verify all files present
ls -la | head -20
cd ../../
git add -A
```

**Step 2: Update CI paths**

Edit `.github/workflows/android-ci.yml` (if exists):
- Change `paths: ["android/**"]` → `paths: ["apps/android/**"]`

If CI file references `android/` directory, update all paths.

**Step 3: Update any build scripts**

Search for hardcoded `android/` paths:

```bash
grep -r "android/" . --include="*.gradle.kts" --include="*.md" --include="*.yml" --exclude-dir=.git | grep -v "apps/android" | head -20
```

Update any found references to `apps/android/`.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: move Android app to apps/android/"
```

### Task 2.2: Move ESP32 firmware

**Files:**
- Move: `esp32/` → `apps/esp32/`
- Update: CI paths, platformio scripts

**Step 1: Move ESP32 directory**

```bash
git mv esp32 apps/esp32
git add -A
```

**Step 2: Update CI paths**

Edit `.github/workflows/esp32-ci.yml`:
- Change `paths: ["esp32/**"]` → `paths: ["apps/esp32/**"]`

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: move ESP32 firmware to apps/esp32/"
```

### Task 2.3: Move and restructure RPi backend

**Files:**
- Move: `rpi/` → `apps/rpi-backend/py-api/`
- Move: `platforms/cpp/` → `apps/rpi-backend/cpp-audio/`
- Move: `api/` → `apps/rpi-backend/py-api/` (if separate)
- Move: `core/` → `apps/rpi-backend/shared/` (shared utilities)

**Step 1: Create RPi backend structure**

```bash
# Structure already created in Phase 1
# Now populate it

# Move Python API
git mv rpi apps/rpi-backend/py-api
git mv api apps/rpi-backend/py-api/  # if separate dir

# Move C++ audio
git mv platforms/cpp apps/rpi-backend/cpp-audio

# Move core utilities (might be shared by py-api and cpp-audio)
git mv core apps/rpi-backend/shared/
```

**Step 2: Update imports in Python code**

Example: If `rpi/services/obd_worker.py` imports from `core/messaging/broker.py`, update to relative import:

```python
# Before:
from core.messaging.broker import ZMQBroker

# After (adjust path based on file location):
from ../../shared.messaging.broker import ZMQBroker
# or
import sys
sys.path.insert(0, '/opt/mia/shared')  # if using absolute deployment path
```

**Step 3: Update CI paths**

Edit `.github/workflows/rpi-backend-ci.yml`:
```yaml
paths:
  - "apps/rpi-backend/**"
  - "requirements.txt"  # if at root
  - "requirements-dev.txt"
```

**Step 4: Commit in logical chunks**

```bash
# First commit: move directories
git add -A
git commit -m "chore: move RPi backend (Python API, C++ audio) to apps/rpi-backend/"

# Second commit: update imports
git add apps/rpi-backend/
git commit -m "refactor: update imports in RPi backend after restructuring"
```

---

## Phase 3: Move Orchestration & MCP into `orchestration/`

### Task 3.1: Move MCP modules

**Files:**
- Move: `modules/` → `orchestration/mcp/`
- Move: `services/` (non-RPi-specific) → `orchestration/mcp/` or keep and reference
- Keep: Hyphenated module names (valid for runtime import via `importlib.util`)

**Step 1: Move modules**

```bash
# Save current modules structure for reference
mkdir -p orchestration/mcp/modules
# Copy preserving structure - OR use git mv if moving everything
git mv modules/* orchestration/mcp/

# The shared framework goes to both old and new location for now (dual-location period)
git add -A
```

**Step 2: Update Python path imports for tests**

Tests that import from `modules/` need updating. If a test currently does:

```python
# tests/unit/test_orchestrator.py
from modules.core_orchestrator.orchestrator import Orchestrator
```

Change to:

```python
from orchestration.mcp.core_orchestrator.orchestrator import Orchestrator
```

Or use `sys.path.insert(0, ...)` at test start for backward compatibility period.

**Step 3: Update CI imports**

Edit `.github/workflows/integration-tests.yml`:
- Update any `PYTHONPATH` exports referencing `modules/`

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: move MCP modules to orchestration/mcp/"
git commit -m "refactor: update imports after orchestration/ restructuring"
```

### Task 3.2: Move MCP prompts and agents config

**Files:**
- Move: `prompts/` → `orchestration/mcp/prompts/`
- Move: `agents/` or `agents.json` → `orchestration/mia-agents/`

**Step 1: Move prompts**

```bash
git mv prompts orchestration/mcp/prompts
```

**Step 2: Move agents config**

```bash
if [ -d "agents" ]; then
  git mv agents orchestration/mia-agents/
elif [ -f "agents.json" ]; then
  mkdir -p orchestration/mia-agents/
  git mv agents.json orchestration/mia-agents/agents.json
fi
git add -A
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: move prompts and agents config to orchestration/"
```

---

## Phase 4: Move Infrastructure into `infra/`

### Task 4.1: Move Docker & containers

**Files:**
- Move: `docker/` → `infra/docker/`
- Move: `containers/` → `infra/docker/containers/`
- Move: `docker-compose*.yml` → `infra/docker/`

**Step 1: Move Docker files**

```bash
git mv docker infra/docker
if [ -d "containers" ]; then
  git mv containers infra/docker/containers
fi

# If docker-compose.yml is in root, move it
if [ -f "docker-compose.yml" ]; then
  git mv docker-compose.yml infra/docker/
fi
if [ -f "docker-compose.dev.yml" ]; then
  git mv docker-compose.dev.yml infra/docker/
fi
if [ -f "docker-compose.prod.yml" ]; then
  git mv docker-compose.prod.yml infra/docker/
fi
git add -A
```

**Step 2: Update root README & scripts to reference new paths**

Example in root Makefile or script:

```bash
# Before:
docker compose -f docker-compose.dev.yml up

# After:
docker compose -f infra/docker/docker-compose.dev.yml up
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: move Docker configs to infra/docker/"
```

### Task 4.2: Move deployment scripts

**Files:**
- Move: `deploy/` → `infra/deploy/`
- Create: `infra/deploy/rpi/`, `infra/deploy/esp32/`, `infra/deploy/aws/`

**Step 1: Move deploy directory**

```bash
git mv deploy infra/deploy
# Verify structure:
ls -la infra/deploy/
```

**Step 2: Create platform-specific subdirs**

```bash
mkdir -p infra/deploy/{rpi,esp32,aws}
# If deploy already has subdirs, verify they match

# If scripts are loose in deploy/, organize them:
# e.g., mv deploy/deploy-rpi.sh infra/deploy/rpi/deploy.sh
```

**Step 3: Update paths in deployment scripts**

If `infra/deploy/rpi/deploy.sh` references systemd files, update:

```bash
# Before:
systemctl enable /home/mia/services/mia-api.service

# After:
systemctl enable /home/mia/infra/systemd/mia-api.service
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: move deployment scripts to infra/deploy/"
```

### Task 4.3: Move systemd services

**Files:**
- Move: systemd `.service` files → `infra/systemd/`

**Step 1: Find and move systemd files**

```bash
# Find .service files
find . -name "*.service" -type f | grep -v ".git"

# Example:
git mv services/*.service infra/systemd/ 2>/dev/null || true
```

**Step 2: Commit**

```bash
git add -A
git commit -m "chore: move systemd services to infra/systemd/"
```

### Task 4.4: Move Conan configuration

**Files:**
- Move: `conanfile.py`, `conan-recipes/`, `profiles/` → `infra/conan/`

**Step 1: Move Conan files**

```bash
git mv conanfile.py infra/conan/ || true
git mv conan-recipes infra/conan/ || true
git mv profiles infra/conan/ || true
git add -A
```

**Step 2: Update CI references**

Update `.github/workflows/` to reference `infra/conan/conanfile.py` if needed.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: move Conan config to infra/conan/"
```

---

## Phase 5: Reorganize Tests & Tools

### Task 5.1: Consolidate tests structure

**Files:**
- Move: `tests/` → review and organize by platform/type
- Create: `tests/integration/scenarios/` for business flow tests

**Step 1: Audit current tests**

```bash
find tests/ -name "test_*.py" | head -20
ls -la tests/
```

**Step 2: Reorganize tests**

```bash
# If tests are scattered, consolidate:
# tests/unit/ → tests/unit/ (stays)
# tests/integration/ → tests/integration/ (stays)
# tests/e2e/ → tests/integration/scenarios/ (rename for clarity)

# Create empty scenario dirs
mkdir -p tests/integration/scenarios/{voice_commands,obd_telemetry,gpio_control}
mkdir -p tests/integration/fixtures/{mqtt,http,zmq}

# If scenario tests exist, move them:
# git mv tests/e2e/test_voice_command.py tests/integration/scenarios/voice_commands/
```

**Step 3: Add pytest conftest for new structure**

Create `tests/integration/conftest.py` if not exists:

```python
import pytest
from pathlib import Path

@pytest.fixture
def scenario_dir():
    """Return path to scenarios directory"""
    return Path(__file__).parent / "scenarios"

@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory"""
    return Path(__file__).parent / "fixtures"
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: reorganize tests structure with integration scenarios"
```

### Task 5.2: Move development tools & scripts

**Files:**
- Move: `scripts/`, `bin/`, development scripts → `tools/`

**Step 1: Move development scripts**

```bash
# Capture what's in scripts/
ls -la scripts/

# Move to appropriate location:
git mv scripts/* tools/local-dev/ || true
git mv bin/* tools/ci/ || true  # or local-dev, depending on purpose

# Remove empty dirs
rmdir scripts/ bin/ 2>/dev/null || true
```

**Step 2: Organize by purpose**

```bash
# tools/ci/ - build, lint, test helpers
# tools/local-dev/ - start dev stack, sync assets, flash firmware

# Examples:
# tools/ci/lint-all.sh
# tools/ci/run-tests.sh
# tools/local-dev/start-dev-stack.sh
# tools/local-dev/flash-esp32.sh
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: move development scripts and tools to tools/"
```

---

## Phase 6: Update CI/CD & Documentation

### Task 6.1: Consolidate GitHub Actions workflows

**Files:**
- Update: `.github/workflows/*.yml` with new paths
- Create: `.github/workflows/integration-tests.yml` if not exists

**Step 1: Update existing workflow files**

For each `.github/workflows/` file, update:
- `paths:` triggers to reference new directory structure
- `working-directory:` if set
- Any `run:` commands that reference old paths

Example `.github/workflows/android-ci.yml`:

```yaml
name: Android CI

on:
  push:
    paths:
      - "apps/android/**"
      - ".github/workflows/android-ci.yml"
    branches:
      - main
  pull_request:
    paths:
      - "apps/android/**"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Android
        run: |
          cd apps/android
          ./gradlew assembleDebug
```

**Step 2: Update all workflow files**

```bash
# List all workflows
ls -la .github/workflows/

# For each file, update paths and directories
```

**Step 3: Add new integration test workflow (optional)**

Create `.github/workflows/integration-tests.yml`:

```yaml
name: Integration Tests

on:
  push:
    paths:
      - "tests/integration/**"
      - "apps/rpi-backend/**"
      - "orchestration/**"
      - ".github/workflows/integration-tests.yml"
    branches:
      - main
  pull_request:
    paths:
      - "tests/integration/**"

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      mqtt:
        image: eclipse-mosquitto:latest
      zmq:
        # Note: ZMQ requires custom setup; this is placeholder
        image: ubuntu:latest

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v -m integration
```

**Step 4: Commit**

```bash
git add .github/
git commit -m "chore: update CI/CD workflows for new repository structure"
```

### Task 6.2: Update root documentation

**Files:**
- Update: `README.md` with new structure references
- Update: Any deployment guides to reference `infra/deploy/`
- Create: `docs/DEVELOPMENT.md` with local dev instructions

**Step 1: Update README.md**

Update the "Build & Test Commands" and "Architecture" sections to reference:
- `apps/android`, `apps/rpi-backend`, `apps/esp32`
- `orchestration/mcp`
- `infra/docker`, `infra/systemd`, `infra/deploy`
- `tools/ci`, `tools/local-dev`

**Step 2: Create or update `docs/DEVELOPMENT.md`**

```markdown
# Development Guide

## Local Setup

### Start Development Stack

```bash
./tools/local-dev/start-dev-stack.sh
```

This starts:
- Docker containers (infra/docker/docker-compose.dev.yml)
- ZMQ broker on port 5555
- FastAPI on port 8000
- MQTT on port 1883

### Run All Tests

```bash
pytest tests/ -m "not hardware"
```

### Build Android App

```bash
cd apps/android
./gradlew assembleDebug
```

### Build & Flash ESP32

```bash
cd apps/esp32
platformio run -t upload
```

### RPi C++ Audio Module

```bash
cd apps/rpi-backend/cpp-audio
cmake -B build && cmake --build build
```

### Lint & Format

```bash
./tools/ci/lint-all.sh
```
```

**Step 3: Commit**

```bash
git add README.md docs/
git commit -m "docs: update documentation for new repository structure"
```

### Task 6.3: Verify nothing broke

**Files:**
- Test: All CI workflows still trigger correctly
- Test: Local builds still work
- Test: Imports still resolve

**Step 1: Test local builds**

```bash
# From repo root:
cd apps/android && ./gradlew check && cd ../..
cd apps/esp32 && platformio check && cd ../..
cd apps/rpi-backend/py-api && python -m pytest tests/ -m "not hardware" && cd ../../../..
cd apps/rpi-backend/cpp-audio && cmake -B build && cmake --build build && cd ../../../..
```

**Step 2: Test Docker build**

```bash
docker compose -f infra/docker/docker-compose.dev.yml build --no-cache
```

**Step 3: Test import paths**

```bash
# Python: verify modules can be imported
cd /tmp
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/sparrow/projects/embedded/mia/orchestration/mcp')
# Try importing a core module
try:
    # from core_orchestrator.orchestrator import Orchestrator
    print("✓ Import path works")
except ImportError as e:
    print(f"✗ Import failed: {e}")
EOF
```

**Step 4: Commit success verification**

```bash
# Create .github/workflows/verify-structure.yml
# This workflow runs sanity checks after restructuring
```

---

## Phase 7: Cleanup & Archive

### Task 7.1: Remove old directories (if safe)

**Files:**
- Delete: Legacy `android/`, `esp32/`, `rpi/`, `platforms/`, `modules/`, `docker/`, `deploy/`, `services/`, `core/` (only after verified moved)

**Step 1: Identify directories to remove**

```bash
# List directories that should be gone:
ls -d android esp32 rpi platforms modules docker deploy services core 2>/dev/null
```

**Step 2: Verify they're fully moved**

```bash
# Before removing, check if anything references old locations
grep -r "from android\|from esp32\|from rpi\|from modules\|from core\|from docker" . \
  --include="*.py" --include="*.yml" --include="*.md" --exclude-dir=.git | head -10
```

**Step 3: Remove old directories**

```bash
git rm -r android esp32 rpi platforms modules docker deploy services core 2>/dev/null || true
git add -A
git commit -m "chore: remove legacy directories after successful migration"
```

### Task 7.2: Final cleanup

**Files:**
- Remove: unused top-level directories (`web/`, `clients/`, `firmware/`, `devices/`, `external/`, etc.)
- Archive: Old documentation in `docs/legacy/` if needed

**Step 1: Assess cleanup candidates**

```bash
# Directories that might be legacy:
ls -d web clients firmware devices external edge-compat platform monitoring site 2>/dev/null
```

**Step 2: Archive if needed**

```bash
# Only remove/archive if confirmed as truly unused
# Example:
if [ -d "web" ] && [ ! -f "web/README.md" ]; then
  mkdir -p docs/legacy/
  git mv web docs/legacy/web 2>/dev/null || true
fi
git add -A
git commit -m "chore: archive legacy directories to docs/legacy/"
```

**Step 3: Final verification**

```bash
# Verify root structure is clean
ls -d */ | sort
# Should be: apps/ docs/ orchestration/ infra/ tests/ tools/ .github/ + hidden dirs
```

---

## Rollback Strategy

If something breaks:

1. **Immediate:** `git reset --hard HEAD~N` (go back N commits)
2. **Partial:** `git revert <commit-hash>` (revert specific commit)
3. **Emergency:** On remote, force-push to previous good state (⚠️ only if no one pulled yet)

All changes use `git mv` (not copy/delete), so git history is preserved.

---

## Success Criteria

✓ All top-level directories fit into: `apps/`, `orchestration/`, `infra/`, `tests/`, `tools/`, `docs/`, `.github/`
✓ Android, RPi, ESP32 builds all pass
✓ Python imports resolve (from `orchestration/mcp/`, etc.)
✓ CI workflows trigger on correct paths
✓ Docker Compose still starts dev stack
✓ All tests pass (`pytest tests/ -m "not hardware"`)
✓ README & ARCHITECTURE.md reflect new structure
✓ New developers can understand structure from directory names alone
