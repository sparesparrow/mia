# MIA Universal: Multi-Platform AI Assistant

MIA Universal is a comprehensive AI-powered voice-controlled car upgrade system with multi-platform support, Model Context Protocol (MCP) integration, and advanced orchestration capabilities.

## 🚀 Quick Start

### Bootstrap Installation

Choose your preferred bootstrap method:

```bash
# Option 1: Direct Python bootstrap (recommended)
python3 complete-bootstrap.py

# Option 2: Shell-based bootstrap
./tools/bootstrap.sh

# Option 3: Initialize existing environment
./tools/init.sh
```

### Repository Configuration

Configure package repositories:

```bash
# Interactive setup
./tools/repo-config.sh setup

# Or configure specific repositories
export CLOUDSMITH_USERNAME="your_username"
export CLOUDSMITH_API_KEY="your_api_key"
./tools/repo-config.sh cloudsmith
```

### Start the System

```bash
# Install dependencies
conan install . --build=missing -r sparetools

# Start core orchestrator
python3 modules/core-orchestrator/main.py
```

## 🏗️ Architecture

MIA Universal implements a distributed microservices architecture with MCP-based communication:

### Core Components

- **MCP Framework** (`modules/mcp_framework.py`): WebSocket-based Model Context Protocol implementation
- **Core Orchestrator** (`modules/core-orchestrator/`): Central coordination service with NLP processing
- **Audio Assistant** (`modules/ai-audio-assistant/`): Voice processing and TTS services
- **Platform Controllers**: Hardware abstraction for different platforms (RPi, ESP32, Android)
- **Communication Services**: Multi-channel messaging and notifications

## 📦 Package Management

### Conan Integration
MIA uses Conan for cross-platform C++ dependency management:

```bash
# Install all dependencies
conan install . --build=missing -r sparetools

# Build C++ components
cd platforms/cpp && cmake --build build
```

### Repository Support
- **Cloudsmith**: Primary repository for MIA packages
- **GitHub Packages**: Fallback repository with GitHub integration
- **Conan Center**: Public C++ libraries

### Bootstrap System
Three bootstrap methods for different deployment scenarios:

1. **Complete Bootstrap** (`complete-bootstrap.py`): Direct downloads, zero external dependencies
2. **Shell Bootstrap** (`tools/bootstrap.sh`): System package managers, fast installation
3. **Docker Bootstrap**: Containerized, reproducible environments

## 🔧 Development Workflow

### Environment Setup
```bash
# Bootstrap development environment
python3 complete-bootstrap.py

# Initialize project
./tools/init.sh --dev

# Configure repositories
./tools/repo-config.sh setup
```

### Running Tests
```bash
# Python tests
python3 -m pytest tests/ -v

# Integration tests
python3 test_orchestrator.py

# OBD simulator tests
./scripts/test-obd-simulator.sh
```

### Building Components
```bash
# C++ platforms
conan install . && conan build .

# Android APK
cd android && ./gradlew assembleDebug

# ESP32 firmware
cd esp32 && idf.py build
```

## 🔌 MCP (Model Context Protocol) Integration

### Enhanced WebSocket Transport
- **Heartbeat monitoring**: Automatic connection health checks
- **Retry logic**: Robust reconnection with exponential backoff
- **Timeout handling**: Configurable timeouts for reliability
- **Error recovery**: Comprehensive error handling and logging

### Core Orchestrator Features
- **Natural Language Processing**: Intent recognition and command parsing
- **Service Discovery**: Automatic MCP service registration and health monitoring
- **Multi-platform Routing**: Intelligent command routing across different platforms
- **Real-time Communication**: WebSocket-based real-time updates

### Available Services
- **ai-audio-assistant**: Voice processing, TTS, audio control
- **ai-platform-linux**: Linux system control and automation
- **ai-communications**: Multi-channel messaging (SMS, email, notifications)
- **ai-home-automation**: Smart home device control
- **ai-maps-navigation**: GPS navigation and routing

## 📱 Platform Support

### Android Integration
- **Kotlin/Compose**: Modern Android development
- **MCP Bridge**: Seamless communication with backend services
- **Real-time UI**: Live updates from vehicle sensors

