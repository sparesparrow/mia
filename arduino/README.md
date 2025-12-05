# Arduino Hardware Integration

This directory contains Arduino code for hardware integration with the MIA Universal platform.

## Available Modules

### LED Strip Controller

- **Location**: `led_strip_controller/`
- **Description**: Controls WS2812B/NeoPixel LED strips via Serial communication
- **Hardware**: Arduino Uno + WS2812B LED strip (23 LEDs)
- **Communication**: USB Serial (ttyUSB0) with Raspberry Pi

See [LED Strip Controller README](led_strip_controller/README.md) for detailed documentation.

## Integration with Raspberry Pi

All Arduino modules communicate with Raspberry Pi via USB Serial connection:

1. **Serial Communication**: JSON commands over USB Serial (115200 baud)
2. **Python Bridge**: Python modules in `modules/hardware-bridge/` handle communication
3. **MQTT Support**: Optional MQTT bridge for distributed control
4. **MCP Integration**: MCP servers for AI-driven control

## Adding New Arduino Modules

To add a new Arduino module:

1. Create new directory: `arduino/[module_name]/`
2. Add `.ino` file with Arduino code
3. Create Python bridge module in `modules/hardware-bridge/`
4. Add MCP integration if needed
5. Document in module README

## Common Patterns

### Serial Communication

All Arduino modules use JSON over Serial:

```cpp
// Arduino side
StaticJsonDocument<512> doc;
deserializeJson(doc, Serial.readStringUntil('\n'));
String cmd = doc["command"] | "";

// Send response
StaticJsonDocument<512> response;
response["status"] = "ok";
serializeJson(response, Serial);
Serial.println();
```

### Python Bridge

```python
import serial
import json

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1.0)

command = {"command": "set_color", "r": 255, "g": 0, "b": 0}
ser.write((json.dumps(command) + "\n").encode())
response = json.loads(ser.readline().decode())
```

## License

Part of the MIA Universal project. See main LICENSE file.
