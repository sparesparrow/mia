# Android ADB Test Skill - Integration Guide

This document explains how to use the **android-adb-test skill** within the MIA project for building, testing, and analyzing the Android app.

## 📍 Skill Location

```
~/projects/embedded/mia/skills/android-adb-test/
├── SKILL.md                                # Skill definition
├── scripts/
│   ├── android-adb-test.sh                # Main orchestrator
│   └── spawn-logcat-monitor.sh            # Subagent launcher
└── references/
    ├── adb-commands.md                     # ADB command reference
    ├── logcat-patterns.md                  # Log patterns
    └── test-scenarios.md                   # Test scenario details
```

## 🚀 Quick Start

### Option 1: Direct Script Usage
```bash
cd ~/projects/embedded/mia
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test --scenario dashboard --screenshots --logs
```

### Option 2: Test Orchestrator (Recommended)
```bash
bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1
# Returns test artifacts + spawns subagent analysis
```

### Option 3: With Subagent Spawning
```bash
# Spawn subagent for logcat analysis
bash scripts/spawn-test-tasks.sh logcat \
  apps/android/test-artifacts/20250218_084500/logs/logcat.txt

# Spawn all analyzers
bash scripts/spawn-test-tasks.sh all \
  apps/android/test-artifacts/20250218_084500
```

---

## 📋 Core Commands

### Build APK
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh build
```
**Output**: `apps/android/app/build/outputs/apk/debug/app-debug.apk`

### Deploy APK
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh deploy \
  --device HT36TW903516
```
**Output**: App installed and running on device

### Run Test Scenario
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh test \
  --scenario dashboard --screenshots --logs \
  --device HT36TW903516
```

### Full Build → Deploy → Test Pipeline
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test \
  --scenario full-flow \
  --screenshots \
  --logs \
  --device HT36TW903516
```

### Interactive Testing (Manual)
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh interactive \
  --device HT36TW903516
# Type: tap 540 800 | swipe 100 500 900 500 | text "hello" | screenshot
```

---

## 🎯 Test Orchestrator Workflow

**File**: `scripts/test-orchestrator.sh`

Orchestrates complete testing pipeline with subagent integration:

```bash
bash scripts/test-orchestrator.sh <device> [scenario] [verbose]
```

**Phases**:
1. **Build APK** — `./gradlew assembleDebug`
2. **Deploy APK** — `adb install -r <apk>`
3. **Run Scenario** — Execute test flow (dashboard, BLE, OBD, etc.)
4. **Collect Artifacts** — Screenshots, logcat, reports
5. **Spawn Logcat Analyzer** — Subagent analyzes errors/crashes
6. **Generate Report** — Summary JSON with findings

**Example**:
```bash
bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1

# Output:
# [08:46:15] MIA Android Test Orchestrator
# [08:46:15] Device: HT36TW903516
# [08:46:15] Scenario: full-flow
# [08:46:20] ✓ Device HT36TW903516 ready
# [08:46:25] ✓ Build complete
# [08:46:35] ✓ Deploy complete
# [08:47:05] ✓ Test scenario complete
# [08:47:06] Artifacts: apps/android/test-artifacts/20250218_084500
# [08:47:07] ✓ Logcat analyzer spawned (async)
# ✅ Test orchestration complete
```

---

## 🧠 Subagent Task Spawning

**File**: `scripts/spawn-test-tasks.sh`

Spawn readonly subagents for analysis:

### 1. Logcat Analyzer
```bash
bash scripts/spawn-test-tasks.sh logcat \
  apps/android/test-artifacts/20250218_084500/logs/logcat.txt \
  full-flow \
  HT36TW903516
```
Analyzes for: crashes, permission errors, BLE/OBD/network issues, memory warnings
Returns: JSON report with error summary + recommendations

### 2. ADB Command Verifier
```bash
bash scripts/spawn-test-tasks.sh adb \
  HT36TW903516 \
  "input tap 540 800"
```
Verifies: ADB connectivity, command success, performance, side effects
Returns: JSON with exit code, timing, stdout/stderr

### 3. Screenshot Comparator
```bash
bash scripts/spawn-test-tasks.sh screenshots \
  before-dir/ \
  after-dir/
```
Compares: UI changes, data rendering, visual issues
Returns: JSON list of changes with severity levels

### 4. Performance Analyzer
```bash
bash scripts/spawn-test-tasks.sh performance \
  apps/android/test-artifacts/20250218_084500/logs/logcat.txt
```
Extracts: Startup time, frame drops, memory usage, GC pauses
Returns: JSON metrics + threshold violations

### 5. Test Report Generator
```bash
bash scripts/spawn-test-tasks.sh report \
  apps/android/test-artifacts/20250218_084500 \
  HT36TW903516 \
  full-flow
```
Aggregates: All test data into markdown report
Returns: Actionable summary with pass/fail verdict

### 6. Spawn All Analyzers
```bash
bash scripts/spawn-test-tasks.sh all \
  apps/android/test-artifacts/20250218_084500
```
Spawns: logcat + performance + report generators in parallel

---

## 🔄 Integration with Coding-Agent

### Scenario: Codex Refactors → Auto Test

```bash
# 1. Make code changes with Codex
bash skills/coding-agent/run.sh \
  "Refactor BLEManager for connection retry logic"

# 2. Trigger test orchestration
bash scripts/test-orchestrator.sh HT36TW903516 ble-scan 1

# 3. Subagent analyzes results
# (Reports: Did retry logic work? Any new errors?)

