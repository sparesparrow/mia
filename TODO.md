# MIA: Modular IoT Assistant

## Lean Architecture: ZeroMQ + FlatBuffers + FastAPI

### Project Overview
MIA is a distributed control system designed for Raspberry Pi 4B as the primary compute node, integrating with Arduino/ESP32 microcontrollers for hardware control and Android smartphones for remote user interfaces. The architecture prioritizes simplicity, low latency, and minimal overhead compared to full ROS2 deployments.

### Design Rationale
- **Why NOT ROS2 for this scope?** ROS2 introduces significant overhead and complexity for a single-RPi deployment with direct Android app control. The Lean architecture achieves the same goals with simpler deployment, faster development, and clearer debugging.
- **Core Technologies:**
  - **ZeroMQ (0MQ)**: Lightweight message broker for process-to-process and cross-device communication
  - **FlatBuffers**: Efficient binary serialization for hardware messages
  - **FastAPI**: Simple, async HTTP/WebSocket API for remote control and telemetry

---

## Phase 1: Foundation (Weeks 1-2)

### 1.1 Project Setup & Infrastructure
- [ ] Create project structure with clear module separation
  - `core/`: ZeroMQ messaging and routing
  - `hardware/`: Arduino/ESP32 drivers and GPIO control
  - `api/`: FastAPI application and WebSocket handlers
  - `schemas/`: FlatBuffers schema definitions
  - `android/`: Android app (native or Flutter)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Docker Compose configuration for local development and RPi deployment

### 1.2 FlatBuffers Schema Design
- [ ] Define core message schemas
  - GPIO control commands (pin, mode, state)
  - Sensor telemetry (temperature, humidity, distance, etc.)
  - System status (uptime, memory, CPU)
  - Command responses and acknowledgments
- [ ] Generate Python and C++ bindings
- [ ] Implement schema versioning strategy

### 1.3 ZeroMQ Core Messaging Layer
- [ ] Implement message broker using ZeroMQ ROUTER-DEALER pattern
- [ ] Create Python message handlers for:
  - Hardware commands (to Arduino/ESP32)
  - Telemetry collection (from sensors)
  - System events
- [ ] Implement message queuing and persistence
- [ ] Setup logging and message tracing

---

## Phase 2: Hardware Integration (Weeks 3-4)

### 2.1 Arduino/ESP32 Communication
- [ ] Design serial/USB communication protocol
  - Handshake and device discovery
  - FlatBuffers message framing over serial
  - Error detection (CRC/checksums)
- [ ] Implement Arduino C++ library for receiving FlatBuffers commands
- [ ] Implement ESP32 WiFi bridge for wireless GPIO control
- [ ] Create hardware abstraction layer in Python

### 2.2 GPIO Control & Sensor Integration
- [ ] Implement GPIO control (RPi.GPIO or gpiozero)
  - Digital outputs (LEDs, relays, motors)
  - Digital inputs (buttons, sensors)
  - PWM support for motor speed/brightness
- [ ] Add sensor drivers
  - I2C/SPI sensors (temperature, humidity, etc.)
  - Analog-to-digital conversion for Arduino sensors
- [ ] Implement sensor polling with configurable intervals

### 2.3 Hardware Abstraction & Device Registry
- [ ] Create device registry for discoverable hardware
- [ ] Implement device profiles (e.g., "LED Strip", "Motor Controller")
- [ ] Setup health monitoring (device connectivity, error states)

---

## Phase 3: FastAPI & Remote Control (Weeks 5-6)

### 3.1 REST API Development
- [ ] Create FastAPI endpoints for:
  - GET /devices - list all connected devices
  - POST /command - send command to device
  - GET /telemetry - fetch latest sensor readings
  - GET /status - system health and uptime
- [ ] Implement request validation using Pydantic models
- [ ] Add authentication/authorization (basic or JWT)
- [ ] Create OpenAPI documentation

### 3.2 WebSocket Real-Time Telemetry
- [ ] Implement WebSocket server for live telemetry streaming
- [ ] Create client-side filters (subscribe only to specific devices/sensors)
- [ ] Implement connection keepalive and auto-reconnect logic

### 3.3 Mobile App Integration
- [ ] Design API contracts for Android app
- [ ] Create mock server for app testing
- [ ] Document all endpoints and WebSocket message formats

---

## Phase 4: Android App Development (Weeks 7-8)

