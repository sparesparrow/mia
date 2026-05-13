# MIA Android Testing Guide

> **Audience**: Android developers, QA testers, CI/CD engineers

The single comprehensive guide for building, deploying, and testing the MIA Android app using the **android-adb-test skill** with subagent orchestration. For a quick command cheat-sheet, see [ANDROID_QUICK_REFERENCE.md](ANDROID_QUICK_REFERENCE.md).

## Table of Contents

- [Quick Start](#quick-start)
- [Skill Location & Structure](#skill-location--structure)
- [Usage Patterns](#usage-patterns)
- [Test Scenarios](#test-scenarios)
- [Subagent Orchestration](#subagent-orchestration)
- [Integration with Coding-Agent](#integration-with-coding-agent)
- [CI/CD Integration](#cicd-integration)
- [Output & Artifacts](#output--artifacts)
- [Device Check](#device-check)
- [Troubleshooting](#troubleshooting)
- [Reference Documentation](#reference-documentation)
- [Advanced: Custom Scenarios](#advanced-custom-scenarios)
- [Pro Tips](#pro-tips)
- [Learning Path](#learning-path)
- [Monitoring & Automation](#next-monitoring--automation)
- [Summary](#summary)

## Quick Start

### One-Command Build & Test
```bash
cd ~/projects/embedded/mia
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test --scenario dashboard --screenshots --logs
```

### With Device Specified
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test --scenario full-flow --screenshots --logs --device HT36TW903516
```

---

## Skill Location & Structure

**In MIA Project**:
```
~/projects/embedded/mia/
├── skills/
│   └── android-adb-test/           # Skill root
│       ├── SKILL.md                 # Skill definition
│       ├── scripts/
│       │   ├── android-adb-test.sh              # Main orchestrator
│       │   └── spawn-logcat-monitor.sh          # Subagent spawner
│       └── references/
│           ├── adb-commands.md                  # ADB command reference
│           ├── logcat-patterns.md               # Log patterns
│           └── test-scenarios.md                # Test scenarios
```

---

## Usage Patterns

### Pattern 1: Build Only (for CI verification)
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh build
# Output: apps/android/app/build/outputs/apk/debug/app-debug.apk
```

### Pattern 2: Deploy Only (for already-built APK)
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh deploy \
  --device HT36TW903516
```

### Pattern 3: Interactive Testing (manual debugging)
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh interactive \
  --device HT36TW903516
# Commands: tap X Y | swipe X1 Y1 X2 Y2 | text "str" | screenshot | logcat | exit
```

### Pattern 4: Test Specific Scenario
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh test \
  --scenario ble-scan --screenshots --logs --device HT36TW903516
```

### Pattern 5: Full CI Build → Deploy → Test → Analyze
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test \
  --scenario full-flow \
  --screenshots \
  --logs \
  --device HT36TW903516
```

---

## Test Scenarios

| Scenario | Purpose | Commands | Time |
|----------|---------|----------|------|
| `dashboard` | Verify UI loads, telemetry displays | Launch → screenshot | ~5s |
| `ble-scan` | Test Bluetooth device discovery | Swipe → tap BLE → wait scan → screenshot | ~15s |
| `obd-pairing` | Test OBD-II pairing flow | Navigate OBD tab → screenshot | ~5s |
| `settings` | Verify settings persistence | Navigate settings → toggle → screenshot | ~5s |
| `anpr` | Test license plate detection | Open camera → detect → screenshot | ~5s |
| `full-flow` | End-to-end user journey | Dashboard → BLE → OBD → Settings → ANPR | ~30s |
| `interactive` | Manual debugging shell | Manual tap/swipe/text commands | N/A |

---

## Subagent Orchestration

### Spawn Logcat Monitor Subagent

After running tests, analyze logs for errors/crashes:

```bash
# Spawn subagent for readonly logcat analysis
sessions_spawn --task "
Analyze logcat from MIA Android test run.

Device: HT36TW903516
Duration: 30 seconds of logs

Logcat location: ~/projects/embedded/mia/apps/android/test-artifacts/20250218_084500/logs/logcat.txt

Parse for:
- Crashes (AndroidRuntime: FATAL EXCEPTION)
- Permission errors
- BLE connection failures
- OBD protocol errors
- Network/WebSocket timeouts
- Memory pressure warnings
- ANR (Application Not Responding)

Return JSON report with:
{
  \"status\": \"pass|fail\",
  \"error_count\": <int>,
  \"crash_count\": <int>,
  \"errors\": [
    {\"type\": \"crash|permission|ble|network|obd|memory\",
     \"message\": \"...\",
     \"severity\": \"error|warning\",
     \"line\": \"...\"}
  ],
  \"recommendations\": [\"action 1\", \"action 2\"]
}
"
```

---

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/android-test.yml`:

```yaml
name: Android Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'apps/android/**'
      - '.github/workflows/android-test.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'apps/android/**'

jobs:
  build-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Android SDK
        uses: android-actions/setup-android@v2
        with:
          api-level: 34
          build-tools: 34.0.0
      
      - name: Build APK
        run: |
          cd apps/android
          chmod +x gradlew
          ./gradlew assembleDebug
      
      - name: Upload Artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: android-test-artifacts
          path: apps/android/test-artifacts/
```

---

## Output & Artifacts

After each test run, artifacts are saved to:

```
apps/android/test-artifacts/<YYYYMMDD_HHMMSS>/
├── screenshots/
│   ├── dashboard_initial_1702345678.png
│   ├── ble_scan_screen_1702345682.png
│   ├── obd_pairing_1702345684.png
│   └── settings_1702345686.png
├── logs/
│   └── logcat.txt
└── reports/
    └── test-report.json
```

---

## Device Check

```bash
adb devices
adb shell getprop ro.product.model
adb shell pm clear cz.mia.app
adb logcat -d -s "cz.mia.app:*" | tail -20
```

---

## Troubleshooting

### Device Not Found
```bash
adb devices
# Accept debug prompt on device, then retry
```

### APK Build Fails
```bash
cd apps/android
./gradlew assembleDebug --stacktrace
./gradlew clean
```

### App Crashes on Launch
```bash
adb logcat -d | grep -A5 "AndroidRuntime: FATAL"
adb shell pm list permissions -g | grep cz.mia.app
```

---

## Reference Documentation

- `apps/android/README.md` — Project overview
- `apps/android/docs/ARCHITECTURE.md` — App architecture & components
- `apps/android/docs/USER_GUIDE.md` — End-user guide
- `skills/android-adb-test/references/adb-commands.md` — ADB command reference
- `skills/android-adb-test/references/logcat-patterns.md` — Error patterns
- `skills/android-adb-test/references/test-scenarios.md` — Scenario specs

---

## Summary

| Task | Command | Time |
|------|---------|------|
| Build APK | `bash ... build` | ~60s |
| Deploy | `bash ... deploy` | ~10s |
| Test Dashboard | `bash ... test --scenario dashboard` | ~5s |
| Full-Flow Test | `bash ... build-and-test --scenario full-flow` | ~90s |
| Interactive Debug | `bash ... interactive` | Manual |

**Total CI/CD cycle**: ~2 minutes for full build → deploy → test → analyze.
