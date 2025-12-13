## **Refined Practical Cursor Commands: MIA-Specific with Correct Details**

Updated with actual project details from the Android app structure, RPi connection (`mia@mia.local`), and existing scripts.

***

## **Android Development Commands**

### **1. `/deploy-apk`**

**File:** `.cursor/commands/deploy-apk.md`

```markdown
Build Android APK in Docker (android/Dockerfile), copy to android/app/build/outputs/apk/debug/, detect connected Android device via adb, install APK with `adb install -r`, launch app (cz.mia.app/.MainActivity), tail logcat filtered to "BLEManager|TelemetryWebSocket|DeviceRepository", output deploy-apk.log
```

**Example Usage:**
```bash
/deploy-apk

# Cursor executes:
# 1. Docker build Android app
cd android && docker build -t mia-android .

# 2. Build APK
docker run --rm -v $(pwd):/workspace mia-android ./gradlew assembleDebug

# 3. Verify APK exists
if [ ! -f app/build/outputs/apk/debug/app-debug.apk ]; then
  echo "❌ APK build failed"
  exit 1
fi

# 4. Detect device
adb devices

# 5. Install APK
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 6. Launch app
adb shell am start -n cz.mia.app/.MainActivity

# 7. Tail logcat
adb logcat | grep -E "BLEManager|TelemetryWebSocket|DeviceRepository"

# Output:
✅ APK built: app/build/outputs/apk/debug/app-debug.apk (8.2 MB)
✅ Device: Samsung Galaxy S23 (192.168.1.50:5555)
✅ Installed successfully
✅ App launched: cz.mia.app/.MainActivity
📱 Logcat:
   12-05 11:54:15 I BLEManager: Initializing...
   12-05 11:54:16 I TelemetryWebSocket: Connecting to ws://mia.local:8000/ws
   12-05 11:54:17 I DeviceRepository: Fetching devices from http://mia.local:8000/devices
```

***

### **2. `/debug-with-adb-user-input-simulation`**

**File:** `.cursor/commands/debug-with-adb-user-input.md`

```markdown
Interactive Android UI testing: connect via adb, list UI elements with uiautomator dump, simulate user interactions (tap BLE scan button, connect to device, toggle GPIO), capture screen recording, screenshot each step, collect logcat with BLEManager filter, output debug-session/ with video + screenshots + ui-hierarchy.xml + logcat.txt
```

**Example Usage:**
```bash
/debug-with-adb-user-input-simulation

# Interactive prompts:
? Select test scenario:
  [1] BLE device scan and connect
  [2] Toggle LED via FastAPI
  [3] View telemetry dashboard
  [4] Custom sequence
> 1

# Cursor executes UI automation:
# Start screen recording
adb shell screenrecord /sdcard/debug-session.mp4 &
RECORDING_PID=$!

# Scenario 1: BLE device scan and connect
echo "Step 1: Launch app"
adb shell am start -n cz.mia.app/.MainActivity
sleep 2
adb shell screencap /sdcard/step1-home.png
adb pull /sdcard/step1-home.png debug-session/

echo "Step 2: Navigate to BLE Devices screen"
# Get UI coordinates from uiautomator dump
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml /tmp/

# Parse XML for "BLE Devices" button coordinates
COORDS=$(python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('/tmp/ui.xml')
for node in tree.iter():
    if node.get('text') == 'BLE Devices':
        bounds = node.get('bounds')
        # Parse [x1,y1][x2,y2] format
        import re
        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
        if match:
            x = (int(match.group(1)) + int(match.group(3))) // 2
            y = (int(match.group(2)) + int(match.group(4))) // 2
            print(f'{x} {y}')
")
adb shell input tap $COORDS
sleep 1
adb shell screencap /sdcard/step2-ble-screen.png

echo "Step 3: Start BLE scanning"
adb shell input tap 540 200  # Bluetooth icon coordinates
sleep 10  # Wait for scan (10s default)
adb shell screencap /sdcard/step3-devices-found.png

echo "Step 4: Connect to first device"
adb shell input tap 540 400  # First device in list
sleep 15  # Wait for connection
adb shell screencap /sdcard/step4-connected.png

# Stop recording
kill $RECORDING_PID
adb pull /sdcard/debug-session.mp4 debug-session/

# Collect logs
adb logcat -d -s BLEManager > debug-session/ble-logs.txt

# Final UI hierarchy
adb shell uiautomator dump /sdcard/final-ui.xml
adb pull /sdcard/final-ui.xml debug-session/

# Output:
✅ Test completed (28s)
📁 Artifacts: debug-session/
   - debug-session.mp4 (screen recording)
   - step1-home.png
   - step2-ble-screen.png
   - step3-devices-found.png
   - step4-connected.png
   - ble-logs.txt
   - final-ui.xml

🔍 Analysis:
   - BLE scan found 3 devices (OBD-Veepeak, ELM327-Pro, Unknown-5F2A)
   - Connection to OBD-Veepeak: SUCCESS (12.3s)
   - Service discovery: 2 services found
   - UART TX/RX characteristics: AVAILABLE
```