### 4.1 App Architecture (Native or Flutter)
- [ ] Setup Android project (Java/Kotlin or Flutter)
- [ ] Implement HTTP client for REST API
- [ ] Implement WebSocket client for telemetry
- [ ] Create UI framework and navigation

### 4.2 Core Features
- [ ] Device discovery and pairing
- [ ] Remote device control (switches, sliders, buttons)
- [ ] Real-time telemetry display (graphs for sensor data)
- [ ] System status dashboard
- [ ] Settings and preferences (API URL, polling intervals, etc.)

### 4.3 User Experience
- [ ] Offline support (cache last-known device state)
- [ ] Error handling and user notifications
- [ ] Responsive design for tablets and phones

---

## Phase 5: Optimization & Polish (Weeks 9-10)

### 5.1 Performance Optimization
- [ ] Profile ZeroMQ message latency
- [ ] Optimize sensor polling intervals
- [ ] Implement efficient WebSocket message compression
- [ ] Test throughput with multiple simultaneous commands

### 5.2 Reliability & Error Handling
- [ ] Implement reconnection logic for network failures
- [ ] Add circuit breakers for hardware that goes offline
- [ ] Implement command retry mechanisms with exponential backoff
- [ ] Comprehensive logging and debugging tools

### 5.3 Security Hardening
- [ ] Implement HTTPS/TLS for FastAPI
- [ ] Add rate limiting to prevent abuse
- [ ] Secure WebSocket (WSS)
- [ ] Input validation and sanitization
- [ ] API key rotation and revocation

---

## Phase 6: Testing & Deployment (Weeks 11-12)

### 6.1 Testing Strategy
- [ ] Unit tests for all Python modules (pytest)
- [ ] Integration tests for ZeroMQ and hardware layers
- [ ] Android app UI tests (Espresso or Flutter integration tests)
- [ ] End-to-end tests with real hardware

### 6.2 Documentation
- [ ] Architecture decision records (ADRs)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Deployment guide for RPi setup
- [ ] Hardware setup instructions (Arduino, sensors, etc.)
- [ ] Android app installation and configuration guide

### 6.3 Deployment
- [ ] RPi systemd services for core components
- [ ] Docker deployment for consistency
- [ ] OTA update mechanism

---

## Cross-Cutting Concerns

### Logging & Monitoring
- [ ] Centralized logging (Python logging, rotating file handlers)
- [ ] Metrics collection (uptime, message throughput, latency)
- [ ] Health check endpoints

### Code Quality
- [ ] PEP 8 compliance and type hints for all Python code
- [ ] Kotlin conventions for Android (if using native)
- [ ] Pre-commit hooks (linting, formatting, type checking)
- [ ] Code reviews for all PRs

