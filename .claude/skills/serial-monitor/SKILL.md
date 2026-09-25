---
name: serial-monitor
description: Monitor and debug serial devices (ESP32, Arduino, embedded MCUs). Capture serial output, parse logs, detect errors/crashes, flash firmware via PlatformIO. Use for ESP32 debugging, serial log analysis, firmware upload monitoring, and integration testing between embedded devices and host systems. Supports subagent-driven log analysis.
---

# Serial Monitor Skill

Monitor, debug, and analyze serial output from embedded devices (ESP32, Arduino, etc.) with subagent-driven log analysis.

## Quick Reference

### List Serial Devices
```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

### Monitor Serial Output
```bash
# With timeout (capture N seconds)
timeout 30 cat /dev/ttyUSB0 > /tmp/serial-log.txt 2>&1

# With minicom (interactive)
minicom -D /dev/ttyUSB0 -b 115200

# With screen
screen /dev/ttyUSB0 115200

# With PlatformIO
cd <project_dir> && pio device monitor --baud 115200
```

### Flash Firmware (ESP32/Arduino via PlatformIO)
```bash
cd <project_dir>
pio run --target upload --upload-port /dev/ttyUSB0
pio device monitor --baud 115200  # Then monitor
```

### Flash + Monitor (one shot)
```bash
cd <project_dir>
pio run --target upload --upload-port /dev/ttyUSB0 && \
  timeout 30 pio device monitor --baud 115200 > /tmp/flash-log.txt 2>&1
```

## Serial Device Detection

### Identify Connected Devices
```bash
# List all serial devices with details
for dev in /dev/ttyUSB* /dev/ttyACM*; do
  [ -e "$dev" ] || continue
  info=$(udevadm info -q property "$dev" 2>/dev/null | grep -E "ID_MODEL=|ID_VENDOR=|ID_SERIAL_SHORT=")
  echo "$dev: $info"
done
```

### Common Device Mappings
| Device | Typical Port | Baud Rate |
|--------|-------------|-----------|
| ESP32 (CP2102) | /dev/ttyUSB0 | 115200 |
| ESP32-S3 (native USB) | /dev/ttyACM0 | 115200 |
| Arduino Uno/Mega | /dev/ttyACM0 | 9600 |
| Arduino Nano (CH340) | /dev/ttyUSB0 | 9600 |
| ELM327 OBD-II | /dev/ttyUSB0 | 38400 |

### Set Permissions
```bash
sudo usermod -a -G dialout $USER  # Add user to dialout group
sudo chmod 666 /dev/ttyUSB0       # Quick fix (non-persistent)
```

## Serial Log Capture

### Capture with Timestamp
```bash
# Capture serial output with timestamps
timeout $DURATION stdbuf -oL cat /dev/$PORT | while IFS= read -r line; do
  echo "[$(date +'%H:%M:%S.%3N')] $line"
done > /tmp/serial-log.txt
```

### Capture to File (background)
```bash
# Start capture in background
stdbuf -oL cat /dev/ttyUSB0 > /tmp/serial-capture.txt 2>&1 &
CAPTURE_PID=$!

# ... do stuff (flash, trigger actions) ...

# Stop capture
kill $CAPTURE_PID 2>/dev/null
```

### PlatformIO Monitor with Log
```bash
pio device monitor --baud 115200 --filter log2file --filter time
# Logs saved to .pio/build/monitor/
```

## ESP32 Log Patterns

### Boot Sequence (Success)
```
rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
I (xxx) boot: ESP-IDF vX.X.X
I (xxx) wifi: wifi driver task
I (xxx) wifi: Init data frame dynamic rx buffer num: 32
I (xxx) wifi_init: rx ba win: 6
I (xxx) wifi: mode : sta
I (xxx) wifi: STA_START
I (xxx) wifi: STA_CONNECTED
I (xxx) wifi: GOT_IP
```

### Error Patterns
```
# Stack overflow / crash
Guru Meditation Error: Core  0 panic'ed (StoreProhibited)
Backtrace: 0x400d1234:0x3ffb1234 ...

# Watchdog timeout
E (xxx) task_wdt: Task watchdog got triggered
abort() was called at PC 0x400d1234

# Memory allocation failure
E (xxx) heap_caps: Failed to allocate XX bytes

# WiFi connection failure
E (xxx) wifi: STA_DISCONNECTED, reason: 201
W (xxx) wifi: sta disconnect, reason: ASSOC_LEAVE

