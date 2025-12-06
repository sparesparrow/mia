# /debug-with-adb-user-input-simulation

Android UI debugging and testing command with ADB user input simulation.

## Usage

```
/debug-with-adb-user-input-simulation [options] [scenario]

# Actual script invocation
bash android/tools/debug-with-adb-user-input-simulation.sh [options] [scenario]
```

### Quick start (device connected)
```
bash android/tools/debug-with-adb-user-input-simulation.sh dashboard --screenshots --logs
```

### Build + install + launch only
```
bash android/tools/debug-with-adb-user-input-simulation.sh install --build
```

## Description

This command provides comprehensive Android UI debugging capabilities by installing the app on a connected device/emulator, simulating user interactions via ADB input commands, and capturing detailed logs and screenshots. It supports both interactive debugging sessions and automated test scenarios.

## Scenarios

- `install`: Install and launch app only
- `dashboard`: Test dashboard UI and telemetry display
- `ble-scan`: Test Bluetooth device scanning
- `obd-pairing`: Test OBD-II adapter pairing
- `settings`: Test settings screen navigation
- `anpr`: Test ANPR (license plate recognition) functionality
- `full-flow`: Complete end-to-end user journey test
- `interactive`: Start interactive debugging session

## Options

- `--device SERIAL`: Target specific device serial (default: auto-detect)
- `--apk PATH`: Custom APK path (default: android/app/build/outputs/apk/debug/app-debug.apk)
- `--build`: Build APK before testing
- `--no-launch`: Install only, don't launch app
- `--screenshots`: Capture screenshots during interactions
- `--logs`: Enable verbose ADB logging
- `--delay MS`: Delay between actions in milliseconds (default: 1000)
- `--timeout SEC`: Operation timeout in seconds (default: 60)
- `--output DIR`: Output directory for screenshots/logs (default: debug-output)
- `--record`: Record screen during testing
- `--cleanup`: Remove app after testing

## Project Configuration

- **Package Name**: `cz.aiservis.app.debug` (debug build)
- **Main Activity**: `.MainActivity`
- **ADB Commands**: Device interaction and input simulation
- **UI Framework**: Jetpack Compose with Material3
- **Test Framework**: Compose UI Testing with Espresso

## Installation and Setup

### 1. Device Connection Check
```bash
adb devices
adb shell getprop ro.product.model
```

### 2. APK Installation
```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

### 3. App Launch
```bash
adb shell am start -n cz.aiservis.app.debug/.MainActivity
```

## User Input Simulation

### Touch Events
```bash
# Tap at coordinates (x,y)
adb shell input tap 500 800

# Long press
adb shell input swipe 500 800 500 800 1500

# Swipe gesture
adb shell input swipe 100 500 900 500
```

### Text Input
```bash
# Enter text in focused field
adb shell input text "test_input"

# Key events
adb shell input keyevent KEYCODE_ENTER
adb shell input keyevent KEYCODE_BACK
```

### System Navigation
```bash
# Home button
adb shell input keyevent KEYCODE_HOME

# Back button
adb shell input keyevent KEYCODE_BACK

# Menu button
adb shell input keyevent KEYCODE_MENU
```

## Test Scenarios

### Dashboard Testing
1. Launch app and wait for dashboard to load
2. Verify telemetry gauges are displayed
3. Simulate OBD data updates
4. Check gauge value updates
5. Capture screenshots of different states

### BLE Device Scanning
1. Navigate to BLE devices screen
2. Trigger device scan
3. Verify scan results display
4. Test device connection attempt
5. Handle connection success/failure

### OBD Pairing Flow
1. Navigate to OBD pairing screen
2. Simulate Bluetooth discovery
3. Test pairing process
4. Verify connection status
5. Check telemetry data flow

### Settings Navigation
1. Access settings screen
2. Test various setting toggles
3. Verify preference persistence
4. Check UI state changes

## Debugging Features

### Log Capture
```bash
# App-specific logs
adb logcat --pid=$(adb shell pidof -s cz.aiservis.app.debug)

# System logs with filters
adb logcat *:W | grep -i aiservis
```

### Screenshot Capture
```bash
# Capture device screenshot
adb exec-out screencap -p > screenshot.png

