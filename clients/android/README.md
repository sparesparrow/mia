# MIA Android Companion App

This directory contains the Android companion application for MIA, providing mobile access to vehicle diagnostics, real-time telemetry, and control interfaces.

## Architecture

The Android app serves as the mobile interface for MIA, featuring:

- **Real-time vehicle telemetry** display
- **BLE device discovery** and connection
- **OBD-II diagnostic** data visualization
- **Voice command** processing and responses
- **Offline operation** with local data storage
- **Material Design 3** user interface

## Components

### App Structure

#### `app/src/main/java/cz/mia/app/`
Main application code:

- **core/** - Shared utilities and business logic
  - `background/BLEManager.kt` - Bluetooth Low Energy management
  - `background/MQTTManager.kt` - MQTT communication
  - `networking/` - HTTP/WebSocket clients
  - `rules/RulesEngine.kt` - Business rule processing

- **data/** - Data layer
  - `remote/` - API communication
  - `local/` - SQLite database and caching
  - `repository/` - Data access abstractions

- **ui/** - User interface (Compose)
  - `screens/` - Main application screens
  - `components/` - Reusable UI components
  - `theme/` - Material Design theming

- **di/** - Dependency injection (Hilt)

### Key Features

#### Bluetooth Low Energy (BLE)
- OBD-II adapter discovery and connection
- Real-time vehicle data streaming
- Connection reliability and reconnection logic
- Battery-optimized background operation

#### User Interface
- Material Design 3 implementation
- Dark/light theme support
- Responsive layouts for different screen sizes
- Accessibility compliance

#### Data Management
- Local caching for offline operation
- Real-time data synchronization
- Historical data analysis
- Export capabilities

## Development

### Prerequisites

#### System Requirements
- **Android Studio** Arctic Fox or later
- **JDK 17+**
- **Android SDK** API 33+
- **Kotlin** 1.9.0+

#### Device Requirements
- **Android 8.0+** (API 26+)
- **BLE support** (most modern Android devices)
- **GPS/location permissions** (for vehicle tracking)

### Setup

1. **Clone and open in Android Studio**
   ```bash
   cd android/
   # Open in Android Studio
   ```

2. **Install dependencies**
   ```bash
   ./gradlew build
   ```

3. **Configure signing** (for release builds)
   ```bash
   cp android/keystore.properties.example android/keystore.properties
   # Edit keystore.properties with your signing configuration
   ```

### Building

#### Debug Build
```bash
./gradlew assembleDebug
```

#### Release Build
```bash
./gradlew assembleRelease
```

#### Testing
```bash
# Unit tests
./gradlew testDebugUnitTest

# Instrumented tests
./gradlew connectedDebugAndroidTest
```

### Development Workflow

#### Code Style
- Kotlin coding conventions
- Detekt for static analysis
- Ktlint for code formatting

#### Testing Strategy
- **Unit tests** for business logic and utilities
- **Integration tests** for BLE and network operations
- **UI tests** for critical user flows
- **Manual testing** on physical devices

## Dependencies

### Core Libraries
```gradle
dependencies {
    // Compose BOM
    implementation platform('androidx.compose:compose-bom:2024.02.00')

    // Networking
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'

    // BLE
    implementation 'androidx.core:core-ktx:1.12.0'

    // Dependency injection
    implementation 'com.google.dagger:hilt-android:2.48'

    // Database
    implementation 'androidx.room:room-runtime:2.6.1'

    // MQTT
    implementation 'org.eclipse.paho:org.eclipse.paho.client.mqttv3:1.2.5'
}
```

### Generated Code
- **FlatBuffers** generated classes from shared schemas
- **Room** database entities and DAOs
- **Hilt** dependency injection components

## Deployment

### Internal Testing
```bash
# Build APK for internal testing
./gradlew assembleDebug

# Install on connected device
./gradlew installDebug
```

### Production Release
```bash
# Build signed APK
./gradlew assembleRelease

# Generate bundle for Play Store
./gradlew bundleRelease
```

### Play Store Configuration
- **Target SDK**: API 34
- **Min SDK**: API 26
- **Permissions**: Location, Bluetooth, Internet
- **Features**: BLE, GPS (optional)

## Integration

### Raspberry Pi Communication
- **WebSocket** for real-time data streaming
- **REST API** for command and control
- **MQTT** for pub/sub messaging
- **BLE fallback** for direct device communication

### Data Flow
1. **BLE Discovery** → Connect to OBD-II adapter
2. **Data Streaming** → Real-time telemetry to UI
3. **Command Processing** → Voice/text commands to vehicle
4. **Offline Storage** → Local caching and sync

## Testing

### Manual Testing Checklist
- [ ] BLE device discovery and pairing
- [ ] Real-time telemetry display
- [ ] Voice command processing
- [ ] Offline operation and sync
- [ ] UI responsiveness across screen sizes
- [ ] Battery optimization in background

### Automated Testing
```bash
# Run all tests
./gradlew test

# Run instrumentation tests
./gradlew connectedCheck

# Generate test coverage
./gradlew jacocoTestReport
```

## Performance Considerations

- **Battery optimization** for BLE operations
- **Memory management** for real-time data streams
- **Network efficiency** with compression and caching
- **UI smoothness** with background processing

## Security

- **Permission handling** for BLE and location
- **Data encryption** for sensitive vehicle data
- **Secure communication** with Raspberry Pi
- **Input validation** for all user inputs