***

### **3. `/run-on-rpi`**

**File:** `.cursor/commands/run-on-rpi.md`

```markdown
Deploy MIA to Raspberry Pi: rsync code to mia@mia.local:/home/mia/mia, run complete-bootstrap.py if needed, start services via docker-compose or systemctl, validate health endpoints (GET /status, GET /devices), tail logs via ssh, output deployment-log.txt
```

**Example Usage:**
```bash
/run-on-rpi

# Cursor executes:
# 1. Check RPi connectivity
if ! ping -c 1 mia.local &>/dev/null; then
  echo "❌ Cannot reach mia.local"
  echo "Try: ssh mia@mia.local (manual check)"
  exit 1
fi

# 2. Sync code to RPi
rsync -avz \
  --exclude='android/' \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --delete \
  . mia@mia.local:/home/mia/mia/

# 3. Check if bootstrap needed
ssh mia@mia.local 'cd /home/mia/mia && \
  if [ ! -f validation-report.json ]; then \
    echo "Running bootstrap..."; \
    python3 complete-bootstrap.py; \
  fi'

# 4. Start services
? Deployment mode:
  [1] docker-compose (recommended)
  [2] systemd service
  [3] direct python (development)
> 1

ssh mia@mia.local 'cd /home/mia/mia && docker-compose up -d --build'

# 5. Wait for startup
echo "⏳ Waiting for services to start..."
sleep 10

# 6. Health check
echo "🏥 Health check:"
curl -s http://mia.local:8000/status | jq .
# {"status":"ok","uptime":8,"devices":12,"services":["ai-servis-core","service-discovery","ai-audio-assistant"]}

curl -s http://mia.local:8000/devices | jq 'length'
# 12

# 7. Tail logs
echo "📋 Live logs (Ctrl+C to stop):"
ssh mia@mia.local 'docker-compose -f /home/mia/mia/docker-compose.yml logs -f --tail=50'

# Output:
✅ Code synced to mia@mia.local:/home/mia/mia
✅ Bootstrap validated (cached)
✅ Docker services started:
   - ai-servis-core (0.0.0.0:8080)
   - service-discovery (0.0.0.0:8090)
   - ai-audio-assistant (0.0.0.0:8082)
✅ Health check: PASS
📡 API: http://mia.local:8000
📡 WebSocket: ws://mia.local:8000/ws

Live Logs:
ai-servis-core | INFO: Core orchestrator running on http://0.0.0.0:8080
ai-servis-core | INFO: MCP discovery on port 8081
service-discovery | INFO: Service discovery listening on 0.0.0.0:8090
ai-audio-assistant | INFO: MCP server ready on port 8082
```

***

### **4. `/build-deploy-integration-test-rpi`**

**File:** `.cursor/commands/build-deploy-integration-test-rpi.md`