# Pull screenshot from device
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png
```

### UI Hierarchy Dump
```bash
# Dump current UI hierarchy
adb shell uiautomator dump
adb pull /sdcard/window_dump.xml
```

### Performance Monitoring
```bash
# Monitor app performance
adb shell dumpsys meminfo cz.aiservis.app.debug
adb shell dumpsys cpuinfo | grep aiservis
```

## Interactive Mode

### Commands Available in Interactive Mode
- `tap X Y`: Tap at coordinates
- `swipe X1 Y1 X2 Y2`: Swipe from point to point
- `text "string"`: Enter text
- `key KEYCODE`: Send key event
- `screenshot`: Capture screenshot
- `logs`: Show recent logs
- `hierarchy`: Dump UI hierarchy
- `exit`: End interactive session

### Interactive Session Example
```bash
$ /debug-with-adb-user-input-simulation interactive
🔧 Interactive ADB Debug Session Started
📱 Connected to: Pixel_4_API_30

Commands:
  tap 500 800     - Tap at (500,800)
  swipe 100 500 900 500  - Swipe across screen
  text "hello"    - Enter text
  screenshot      - Capture screenshot
  logs            - Show app logs
  exit            - End session

> tap 540 1200
✅ Tapped at (540,1200)

> screenshot
📸 Screenshot saved: debug-output/screenshot_001.png

> logs
📋 Recent logs:
  I/AIServis: Dashboard loaded
  D/AIServis: Telemetry updated: speed=45
```

## Automated Test Execution

### Scenario: Dashboard Telemetry Test
```bash
/debug-with-adb-user-input-simulation dashboard --screenshots --logs
```

**Test Steps:**
1. Install and launch app
2. Wait for dashboard to load (verify gauges visible)
3. Simulate OBD connection via mock data
4. Verify telemetry values update on UI
5. Test gauge animations and warnings
6. Capture before/after screenshots

### Scenario: BLE Device Discovery
```bash
/debug-with-adb-user-input-simulation ble-scan --delay 2000
```

**Test Steps:**
1. Navigate to BLE devices screen
2. Trigger device scan
3. Wait for scan results
4. Attempt device connection
5. Verify connection status feedback

## Output and Reporting

### Test Results Directory Structure
```
debug-output/
├── screenshots/
│   ├── dashboard_initial.png
│   ├── dashboard_with_data.png
│   └── ble_scan_results.png
├── logs/
│   ├── app_logcat.txt
│   ├── system_logcat.txt
│   └── uiautomator_dump.xml
├── test-results.json
└── test-report.md
```

### Test Report Format
```json
{
  "test_scenario": "dashboard",
  "device": "Pixel_4_API_30",
  "timestamp": "2024-12-05T14:30:00Z",
  "duration_ms": 15420,
  "steps_completed": 8,
  "steps_total": 8,
  "screenshots_captured": 3,
  "errors": [],
  "performance_metrics": {
    "app_startup_time_ms": 2340,
    "ui_response_time_ms": 150,
    "memory_usage_mb": 89
  }
}
```

## Error Handling

### Common Issues and Solutions
- **Device Not Connected**: Verify USB debugging enabled, try `adb kill-server && adb start-server`
- **App Not Installing**: Check storage space, try `adb install -r --no-streaming`
- **UI Elements Not Found**: Verify screen coordinates, check device resolution
- **Permissions Denied**: Grant necessary permissions via `adb shell pm grant`
- **Test Timeouts**: Increase timeout values, check device performance

### Recovery Actions
- Automatic screenshot capture on failures
- Log preservation for debugging
- Device state reset between tests
- Graceful cleanup on interruption

## Integration with Testing Framework

### Running with Gradle Tests
```bash
# Run instrumented tests first
./gradlew connectedAndroidTest

# Then run ADB simulation tests
/debug-with-adb-user-input-simulation full-flow
```

### CI/CD Integration
```bash
# In GitHub Actions workflow
- name: Build APK
  run: ./android/tools/build-in-docker.sh

- name: Run ADB UI Tests
  run: /debug-with-adb-user-input-simulation dashboard --screenshots
```

## Prerequisites

- **ADB**: Android Debug Bridge installed and configured
- **Device/Emulator**: Android device or emulator running
- **USB Debugging**: Enabled on physical devices
- **App Permissions**: Granted for testing scenarios
- **Storage Access**: For screenshot and log capture

## Performance Considerations

- **Action Delays**: Configurable delays prevent race conditions
- **Screenshot Impact**: Minimal performance overhead
- **Log Filtering**: Efficient log capture and filtering
- **Resource Cleanup**: Automatic cleanup of temporary files
- **Parallel Execution**: Support for multiple device testing