### ESP32 Firmware
- **ESP-IDF**: Official Espressif development framework
- **BPM Detection**: Real-time audio beat detection
- **WiFi/Bluetooth**: Wireless communication protocols

### Raspberry Pi Services
- **Python Services**: Microservices architecture
- **Hardware Control**: GPIO, I2C, SPI interfaces
- **OBD-II Integration**: Vehicle diagnostic communication

## 🔒 Security & Compliance

### Built-in Security
- **CodeQL Analysis**: Automated vulnerability detection
- **Trivy Scanning**: Container and filesystem security
- **Bandit**: Python security linting
- **OWASP Checks**: Web application security

### Compliance Features
- **GDPR**: Data protection and privacy measures
- **Automotive Security**: Vehicle-specific security requirements
- **Audit Logging**: Comprehensive security event logging
  - `POST /gpio/set` - Set GPIO pin value
  - `GET /gpio/{pin}` - Get GPIO pin value
  - `WS /ws` - WebSocket for real-time telemetry

### GPIO Worker
- Connects to ZeroMQ broker
- Controls Raspberry Pi GPIO pins
- Supports digital input/output
- Falls back to simulation mode if GPIO libraries unavailable

### Serial Bridge
- Reads JSON telemetry from ESP32/Arduino via USB Serial
- Publishes telemetry to ZeroMQ PUB socket (port 5556) on topic `mcu/telemetry`
- Auto-detects serial ports (`/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
- Handles reconnection logic for robust operation
- Falls back to mock data generation when hardware unavailable

### OBD Worker (ELM327 Simulator)
- Implements Digital Twin architecture for OBD-II simulation
- Subscribes to hardware telemetry via PUB/SUB (port 5556)
- Registers with ZeroMQ broker (port 5555) for command/control
- Runs ELM327 emulator with dynamic PID responses based on real-time hardware input
- Maps MCU potentiometer values to engine parameters (RPM, speed, coolant temp)

### Citroën OBD-II Bridge

The Citroën bridge connects to PSA vehicles via ELM327 OBD-II adapter.

#### Quick Start
```bash
# Deploy service
sudo cp rpi/services/mia-citroen-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mia-citroen-bridge

# Test with mock mode
ELM_MOCK=1 python3 agents/citroen_bridge.py

# Start real service
sudo systemctl start mia-citroen-bridge
```

#### Supported PIDs
- Standard: RPM, Speed, Coolant Temp
- PSA-specific: DPF Soot, Oil Temp, Eolys Level

See [docs/automotive/citroen-integration.md](../docs/automotive/citroen-integration.md) for full documentation.

## Installation

### Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libzmq3-dev
```

### Python Packages

```bash
pip3 install -r requirements.txt
```

## Deployment

Use the main deployment script:

```bash
sudo ./scripts/deploy-raspberry-pi.sh
```

This will:
1. Install all dependencies
2. Build C++ components
3. Install Python services
4. Create systemd services
5. Enable services to start on boot

## Manual Setup

### 1. Install Python dependencies

```bash
pip3 install -r rpi/requirements.txt
```

### 2. Copy files to installation directory

```bash
sudo mkdir -p /opt/mia
sudo cp -r . /opt/mia/
```

### 3. Install systemd services

```bash
sudo cp rpi/services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 4. Enable and start services

```bash
# Core services
sudo systemctl enable zmq-broker mia-api mia-gpio-worker
sudo systemctl start zmq-broker mia-api mia-gpio-worker

# OBD Simulator services (optional)
sudo systemctl enable mia-serial-bridge mia-obd-worker
sudo systemctl start mia-serial-bridge mia-obd-worker
```

## Service Management

### Start services

```bash
sudo systemctl start zmq-broker
sudo systemctl start mia-api
sudo systemctl start mia-gpio-worker
sudo systemctl start mia-serial-bridge
sudo systemctl start mia-obd-worker
```

### Stop services

```bash
sudo systemctl stop zmq-broker
sudo systemctl stop mia-api
sudo systemctl stop mia-gpio-worker
sudo systemctl stop mia-obd-worker
sudo systemctl stop mia-serial-bridge
```

### Check status

```bash
sudo systemctl status zmq-broker
sudo systemctl status mia-api
sudo systemctl status mia-gpio-worker
sudo systemctl status mia-serial-bridge
sudo systemctl status mia-obd-worker
```

### View logs

```bash
sudo journalctl -u zmq-broker -f
sudo journalctl -u mia-api -f
sudo journalctl -u mia-gpio-worker -f
sudo journalctl -u mia-serial-bridge -f
sudo journalctl -u mia-obd-worker -f
```

## Testing

### Test API endpoints

```bash
# Health check
curl http://localhost:8000/status

# List devices
curl http://localhost:8000/devices

# Configure GPIO pin 18 as output
curl -X POST http://localhost:8000/gpio/configure \
  -H "Content-Type: application/json" \
  -d '{"pin": 18, "direction": "output"}'

# Set GPIO pin 18 to HIGH
curl -X POST http://localhost:8000/gpio/set \
  -H "Content-Type: application/json" \
  -d '{"pin": 18, "value": true}'

# Get GPIO pin 18 value
curl http://localhost:8000/gpio/18
```

### Test OBD Simulator

The OBD simulator creates a "Digital Twin" where physical controls (ESP32/Arduino potentiometers) drive OBD-II PID values in real-time.

#### Hardware Setup

1. **Flash ESP32/Arduino** with the following firmware:

```cpp
void setup() { 
  Serial.begin(115200); 
}

void loop() {
  int pot1 = analogRead(A0); // RPM Input (0-1023)
  int pot2 = analogRead(A1); // Speed Input (0-1023)
  
  // Send JSON formatted line
  Serial.print("{\"pot1\":");
  Serial.print(pot1);
  Serial.print(", \"pot2\":");
  Serial.print(pot2);
  Serial.println("}");
  
  delay(100); // 10Hz update rate
}
```

2. **Connect ESP32/Arduino** to Raspberry Pi via USB

3. **Start services** (serial bridge will auto-detect the device):

```bash
sudo systemctl start zmq-broker
sudo systemctl start mia-serial-bridge
sudo systemctl start mia-obd-worker
```

#### Verify Telemetry Flow

Check that serial bridge is receiving data:

```bash
sudo journalctl -u mia-serial-bridge -f
```

You should see log entries showing telemetry being published.

#### Connect OBD Scanner

The ELM327 emulator creates a virtual serial port (PTY). Check logs to find the PTY path:

```bash
sudo journalctl -u mia-obd-worker | grep -i pty
```

Connect your OBD diagnostic tool to this PTY. As you turn the potentiometers on the ESP32, the RPM and speed values in the OBD responses will update in real-time.

#### Manual Testing

Test serial bridge directly:

```bash
python3 rpi/hardware/serial_bridge.py --port /dev/ttyUSB0
```

Test OBD worker directly:

```bash
python3 rpi/services/obd_worker.py
```

### Test WebSocket

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(test_websocket())
```

## API Documentation

Once the FastAPI server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Implementation Status

### Phase 1: Foundation ✅
- [x] Project structure
- [x] ZeroMQ messaging broker (ROUTER-DEALER)
- [x] Message handlers

### Phase 2: Hardware Integration ✅
- [x] GPIO control worker
- [x] Hardware abstraction layer

### Phase 3: FastAPI & Remote Control ✅
- [x] REST API endpoints
- [x] WebSocket server
- [x] Request validation (Pydantic)

### Phase 6: Deployment ✅
- [x] Systemd services
- [x] Auto-start on boot
- [x] Deployment script

### Phase 7: OBD Simulator (Digital Twin) ✅
- [x] Serial bridge for ESP32/Arduino communication
- [x] OBD worker with ELM327 emulator integration
- [x] Dynamic PID responses based on hardware telemetry
- [x] ZeroMQ PUB/SUB telemetry distribution
- [x] Hardware-in-the-loop simulation architecture

## Next Steps

- [ ] Complete ELM327-emulator library integration (PTY creation)
- [ ] Add FlatBuffers schema support
- [ ] Add sensor drivers (I2C/SPI)
- [ ] Implement device registry
- [ ] Add authentication/authorization
- [ ] Add comprehensive logging
- [ ] Performance optimization
- [ ] OBD-II PID response validation

## Troubleshooting

### Services won't start

Check logs:
```bash
sudo journalctl -u zmq-broker -n 50
sudo journalctl -u mia-api -n 50
sudo journalctl -u mia-gpio-worker -n 50
```

### GPIO not working

1. Check permissions:
```bash
ls -l /dev/gpiochip*
```

2. Ensure running as root or user in gpio group:
```bash
sudo usermod -a -G gpio $USER
```

3. Check if GPIO libraries are installed:
```bash
python3 -c "import RPi.GPIO; print('RPi.GPIO available')"
python3 -c "import gpiozero; print('gpiozero available')"
```

### Port already in use

```bash
sudo netstat -tulpn | grep -E "5555|8000"
```

### ZeroMQ connection errors

Ensure broker is running before starting other services:
```bash
sudo systemctl start zmq-broker
sleep 2
sudo systemctl start mia-api mia-gpio-worker
```

### Serial bridge not detecting device

1. Check if device is connected:
```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

2. Check permissions:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in, or use newgrp dialout
```

3. Specify port manually:
```bash
sudo systemctl edit mia-serial-bridge
# Add:
# [Service]
# ExecStart=
# ExecStart=/usr/bin/python3 /opt/ai-servis/rpi/hardware/serial_bridge.py --port /dev/ttyUSB0
```

4. Test serial connection manually:
```bash
python3 -c "import serial; s=serial.Serial('/dev/ttyUSB0', 115200); print(s.readline())"
```

### OBD worker not receiving telemetry

1. Verify serial bridge is publishing:
```bash
sudo journalctl -u mia-serial-bridge | grep "Published telemetry"
```

2. Check ZeroMQ PUB socket is bound:
## 🔄 CI/CD Pipeline

### Workflow Architecture
MIA uses a comprehensive multi-platform CI/CD pipeline:

- **Main Pipeline** (`main.yml`): Complete build, test, and deployment
- **Docker Builds** (`docker-multiplatform.yml`): Multi-architecture container builds
- **ESP32 Builds** (`esp32.yml`): Firmware compilation and testing
- **Web Deployment** (`build-web.yml`): Frontend deployment to AWS

### Quality Gates
- **Security Scanning**: Automated vulnerability detection
- **Code Quality**: Linting, type checking, and formatting
- **Integration Tests**: End-to-end system validation
- **Performance Testing**: Load and stress testing

## 📚 Documentation

### Developer Resources
- **[Bootstrap Guide](docs/BOOTSTRAP_COMPARISON.md)**: Comprehensive bootstrap documentation
- **[Repository Switching](docs/REPOSITORY_SWITCHING.md)**: Package repository management
- **[API Documentation](docs/API.md)**: REST and WebSocket API reference
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Production deployment instructions

### Architecture Documentation
- **[MCP Protocol](docs/MCP_PROTOCOL.md)**: Model Context Protocol implementation
- **[Platform Integration](docs/PLATFORM_INTEGRATION.md)**: Platform-specific guides
- **[Security](docs/SECURITY.md)**: Security architecture and compliance

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Bootstrap your environment: `python3 complete-bootstrap.py`
3. Configure repositories: `./tools/repo-config.sh setup`
4. Install dependencies: `conan install . --build=missing`
5. Run tests: `python3 -m pytest`

### Code Standards
- **Python**: Black formatting, isort imports, mypy type checking
- **C++**: CMake builds, clang-format, cppcheck analysis
- **Kotlin**: Spotless formatting, Detekt linting
- **Documentation**: Markdown with Mermaid diagrams

### Commit Guidelines
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Reference issues: `fixes #123`
- Keep commits focused and atomic

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **ESP32 Community**: Firmware development support
- **Conan Team**: Cross-platform package management
- **MCP Contributors**: Model Context Protocol development
- **Open Source Community**: Libraries and tools that make this possible

---

**Built with ❤️ for the automotive AI revolution**
