# MIA LED Monitor Service

> **Audience**: Backend developers, hardware integrators

The LED Monitor Service integrates the Arduino LED controller with the MIA ZeroMQ architecture, providing real-time visual feedback for AI states, service health, and vehicle data.

## Overview

The LED Monitor Service:
- Monitors health of all MIA services via ZeroMQ broker
- Controls 23-LED WS2812B strip for visual status indication
- Subscribes to telemetry data for OBD visualization
- Provides AI state animations and emergency override

## LED Zone Allocation

```
LED Index:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22
Function:  [P][S][S][S][S][A][A][A][A][A][A][A][A][A][A][A][B][B][B][N][N][N][N]

Legend:
[P]rivacy/Recording (LED 0)
[S]ervice Health (LEDs 1-4)
[A]I Communication Zone (LEDs 5-16)
[B]ackground Tasks/Sensors (LEDs 17-19)
[N]otification Zone (LEDs 20-22)
```

## Service Architecture

1. **Arduino LED Controller** (`arduino/led_strip_controller/`) — firmware
2. **Python LED Controller** (`apps/rpi-backend/py-api/hardware/led_controller.py`) — high-level interface
3. **LED Monitor Service** (`apps/rpi-backend/py-api/services/led_monitor_service.py`) — ZeroMQ integration

## Installation

```bash
# Install Arduino libraries
arduino-cli lib install "FastLED"
arduino-cli lib install "ArduinoJson"

# Upload firmware
cd arduino/led_strip_controller
./upload.sh

# Enable systemd service
sudo systemctl enable mia-led-monitor
sudo systemctl start mia-led-monitor
```

## Commands

```json
{"cmd": "ai_state", "state": "listening", "priority": 1}
{"cmd": "ai_state", "state": "speaking", "priority": 1}
{"cmd": "service_status", "service": "obd", "status": "error", "priority": 0}
{"cmd": "obd_data", "type": "rpm", "value": 75}
{"cmd": "set_mode", "mode": "drive"}
{"cmd": "emergency", "action": "activate"}
```

## Troubleshooting

- LED strip not working: check 5V power supply and strip connections
- Serial issues: `ls /dev/ttyUSB*`, verify baud rate 115200
- Service health: `systemctl status mia-led-monitor`, check ZeroMQ port 5555
