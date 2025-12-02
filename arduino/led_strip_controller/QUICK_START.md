# Quick Start Guide: Arduino LED Strip Controller

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
cd /home/sparrow/projects/ai-servis
pip install -r modules/hardware-bridge/requirements.txt

# Verify Arduino is connected
ls -l /dev/ttyUSB0

# Set permissions (if needed)
sudo chmod 666 /dev/ttyUSB0
```

### 3. Test Connection

```bash
# Run test script
python modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0
```

### 4. Use in Python

```python
from modules.hardware_bridge.arduino_led_controller import ArduinoLEDController

controller = ArduinoLEDController("/dev/ttyUSB0")
controller.connect()

# Set all LEDs to blue
controller.set_color(0, 0, 255)

# Start rainbow animation
controller.start_rainbow(speed=10)

controller.disconnect()
```

### 5. MQTT Control (Optional)

```bash
# Start MQTT bridge
python -m modules.hardware_bridge.arduino_led_controller /dev/ttyUSB0 localhost

# Publish MQTT command (in another terminal)
mosquitto_pub -h localhost -t "hardware/arduino/led/set_color" \
  -m '{"r": 255, "g": 0, "b": 0}'
```

### 6. MCP Integration (Optional)

```bash
# Start MCP server
python -m modules.hardware_bridge.arduino_led_mcp /dev/ttyUSB0 8084

# Now AI orchestrator can control LEDs via MCP tools
```

## Common Commands

### Set Color
```python
controller.set_color(255, 0, 0)  # Red
controller.set_color(0, 255, 0)  # Green
controller.set_color(0, 0, 255)  # Blue
```

### Set Brightness
```python
controller.set_brightness(128)  # 50% brightness
controller.set_brightness(255)  # Full brightness
```

### Animations
```python
controller.start_rainbow(speed=10)      # Rainbow cycle
controller.start_chase(255, 0, 0, 100) # Red chase
controller.start_animation("blink", speed=500)  # Blink
```

### Clear
```python
controller.clear()  # Turn off all LEDs
```

## Troubleshooting

**Arduino not found?**
```bash
sudo chmod 666 /dev/ttyUSB0
sudo usermod -a -G dialout $USER  # Then logout/login
```

**LEDs not working?**
- Check LED strip is on pin 6
- Verify power supply (5V, 1.4A+ for 23 LEDs)
- Check wiring connections

**Serial errors?**
- Ensure only one program accesses serial port
- Check baud rate matches (115200)
- Verify Arduino code is uploaded

## Next Steps

- See [README.md](README.md) for detailed documentation
- Check [test_arduino_led.py](../../modules/hardware-bridge/test_arduino_led.py) for examples
- Integrate with AI orchestrator for voice control
