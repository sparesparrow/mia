# AI-Servis Android App User Guide

Welcome to the AI-Servis Android application! This guide will help you get started with the app and make the most of its features.

## Table of Contents

1. [Installation](#installation)
2. [Initial Setup](#initial-setup)
3. [BLE Device Connection](#ble-device-connection)
4. [API Configuration](#api-configuration)
5. [Telemetry Viewing](#telemetry-viewing)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

## Installation

### Requirements
- Android 7.0 (API 24) or higher
- Bluetooth Low Energy (BLE) support
- Location services enabled
- Internet connection (for API features)

### Install from APK
1. Enable "Install from unknown sources" in Settings > Security
2. Download the APK file to your device
3. Open the APK file to install
4. Grant required permissions when prompted

### Install from Play Store
*(Coming soon)*

## Initial Setup

### First Launch
1. Open the AI-Servis app
2. Grant the following permissions when prompted:
   - **Bluetooth permissions** (Android 12+: BLUETOOTH_SCAN, BLUETOOTH_CONNECT)
   - **Location permission** (required for BLE scanning)
   - **Camera permission** (for ANPR features)
   - **Notification permission** (Android 13+)

### Permissions Explained

| Permission | Purpose |
|------------|---------|
| Bluetooth Scan | Discover nearby OBD-II devices |
| Bluetooth Connect | Connect to and communicate with devices |
| Location | Required by Android for BLE scanning |
| Camera | License plate recognition (ANPR) |
| Notifications | Background service alerts |

## BLE Device Connection

### Discovering Devices

1. Navigate to the **BLE Devices** screen
2. Tap the **Bluetooth icon** in the top bar or the **Start Scanning** button
3. Wait for devices to appear (scan runs for 10 seconds)
4. The app filters for known OBD-II adapter names:
   - OBD
   - ELM327
   - VGATE
   - VEEPEAK
   - BAFX

### Connecting to a Device

1. From the discovered devices list, tap on a device
2. Wait for the connection to establish (up to 15 seconds)
3. The app will:
   - Connect to the GATT server
   - Discover services
   - Enable notifications
   - Initialize the OBD adapter (ATZ, ATE0, ATL0, ATS0, ATSP0)

### Connection Status Indicators

| State | Icon | Description |
|-------|------|-------------|
| Disconnected | 🔵 Bluetooth | No active connection |
| Scanning | 🔍 Searching | Actively scanning for devices |
| Connecting | ⏳ Spinner | Connection in progress |
| Connected | ✅ Check | Successfully connected |
| Error | ❌ | Connection failed |

### Signal Strength

The signal strength indicator shows the RSSI (Received Signal Strength Indicator):

| Signal | RSSI Range | Quality |
|--------|------------|---------|
| Excellent | > -50 dBm | Very strong |
| Good | -50 to -60 dBm | Strong |
| Fair | -60 to -70 dBm | Moderate |
| Weak | < -70 dBm | Poor |

### Disconnecting

1. Tap on the connected device card
2. Tap **Disconnect** button
3. Or navigate away from the screen

## API Configuration

### Default Configuration

The app is configured to connect to:
- **API URL**: `http://192.168.1.100:8000/`
- **WebSocket URL**: `ws://192.168.1.100:8000`

### Changing API Endpoints

To connect to a different server:

1. Build the app with custom `BuildConfig` values:
   ```groovy
   buildConfigField 'String', 'API_BASE_URL', '"http://your-server:port/"'
   buildConfigField 'String', 'WS_BASE_URL', '"ws://your-server:port"'
   ```

2. Or modify the values in `android/app/build.gradle`

### Network Requirements

- The device must be on the same network as the server
- Port 8000 (or configured port) must be accessible
- For secure connections, use HTTPS/WSS

## Telemetry Viewing

### Real-time Data

The app can display live telemetry from connected devices:

- **Speed** (km/h or mph)
- **RPM** (engine revolutions)
- **Temperature** (coolant, oil)
- **Fuel level**
- **Battery voltage**

### Historical Data

Access historical telemetry through the API:

1. Navigate to the Dashboard
2. Select a time range
3. View charts and statistics

### Supported Sensors

| Sensor | OBD Command | Description |
|--------|-------------|-------------|
| Speed | 010D | Vehicle speed |
| RPM | 010C | Engine RPM |
| Coolant Temp | 0105 | Engine coolant temperature |
| Intake Air | 010F | Intake air temperature |
| Throttle | 0111 | Throttle position |
| Fuel Level | 012F | Fuel tank level |

## Troubleshooting

### BLE Connection Issues

#### "Device not found"
- Ensure Bluetooth is enabled
- Check that location services are on
- Make sure the OBD adapter is powered on
- Try moving closer to the device

#### "Service discovery failed"
- The device may not support the expected UART service
- Try resetting the OBD adapter
- Check if the adapter is compatible

#### "Missing permissions"
- Go to Settings > Apps > AI-Servis > Permissions
- Enable all required permissions
- Restart the app

#### Connection drops frequently
- Move closer to the OBD adapter
- Check for interference from other Bluetooth devices
- Ensure the adapter has sufficient power

### API Connection Issues

#### "Network error"
- Check Wi-Fi connection
- Verify the server is running
- Ensure correct API URL is configured
- Check firewall settings

#### "Authentication failed"
- Verify API credentials
- Check if the server requires authentication

### App Crashes

1. Clear app data:
   - Settings > Apps > AI-Servis > Storage > Clear Data
2. Reinstall the app
3. Report the issue with logs

### Getting Logs

Enable USB debugging and run:
```bash
adb logcat -s BLEManager TelemetryWebSocket DeviceRepository
```

## FAQ

### Q: Which OBD-II adapters are supported?
**A:** The app supports Bluetooth Low Energy (BLE) OBD-II adapters that use the Nordic UART Service (NUS) or similar UART-over-BLE protocols. Common compatible adapters include:
- Veepeak BLE OBD2
- BAFX Bluetooth 4.0 OBD2
- Vgate iCar Pro BLE

### Q: Why does the app need location permission?
**A:** Android requires location permission for Bluetooth scanning because BLE beacons can be used for location tracking. This is a platform requirement, and the app does not track your location.

### Q: Can I use the app without an internet connection?
**A:** Yes, for BLE device communication and local OBD queries. API features (remote telemetry, device management) require internet connectivity.

### Q: How do I pair my OBD adapter?
**A:** The app handles pairing automatically. Simply scan for devices and tap to connect. No manual pairing in Android settings is required for BLE devices.

### Q: Why is scanning taking so long?
**A:** The default scan duration is 10 seconds to ensure all nearby devices are discovered. You can stop scanning early by tapping the Bluetooth icon again.

### Q: Can I connect to multiple devices?
**A:** Currently, the app supports one active BLE connection at a time. Future versions may support multiple connections.

### Q: How do I reset the OBD adapter?
**A:** The app sends an ATZ (reset) command automatically upon connection. For a hard reset, disconnect the adapter from the OBD port for 30 seconds.

### Q: What data is sent to the server?
**A:** The app can send:
- Device telemetry readings
- Connection status
- Vehicle data (speed, RPM, etc.)

All data transmission can be controlled through app settings.

### Q: Is my data secure?
**A:** For production use, configure HTTPS for API connections and WSS for WebSocket connections. BLE communication uses standard Android security.

## Support

For additional help:
- Check the [GitHub Issues](https://github.com/your-repo/ai-servis/issues)
- Contact support at support@example.com
- Join our community forum

## Version History

### v1.0.0
- Initial release
- BLE device scanning and connection
- OBD-II command support
- REST API integration
- WebSocket telemetry streaming
- ANPR camera integration