```markdown
Full E2E workflow: build Android APK, deploy to mia@mia.local, install APK on phone, run integration test (android/test/integration/test_e2e_android_rpi.py), validate end-to-end latency <50ms, collect logs from both devices, output integration-test-report.json
```

**Example Usage:**
```bash
/build-deploy-integration-test-rpi

# Cursor orchestrates full stack test:
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 MIA Full Stack Integration Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Build Android APK
echo "[1/5] Building Android APK..."
cd android && docker run --rm -v $(pwd):/workspace mia-android ./gradlew assembleDebug
✅ APK built (8.2 MB)

# Step 2: Deploy RPi backend
echo "[2/5] Deploying to RPi (mia@mia.local)..."
rsync -avz --exclude='android/' . mia@mia.local:/home/mia/mia/
ssh mia@mia.local 'cd /home/mia/mia && docker-compose restart ai-servis-core'
sleep 5
✅ RPi services restarted

# Step 3: Install APK on Android
echo "[3/5] Installing APK on device..."
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
✅ APK installed

# Step 4: Run integration test
echo "[4/5] Running E2E integration test..."
python3 android/test/integration/test_e2e_android_rpi.py \
  --rpi-host mia.local \
  --android-device $(adb devices | grep "device$" | awk '{print $1}')

# Test execution (from test_e2e_android_rpi.py):
# 1. Android app sends POST http://mia.local:8000/command
#    {"device": "led1", "action": "toggle"}
# 2. RPi receives command, routes via ZeroMQ
# 3. GPIO controller toggles pin 17 (LED)
# 4. RPi sends telemetry via WebSocket
#    {"device": "led1", "state": "HIGH", "timestamp": ...}
# 5. Android app receives WebSocket update
# 6. Measure total latency

Test Results:
─────────────────────────────────────────────────
test_gpio_toggle_e2e            ✅ PASS (34ms)
  - Command sent: 3ms
  - RPi processing: 12ms
  - GPIO toggle: 8ms
  - Telemetry delivery: 11ms
  ✅ Total latency: 34ms (SLA: <50ms)

test_websocket_telemetry        ✅ PASS (8ms)
test_device_list_sync           ✅ PASS (142ms)
test_ble_obd_simulation         ✅ PASS (2.1s)
─────────────────────────────────────────────────
Total: 4 tests, 4 passed, 0 failed
Time: 2.3s

# Step 5: Collect logs
echo "[5/5] Collecting logs..."
adb logcat -d > integration-test-report/android-logcat.txt
ssh mia@mia.local 'docker-compose logs --tail=200' > integration-test-report/rpi-logs.txt

# Output:
✅ Integration test: PASS (4/4 tests)
✅ End-to-end latency: 34ms (meets <50ms SLA)
📁 Artifacts:
   - integration-test-report.json
   - android-logcat.txt
   - rpi-logs.txt
   - test-recording.mp4
```

***

## **Arduino/Hardware Commands**

### **5. `/deploy-arduino`**

**File:** `.cursor/commands/deploy-arduino.md`

```markdown
Upload Arduino sketch: detect board with arduino-cli, compile arduino/led_strip_controller/, flash to /dev/ttyUSB0 (or detected port), open serial monitor at 115200 baud, validate handshake with RPi, output arduino-deploy.log
```

