# MIA Android Test Scenarios

## Scenario: Dashboard

**Purpose**: Verify app launch, UI rendering, and telemetry display.

**Flow**:
1. Launch app → MainActivity
2. Wait 2s for dashboard to load
3. Verify telemetry gauges visible (RPM, Speed, Coolant, Fuel)
4. Capture screenshot

**Expected Logs**:
```
I/cz.mia.app: Dashboard loaded
I/DashboardVM: Telemetry update received
```

**Success Criteria**:
- App launches without crash
- Dashboard screen displays
- No errors in logcat
- Screenshot shows all gauges

**Manual Testing**:
```bash
adb shell am start -n cz.mia.app/.MainActivity
sleep 2
adb exec-out screencap -p > dashboard.png
# Verify screenshot shows dashboard UI
```

**Automated**:
```bash
./android-adb-test.sh build-and-test --scenario dashboard --screenshots
```

---

## Scenario: BLE Scan

**Purpose**: Test Bluetooth device discovery and UI feedback.

**Flow**:
1. Launch app
2. Swipe up to access tab navigation
3. Tap BLE/Devices tab
4. Verify scan button visible
5. Wait for device list or "No devices found"
6. Capture screenshot

**Expected Logs**:
```
I/BLEManager: Starting device scan
I/BLEManager: Scan started (duration: 12s)
I/BLEManager: Device discovered: <name> (<address>)
```

**Success Criteria**:
- BLE tab accessible
- Scan completes without error
- Device list (or empty state) displays
- No permission errors in logcat

**Manual Testing**:
```bash
adb shell input swipe 500 1600 500 400  # Scroll up
sleep 1
adb shell input tap 540 300             # Tap BLE tab
sleep 12  # Wait for scan
adb exec-out screencap -p > ble_scan.png
```

**Automated**:
```bash
./android-adb-test.sh build-and-test --scenario ble-scan --screenshots
```

---

## Scenario: OBD Pairing

**Purpose**: Test OBD-II adapter pairing flow.

**Flow**:
1. Launch app
2. Navigate to OBD/Pairing tab
3. Verify pairing UI visible
4. Attempt connection to test adapter (if available)
5. Capture connection status
6. Capture screenshot

**Expected Logs**:
```
I/OBDManager: Pairing screen displayed
I/OBDManager: Connecting to <adapter>
I/OBDManager: Connection successful
```

Or (if no adapter):
```
I/OBDManager: No OBD adapter available
```

**Success Criteria**:
- OBD tab accessible
- Pairing UI displays
- Connection attempt logs appear
- No crashes or permission errors

**Manual Testing**:
```bash
adb shell input swipe 500 1600 500 400
sleep 1
adb shell input tap 540 1200             # Tap OBD tab
sleep 2
adb exec-out screencap -p > obd_pairing.png
```

**Automated**:
```bash
./android-adb-test.sh build-and-test --scenario obd-pairing --screenshots
```

---

## Scenario: Settings

**Purpose**: Test settings screen navigation and option toggles.

**Flow**:
1. Launch app
2. Navigate to Settings tab
3. Verify settings options visible (theme, notifications, etc.)
4. Attempt to toggle a setting (e.g., Dark Mode)
5. Verify preference persists
6. Capture screenshot

**Expected Logs**:
```
I/SettingsVM: Settings screen loaded
I/SettingsVM: Preference updated: <key>=<value>
```

**Success Criteria**:
- Settings tab accessible
- Options display correctly
- Preference changes applied
- No crashes

**Manual Testing**:
```bash
adb shell input swipe 500 1600 500 400
sleep 1
adb shell input tap 540 1700             # Tap Settings
sleep 2
adb shell input tap 540 400              # Toggle setting
sleep 1
adb exec-out screencap -p > settings.png
```

**Automated**:
```bash
./android-adb-test.sh build-and-test --scenario settings --screenshots
```

---

## Scenario: ANPR (License Plate Recognition)

**Purpose**: Test camera view and ANPR detection UI.

**Flow**:
1. Launch app
2. Navigate to Camera/ANPR screen
3. Request camera permission if needed
4. Wait for camera preview
5. Verify ANPR detection overlay visible
6. Wait 3s for any detections
7. Capture screenshot

