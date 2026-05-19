# MIA Raspberry Pi Implementation

> **Audience**: Backend developers, deployment engineers

This directory contains the Python-based implementation of MIA for Raspberry Pi, following the Lean Architecture specified in ARCHITECTURE.md.

## Architecture

- **ZeroMQ Broker** (`apps/rpi-backend/shared/messaging/broker.py`): Message routing using ROUTER-DEALER pattern on port 5555
- **FastAPI Server** (`api/main.py`): REST API and WebSocket endpoints on port 8000
- **GPIO Worker** (`hardware/gpio_worker.py`): Hardware control via GPIO pins
- **Serial Bridge** (`hardware/serial_bridge.py`): ESP32/Arduino serial to ZeroMQ bridge
- **OBD Worker** (`services/obd_worker.py`): ELM327 OBD-II simulator with dynamic PID responses

## Components

### ZeroMQ Broker
- Listens on port 5555
- Routes messages between FastAPI server and workers
- Handles worker registration and message distribution

### FastAPI Server
- REST API on port 8000
- Endpoints:
  - `GET /devices` - List connected devices
  - `POST /command` - Send device commands
  - `GET /telemetry` - Get sensor readings
  - `GET /status` - System health
  - `POST /gpio/configure` - Configure GPIO pin
  - `POST /gpio/set` - Set GPIO pin value
  - `GET /gpio/{pin}` - Get GPIO pin value
  - `WS /ws` - WebSocket for real-time telemetry

### GPIO Worker
- Connects to ZeroMQ broker
- Controls Raspberry Pi GPIO pins
- Falls back to simulation mode if GPIO libraries unavailable

### Serial Bridge
- Reads JSON telemetry from ESP32/Arduino via USB Serial
- Publishes telemetry to ZeroMQ PUB socket (port 5556) on topic `mcu/telemetry`
- Auto-detects serial ports (`/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
- Handles reconnection logic; falls back to mock data generation when hardware unavailable

### OBD Worker (ELM327 Simulator)
- Implements Digital Twin architecture for OBD-II simulation
- Subscribes to hardware telemetry via PUB/SUB (port 5556)
- Registers with ZeroMQ broker (port 5555) for command/control
- Runs ELM327 emulator with dynamic PID responses based on real-time hardware input

### Vehicle OBD-II Integration

**Primary prototype: Audi A4 B3 Cabriolet (2004)**

MIA connects to vehicles via ELM327 OBD-II adapter for read-only telemetry and diagnostics.

#### Quick Start
```bash
# Start core OBD services
sudo systemctl start zmq-broker mia-serial-bridge mia-obd-worker

# Test with mock mode (no vehicle needed)
ELM_MOCK=1 python3 -m pytest tests/ -m automotive
```

#### Supported PIDs
- Standard OBD-II: RPM, Speed, Coolant Temp, Fuel Level, Engine Load
- VAG/Audi read-only: VIN (DID F190), DTC summary (service 0x19)
- PSA-specific (legacy Citroën bridge): DPF Soot, Oil Temp, Eolys Level

See [docs/automotive/raspberry-pi-audi-integration.md](../../../docs/automotive/raspberry-pi-audi-integration.md) for Audi integration.

## Installation

### Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev libzmq3-dev
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

### Manual Service Setup

```bash
# Core services
sudo systemctl enable zmq-broker mia-api mia-gpio-worker
sudo systemctl start zmq-broker mia-api mia-gpio-worker

# OBD services (optional)
sudo systemctl enable mia-serial-bridge mia-obd-worker
sudo systemctl start mia-serial-bridge mia-obd-worker
```

## Service Management

```bash
# Check status
sudo systemctl status zmq-broker mia-api mia-gpio-worker mia-serial-bridge mia-obd-worker

# View logs
sudo journalctl -u mia-api -f
sudo journalctl -u mia-obd-worker -f
```

## Testing

```bash
# Health check
curl http://localhost:8000/status

# Configure GPIO pin 18 as output
curl -X POST http://localhost:8000/gpio/configure \
  -H "Content-Type: application/json" \
  -d '{"pin": 18, "direction": "output"}'
```

## API Documentation

Once the FastAPI server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Services won't start
```bash
sudo journalctl -u zmq-broker -n 50
sudo journalctl -u mia-api -n 50
```

### GPIO not working
```bash
sudo usermod -a -G gpio $USER
```

### Serial bridge not detecting device
```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
sudo usermod -a -G dialout $USER
```

### ZeroMQ connection errors

Ensure broker is running before starting other services:
```bash
sudo systemctl start zmq-broker
sleep 2
sudo systemctl start mia-api mia-gpio-worker
```
