---
name: android-adb-test
description: MIA Android app testing via ADB. Build APK, deploy to device/emulator, run test scenarios with UI automation (tap, swipe, screenshots). Orchestrate logcat analysis and adb command monitoring via readonly subagents. Use when testing MIA Android features end-to-end: dashboard telemetry, BLE pairing, OBD flows, ANPR detection, or full user journeys. Supports interactive mode for manual debugging.
---

# Android ADB Test Skill for MIA

Unified testing framework for MIA Android app combining APK builds, device deployment, ADB UI automation, and subagent-driven log analysis.

## Quick Start

### One-shot test (dashboard flow)
```bash
bash scripts/android-adb-test.sh build-and-test --scenario dashboard --screenshots
```

### Build only
```bash
bash scripts/android-adb-test.sh build
```

### Deploy + interactive debugging
```bash
bash scripts/android-adb-test.sh deploy --interactive
```

### Monitor logcat live (readonly)
```bash
bash scripts/spawn-logcat-monitor.sh --device <serial> --duration 30
```

## Core Workflows

### 1. Build APK

**Script**: `scripts/android-adb-test.sh build`

- Runs `./gradlew assembleDebug` (or Docker wrapper)
- Outputs to `apps/android/app/build/outputs/apk/debug/app-debug.apk`
- Validates APK signature and structure
- Returns exit code 0 on success, non-zero on build failure

**For CI integration**: Spawn subagent with build task, capture stdout/stderr, report back.

### 2. Deploy to Device/Emulator

**Script**: `scripts/android-adb-test.sh deploy --device <serial>`

- Auto-detects device if `--device` omitted
- Uninstalls stale package (`cz.mia.app`)
- Installs fresh APK via `adb install -r`
- Launches app: `adb shell am start -n cz.mia.app/.MainActivity`
- Polls for app readiness (UI responsive, no crashes)

### 3. Run Test Scenarios

Predefined interaction flows with auto-capture:

| Scenario | Flow | Use Case |
|----------|------|----------|
| `dashboard` | Launch → wait telemetry → screenshot | Verify UI loads, data displays |
| `ble-scan` | Navigate BLE tab → tap scan → wait results → screenshot | Test device discovery |
| `obd-pairing` | Navigate OBD tab → tap pair → capture screen | Test adapter pairing flow |
| `settings` | Navigate settings → toggle options → screenshot | Verify settings persistence |
| `anpr` | Navigate camera view → wait detection → screenshot | Test license plate detection |
| `full-flow` | Chained: dashboard → BLE → OBD → ANPR | End-to-end user journey |
| `interactive` | Launch app → shell for manual commands | Manual debugging & exploration |

**Example**:
```bash
bash scripts/android-adb-test.sh build-and-test --scenario full-flow --screenshots --logs
```

### 4. ADB UI Automation

**Tap at coordinates**:
```bash
adb -s <serial> shell input tap 540 800
```

**Swipe gesture**:
```bash
adb -s <serial> shell input swipe 100 500 900 500
```

**Enter text**:
```bash
adb -s <serial> shell input text "search query"
```

**Navigation keys**:
```bash
adb -s <serial> shell input keyevent KEYCODE_BACK   # Back
adb -s <serial> shell input keyevent KEYCODE_HOME   # Home
```

**Screenshot**:
```bash
adb -s <serial> exec-out screencap -p > screen.png
```

### 5. Readonly Subagent Monitors

Deploy subagents for continuous, readonly monitoring (no device modifications).

#### Logcat Monitor
Tail app logs, parse for errors/crashes/warnings, report findings:

```bash
bash scripts/spawn-logcat-monitor.sh \
  --device <serial> \
  --duration 30 \
  --filters "cz.mia.app:* AndroidRuntime:E"
```

Subagent analyzes:
- **Crashes**: `AndroidRuntime: FATAL EXCEPTION`
- **Permission errors**: `Permission denied` / `PermissionException`
- **BLE errors**: `BLEManager: Connection failed`, `Bluetooth adapter offline`
- **Network errors**: `WebSocket: Failed to connect`, `Retrofit: timeout`
- **OBD errors**: `OBDManager: Invalid response`, `ELM327: SEARCHING`
- **Memory/ANR**: `WARN: Low memory`, `ANR: Application not responding`

Returns JSON report:
```json
{
  "status": "pass|fail",
  "duration_sec": 30,
  "crash_count": 0,
  "error_count": 2,
  "warning_count": 5,
  "errors": [
    {"type": "network", "message": "WebSocket failed", "timestamp": "12:34:56"}
  ],
  "recommendations": ["Check network connectivity", "Verify backend URL"]
}
```

#### ADB Command Monitor
Execute adb commands, capture stdout/stderr, evaluate success/failure:

```bash
bash scripts/spawn-adb-monitor.sh \
  --device <serial> \
  --command "input tap 540 800" \
  --timeout 5
```

Returns:
```json
{
  "status": "success|timeout|error",
  "command": "input tap 540 800",
  "stdout": "",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 150
}
```

## Artifact Structure

Test runs produce:

```
apps/android/test-artifacts/<timestamp>/
├── build/
│   ├── app-debug.apk           # Built APK
│   ├── build.log               # Gradle output
│   └── build-time.txt          # Build duration
├── deploy/
│   ├── install.log             # APK install log
│   └── launch.log              # App launch log
├── scenario-<name>/
│   ├── screenshots/
│   │   ├── step_001.png
│   │   ├── step_002.png
│   ├── logcat.txt              # Raw logcat during scenario
│   ├── logcat-analysis.json    # Parsed errors/warnings
│   ├── performance.json        # App startup time, memory
│   └── result.json             # Pass/fail summary
└── test-report.md              # Markdown summary
```

## Subagent Integration

### Spawn Logcat Analyzer
```bash
# From main session, spawn subagent:
sessions_spawn --task "
Analyze logcat for MIA Android app over 30 seconds.
Device serial: ZY32KXSJ2F
Filters: cz.mia.app:* AndroidRuntime:E
Look for:
- Crashes (AndroidRuntime: FATAL EXCEPTION)
- Permission errors
- BLE/Bluetooth issues
- Network timeouts
- OBD protocol errors
- Memory pressure
Report findings as JSON with recommendations.
"
```

### Spawn ADB Command Executor
```bash
sessions_spawn --task "
Run ADB tap on MIA Android app.
Device: ZY32KXSJ2F
Coordinates: X=540 Y=800
Timeout: 5 seconds
Capture screenshot after tap.
Report success/failure and any errors.
"
```

### Orchestrate Full Test
```bash
# Main agent spawns build task
sessions_spawn --label "build" --task "Build MIA Android APK debug..."

# Waits for build completion
# Then spawns deploy task
sessions_spawn --label "deploy" --task "Deploy APK to device..."

# Then spawns scenario test
sessions_spawn --label "test-dashboard" --task "Run dashboard scenario..."

# Parallel: spawn logcat monitor
sessions_spawn --label "logcat-monitor" --task "Monitor logcat during test..."

# Collect all reports, generate summary
```

## Key Log Patterns

### MIA Android App Logs
- **Tag**: `cz.mia.app`, `BLEManager`, `OBDManager`, `WebSocketClient`
- **Severity**: `D` (debug), `I` (info), `W` (warning), `E` (error)

### Success Indicators
- `I/cz.mia.app: Dashboard loaded`
- `I/BLEManager: Device scan started`
- `I/OBDManager: Connected to adapter`
- `I/WebSocketClient: Connection established`

### Failure Indicators
- `E/AndroidRuntime: FATAL EXCEPTION`
- `E/BLEManager: Bluetooth adapter unavailable`
- `E/OBDManager: Failed to parse response`
- `E/WebSocketClient: Connection timeout`
- `W/cz.mia.app: Low memory (xyz MB)`

## Device Configuration

### Physical Android Device
1. Enable Developer Options: Settings → About Phone → tap Build number 7x
2. Enable USB Debugging: Settings → Developer Options → USB debugging
3. Connect via USB, accept debug prompt
4. Verify: `adb devices` shows device

### Android Emulator
```bash
# Launch AVD
emulator -avd <avd_name>

# Verify connection
adb devices  # Shows "emulator-5554"
```

### Wireless ADB (Advanced)
```bash
# On USB first
adb tcpip 5555

# Disconnect USB, connect wirelessly
adb connect <device_ip>:5555

# Verify
adb devices
```

## Integration with Other Skills/Agents

### Example: Codex Code Review + ADB Test
```bash
# Codex generates BLE manager changes
codex exec "Refactor BLEManager for retry logic"

# Then spawn subagent to test changes
sessions_spawn --task "
After BLEManager changes:
1. Build APK with updated code
2. Deploy to device
3. Run BLE scan scenario
4. Analyze logcat for connection errors
5. Report whether retry logic works
"
```

### Example: GitHub PR Automation
```bash
# When PR is submitted with Android changes
# Spawn build+test subagent
sessions_spawn --task "
Build MIA Android APK from PR branch.
Run full-flow test scenario.
Capture screenshots and logcat.
Report pass/fail.
If failures: extract error logs and post to PR.
"
```

## Troubleshooting

### Device Not Found
```bash
# Check connections
adb devices

# Restart ADB server
adb kill-server && adb start-server

# Check USB permissions (Linux/Mac)
ls -la /dev/bus/usb/
```

### APK Install Fails
```bash
# Check storage
adb shell df -h

# Clear app data
adb uninstall cz.mia.app

# Try without streaming
adb install -r --no-streaming app-debug.apk
```

### App Crashes Immediately
```bash
# Check logcat for crashes
adb logcat -d | grep -iE "AndroidRuntime|cz.mia.app" | tail -30

# Check permissions granted
adb shell pm list permissions -g | grep -i "cz.mia.app"
```

### Logcat Too Noisy
```bash
# Filter by app PID only
PID=$(adb shell pidof -s cz.mia.app)
adb logcat --pid=$PID

# Filter by tags
adb logcat -s "cz.mia.app:*" "BLEManager:*" "OBDManager:*"
```

## References

See related documentation:
- **ADB Commands**: [references/adb-commands.md](references/adb-commands.md)
- **Logcat Patterns**: [references/logcat-patterns.md](references/logcat-patterns.md)
- **Test Scenarios**: [references/test-scenarios.md](references/test-scenarios.md)
- **MIA App Architecture**: MIA project docs (apps/android/docs/ARCHITECTURE.md)