**Expected Logs**:
```
I/CameraX: Camera opened
I/ANPRManager: Detection started
I/ANPRManager: Plate detected: <confidence>%
```

Or:
```
W/ANPRManager: No plates detected
```

**Success Criteria**:
- Camera permission granted
- Preview displays
- Detection overlay visible
- No crashes or permission denials

**Manual Testing**:
```bash
# First, grant camera permission
adb shell pm grant cz.mia.app android.permission.CAMERA
# Then run scenario
adb shell am start -n cz.mia.app/.MainActivity
sleep 1
adb shell input tap 540 1000             # Tap camera/ANPR
sleep 3
adb exec-out screencap -p > anpr.png
```

**Automated**:
```bash
./android-adb-test.sh build-and-test --scenario anpr --screenshots --logs
```

---

## Scenario: Full Flow

**Purpose**: End-to-end user journey combining all features.

**Flow**:
1. Dashboard scenario
2. BLE Scan scenario
3. OBD Pairing scenario
4. Settings scenario
5. ANPR scenario

**Use Case**:
- Comprehensive regression testing
- Verify feature interactions
- Detect UI state conflicts

**Automated**:
```bash
./android-adb-test.sh build-and-test --scenario full-flow --screenshots --logs
```

**Output**:
```
apps/android/test-artifacts/<timestamp>/
├── screenshots/
│   ├── dashboard_initial.png
│   ├── dashboard_telemetry.png
│   ├── ble_scan_screen.png
│   ├── obd_pairing.png
│   ├── settings.png
│   ├── anpr_camera.png
├── logs/
│   └── logcat.txt
└── reports/
    └── test-report.json
```

---

## Scenario: Interactive

**Purpose**: Manual debugging and exploration.

**Commands**:
```bash
tap X Y              # Tap at coordinates
swipe X1 Y1 X2 Y2   # Swipe from to
text "string"        # Enter text
screenshot [name]    # Capture screen
logcat               # View recent logs
exit                 # End session
```

**Usage**:
```bash
./android-adb-test.sh interactive --device <serial>

# Example interactive session
> tap 540 800
✓ Tapped at (540,800)

> screenshot dashboard
📸 Screenshot: dashboard_1702345678.png

> logcat
I/cz.mia.app: Dashboard loaded
I/DashboardVM: Telemetry: RPM=1200
...

> exit
```

---

## Custom Scenarios

Create scenario functions in the main script:

```bash
scenario_custom_flow() {
  log "Scenario: custom flow"
  
  # Launch and stabilize
  adb_tap 540 800       # Tap element A
  adb_swipe 100 500 900 500  # Swipe
  take_screenshot "step_1"
  
  sleep 2
  adb_text "search query"
  take_screenshot "step_2"
  
  adb_tap 540 1000      # Tap element B
  sleep 3
  take_screenshot "step_3"
}
```

Then run:
```bash
./android-adb-test.sh build-and-test --scenario custom-flow --screenshots --logs
```

---

## Logcat Analysis During Tests

### Monitor for specific errors
```bash
adb logcat -d | grep -E "FATAL|Error|timeout|Permission denied"
```

### Extract performance metrics
```bash
# App startup time (from launch to first UI log)
adb logcat -d | grep "MainActivity\|Dashboard"
```

### Check memory during test
```bash
adb shell dumpsys meminfo cz.mia.app
```

### Verify no hangs (check for recent logs)
```bash
# If logcat shows no new logs for 30s, app may be frozen
adb logcat -d -t 60 | tail -5
```

---

## Continuous Integration Integration

### GitHub Actions Example
```yaml
name: Android Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Android Emulator
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 30
      
      - name: Run Tests
        run: |
          ./apps/android/tools/android-adb-test.sh build-and-test \
            --scenario full-flow \
            --screenshots \
            --logs \
            --device emulator-5554
      
      - name: Upload Artifacts
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-artifacts
          path: apps/android/test-artifacts/
```

### Linking to Subagent Analysis
```bash
# Spawn logcat analyzer subagent after test completes
sessions_spawn --task "
Analyze logcat from test run at: apps/android/test-artifacts/<timestamp>/logs/logcat.txt
Look for errors, crashes, permission issues.
Report findings and recommendations.
"
```
