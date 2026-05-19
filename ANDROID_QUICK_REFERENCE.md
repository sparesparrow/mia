# Android Testing Quick Reference

> **Audience**: Developers who already know the system — quick lookup only

For the complete guide, see [ANDROID_TESTING.md](ANDROID_TESTING.md).

---

## Most Common Commands

```bash
# Full build + test
bash scripts/test-orchestrator.sh HT36TW903516 full-flow 1

# Build only
bash skills/android-adb-test/scripts/android-adb-test.sh build

# Deploy only
bash skills/android-adb-test/scripts/android-adb-test.sh deploy --device HT36TW903516

# Interactive testing
bash skills/android-adb-test/scripts/android-adb-test.sh interactive --device HT36TW903516

# Analyze logcat
bash scripts/spawn-test-tasks.sh all apps/android/test-artifacts/<timestamp>
```

---

## Scenarios

| Scenario | Purpose | Time |
|----------|---------|------|
| `dashboard` | UI load + telemetry | 5s |
| `ble-scan` | Device discovery | 15s |
| `obd-pairing` | Adapter pairing | 5s |
| `settings` | Settings persistence | 5s |
| `anpr` | License plate detection | 5s |
| `full-flow` | All of above | 30s |
| `interactive` | Manual debugging | N/A |

```bash
bash scripts/test-orchestrator.sh <device> <scenario>
```

---

## Interactive Commands

| Command | Effect |
|---------|--------|
| `tap 540 800` | Tap at X,Y |
| `swipe 100 500 900 500` | Swipe from→to |
| `text "hello"` | Type text |
| `screenshot` | Capture screen |
| `logcat` | Show recent logs |
| `exit` | End session |

---

## Device Check

```bash
adb devices                                    # List devices
adb shell getprop ro.product.model             # Device info
adb shell pm clear cz.mia.app                  # Clear app data
adb logcat -d -s "cz.mia.app:*" | tail -20    # Recent logs
adb kill-server && adb start-server            # Reset ADB
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Device not found | `adb devices` → accept debug prompt on device |
| Build fails | `cd apps/android && ./gradlew clean assembleDebug` |
| App crashes | `adb logcat -d \| grep "FATAL" -A5` |
| Test hangs | `adb shell am force-stop cz.mia.app` |
| Can't connect | `adb kill-server && adb start-server` |

---

## Artifacts

```
apps/android/test-artifacts/<YYYYMMDD_HHMMSS>/
├── screenshots/    # PNG captures
├── logs/           # logcat.txt
└── reports/        # test-report.json
```

---

## Reference Docs

| File | Content |
|------|-------|
| [ANDROID_TESTING.md](ANDROID_TESTING.md) | **Complete guide** — start here |
| `skills/android-adb-test/SKILL.md` | Skill spec + workflows |
| `skills/android-adb-test/references/adb-commands.md` | 60+ ADB commands |
| `skills/android-adb-test/references/logcat-patterns.md` | Error patterns |
| `skills/android-adb-test/references/test-scenarios.md` | Scenario specs |
