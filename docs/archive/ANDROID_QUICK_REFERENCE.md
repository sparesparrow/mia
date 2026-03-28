# Android Testing Quick Reference

**Location**: `~/projects/embedded/mia/`

## 🔥 Most Common Commands

### Test (1 command)
```bash
bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1
```

### Build Only
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh build
```

### Deploy Only
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh deploy --device HT36TW903516
```

### Interactive Testing
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh interactive --device HT36TW903516
```

### Analyze Logcat
```bash
bash scripts/spawn-test-tasks.sh all apps/android/test-artifacts/<timestamp>
```

---

## 📋 Scenarios

| Cmd | Desc | Time |
|-----|------|------|
| `dashboard` | UI load + telemetry | 5s |
| `ble-scan` | Device discovery | 15s |
| `obd-pairing` | Adapter pairing | 5s |
| `settings` | Settings persistence | 5s |
| `anpr` | License plate detection | 5s |
| `full-flow` | All of above | 30s |

**Usage**:
```bash
bash scripts/test-orchestrator.sh <device> <scenario>
```

---

## 🎮 Interactive Commands

Once in interactive mode:

| Cmd | Effect |
|-----|--------|
| `tap 540 800` | Tap at X,Y |
| `swipe 100 500 900 500` | Swipe from→to |
| `text "hello"` | Type text |
| `screenshot` | Capture screen |
| `logcat` | Show recent logs |
| `exit` | End session |

---

## 📁 Artifact Structure

After each test:
```
apps/android/test-artifacts/20250218_084500/
├── screenshots/        # PNG captures
├── logs/              # logcat.txt
└── reports/           # test-report.json
```

View latest:
```bash
open "apps/android/test-artifacts/$(ls -t apps/android/test-artifacts | head -1)"
```

---

## 🔧 Device Check

```bash
# List devices
adb devices

# Get device info
adb shell getprop ro.product.model

# Clear app data
adb shell pm clear cz.mia.app

# View recent logs
adb logcat -d -s "cz.mia.app:*" | tail -20
```

---

## 🚨 Troubleshooting

| Issue | Fix |
|-------|-----|
| Device not found | `adb devices` → accept debug prompt |
| Build fails | `cd apps/android && ./gradlew clean assembleDebug` |
| App crashes | `adb logcat -d \| grep "FATAL" -A5` |
| Test hangs | `adb shell am force-stop cz.mia.app` |
| Can't connect | Restart adb: `adb kill-server && adb start-server` |

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `ANDROID_SKILL_README.md` | **START HERE** — Integration guide |
| `ANDROID_TESTING.md` | Complete testing guide |
| `skills/android-adb-test/SKILL.md` | Skill spec + workflows |
| `skills/android-adb-test/references/adb-commands.md` | 60+ ADB commands |
| `skills/android-adb-test/references/logcat-patterns.md` | Error patterns |
| `skills/android-adb-test/references/test-scenarios.md` | Scenario specs |

---

## 🎯 Typical Workflow

### 1. Change Code
Edit `apps/android/app/src/main/...`

### 2. Quick Test
```bash
bash scripts/test-orchestrator.sh HT36TW903516 dashboard 1
```

### 3. Review Results
```bash
# View screenshots
ls -lh apps/android/test-artifacts/*/screenshots/

# Check for errors
grep -i error apps/android/test-artifacts/*/logs/logcat.txt
```

### 4. Debug if Needed
```bash
bash skills/android-adb-test/scripts/android-adb-test.sh interactive \
  --device HT36TW903516
# Then: tap/swipe/screenshot manually
```

### 5. Commit & Push
GitHub Actions runs full test automatically

---

## 🤖 Subagent Tasks

```bash
# Analyze logcat
bash scripts/spawn-test-tasks.sh logcat \
  apps/android/test-artifacts/latest/logs/logcat.txt

# All analysis
bash scripts/spawn-test-tasks.sh all \
  apps/android/test-artifacts/latest
```

Spawns readonly monitors (doesn't modify device)

---

## 📞 Help

```bash
# Get help on main script
bash skills/android-adb-test/scripts/android-adb-test.sh -h

# Get help on orchestrator
bash scripts/test-orchestrator.sh

# Get help on subagent spawner
bash scripts/spawn-test-tasks.sh
```

---

## ⚡ Pro Tips

1. **Run tests in background**
   ```bash
   nohup bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1 > test.log &
   ```

2. **Monitor live logcat**
   ```bash
   adb logcat -v time | grep "cz.mia.app\|BLEManager"
   ```

3. **Quick permission grant**
   ```bash
   adb shell pm grant cz.mia.app android.permission.CAMERA
   ```

4. **Screenshot comparison**
   ```bash
   adb exec-out screencap -p > before.png
   # ... do something ...
   adb exec-out screencap -p > after.png
   diff <(md5sum *.png)
   ```

5. **Device screen mirror**
   ```bash
   scrcpy -s HT36TW903516
   ```

---

## 📦 What's Included

- ✅ Automated APK build
- ✅ Device deploy & launch
- ✅ 7 test scenarios
- ✅ ADB UI automation
- ✅ Screenshot capture
- ✅ Logcat parsing
- ✅ Subagent orchestration
- ✅ GitHub Actions workflow
- ✅ 60+ page documentation

---

**Start**: Read `ANDROID_SKILL_README.md`  
**Then**: Run `bash scripts/test-orchestrator.sh <device> dashboard 1`  
**Finally**: Integrate with your workflow 🚀
