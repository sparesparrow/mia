---
mode: agent
description: "Android companion app — Kotlin, Jetpack Compose, BLE, MQTT, OBD dashboard, ANPR, DVR"
---

# MIA Android Client Worker

You own `apps/android/`. The mobile brain that talks to RPi and directly to ESP32 over BLE.

## Architecture

| Module | Purpose |
|--------|---------|
| `app` | MainActivity, navigation, voice entry |
| `data` | Repositories, MQTT/HTTP clients, Room DB |
| `domain` | Use cases, business logic |
| `ui` | Compose screens, themes, widgets |

## Stack

- Kotlin + Jetpack Compose + Material 3
- Hilt DI, Room DB, Retrofit/OkHttp
- MQTT client → RPi broker :1883
- REST → RPi FastAPI :8000
- BLE scanning for local ESP32 discovery
- WebSocket for real-time telemetry
- Package: `cz.mia.app` (affects ADB/logcat commands)
- Target SDK 34, Min SDK 22

## Conventions

- Gradle 8.x Kotlin DSL (`build.gradle.kts`)
- MVVM with `StateFlow` in ViewModels
- MQTT topic pattern: `mia/{device_id}/{component}/{action}`
- Navigation: Compose Navigation with typed routes
- Excluded from Python linting (`.pre-commit-config.yaml`)

## Key Commands

```bash
cd apps/android && ./gradlew assembleDebug
cd apps/android && ./gradlew test           # unit tests
adb logcat MIA:V *:S                        # app logs only
adb shell am start -n cz.mia.app/.MainActivity
```

## When working here

1. Align MQTT topics with RPi backend and ESP32 firmware
2. REST contracts must match `py-api/api/` endpoint shapes
3. BLE service UUIDs defined in `contracts/ble-gatt.md`
4. Use `@pytest.mark.android` for any cross-platform test touching Android
5. Don't modify Python linter configs — Android is excluded