**Example Usage:**
```bash
/deploy-arduino

# Cursor executes:
# 1. Detect Arduino board
arduino-cli board list

# Output:
Port         Protocol Type       Board Name    FQBN              Core
/dev/ttyUSB0 serial   Serial Port Arduino Uno   arduino:avr:uno   arduino:avr

# 2. Compile sketch
arduino-cli compile \
  --fqbn arduino:avr:uno \
  arduino/led_strip_controller/

# Output:
Sketch uses 8432 bytes (26%) of program storage
Global variables use 512 bytes (25%) of dynamic memory

# 3. Upload
arduino-cli upload \
  -p /dev/ttyUSB0 \
  --fqbn arduino:avr:uno \
  arduino/led_strip_controller/

✅ Upload complete (3.4s)

# 4. Open serial monitor
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200

# Serial output:
[ARDUINO] MIA LED Strip Controller v1.0
[ARDUINO] Initializing...
[ARDUINO] GPIO pins: 2,3,4,5,6,7,8,9,10,11,12,13
[ARDUINO] UART: 115200 baud
[ARDUINO] Waiting for handshake from RPi...
[ARDUINO] Handshake received: {"type":"init"}
[ARDUINO] Sending ACK: {"status":"ready","pins":12}
[ARDUINO] Ready for commands

# Test command from RPi:
[ARDUINO] RX: {"device":"led1","pin":13,"action":"HIGH"}
[ARDUINO] GPIO 13 -> HIGH
[ARDUINO] TX: {"device":"led1","pin":13,"state":"HIGH"}
```

***

### **6. `/test-gpio-hardware`**

**File:** `.cursor/commands/test-gpio-hardware.md`

```markdown
Interactive GPIO test on RPi: ssh mia@mia.local, list GPIO pins (BCM numbering), prompt for pin selection, toggle HIGH/LOW with 1s intervals, read back state, display voltage confirmation, output gpio-test-report.txt
```

**Example Usage:**
```bash
/test-gpio-hardware

# Cursor prompts:
? Connect to RPi: [mia.local]
> mia.local

# Lists available GPIO:
Available GPIO Pins (RPi 4B, BCM numbering):
Physical  BCM  Name            Usage in MIA
   3       2   GPIO2/SDA1      I2C sensors
   5       3   GPIO3/SCL1      I2C sensors
   7       4   GPIO4           Available
  11      17   GPIO17          LED control
  13      27   GPIO27          Motor PWM
  15      22   GPIO22          Available
  ...

? Select pin to test:
> 17

? Test mode:
  [1] Digital output (toggle)
  [2] PWM output (fade)
  [3] Digital input (read)
> 1

# Cursor executes on RPi:
ssh mia@mia.local 'python3 - << "EOF"
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

print("[TEST] GPIO 17 - Digital Output Test")
print("[TEST] Setting HIGH...")
GPIO.output(17, GPIO.HIGH)
time.sleep(1)
state = GPIO.input(17)
print(f"[TEST] Read-back: {state} (1=HIGH, 0=LOW)")

print("[TEST] Setting LOW...")
GPIO.output(17, GPIO.LOW)
time.sleep(1)
state = GPIO.input(17)
print(f"[TEST] Read-back: {state}")

GPIO.cleanup()
print("[TEST] Complete - GPIO cleaned up")
EOF
'

# Output:
✅ Connected to mia@mia.local
🔌 Testing GPIO 17 (LED control)

[TEST] GPIO 17 - Digital Output Test
[TEST] Setting HIGH...
[TEST] Read-back: 1 (1=HIGH, 0=LOW) ✅
[TEST] Setting LOW...
[TEST] Read-back: 0 ✅
[TEST] Complete - GPIO cleaned up

✅ GPIO 17 working correctly
📁 Saved: gpio-test-report.txt

Recommendations:
- Use GPIO 17 for LED control (as planned in MIA)
- Voltage level verified: 3.3V
- No hardware issues detected
```

***

## **Debugging & Log Analysis Commands**

### **7. `/summarize-logs-and-plan-suggested-actions`**

**File:** `.cursor/commands/summarize-logs-plan-actions.md`

```markdown
AI-powered log analysis: collect logs (RPi docker logs --since 1h, adb logcat -d, Arduino serial), detect error patterns, classify by severity (CRITICAL/WARNING/INFO), correlate errors across services, use MCP prompts for root cause analysis, generate action plan with prioritized fixes, output log-analysis.md + suggested-actions.json
```

