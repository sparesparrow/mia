# MIA Raspberry Pi Orchestration Layer

This directory contains the Python-based orchestration and service layer for MIA running on Raspberry Pi.

## Architecture

The Raspberry Pi serves as the central orchestration hub, managing communication between:

- **Hardware peripherals** (Arduino, sensors, GPIO)
- **Android companion app** (via WebSocket/BLE)
- **ESP32 edge devices** (via serial/WiFi)
- **Cloud services** (monitoring, updates)

## Components

### Core Services

#### `api/`
FastAPI-based REST and WebSocket endpoints:
- Device management APIs
- Real-time telemetry streaming
- Command and control interfaces
- System health monitoring

#### `core/`
Shared utilities and messaging infrastructure:
- ZeroMQ broker for inter-process communication
- FlatBuffers message parsing/generation
- Device registry and discovery
- Configuration management

#### `hardware/`
Hardware abstraction layer:
- GPIO control and sensor interfaces
- Arduino serial communication
- Camera and peripheral management
- Hardware health monitoring

#### `services/`
Systemd services for production deployment:
- `mia-api.service` - REST API server
- `mia-broker.service` - ZeroMQ message broker
- `mia-gpio-worker.service` - Hardware control
- `mia-obd-worker.service` - OBD-II processing

## Dependencies

### Python Packages
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
paho-mqtt==1.6.1
pyzmq==25.1.1
flatbuffers==23.5.26
RPi.GPIO==0.7.1
```

### System Dependencies
```bash
sudo apt-get install python3-dev python3-pip
sudo apt-get install libzmq3-dev
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python -m uvicorn api.main:app --reload

# Run message broker
python core/messaging/broker.py
```

### Testing
```bash
# Run unit tests
python -m pytest tests/ -v

# Run integration tests
python test_integration.py

# Test hardware interfaces
python hardware/test_end_to_end.py
```

### Production Deployment
```bash
# Install system services
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable mia-broker
sudo systemctl start mia-broker
```

## Hardware Requirements

- **Raspberry Pi 4B/5** (recommended)
- **GPIO access** for hardware control
- **USB ports** for Arduino/ESP32 communication
- **Camera module** (optional, for computer vision features)
- **WiFi/Ethernet** for network connectivity

## Configuration

### Environment Variables
```bash
export MIA_BROKER_PORT=5555
export MIA_API_PORT=8000
export MIA_LOG_LEVEL=INFO
export MIA_CONFIG_PATH=/etc/mia/
```

### Device Configuration
See `core/registry/device_registry.py` for device configuration and `core/paths.py` for path management.

## Integration with Other Components

### Android App
- Communicates via WebSocket (`ws://raspberry-pi:8000/ws`)
- Receives real-time telemetry and sends commands
- BLE fallback for local communication

### ESP32 Devices
- Serial communication via USB
- WiFi direct connection for distributed setups
- FlatBuffers messages for efficient data transfer

### Arduino Peripherals
- Serial protocol for GPIO control and sensor data
- Interrupt-driven communication for real-time responses
- Hardware handshake for reliability

## Monitoring

### Health Checks
- System resource monitoring
- Hardware interface status
- Network connectivity verification
- Service availability checks

### Logging
- Structured logging with log levels
- Rotation and archival
- Remote logging support (optional)

## Security Considerations

- API authentication and authorization
- Secure WebSocket connections
- Hardware access controls
- Network isolation for sensitive operations