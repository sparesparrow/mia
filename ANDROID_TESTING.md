# MIA Android Testing Guide

Complete guide for building, deploying, and testing the MIA Android app using the **android-adb-test skill** with subagent orchestration.

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

### Orchestrate Build + Test + Analyze

```bash
#!/bin/bash
# Full test pipeline with subagent monitoring

DEVICE="HT36TW903516"

# 1. Build & deploy
echo "Building & deploying APK..."
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test \
  --scenario full-flow \
  --screenshots \
  --logs \
  --device "$DEVICE"

TEST_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOGCAT_PATH="apps/android/test-artifacts/$(ls -t apps/android/test-artifacts | head -1)/logs/logcat.txt"

# 2. Spawn logcat analyzer subagent (readonly)
echo "Spawning logcat analyzer..."
sessions_spawn --label "logcat-analyzer" --task "
Analyze logcat from MIA Android test: $LOGCAT_PATH
Focus on errors, crashes, permission issues.
Report JSON findings.
"

# 3. Spawn ADB command evaluator (readonly)
echo "Spawning ADB command evaluator..."
sessions_spawn --label "adb-evaluator" --task "
Verify ADB commands from test run: $DEVICE
Check connectivity, command latency, any disconnects.
Report JSON status.
"

# 4. Wait for results and aggregate
echo "Waiting for subagent results..."
# (Subagents complete async; main session gets notified)
```

---

## Integration with Coding-Agent

### Scenario: Code Change → Auto Test

```bash
# 1. Codex makes changes to BLEManager
bash skills/coding-agent/run.sh \
  "Refactor BLEManager for connection retry logic. Add exponential backoff."

# 2. Build new APK (from updated code)
bash skills/android-adb-test/scripts/android-adb-test.sh build

# 3. Spawn test subagent
sessions_spawn --task "
After BLEManager changes:
1. Deploy APK to device HT36TW903516
2. Run ble-scan scenario
3. Analyze logcat for connection errors
4. Report: Did retry logic work? Any timeouts?
"

# 4. Get report
# Subagent returns: Pass/Fail + specific errors found
```

### Scenario: Codex Reviews PR with Tests

```bash
# 1. Codex reviews PR code
bash skills/coding-agent/run.sh \
  "Review PR #42 for Android BLE changes. Check for thread safety, memory leaks."

# 2. Auto-test the PR branch
sessions_spawn --task "
Test MIA Android app from PR branch.

Steps:
1. Checkout PR branch
2. Build APK
3. Deploy to device
4. Run ble-scan + obd-pairing scenarios
5. Capture screenshots & logcat
6. Report pass/fail + any errors

Device: HT36TW903516
Scenarios: ble-scan, obd-pairing
"

# 3. Post results to GitHub
gh pr comment 42 --body "
✅ **Android Test Results**
- Build: PASS
- BLE Scan: PASS
- OBD Pairing: PASS
- Logcat: No errors

See artifacts: [link to test-artifacts]
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
      
      - name: Start Emulator
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          script: |
            bash ../../skills/android-adb-test/scripts/android-adb-test.sh \
              build-and-test \
              --scenario full-flow \
              --screenshots \
              --logs
      
      - name: Upload Artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: android-test-artifacts
          path: apps/android/test-artifacts/
      
      - name: Comment PR
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const artifacts = fs.readdirSync('apps/android/test-artifacts');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `✅ Android Tests Completed\n\nArtifacts: ${artifacts[0]}`
            });
```

### Local Pre-commit Hook

Create `scripts/pre-commit-android-test.sh`:

```bash
#!/bin/bash
# Run Android tests before commit on android/ changes

if git diff --cached --name-only | grep -q "apps/android"; then
  echo "Android files changed. Running tests..."
  
  bash skills/android-adb-test/scripts/android-adb-test.sh build && {
    echo "✓ Build passed"
    exit 0
  } || {
    echo "✗ Build failed. Commit aborted."
    exit 1
  }
fi
```

Install hook:
```bash
chmod +x scripts/pre-commit-android-test.sh
ln -s ../../scripts/pre-commit-android-test.sh .git/hooks/pre-commit
```

