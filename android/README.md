# MIA Android Application

A comprehensive Android application for vehicle telematics, ANPR (Automatic Number Plate Recognition), DVR recording, and OBD-II communication.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Building](#building)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Core Components](#core-components)
- [Contributing](#contributing)

## 🏗️ Architecture Overview

The application follows a clean architecture pattern with the following layers:

```
┌─────────────────────────────────────────────────┐
│                    UI Layer                      │
│  (Compose, Screens, ViewModels)                 │
├─────────────────────────────────────────────────┤
│                  Domain Layer                    │
│  (Managers, Rules Engine, Repositories)         │
├─────────────────────────────────────────────────┤
│                   Data Layer                     │
│  (Room Database, DataStore, Network)            │
└─────────────────────────────────────────────────┘
```

### Key Technologies

- **Kotlin** - Primary language
- **Jetpack Compose** - Modern declarative UI
- **Hilt** - Dependency injection
- **Room** - Local database
- **CameraX** - Camera operations (ANPR, DVR)
- **ML Kit** - Text recognition for license plates
- **Nordic BLE Library** - Bluetooth LE communication
- **Paho MQTT** - IoT messaging
- **WorkManager** - Background processing

## ✨ Features

### OBD-II Communication
- Bluetooth LE connection to ELM327/OBD-II adapters
- Real-time vehicle telemetry (RPM, speed, fuel, coolant, engine load)
- DTC (Diagnostic Trouble Code) reading and clearing
- Adaptive sampling modes (Normal, Reduced, Minimal)

### ANPR (License Plate Recognition)
- Real-time camera analysis using CameraX
- ML Kit text recognition with region-specific heuristics
- Privacy-preserving plate hashing
- Confidence-based filtering
- Support for CZ and EU plate formats

### DVR Recording
- Continuous video recording with rolling buffer
- Event-triggered clip extraction
- Automatic offload scheduling
- Storage management

### Voice Alerts
- Text-to-speech notifications
- Support for Czech and English locales
- Priority-based queue management
- Audio focus handling

### System Policy Management
- Battery-aware operation modes
- Thermal throttling detection
- Power save mode integration
- Advisory messages for users

## 📱 Requirements

- Android 7.0 (API 24) or higher
- Bluetooth LE support
- Camera (for ANPR and DVR)
- Microphone (for DVR audio)

### Permissions Required

```xml
<!-- Bluetooth -->
<uses-permission android:name="android.permission.BLUETOOTH" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />

<!-- Camera & Recording -->
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

<!-- Foreground Service -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
```

## 🔧 Setup

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- JDK 17
- Android SDK 34

### Clone and Open

```bash
git clone https://github.com/your-org/ai-servis.git
cd mia/android
```

Open the `android` folder in Android Studio.

### Configure Signing (Optional)

For release builds, create `keystore.properties` in the android root:

```properties
storeFile=path/to/keystore.jks
storePassword=your_store_password
keyAlias=your_key_alias
keyPassword=your_key_password
```

## 🔨 Building

### Using Gradle

```bash
# Debug build
./gradlew assembleDebug

# Release build
./gradlew assembleRelease

# All checks (build + test + lint)
./gradlew assembleDebug test lint
```

### Using Docker

```bash
# Debug build
./tools/build-in-docker.sh --task assembleDebug

# Run tests
./tools/build-in-docker.sh --test

# Run lint
./tools/build-in-docker.sh --lint

# All tasks
./tools/build-in-docker.sh --all
```

### Validate APK

```bash
./tools/validate-apk.sh
```

## 🧪 Testing

### Unit Tests

```bash
./gradlew test
```

Unit tests are located in `app/src/test/`:
- `OBDManagerTest` - OBD protocol parsing
- `BLEManagerTest` - Bluetooth communication
- `VoiceManagerTest` - TTS functionality
- `DVRManagerTest` - Video recording
- `SystemPolicyManagerTest` - Power management
- `BackoffTest` - Retry logic

### Instrumented Tests

```bash
./gradlew connectedAndroidTest
```

Instrumented tests are located in `app/src/androidTest/`:
- `DatabaseTest` - Room database operations
- `EventRepositoryTest` - Data persistence
- `DashboardScreenTest` - UI gauges
- `SettingsScreenTest` - Settings persistence

### Test Coverage

```bash
./gradlew createDebugCoverageReport
```

Reports are generated in `app/build/reports/coverage/`.

## 📁 Project Structure

```
android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/cz/aiservis/app/
│   │   │   │   ├── core/
│   │   │   │   │   ├── background/     # Service managers
│   │   │   │   │   │   ├── BLEManager.kt
│   │   │   │   │   │   ├── OBDManager.kt
│   │   │   │   │   │   ├── ANPRManager.kt
│   │   │   │   │   │   ├── DVRManager.kt
│   │   │   │   │   │   ├── DrivingService.kt
│   │   │   │   │   │   └── SystemPolicyManager.kt
│   │   │   │   │   ├── camera/         # Camera processing
│   │   │   │   │   ├── networking/     # Network utilities
│   │   │   │   │   ├── rules/          # Alert rules
│   │   │   │   │   ├── security/       # Privacy hashing
│   │   │   │   │   ├── storage/        # Preferences
│   │   │   │   │   └── voice/          # TTS
│   │   │   │   ├── data/
│   │   │   │   │   ├── db/             # Room database
│   │   │   │   │   └── repositories/   # Data access
│   │   │   │   ├── features/           # ViewModels
│   │   │   │   └── ui/
│   │   │   │       ├── components/     # Reusable UI
│   │   │   │       └── screens/        # Screen composables
│   │   │   └── res/                    # Resources
│   │   ├── test/                       # Unit tests
│   │   └── androidTest/                # Instrumented tests
│   └── build.gradle                    # App build config
├── tools/
│   ├── build-in-docker.sh              # Docker build script
│   ├── validate-apk.sh                 # APK validation
│   ├── bootstrap-obd.py                # OBD-II simulator
│   └── lib/
│       └── cpython_bootstrap.py        # Bundled CPython module
├── build.gradle                        # Project build config
└── Dockerfile                          # Build environment
```

## 🔩 Core Components

### BLEManager

Handles Bluetooth LE communication with OBD-II adapters:

```kotlin
interface BLEManager {
    val connectionState: StateFlow<BleConnectionState>
    val discoveredDevices: StateFlow<List<BleDeviceInfo>>
    
    suspend fun initialize()
    suspend fun startScanning()
    suspend fun connectWithRetry(deviceAddress: String): Boolean
    suspend fun sendCommand(command: String): String?
    suspend fun disconnect()
}
```

### OBDManager

Manages OBD-II protocol and vehicle telemetry:

```kotlin
interface OBDManager {
    val obdData: Flow<OBDData>
    val connectionStatus: StateFlow<OBDConnectionStatus>
    
    suspend fun startMonitoring()
    suspend fun stopMonitoring()
    fun setSamplingMode(mode: SamplingMode)
    suspend fun readDTCs(): List<DTCInfo>
    suspend fun clearDTCs(): Boolean
}
```

### ANPRManager

Performs real-time license plate recognition:

```kotlin
interface ANPRManager {
    val events: Flow<ANPREvent>
    val state: StateFlow<ANPRState>
    
    suspend fun startDetection()
    suspend fun stopDetection()
    fun bindPreview(previewView: PreviewView, lifecycleOwner: LifecycleOwner)
}
```

### VoiceManager

Provides text-to-speech alerts:

```kotlin
interface VoiceManager {
    val state: StateFlow<VoiceState>
    
    suspend fun speak(text: String)
    suspend fun speakNow(text: String, priority: SpeechPriority = SpeechPriority.CRITICAL)
    fun stop()
    fun setLocale(locale: Locale): Boolean
}
```

### DVRManager

Controls video recording and clip extraction:

```kotlin
interface DVRManager {
    val clipEvents: SharedFlow<ClipEvent>
    val state: StateFlow<DVRState>
    
    fun startRecording()
    fun stopRecording()
    fun triggerEventClip(reason: String)
    suspend fun bindCamera(lifecycleOwner: LifecycleOwner)
}
```

## 🎨 UI Components

### Dashboard Gauges

The dashboard displays real-time vehicle data with animated gauges:

- **Speedometer** - Circular gauge with needle indicator
- **RPM Gauge** - Tachometer with redline zone
- **Compact Gauges** - Fuel level, coolant temp, engine load

### Camera Preview Screen

Full-screen camera view with:

- ANPR detection overlay
- Detection statistics
- DVR recording controls
- Plate confidence indicators

### OBD Pairing Screen

Bluetooth device scanner with:

- Signal strength indicators
- Connection status
- Auto-discovery of OBD adapters

## 🛠️ Development Tools

### OBD-II Simulator

For testing BLE OBD integration without hardware:

```bash
# Interactive mode
python3 tools/bootstrap-obd.py

# Demo mode (60 seconds of simulated telemetry)
python3 tools/bootstrap-obd.py --demo 60

# Use bundled CPython (recommended)
python3 tools/bootstrap-obd.py --device "Test OBD"
```

### Bundled CPython

The `tools/lib/cpython_bootstrap.py` module provides bundled CPython 3.12.7 for cross-platform tool development:

```python
from lib.cpython_bootstrap import CPythonBootstrap

# Ensure Python is available
with CPythonBootstrap() as python_path:
    subprocess.run([python_path, "my_script.py"])

# Or use CLI
python3 tools/lib/cpython_bootstrap.py --info
python3 tools/lib/cpython_bootstrap.py script.py [args...]
```

Supported platforms:
- Linux (x86_64, aarch64)
- macOS (x86_64, arm64)
- Windows (x86_64)

### APK Deployment

After building, deploy to a connected Android device:

```bash
# Via KDE Connect (wireless)
kdeconnect-cli --list-devices
kdeconnect-cli --device <ID> --share app/build/outputs/apk/debug/app-debug.apk

# Via ADB (USB)
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n cz.mia.app/.MainActivity
```

## 🤝 Contributing

### Code Style

- Follow Kotlin coding conventions
- Use KDoc for public APIs
- Write unit tests for new functionality
- Run lint before committing

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure CI passes
4. Request review

### Commit Messages

Follow conventional commits:

```
feat: Add new feature
fix: Fix bug in component
docs: Update documentation
test: Add tests for feature
refactor: Refactor code without changing behavior
```

## 📄 License

Copyright © 2024 MIA. All rights reserved.