### Process & Coordination
- [ ] Weekly standups on Discord (#mia-dev channel)
- [ ] GitHub Issues for tracking blockers and bugs
- [ ] Commit messages must reference this TODO with task ID (e.g., "feat: P1-1.1 Project setup")

---

## Success Criteria

### MVP Completion
1. **Hardware Control**: Successfully control GPIO pins on RPi and Arduino via HTTP REST API
2. **Remote Access**: Android app can connect to system and trigger device commands
3. **Telemetry Streaming**: Real-time sensor data visible in app via WebSocket
4. **Offline Resilience**: System recovers gracefully when components disconnect
5. **Documentation**: Full setup and API docs for future contributors

### Performance Targets
- Command latency: < 50ms end-to-end (app to GPIO toggle)
- Telemetry update frequency: 10Hz (100ms intervals)
- Uptime target: 99.5% (excluding intentional shutdowns)
- Zero data loss for commands (implemented via ACKs)

### Security Baseline
- All API traffic encrypted (HTTPS/WSS)
- Device authentication via API key or JWT
- Input validation on all endpoints

---

## Architectural Diagrams

### System Overview
```
┌─────────────────┐
│  Android App    │
└────────┬────────┘
         │ HTTP/WebSocket
         │
    ┌────▼──────────────────┐
    │  FastAPI Server       │
    │  (RPi, :8000)         │
    └────┬───────────────────┘
         │ ZeroMQ ROUTER/DEALER
         │
    ┌────▼──────────────────┐
    │ Message Broker        │
    │ (Router: :5555)       │
    └────┬──────────────────┘
         │
    ┌────┴────────────────────┐
    │  GPIO Controller        │
    │  (Sensors, Actuators)   │
    │                         │
    └─────────────────────────┘
         ↓
    ┌──────────────────────────┐
    │  Hardware               │
    │  - Arduino (Serial USB) │
    │  - ESP32 (WiFi)         │
    │  - RPi GPIO             │
    └──────────────────────────┘
```

### Message Flow Example (Toggle LED)
```
1. Android App → REST POST /command {device: "led1", action: "toggle"}
2. FastAPI → ZeroMQ DEALER → Router
3. Router → GPIO Worker (subscribed to device commands)
4. GPIO Worker → RPi GPIO output (pin 17, HIGH)
5. GPIO Worker → Router → FastAPI → Android App (ACK response)
```

---

## Repository Structure
```
mia/
├── core/
│   ├── messaging/     # ZeroMQ broker and message routing
│   ├── models/        # FlatBuffers generated classes
│   └── utils/         # Common utilities
├── hardware/
│   ├── gpio_control.py
│   ├── arduino_driver.py
│   └── sensor_drivers/
├── api/
│   ├── main.py        # FastAPI app
│   ├── routes/        # API endpoints
│   └── websocket/     # WebSocket handlers
├── schemas/
│   ├── *.fbs          # FlatBuffers schema files
│   └── generated/     # Generated bindings
├── tests/
├── docker-compose.yml
├── requirements.txt
├── README.md
├── TODO.md (this file)
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    └── DEPLOYMENT.md
```

---

## MCP Security Module (NEW - Phase 7)

### Overview
Integration with Kernun proxy MCP server for network security analysis.
Optional module enabled via Conan configuration.

### 7.1 Kernun MCP Tools Conan Package
- [x] Create Conan recipe (`conan-recipes/kernun-mcp-tools/conanfile.py`)
- [x] Implement C++ wrapper library with MCP tools
- [x] Add CMakeLists.txt for build configuration
- [x] Support shared/static library options

### 7.2 Root Conanfile Integration
- [x] Add `with_proxy_mcp` option (default: False)
- [x] Conditional dependency on kernun-mcp-tools
- [x] Update package_info with library export

### 7.3 Python MCP Client
- [x] Create `modules/security/proxy_mcp_client.py`
- [x] Implement async client with aiohttp
- [x] Support WebSocket and HTTP fallback
- [x] Add FastAPI integration helper
- [x] Create data classes for type safety

### 7.4 Available MCP Tools
| Tool | Description |
|------|-------------|
| `analyze_traffic` | Network traffic analysis with threat detection |
| `inspect_session` | Detailed session inspection (TLS, ciphers) |
| `modify_tls_policy` | TLS/SSL policy configuration |
| `update_proxy_rules` | Firewall and proxy rule management |
| `update_clearweb_database` | Content categorization database |

### Usage Example
```python
from modules.security import ProxyMCPClient

async with ProxyMCPClient("localhost", 3000) as client:
    # Analyze traffic
    result = await client.analyze_traffic(time_range_seconds=300)
    
    # Get TLS policies
    policies = await client.get_tls_policies()
    
    # Update proxy rule
    await client.update_proxy_rules([{
        "rule_id": "block-malware",
        "name": "Block Malware Domains",
        "action": "deny",
        "dest_pattern": "*.malware.com"
    }])
```

---

## CPython Bootstrap Tools (NEW)

### Overview
Shared CPython bootstrap module for Android development tools.

### Features
- [x] Bundled CPython 3.12.7 from GitHub releases
- [x] Multi-platform support (Linux, macOS, Windows)
- [x] Automatic download and caching
- [x] Context manager and CLI interface
- [x] OBD simulator example tool

### Files
| File | Purpose |
|------|---------|
| `android/tools/lib/cpython_bootstrap.py` | Shared bootstrap module |
| `android/tools/bootstrap-obd.py` | OBD-II simulator tool |

---

## Notes for Future Reference

### Why FlatBuffers instead of JSON?
- Binary format is more efficient for embedded systems
- Faster parsing without allocations
- Schema versioning ensures forward/backward compatibility
- Smaller message payloads reduce network bandwidth

### Why ZeroMQ instead of message queues (RabbitMQ, etc.)?
- Lighter weight, no external broker service required
- DEALER-ROUTER pattern naturally distributes work
- Native RPi support, minimal dependencies
- Built-in reconnection logic

### Why FastAPI instead of Flask?
- Native async/await support
- Pydantic validation out-of-the-box
- WebSocket support built-in
- Auto-generated OpenAPI documentation
- Better performance

### Android Implementation Choice (TBD)
- **Native (Kotlin)**: Full control, best performance, steeper learning curve
- **Flutter**: Cross-platform, easier maintenance, good performance for this scope
- Decision pending team feedback

---

## Contributors
- Assigned TBD (awaiting team allocation)
- Reviewed by: Project lead

---

## Change Log
- **v1.0** (2025-01-XX): Initial architecture document. Replaced old ROS2/MCP-heavy design with Lean ZeroMQ+FlatBuffers+FastAPI approach. Approved by user after extensive feedback on RPi-only deployment simplicity.


---

## Repository Cleanup Tasks

### Removing Obsolete Documentation
The following files in `docs/` folder should be removed using Git CLI, as they relate to the old AI-SERVIS/ROS2 architecture and are now superseded by this TODO.md:

```bash
# Remove individual TODO files from old design
git rm docs/TODO-master-list.md
git rm docs/TODO-michal-ci-cd.md
git rm docs/TODO-pavel-architecture.md
git rm docs/TODO-vojtech-implementation.md

# Remove obsolete architecture documentation
git rm docs/ai-servis-universal-proposal.md
git rm docs/core-orchestrator-enhanced.md
git rm docs/implementation-ready-summary.md

# Commit the cleanup
git commit -m 'chore: Remove obsolete architecture documentation from old ROS2/MCP design'
```

**Status**: Manual execution required via Git CLI (GitHub web UI limitations for batch file deletion)
**Priority**: Medium (cleanup task, not blocking feature development)
**Assigned to**: DevOps team lead or project maintainer

---

## MCP Ecosystem Integration (Conan-Based)

### Architecture: Modular Dependency Management

MIA integrates with the MCP ecosystem via **Conan dependency management** (no git submodules). Each component is independently maintained as a fork, versioned in Conan, and composable:

```
sparetools/packages/
├── shared-dev-tools/          # Python reusable tools library
├── tinymcp/                   # C++ tool servers (stdio transport)
├── mcp-server-cpp/            # C++ JSON-RPC server (HTTP/HTTPS)
└── conanfile.py               # Central package definitions

mcp-prompts/
├── src/                       # Python MCP server
└── conanfile.py              # Python package

mcp-transport-telegram/
├── src/                       # Python MCP server
└── conanfile.py              # Python package

mia/
├── conanfile.py              # Declares optional MCP dependencies
├── requirements/
│   ├── base.txt              # core only
│   ├── mcp.txt               # all MCP components
│   └── tools.txt             # TinyMCP tools
└── docker-compose.yml        # Multi-service deployment
```

### Conan Dependency Declaration (mia/conanfile.py)

```python
from conan import ConanFile

class MIAConan(ConanFile):
    name = "mia"
    version = "0.1.0"
    
    # Core dependencies (always included)
    requires = (
        "zeromq/4.3.4",
        "flatbuffers/23.5.26",
    )
    
    # MCP optional dependencies (via profiles)
    options = {
        "with_mcp_tools": [True, False],      # TinyMCP
        "with_mcp_server": [True, False],    # MCPServer.cpp
        "with_mcp_prompts": [True, False],   # mcp-prompts
        "with_telegram": [True, False],      # mcp-transport-telegram
    }
    
    default_options = {
        "with_mcp_tools": False,
        "with_mcp_server": False,
        "with_mcp_prompts": False,
        "with_telegram": False,
    }
    
    def configure(self):
        # Conan recipes for fork/remote packages
        if self.options.with_mcp_tools:
            self.requires.append("tinymcp/0.1.0@sparesparrow/stable")
        if self.options.with_mcp_server:
            self.requires.append("mcp-server-cpp/0.1.0@sparesparrow/stable")
        if self.options.with_mcp_prompts:
            self.requires.append("mcp-prompts/0.1.0@sparesparrow/stable")
        if self.options.with_telegram:
            self.requires.append("mcp-transport-telegram/0.1.0@sparesparrow/stable")
```

### Installation Profiles

**Minimal (RPi with local tools only):**
```bash
conan install . -o mia:with_mcp_tools=True
```

**Full-featured (all MCP components):**
```bash
conan install . -o mia:with_mcp_tools=True -o mia:with_mcp_server=True \
  -o mia:with_mcp_prompts=True -o mia:with_telegram=True
```

**From profiles file:**
```bash
conan install . --profile:build=default --profile:host=rpi_minimal
conan install . --profile:build=default --profile:host=rpi_full
```

### Python Shared Tools (via sparetools)

Reusable Python utilities maintained in `sparetools/packages/shared-dev-tools/`:

```
sparetools/packages/shared-dev-tools/
├── mia_tools/
│   ├── device_registry.py     # Device discovery/management
│   ├── gpio_abstraction.py    # GPIO driver wrappers
│   ├── sensor_drivers.py      # I2C/SPI sensor drivers
│   ├── message_formatting.py  # MCP message helpers
│   └── __init__.py
├── setup.py                   # PyPI package: mia-shared-tools
└── conanfile.py              # Conan recipe version
```

**Usage in MIA:**
```python
# MIA imports from shared-dev-tools
from mia_tools.device_registry import DeviceRegistry
from mia_tools.gpio_abstraction import GPIOController
from mia_tools.sensor_drivers import I2CSensorDriver
```

### Boot Sequence with Conan

```bash
# 1. Install dependencies (with profile)
conan install . --profile:host=rpi_full

# 2. Start MCP components (managed by docker-compose or systemd)
if [ -d "generators/" ]; then
  source ./generators/deactivate_conanbuild.sh
  source ./generators/conanbuild.sh
fi

# 3. Start services in order
systemctl start mcp-prompts        # Prompt catalog
sleep 2
systemctl start tinymcp-gpio       # GPIO tool server
systemctl start tinymcp-sensors    # Sensor tool server
sleep 2
systemctl start mcp-transport-telegram  # Telegram bridge
sleep 2
systemctl start mia                # Main orchestrator
```

### Docker Compose (Multi-service Deployment)

```yaml
# docker-compose.yml - Full deployment
version: '3.8'
services:
  mcp-prompts:
    build: ./mcp-prompts
    ports: ["5555:5555"]
    environment:
      - STORAGE=postgres
      - DB_URL=postgresql://prompts:pass@postgres:5432/mia_prompts
  
  tinymcp-gpio:
    build: ./sparetools/packages/tinymcp
    command: python -m tinymcp.gpio_server --stdio
    
  tinymcp-sensors:
    build: ./sparetools/packages/tinymcp
    command: python -m tinymcp.sensor_server --stdio
    devices:
      - /dev/i2c-1:/dev/i2c-1
  
  mcp-transport-telegram:
    build: ./mcp-transport-telegram
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  
  mia:
    build: .
    ports: ["8000:8000"]
    depends_on:
      - mcp-prompts
      - tinymcp-gpio
      - tinymcp-sensors
      - mcp-transport-telegram
    environment:
      - MCP_PROMPTS_URL=http://mcp-prompts:5555
      - TELEGRAM_MCP_URL=http://mcp-transport-telegram:5556
```

### Phase 1 Task: Setup Conan Infrastructure

- [ ] Create `conanfile.py` in MIA root with optional MCP dependencies
- [ ] Create Conan recipes for each MCP repo fork (in respective repos)
- [ ] Publish recipes to local Conan cache or remote (artifactory/bintray)
- [ ] Create RPi deployment profiles (minimal/full)
- [ ] Create docker-compose.yml (production deployment)
- [ ] Document Conan installation workflow

### Phase 2 Task: Python Shared Tools Library

- [ ] Consolidate device/GPIO/sensor utilities in `sparetools/packages/shared-dev-tools`
- [ ] Create PyPI package: `mia-shared-tools`
- [ ] Publish Conan recipe for shared-dev-tools
- [ ] Update MIA to import from shared-dev-tools instead of local copies

### Benefits of Conan-Based Approach

1. **No Git Submodules**: Clean dependency management
2. **Cross-Repo**: sparetools, mcp-prompts, tinymcp all independently versioned
3. **Flexible Deployments**: RPi minimal vs full via profiles
4. **Reusable Tools**: Python tools in sparetools/shared-dev-tools used by all repos
5. **Production-Ready**: Docker Compose + Conan for enterprise CI/CD
6. **Upstream-Friendly**: Each fork remains independently forkable/upgradable

### See Also
- [SpareTools - Conan Recipes Hub](https://github.com/sparesparrow/sparetools)
- [MCP Prompts - Prompt Catalog](https://github.com/sparesparrow/mcp-prompts)
- [MCP Transport Telegram - Telegram MCP](https://github.com/sparesparrow/mcp-transport-telegram)