---

## Output & Artifacts

After each test run, artifacts are saved to:

```
apps/android/test-artifacts/<YYYYMMDD_HHMMSS>/
├── screenshots/
│   ├── dashboard_initial_1702345678.png      # Dashboard launch
│   ├── dashboard_telemetry_1702345680.png    # With data
│   ├── ble_scan_screen_1702345682.png        # BLE devices
│   ├── obd_pairing_1702345684.png            # OBD screen
│   ├── settings_1702345686.png               # Settings
│   └── anpr_camera_1702345688.png            # Camera preview
├── logs/
│   └── logcat.txt                            # Raw logcat (30s capture)
└── reports/
    ├── test-report.json                      # Summary
    └── logcat-analysis.json                  # Parsed errors (from subagent)
```

### View Latest Results

```bash
# Open latest test artifacts
open "apps/android/test-artifacts/$(ls -t apps/android/test-artifacts | head -1)"

# View screenshots
ls apps/android/test-artifacts/*/screenshots/

# Check logcat for errors
grep -E "FATAL|Error|timeout" apps/android/test-artifacts/*/logs/logcat.txt
```

---

## Troubleshooting

### Device Not Found
```bash
# Check connection
adb devices

# Accept debug prompt on device (should appear when USB connected)
# Then try again
adb devices
```

### APK Build Fails
```bash
# Check Gradle errors
cd apps/android
./gradlew assembleDebug --stacktrace

# Clear cache
./gradlew clean
```

### App Crashes on Launch
```bash
# Check logcat for crash
adb logcat -d | grep -A5 "AndroidRuntime: FATAL"

# Verify permissions granted
adb shell pm list permissions -g | grep cz.mia.app
```

### Scenario Hangs
```bash
# Manually check app state
adb shell dumpsys activity top

# Kill app and restart
adb shell am force-stop cz.mia.app
adb shell am start -n cz.mia.app/.MainActivity
```

---

## Reference Documentation

**Inside the skill** (`skills/android-adb-test/references/`):

- **adb-commands.md** — 60+ ADB commands (device mgmt, input, logs, transfers)
- **logcat-patterns.md** — Success/failure log patterns, filtering, error codes
- **test-scenarios.md** — Detailed scenario flows, manual + automated examples

**MIA Android App Docs**:

- `apps/android/README.md` — Project overview
- `apps/android/DEPLOYMENT_README.md` — APK deployment guide
- `apps/android/docs/ARCHITECTURE.md` — App architecture & components

---

## Advanced: Custom Scenarios

Add custom test flows to the skill:

```bash
# Create custom scenario in SKILL.md or extend scripts/android-adb-test.sh
scenario_custom_voice_command() {
  log "Scenario: Voice Command Flow"
  
  # Launch app
  adb -s "$DEVICE_SERIAL" shell am start -n "$PACKAGE_NAME/$MAIN_ACTIVITY"
  sleep 3
  take_screenshot "app_loaded"
  
  # Tap microphone button
  adb_tap 540 1200
  sleep 1
  take_screenshot "listening"
  
  # Simulate speech via text input
  adb_text "Turn on the light"
  sleep 2
  take_screenshot "command_sent"
  
  # Verify response
  adb_swipe 500 1600 500 400  # Scroll to log area
  sleep 1
  take_screenshot "response_visible"
}
```

Then run:
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test --scenario custom-voice-command --screenshots --logs
```

---

## Next: Monitoring & Automation

### Cron Job for Nightly Tests
```bash
# In HEARTBEAT.md or cron job:
0 2 * * * cd ~/projects/embedded/mia && \
  bash skills/android-adb-test/scripts/android-adb-test.sh \
  build-and-test --scenario full-flow --logs && \
  # Post results to Slack/email
```

### Continuous Monitoring
```bash
# Monitor device every 30 minutes for connectivity
*/30 * * * * adb devices | grep -q "device$" || \
  notify-send "MIA: Device disconnected"
```

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

**Ready to integrate with coding agents, GitHub Actions, and subagent orchestration!** 🚀
