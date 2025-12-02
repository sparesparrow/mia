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
