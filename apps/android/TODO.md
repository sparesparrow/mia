# MIA Android: Active Backlog

This file tracks the live Android backlog for `apps/android/`. It replaces the older generated checklist that mixed completed claims, speculative roadmap items, and stale package or path references.

Last reviewed: 2026-04-08

## Current State

- App identity is `cz.mia.app`
- Main app code lives under `apps/android/app/src/main/java/cz/mia/app/`
- The project already contains Compose UI, Hilt DI, Room, Retrofit, WebSocket, BLE, CameraX, ANPR, DVR, voice, WorkManager, and LED-monitor surfaces
- Build config currently lives in [app/build.gradle](app/build.gradle)
- A version catalog also exists in [gradle/libs.versions.toml](gradle/libs.versions.toml), but the app build still uses hardcoded dependency versions

## What Changed In This Rewrite

- Removed the “all phases complete” and “production-ready” claims
- Removed stale references to `cz.aiservis.app` and top-level `android/` paths as the source of truth
- Replaced large speculative feature lists with a smaller set of active engineering priorities
- Kept future work only where it is still useful for planning

## Priority A0: Build and Tooling Health

### A0.1 Restore Debug Build

- [ ] Restore a repeatable `cd apps/android && ./gradlew assembleDebug`
- [ ] Capture the actual failure mode and fix the minimal root cause instead of adding more build workarounds
- [ ] Verify the same path in CI after the local build is restored

### A0.2 Align Build Configuration

- [ ] Decide whether to keep hardcoded dependency versions in [app/build.gradle](app/build.gradle) or migrate to the existing version catalog in [gradle/libs.versions.toml](gradle/libs.versions.toml)
- [ ] Align Compose, Kotlin, AGP, Hilt, and test dependency versions so the build description has one clear source of truth
- [ ] Document the minimum supported JDK, Android SDK, and Gradle versions for local development

### A0.3 Fix Android Documentation Drift

- [ ] Update [README.md](README.md) so package names, paths, and examples match `cz.mia.app` and `apps/android/`
- [ ] Remove or rewrite stale statements that imply the Android app is already fully shipped or app-store ready

## Priority A1: Runtime Integration

### A1.1 Backend Contract Alignment

- [ ] Verify `API_BASE_URL` and `WS_BASE_URL` usage against the current Raspberry Pi backend surfaces
- [ ] Align Android data models with the normalized telemetry contract once the root backlog item lands
- [ ] Keep transport-specific Audi/VAG protocol details out of Android unless a dedicated diagnostics UI is explicitly chosen

### A1.2 Real Device Validation

- [ ] Validate BLE scan, connect, disconnect, and reconnect flows on supported Android versions
- [ ] Validate OBD pairing and command flow against a real Pi-backed environment, not only mock or emulator paths
- [ ] Validate offline and poor-connectivity behavior for REST and WebSocket flows

### A1.3 Background and Worker Paths

- [ ] Verify WorkManager, health ping, and continuous-monitoring paths under realistic battery and background limits
- [ ] Confirm background behavior does not silently regress on newer Android versions

## Priority A2: Feature Surface Audit

### A2.1 Dashboard and Telemetry

- [ ] Audit dashboard, alerts, clips, and telemetry screens against the current backend payloads
- [ ] Remove or mark any UI that depends on contract assumptions no longer guaranteed by the backend

### A2.2 LED and Vehicle Views

- [ ] Verify the LED monitor path against the current backend and hardware surfaces before expanding it further
- [ ] Decide whether Android should expose normalized vehicle data only or add explicit read-only Audi diagnostics views later

### A2.3 Data Layer Consistency

- [ ] Audit Room entities, repositories, and cached-state handling for consistency between `data/repository/` and `data/repositories/`
- [ ] Confirm migration and persistence behavior for the current database schema

## Priority A2: Testing and QA

### A2.4 Fast Checks

- [ ] Restore and document a minimum Android validation set:
  - `./gradlew assembleDebug`
  - `./gradlew testDebugUnitTest`
  - `./gradlew lint`

### A2.5 Device and Instrumentation Coverage

- [ ] Define which flows require a physical device instead of emulator coverage
- [ ] Add or refresh instrumentation coverage for the screens and managers that remain active development surfaces
- [ ] Publish a small device and Android-version test matrix for contributors and CI

## Priority A3: Cleanup and Future Work

### A3.1 Cleanup

- [ ] Remove stale backlog items once their owning docs or implementation plans are moved elsewhere
- [ ] Keep this file focused on active Android work, not cross-repo deployment or speculative product roadmap items

### A3.2 Deferred Features

- [ ] Evaluate on-device ML only after build stability and runtime contract work are healthy
- [ ] Evaluate Wear OS, Android Automotive, and voice-assistant expansion only after the main app validation path is stable
- [ ] Keep enterprise and app-store readiness work deferred until the current build and device path are reliable

## Landed and Worth Preserving

- [x] `cz.mia.app` application structure exists and is non-trivial
- [x] Compose, Hilt, Room, BLE, networking, camera, ANPR, DVR, LED, and voice surfaces are present in code
- [x] Android-side CPython bootstrap tooling exists under `tools/`
- [x] Multiple ViewModels, repositories, screens, and tests already exist and should be evolved rather than re-planned from scratch

## Reference Files

- [README.md](README.md)
- [app/build.gradle](app/build.gradle)
- [gradle/libs.versions.toml](gradle/libs.versions.toml)
- [app/src/main/java/cz/mia/app/MainActivity.kt](app/src/main/java/cz/mia/app/MainActivity.kt)
- [app/src/main/java/cz/mia/app/MIAApplication.kt](app/src/main/java/cz/mia/app/MIAApplication.kt)
- [../../TODO.md](../../TODO.md)