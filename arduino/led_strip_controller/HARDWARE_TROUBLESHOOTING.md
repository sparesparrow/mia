# LED Hardware Troubleshooting Guide

## Problem: LEDs Not Lighting Up

If the Arduino responds to commands but LEDs don't light up, this is a **hardware connection issue**.

## Step-by-Step Diagnosis

### 1. Verify Power Supply
- **WS2812B LEDs require external 5V power** (Arduino USB power is insufficient for 23 LEDs)
- **Minimum power**: 1.4A (23 LEDs × 60mA per LED at full brightness)
- **Recommended**: 2A+ power supply for safety margin
- **Check**: LED strip should have separate power input (VCC/GND) connected to external supply
- **Critical**: Arduino ground (GND) must be connected to LED strip ground (common ground required)

### 2. Verify Data Connection
- **Current firmware uses pin 6**
- **Check**: LED data wire (usually labeled DIN or DI) connected to Arduino pin 6
- **Test**: Try different pins if pin 6 doesn't work (common: 3, 5, 9, 10, 11)

### 3. Test Different Pins
If pin 6 doesn't work, test other pins:

1. Edit `pin_test.ino` and change `#define TEST_PIN 6` to another pin (e.g., `#define TEST_PIN 3`)
2. Upload the sketch: `cd ai-servis/arduino/led_strip_controller && arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno .`
3. Watch for LEDs lighting up
4. If LEDs work, update `led_strip_controller.ino` with the correct pin

### 4. Verify LED Strip Type
- **Firmware expects**: WS2812B
- **Check**: Your LED strip model number
- **Alternative types**: WS2811, WS2813, SK6812 (may need different configuration)
- **Color order**: Firmware uses GRB, but some strips use RGB (try changing `COLOR_ORDER`)

### 5. Check Wiring
**Correct wiring:**
```
LED Strip          Arduino
--------          --------
VCC (5V)    ->    External 5V power supply (+)
GND         ->    Arduino GND (common ground!)
DIN/DI      ->    Arduino Pin 6 (data)
```

**Common mistakes:**
- ❌ LED power connected to Arduino 5V pin (insufficient current)
- ❌ Missing ground connection between Arduino and LED strip
- ❌ Data wire on wrong pin
- ❌ Loose connections

### 6. Test with Simple Sketch
Upload `pin_test.ino` to verify hardware works independently of serial commands.

## Quick Test Commands

```bash
# Test hardware test command (should cycle colors)
cd /home/mia/ai-servis
python3 -c "import serial; import time; ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2); time.sleep(2); ser.write(b'{\"command\":\"hardware_test\"}\n'); ser.flush(); time.sleep(4); ser.close()"

# Test maximum brightness and white
python3 -c "import serial; import time; ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2); time.sleep(2); ser.write(b'{\"command\":\"set_brightness\",\"brightness\":255}\n'); time.sleep(0.3); ser.write(b'{\"command\":\"set_color\",\"r\":255,\"g\":255,\"b\":255}\n'); time.sleep(1); ser.close()"
```

## Expected Behavior

**If hardware is correct:**
- ✅ Startup flash (3 white flashes when Arduino boots)
- ✅ LEDs respond to `hardware_test` command
- ✅ LEDs light up with maximum brightness (255)

**If hardware has issues:**
- ❌ No startup flash
- ❌ No response to any commands
- ❌ Arduino responds but LEDs stay off

## Next Steps

1. **If LEDs work with pin_test.ino**: Update firmware with correct pin number
2. **If LEDs don't work with pin_test.ino**: Check power supply and wiring
3. **If unsure which pin**: Test pins 3, 5, 6, 9, 10, 11 one by one


