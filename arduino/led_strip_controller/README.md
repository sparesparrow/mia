# Arduino Uno LED Strip Controller

LED strip controller for Arduino Uno that controls 23 programmable 5V LED diodes (WS2812B/NeoPixel compatible) and communicates with Raspberry Pi via USB Serial.

## Hardware Requirements

- **Arduino Uno** (or compatible)
- **WS2812B LED Strip** with 23 LEDs (or NeoPixel compatible)
- **USB Cable** for connecting Arduino to Raspberry Pi
- **Power Supply** for LED strip (5V, sufficient amperage for 23 LEDs)

## Wiring

1. **LED Strip Data Pin**: Connect to Arduino pin 6 (PWM capable)
2. **LED Strip Power**: Connect 5V and GND to appropriate power supply
3. **USB Connection**: Connect Arduino to Raspberry Pi via USB

**Note**: For 23 LEDs, ensure your power supply can provide at least 1.4A (23 LEDs × 60mA max per LED). Use external power supply if Arduino USB power is insufficient.

## Arduino Setup

### Required Libraries

Install the following Arduino libraries via Library Manager:

1. **FastLED** (by Daniel Garcia)
   - Tools → Manage Libraries → Search "FastLED" → Install

2. **ArduinoJson** (by Benoit Blanchon)
   - Tools → Manage Libraries → Search "ArduinoJson" → Install

### Upload Code

1. Open `led_strip_controller.ino` in Arduino IDE
2. Select board: **Tools → Board → Arduino Uno**
3. Select port: **Tools → Port → [Your Arduino Port]**
4. Upload: **Sketch → Upload**

## Communication Protocol

The Arduino communicates via Serial (USB) using JSON commands at 115200 baud.

### Commands

#### Set Color (All LEDs)
```json
{
  "command": "set_color",
  "r": 255,
  "g": 0,
  "b": 0
}
```

#### Set Brightness
```json
{
  "command": "set_brightness",
  "brightness": 128
}
```

#### Set Individual LED
```json
{
  "command": "set_led",
  "led": 5,
  "r": 255,
  "g": 255,
  "b": 0
}
```

#### Start Animation
```json
{
  "command": "animation",
  "animation": "blink",
  "speed": 500
}
```

Available animations:
- `blink` - Blink all LEDs on/off
- `fade` - Fade in/out
- `rainbow` - Rainbow color cycle
- `chase` - Chasing light effect

#### Start Rainbow Animation
```json
{
  "command": "rainbow",
  "speed": 10
}
```

#### Start Chase Animation
```json
{
  "command": "chase",
  "r": 255,
  "g": 0,
  "b": 0,
  "speed": 100
}
```

#### Clear All LEDs
```json
{
  "command": "clear"
}
```

#### Get Status
```json
{
  "command": "status"
}
```

### Responses

All commands return a JSON response:

**Success:**
```json
{
  "status": "color_set",
  "message": "Color set to RGB(255,0,0)",
  "brightness": 128,
  "current_color": {
    "r": 255,
    "g": 0,
    "b": 0
  }
}
```

**Error:**
```json
{
  "status": "error",
  "error_type": "invalid_led",
  "message": "LED index must be 0-22"
}
```

## Raspberry Pi Integration

### Python Module

The Python module `arduino_led_controller.py` provides a high-level interface for controlling the LED strip from Raspberry Pi.

### Usage Example

```python
from modules.hardware_bridge.arduino_led_controller import ArduinoLEDController

# Connect to Arduino
controller = ArduinoLEDController(serial_port="/dev/ttyUSB0")
controller.connect()

# Set all LEDs to red
controller.set_color(255, 0, 0)

# Set brightness
controller.set_brightness(128)

# Set individual LED
controller.set_led(5, 255, 255, 0)

# Start rainbow animation
controller.start_rainbow(speed=10)

# Clear all LEDs
controller.clear()

# Get status
status = controller.get_status()
print(status)

# Disconnect
controller.disconnect()
```

### MQTT Bridge

Run the MQTT bridge to enable MQTT control:

```bash
python -m modules.hardware_bridge.arduino_led_controller /dev/ttyUSB0 localhost
```

This will subscribe to MQTT topics:
- `hardware/arduino/led/set_color`
- `hardware/arduino/led/set_brightness`
- `hardware/arduino/led/set_led`
- `hardware/arduino/led/animation`
- `hardware/arduino/led/rainbow`
- `hardware/arduino/led/chase`
- `hardware/arduino/led/clear`
- `hardware/arduino/led/status`

### MCP Integration

The MCP server provides AI-driven LED control through the Model Context Protocol:

```bash
python -m modules.hardware_bridge.arduino_led_mcp /dev/ttyUSB0 8084
```

Available MCP tools:
- `arduino_led_set_color` - Set all LEDs to a color
- `arduino_led_set_brightness` - Set brightness
- `arduino_led_set_led` - Set individual LED
- `arduino_led_animation` - Start animation
- `arduino_led_clear` - Clear all LEDs
- `arduino_led_status` - Get status

## Troubleshooting

### Arduino Not Detected

1. Check USB connection
2. Verify USB cable supports data (not just power)
3. Check permissions: `sudo chmod 666 /dev/ttyUSB0`
4. Add user to dialout group: `sudo usermod -a -G dialout $USER`

### LEDs Not Working

1. Verify LED strip is connected to pin 6
2. Check power supply (5V, sufficient amperage)
3. Verify LED strip type matches (WS2812B)
4. Check wiring connections

### Serial Communication Errors

1. Verify baud rate matches (115200)
2. Check for multiple programs accessing serial port
3. Ensure Arduino is powered and code is uploaded
4. Check serial port path: `ls -l /dev/ttyUSB*`

### LED Colors Incorrect

1. Check COLOR_ORDER in Arduino code (may need GRB, RGB, etc.)
2. Verify LED strip manufacturer specifications
3. Test with known good color values

## Configuration

### Change LED Pin

Edit `led_strip_controller.ino`:

```cpp
#define LED_PIN 6  // Change to desired pin
```

### Change Number of LEDs

Edit `led_strip_controller.ino`:

```cpp
#define NUM_LEDS 23  // Change to your LED count
```

### Change Color Order

Edit `led_strip_controller.ino`:

```cpp
#define COLOR_ORDER GRB  // Options: GRB, RGB, BGR, etc.
```

## License

Part of the AI-SERVIS Universal project. See main LICENSE file.