**Example Usage:**
```bash
/summarize-logs-and-plan-suggested-actions

# Cursor collects logs:
echo "📊 Collecting logs from all services..."

# RPi logs
ssh mia@mia.local 'docker-compose logs --since 1h' > /tmp/rpi-logs.txt

# Android logs
adb logcat -d -s BLEManager:* TelemetryWebSocket:* DeviceRepository:* > /tmp/android-logs.txt

# Arduino serial (if available)
if arduino-cli board list | grep -q ttyUSB0; then
  timeout 5 arduino-cli monitor -p /dev/ttyUSB0 > /tmp/arduino-logs.txt || true
fi

# AI analysis via MCP prompts:
python3 << 'EOF'
import json
from pathlib import Path
from collections import defaultdict

# Parse logs and detect patterns
errors = defaultdict(list)
warnings = defaultdict(list)

# Example pattern detection (simplified):
for log_file in ['/tmp/rpi-logs.txt', '/tmp/android-logs.txt']:
    with open(log_file) as f:
        for line in f:
            if 'error' in line.lower() or 'exception' in line.lower():
                errors[log_file].append(line.strip())
            elif 'warn' in line.lower():
                warnings[log_file].append(line.strip())

# Generate analysis report
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("📊 Log Analysis Summary (Last 1 hour)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()
print(f"🔴 CRITICAL Issues: {len([e for es in errors.values() for e in es if 'connection refused' in e.lower()])}")
print(f"🟡 WARNINGS: {len([w for ws in warnings.values() for w in ws])}")
print()

# Detailed analysis with examples from actual logs...
EOF

# Output:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Log Analysis Summary (Last 1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 CRITICAL Issues (2):

1. BLE Connection Timeout (18 occurrences)
   Source: Android logcat
   Pattern: "BLEManager: Connection timeout after 15s"
   Last seen: 11:47:32
   Impact: App cannot connect to OBD device
   
   Root Cause Analysis (via MCP):
   - BLE adapter may be in wrong state (need ATZ reset)
   - Signal strength too weak (RSSI < -80 dBm)
   - Device already paired to another phone

2. FastAPI 504 Gateway Timeout (5 occurrences)
   Source: RPi docker logs
   Pattern: "ai-servis-core | ERROR: POST /command -> 504"
   Impact: Android commands not reaching RPi
   
   Root Cause: ZeroMQ router not responding

🟡 WARNINGS (8):

1. High Memory Usage (RPi)
   - ai-servis-core: 342 MB / 4 GB (8.5%)
   - Recommendation: Normal, no action needed

2. WebSocket Reconnects (Android)
   - 3 reconnections in last hour
   - Reason: Network switching (WiFi -> Mobile Data)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ Suggested Action Plan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Priority 1: Fix BLE Connection Timeouts
  Step 1: Check BLE adapter power
    Command: adb shell dumpsys bluetooth_manager
    Look for: "Adapter state: ON"
  
  Step 2: Reset BLE stack
    Command: adb shell svc bluetooth disable && sleep 2 && adb shell svc bluetooth enable
  
  Step 3: Verify RSSI strength
    - Move Android phone closer to OBD adapter
    - Target RSSI: > -60 dBm

Priority 2: Restart Service Discovery
  Command: ssh mia@mia.local 'docker-compose restart service-discovery'
  Validation: curl http://mia.local:8080/status
  
Priority 3: Monitor WebSocket Stability
  - Already stable (3 reconnects acceptable)
  - No action needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Artifacts:
   - log-analysis.md (full report)
   - suggested-actions.json (machine-readable)
   - error-timeline.svg (visual)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

? Apply Priority 1 fix (reset BLE)? [Y/n]
```

***

### **8. `/tail-all-logs`**

**File:** `.cursor/commands/tail-all-logs.md`

```markdown
Multi-source log streaming: open 3-pane terminal (RPi docker logs, Android logcat, Arduino serial), color-code by source ([RPi] green, [ANDROID] blue, [ARDUINO] yellow), auto-scroll, save to combined-logs.txt with timestamps
```

