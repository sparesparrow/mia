# MIA Raspberry Pi Implementation

This directory contains the Python-based implementation of MIA for Raspberry Pi, following the Lean Architecture specified in TODO.md.

## Architecture

- **ZeroMQ Broker** (`core/messaging/broker.py`): Message routing using ROUTER-DEALER pattern
- **FastAPI Server** (`api/main.py`): REST API and WebSocket endpoints
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
sudo mkdir -p /opt/ai-servis/rpi
sudo cp -r rpi/* /opt/ai-servis/rpi/
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
```bash
sudo netstat -tulpn | grep 5556
```

3. Verify OBD worker is subscribed:
```bash
sudo journalctl -u mia-obd-worker | grep "Subscribed to telemetry"
```

4. Test ZMQ subscription manually:
```python
import zmq
ctx = zmq.Context()
sub = ctx.socket(zmq.SUB)
sub.connect("tcp://localhost:5556")
sub.subscribe("mcu/telemetry")
while True:
    topic, msg = sub.recv_multipart()
    print(f"Topic: {topic}, Message: {msg}")
```
