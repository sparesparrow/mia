# Upload Instructions for Arduino LED Strip Controller

## Method 1: Using Arduino IDE (Recommended - Easiest)

### Step 1: Install Arduino IDE
```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install arduino

# Or download from: https://www.arduino.cc/en/software
```

### Step 2: Install Required Libraries
1. Open Arduino IDE
2. Go to **Tools → Manage Libraries**
3. Search and install:
   - **FastLED** (by Daniel Garcia)
   - **ArduinoJson** (by Benoit Blanchon)

### Step 3: Upload Code
1. Open `led_strip_controller.ino` in Arduino IDE
2. Select board: **Tools → Board → Arduino AVR Boards → Arduino Uno**
3. Select port: **Tools → Port → /dev/ttyUSB0** (or your Arduino port)
4. Click **Sketch → Upload** (or press Ctrl+U)
5. Wait for "Done uploading" message

### Step 4: Verify Upload
1. Open Serial Monitor: **Tools → Serial Monitor**
2. Set baud rate to **115200**
3. You should see: `{"status":"ready","message":"LED strip controller initialized"}`

## Method 2: Using Arduino CLI (Command Line)

### Install Arduino CLI
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/
arduino-cli version  # Verify installation
```

### Upload Using Script
```bash
cd arduino/led_strip_controller
./upload.sh
```

### Or Upload Manually
```bash
# Install core and libraries
arduino-cli core update-index
arduino-cli core install arduino:avr
arduino-cli lib install "FastLED"
arduino-cli lib install "ArduinoJson"

# Compile and upload
arduino-cli compile --fqbn arduino:avr:uno .
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno .
```

## Method 3: Using PlatformIO (Advanced)

If you use PlatformIO:

```bash
# Install PlatformIO
pip install platformio

# Navigate to sketch directory
cd arduino/led_strip_controller

# Upload
pio run --target upload --upload-port /dev/ttyUSB0
```

## Troubleshooting

### Permission Denied
```bash
sudo chmod 666 /dev/ttyUSB0
# Or add user to dialout group (permanent fix)
sudo usermod -a -G dialout $USER
# Then logout and login again
```

### Board Not Found
```bash
# List available boards
arduino-cli board list

# Or in Arduino IDE, check Tools → Port
```

### Upload Failed
1. Press reset button on Arduino just before upload
2. Check USB cable (must support data, not just power)
3. Try different USB port
4. Verify board selection matches your Arduino model

### Libraries Not Found
- Ensure libraries are installed in Arduino IDE Library Manager
- Check library names match exactly: "FastLED" and "ArduinoJson"
- Restart Arduino IDE after installing libraries

## Verify Upload Success

After uploading, test the connection:

```bash
# Test with Python script
python modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0

# Or send test command via serial
echo '{"command":"status"}' > /dev/ttyUSB0
cat /dev/ttyUSB0
```

Expected response:
```json
{
  "status": "ok",
  "brightness": 128,
  "current_color": {"r": 255, "g": 255, "b": 255},
  "animation": "none",
  "num_leds": 23
}
```

## Next Steps

Once uploaded successfully:
1. Test LED control: `python modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0`
2. Start MQTT bridge: `python -m modules.hardware_bridge.arduino_led_controller /dev/ttyUSB0 localhost`
3. Integrate with MCP: `python -m modules.hardware_bridge.arduino_led_mcp /dev/ttyUSB0 8084`
