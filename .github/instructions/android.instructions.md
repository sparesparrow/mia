---
description: "Use when working on the Android app, Jetpack Compose UI, Gradle builds, BLE or OBD flows, ADB/device testing, or Kotlin code under apps/android."
name: "Android App Guidance"
applyTo:
  - "apps/android/**"
  - "android/**"
  - "skills/android-adb-test/**"
  - "scripts/test-orchestrator.sh"
  - "scripts/test-android-ble-connection.sh"
  - "ANDROID_*.md"
---
# Android App Guidance

- Treat `apps/android/` as the primary Android app. The top-level `android/` directory only contains wrapper files such as `gradlew` and `gradle/`.
- Keep the existing app layering from [apps/android/README.md](../../apps/android/README.md): Compose screens and ViewModels stay thin; domain logic belongs in managers, repositories, and data-layer code.
- Match the build stack already pinned in [apps/android/app/build.gradle](../../apps/android/app/build.gradle) and [apps/android/gradle/libs.versions.toml](../../apps/android/gradle/libs.versions.toml): Kotlin 1.9.22, compileSdk/targetSdk 34, Java 17, Jetpack Compose, Hilt, Room, Retrofit/OkHttp, Nordic BLE, CameraX, ML Kit, and WorkManager.
- Keep the Android app identity stable. The package name is `cz.mia.app`; use that package in source, tests, ADB commands, and device scripts.
- Debug and release backend URLs already live in `BuildConfig` fields in [apps/android/app/build.gradle](../../apps/android/app/build.gradle). Update them centrally instead of hardcoding endpoints in screens, managers, or tests.
- BLE, camera, microphone, and location flows require runtime permission handling. Fail clearly and degrade safely when a permission or hardware capability is missing.
- Prefer Gradle validation for Android work: `cd apps/android && ./gradlew assembleDebug testDebugUnitTest lint`. Use `./gradlew connectedAndroidTest` only when a device or emulator is actually available.
- Use the existing device-testing workflows instead of ad hoc ADB sequences when you need build, deploy, screenshots, and logs together:
  - `bash scripts/test-orchestrator.sh <device-serial> <scenario> 1`
  - `bash skills/android-adb-test/scripts/android-adb-test.sh build|deploy|test|interactive ...`
- For BLE and OBD changes, prefer validation on a physical device. Emulator coverage is useful for UI and instrumentation work but is not enough for connection reliability changes.
- Root Python linters do not validate Android sources. Use Gradle and Android-specific tooling for Kotlin, Compose, and device-test verification.
- Related docs: [apps/android/README.md](../../apps/android/README.md), [ANDROID_TESTING.md](../../ANDROID_TESTING.md), [ANDROID_QUICK_REFERENCE.md](../../ANDROID_QUICK_REFERENCE.md), [docs/android-device-setup.md](../../docs/android-device-setup.md), and [../copilot-instructions.md](../copilot-instructions.md).