# BLE errors
E (xxx) BLE: gattc_cb: ESP_GATTC_DISCONNECT_EVT, reason = 0x13

# I2C/SPI errors
E (xxx) i2c: i2c_master_cmd_begin: timeout
E (xxx) spi: spi_bus_lock_acquire_core: timeout
```

### Success Indicators
```
I (xxx) main: Setup complete
I (xxx) wifi: GOT_IP, ip: 192.168.x.x
I (xxx) BLE: Advertising started
I (xxx) OBD: Connected to ELM327
I (xxx) SENSOR: Reading: temp=25.3 hum=45.2
```

## Subagent Integration

### Spawn Serial Log Analyzer
```
Analyze ESP32 serial output for errors and issues.

Device: /dev/ttyUSB0
Duration: 30 seconds
Firmware: MIA WiFi Bridge

Serial log:
```
<paste captured log>
```

Analyze for:
1. Boot failures (Guru Meditation, panic, abort)
2. WiFi connection issues (STA_DISCONNECTED, reason codes)
3. BLE errors (GATT disconnects, advertising failures)
4. Memory issues (heap allocation failures, stack overflow)
5. Watchdog timeouts (task_wdt triggered)
6. Sensor errors (I2C timeout, SPI failures)
7. Application errors (custom error messages)

Return JSON:
{
  "status": "pass|fail",
  "boot_success": true|false,
  "wifi_connected": true|false,
  "errors": [...],
  "recommendations": [...]
}
```

### Spawn Flash + Monitor Agent
```
Flash ESP32 firmware and monitor boot sequence.

Project: ~/projects/embedded/mia/apps/esp32
Port: /dev/ttyUSB0
Baud: 115200

Steps:
1. cd ~/projects/embedded/mia/apps/esp32
2. pio run --target upload --upload-port /dev/ttyUSB0
3. Capture serial output for 30 seconds
4. Analyze boot sequence
5. Report success/failure
```

## MIA Integration Testing

### Full Stack: Android + RPi + ESP32

#### 1. Flash ESP32
```bash
cd ~/projects/embedded/mia/apps/esp32
pio run --target upload --upload-port /dev/ttyUSB0
```

#### 2. Start RPi Backend
```bash
cd ~/projects/embedded/mia/apps/rpi-backend/py-api
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 3. Deploy Android App
```bash
adb install -r apps/android/app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n cz.mia.app/.MainActivity
```

#### 4. Monitor All Three
```bash
# Terminal 1: ESP32 serial
timeout 60 cat /dev/ttyUSB0 > /tmp/esp32-log.txt &

# Terminal 2: RPi backend logs
tail -f ~/projects/embedded/mia/apps/rpi-backend/py-api/logs/*.log > /tmp/rpi-log.txt &

# Terminal 3: Android logcat
adb logcat -v time > /tmp/android-log.txt &

# Wait for test duration
sleep 60

# Kill monitors
kill %1 %2 %3

# Analyze all logs
```

#### 5. Integration Test Scenarios
| Test | ESP32 | RPi | Android |
|------|-------|-----|---------|
| WiFi Bridge | Connects to WiFi | Receives data on ZeroMQ | Shows telemetry |
| BLE OBD | Reads OBD data | Processes via bridge | Displays gauges |
| Sensor Read | Sends sensor data | Routes to MQTT | Updates UI |
| Voice Command | N/A | Processes STT→TTS | Sends intent |

## Troubleshooting

### Device Not Found
```bash
# Check if device is connected
lsusb | grep -i "cp210\|ch340\|ftdi\|esp"

# Check kernel messages
dmesg | tail -20 | grep -i "tty\|usb\|serial"

# Check permissions
ls -la /dev/ttyUSB* /dev/ttyACM*
```

### Device Busy
```bash
# Find what's using the port
fuser /dev/ttyUSB0
lsof /dev/ttyUSB0

# Kill the process
fuser -k /dev/ttyUSB0
```

### Flash Fails
```bash
# Hold BOOT button on ESP32 during flash
# Or try lower baud rate
pio run --target upload --upload-port /dev/ttyUSB0 --upload-speed 115200

# Reset ESP32 manually after flash
```

### Garbled Output
```bash
# Wrong baud rate — try common rates
for baud in 9600 19200 38400 57600 115200 230400 460800 921600; do
  echo "Testing $baud..."
  timeout 2 stty -F /dev/ttyUSB0 $baud
  timeout 2 cat /dev/ttyUSB0
  echo ""
done
```
