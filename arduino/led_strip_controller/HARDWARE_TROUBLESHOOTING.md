# LED Hardware Troubleshooting Guide

> **Audience**: Hardware integrators, embedded developers

## Problem: LEDs Not Lighting Up

If the Arduino responds to commands but LEDs don't light up, this is a **hardware connection issue**.

## Step-by-Step Diagnosis

### 1. Verify Power Supply
- **WS2812B LEDs require external 5V power** (Arduino USB power is insufficient for 23 LEDs)
- **Minimum power**: 1.4A (23 LEDs × 60mA per LED at full brightness)
- **Recommended**: 2A+ power supply for safety margin
- **Critical**: Arduino ground (GND) must be connected to LED strip ground (common ground required)

### 2. Verify Data Connection
- **Current firmware uses pin 6**
- **Check**: LED data wire (usually labeled DIN or DI) connected to Arduino pin 6

### 3. Check Wiring
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

### 4. Quick Test Commands

```bash
# Test hardware_test command (should cycle colors)
cd /home/mia/mia
python3 -c "
import serial, time
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
time.sleep(2)
ser.write(b'{\"command\":\"hardware_test\"}\n')
time.sleep(4)
ser.close()
"
```

## Expected Behavior

**If hardware is correct:**
- ✅ Startup flash (3 white flashes when Arduino boots)
- ✅ LEDs respond to `hardware_test` command

**If hardware has issues:**
- ❌ No startup flash
- ❌ Arduino responds but LEDs stay off

## Next Steps

1. If LEDs work with `pin_test.ino`: Update firmware with correct pin number
2. If LEDs don't work: Check power supply and wiring
3. See [QUICK_START.md](QUICK_START.md) for full setup