**Example Usage:**
```bash
/tail-all-logs

# Cursor opens tmux with 3 panes:
tmux new-session \; \
  split-window -h \; \
  split-window -v \; \
  select-pane -t 0 \; \
  send-keys "ssh mia@mia.local 'docker-compose logs -f --tail=20 | while read line; do echo \"\\033[0;32m[RPi]\\033[0m \$line\"; done'" C-m \; \
  select-pane -t 1 \; \
  send-keys "adb logcat -s BLEManager:* TelemetryWebSocket:* | while read line; do echo \"\\033[0;34m[ANDROID]\\033[0m \$line\"; done" C-m \; \
  select-pane -t 2 \; \
  send-keys "arduino-cli monitor -p /dev/ttyUSB0 2>/dev/null | while read line; do echo \"\\033[0;33m[ARDUINO]\\033[0m \$line\"; done" C-m

# Visual output:
┌─────────────────────── [RPi] ────────────────────────┐
│ 11:54:42 ai-servis-core | INFO: POST /command       │
│ 11:54:42 service-discovery | DEBUG: Service found  │
│ 11:54:42 ai-audio-assistant | INFO: Template loaded │
├─────────────────────── [ANDROID] ───────────────────┤
│ 11:54:42 BLEManager: Sending command: toggle LED    │
│ 11:54:42 TelemetryWebSocket: Message sent          │
│ 11:54:43 BLEManager: ACK received (18ms)            │
├─────────────────────── [ARDUINO] ───────────────────┤
│ 11:54:42 [GPIO] RX: {"device":"led1","pin":13}     │
│ 11:54:42 [GPIO] Pin 13 -> HIGH                      │
│ 11:54:42 [GPIO] TX: {"state":"HIGH"}                │
└──────────────────────────────────────────────────────┘

Press Ctrl+B then D to detach, logs saved to combined-logs.txt
```

***

## **Quick Workflow Commands**

### **9. `/quick-test-android-only`**

**File:** `.cursor/commands/quick-test-android-only.md`

```markdown
Fast Android iteration: incremental APK build (gradle assembleDebug), push to device, restart app clearing cache, run UI tests (adb shell am instrument), no RPi deployment, output in 15s, test-result.json
```

***

### **10. `/simulate-backend-local`**

**File:** `.cursor/commands/simulate-backend-local.md`

```markdown
Local backend simulation: start FastAPI with mock GPIO adapter (SIMULATION_MODE=true), mock BLE responses, generate fake telemetry data, allow Android testing without RPi/Arduino hardware, output simulation-log.txt
```

***

### **11. `/fix-and-redeploy`**

**File:** `.cursor/commands/fix-and-redeploy.md`

```markdown
Smart auto-retry: detect last deployment error (parse stderr), suggest fix (adb authorization, RPi unreachable, port conflict), apply fix automatically, retry up to 3 times, output fix-attempts.log
```

***

### **12. `/full-stack-restart`**

**File:** `.cursor/commands/full-stack-restart.md`

```markdown
Complete system restart: stop Android app (am force-stop), stop RPi services (ssh mia@mia.local docker-compose down), reset Arduino (DTR toggle), wait 5s, start in sequence (Arduino→RPi→Android), validate all health checks, output restart-report.txt
```

***

## **Summary: Time Savings**

| Command | Daily Usage | Time Saved/Use |
|---------|-------------|----------------|
| `/deploy-apk` | 10-15x | 3 min → 30s |
| `/debug-with-adb-user-input-simulation` | 3-5x | 15 min → 2 min |
| `/run-on-rpi` | 5-8x | 5 min → 45s |
| `/build-deploy-integration-test-rpi` | 2-3x | 10 min → 3 min |
| `/summarize-logs-and-plan-suggested-actions` | 2-4x | 30 min → 5 min |
| `/tail-all-logs` | Always on | N/A (monitoring) |
| `/quick-test-android-only` | 20-30x | 2 min → 15s |


