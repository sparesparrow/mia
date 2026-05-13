# Quick Start Guide: Arduino LED Strip Controller

> **Audience**: Hardware integrators, embedded developers

## Overview

This implementation provides a complete LED strip controller system:
- **Arduino Uno** controls 23 WS2812B LEDs via USB Serial
- **Raspberry Pi** communicates with Arduino via `/dev/ttyUSB0`
- **MQTT/MCP Integration** for AI-driven control

## Quick Setup (5 minutes)

### 1. Arduino Setup

```bash
# Install required libraries in Arduino IDE:
# - FastLED (by Daniel Garcia)
# - ArduinoJson (by Benoit Blanchon)

# Upload led_strip_controller.ino to Arduino Uno
# Connect LED strip data pin to Arduino pin 6
```

### 2. Raspberry Pi Setup

```bash
# Install Python dependencies
cd /opt/mia
pip install -r modules/hardware-bridge/requirements.txt

# Verify Arduino is connected
ls -l /dev/ttyUSB0

# Set permissions (if needed)
sudo usermod -a -G dialout $USER
```

### 3. Test Connection

```bash
python modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0
```

### 4. Use in Python

```python
from modules.hardware_bridge.arduino_led_controller import ArduinoLEDController

controller = ArduinoLEDController("/dev/ttyUSB0")
controller.connect()
controller.set_color(0, 0, 255)  # All LEDs blue
controller.start_rainbow(speed=10)
controller.disconnect()
```

### 5. MQTT Control (Optional)

```bash
# Start MQTT bridge
python -m modules.hardware_bridge.arduino_led_controller /dev/ttyUSB0 localhost

# Publish MQTT command
mosquitto_pub -h localhost -t "hardware/arduino/led/set_color" \
  -m '{"r": 255, "g": 0, "b": 0}'
```

## Troubleshooting

- Arduino not found: `sudo chmod 666 /dev/ttyUSB0`
- LEDs not working: check LED strip on pin 6, verify 5V 1.4A+ power supply
- Serial errors: ensure only one program accesses serial port, baud rate 115200

See [HARDWARE_TROUBLESHOOTING.md](HARDWARE_TROUBLESHOOTING.md) for detailed diagnosis.