# 4. Report back to Codex
# "Retry logic works. Connection failures: 0 in 30s test."
```

### Scenario: PR Auto-Test on GitHub

**Workflow**: `.github/workflows/android-test.yml`

When PR is submitted with Android changes:
1. Build APK from PR branch
2. Run test scenarios on emulator
3. Spawn logcat analyzers
4. Post results to PR comment

```yaml
# Result comment posted to PR:
# ✅ Android Tests Completed
# | Scenario | Status |
# |----------|--------|
# | dashboard | ✅ PASS |
# | ble-scan | ✅ PASS |
# | obd-pairing | ✅ PASS |
# | full-flow | ✅ PASS |
```

---

## 📊 Artifact Structure

Test runs produce timestamped artifacts:

```
apps/android/test-artifacts/20250218_084500/
├── screenshots/
│   ├── dashboard_initial_1702345678.png
│   ├── dashboard_telemetry_1702345680.png
│   ├── ble_scan_screen_1702345682.png
│   ├── obd_pairing_1702345684.png
│   ├── settings_1702345686.png
│   └── anpr_camera_1702345688.png
├── logs/
│   └── logcat.txt                        # Raw logcat
├── reports/
│   ├── test-report.json                  # Skill-generated summary
│   └── orchestrator-report.json           # Orchestrator summary
└── (other test artifacts)
```

### View Results
```bash
# Open latest artifacts
open "apps/android/test-artifacts/$(ls -t apps/android/test-artifacts | head -1)"

# View screenshots
ls apps/android/test-artifacts/*/screenshots/

# Check for errors
grep -iE "error|fatal|crash|timeout" \
  apps/android/test-artifacts/*/logs/logcat.txt
```

---

## 🔧 Reference Documentation

Inside the skill (`skills/android-adb-test/references/`):

### adb-commands.md
Comprehensive ADB command reference:
- Device management (list, select, restart)
- APK installation/uninstall
- App launch/control
- UI automation (tap, swipe, text)
- Screenshots & video
- Logcat filtering
- File transfer
- Permissions
- Reverse port forwarding

### logcat-patterns.md
Log pattern identification:
- MIA app tags (BLEManager, OBDManager, etc.)
- Success indicators
- Error patterns (crashes, permissions, BLE, network, OBD, memory)
- Log level guide
- Filtering examples
- Automated log parsing

### test-scenarios.md
Detailed test scenario specifications:
- Dashboard testing
- BLE device scanning
- OBD-II pairing
- Settings navigation
- ANPR detection
- Full-flow (end-to-end)
- Interactive mode
- Custom scenario examples

---

## 🚨 Troubleshooting

### Device Not Found
```bash
adb devices
# If "unauthorized", accept debug prompt on device
adb devices  # Try again
```

### Build Fails
```bash
cd apps/android
./gradlew clean assembleDebug --stacktrace
```

### App Crashes
```bash
adb logcat -d | grep -A5 "AndroidRuntime: FATAL"
```

### Test Hangs
```bash
# Check if device still responsive
adb shell getprop ro.product.model

# Check app logs
adb logcat -d -s "cz.mia.app:*" | tail -30
```

### Subagent Not Spawning
```bash
# Verify in OpenClaw context
command -v sessions_spawn

# Manual analysis fallback:
bash scripts/spawn-test-tasks.sh logcat <logcat_file>
# (Will still run even outside OpenClaw)
```

---

## 📝 Example Workflows

### Daily Regression Test
```bash
#!/bin/bash
DEVICE="HT36TW903516"
DATE=$(date +%Y%m%d)

bash scripts/test-orchestrator.sh "$DEVICE" full-flow

# Archive results
mkdir -p test-results/$DATE
cp -r apps/android/test-artifacts/latest/* test-results/$DATE/

# Notify team
echo "Daily Android tests completed" | mail team@example.com
```

### CI/CD Pipeline
```yaml
# .github/workflows/android-test.yml already included
# Runs on every push to apps/android/*
# Builds, tests, archives artifacts
```

### Manual PR Review
```bash
# 1. Get device
bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1

# 2. Manually inspect screenshots
open apps/android/test-artifacts/latest/screenshots/

# 3. Check logcat for concerns
grep -iE "error|warning" apps/android/test-artifacts/latest/logs/logcat.txt

# 4. Run specific scenario for deeper investigation
bash skills/android-adb-test/scripts/android-adb-test.sh interactive \
  --device HT36TW903516
```

---

## 🎓 Learning Path

1. **Start Simple**: Run dashboard scenario
   ```bash
   bash scripts/test-orchestrator.sh HT36TW903516 dashboard 1
   ```

2. **View Artifacts**: Check screenshots and logcat
   ```bash
   ls apps/android/test-artifacts/*/screenshots/
   ```

3. **Understand Errors**: Read logcat patterns
   ```bash
   cat skills/android-adb-test/references/logcat-patterns.md
   ```

4. **Manual Testing**: Use interactive mode
   ```bash
   bash skills/android-adb-test/scripts/android-adb-test.sh interactive \
     --device HT36TW903516
   ```

5. **Subagent Analysis**: Spawn analyzers
   ```bash
   bash scripts/spawn-test-tasks.sh all apps/android/test-artifacts/latest
   ```

6. **Full Pipeline**: Run orchestrator with all phases
   ```bash
   bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1
   ```

---

## 📞 Support

- **Skill**: `~/projects/embedded/mia/skills/android-adb-test/SKILL.md`
- **Orchestrator**: `~/projects/embedded/mia/scripts/test-orchestrator.sh`
- **MIA Docs**: `~/projects/embedded/mia/ANDROID_TESTING.md`
- **App Docs**: `~/projects/embedded/mia/apps/android/README.md`

---

**Ready to test MIA Android app end-to-end with subagent analysis!** 🚀
