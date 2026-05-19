# MIA Android App User Guide

> **Audience**: End users, vehicle owners

Welcome to the MIA Android application! This guide will help you get started with the app and make the most of its features.

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
1. Open the MIA app
2. Grant the following permissions when prompted:
   - **Bluetooth permissions** (Android 12+: BLUETOOTH_SCAN, BLUETOOTH_CONNECT)
   - **Location permission** (required for BLE scanning)
   - **Camera permission** (for ANPR features)
   - **Notification permission** (Android 13+)

### Permissions Explained

| Permission | Purpose |
|------------|--------|
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

## Telemetry Viewing

### Real-time Data

The app displays live telemetry from connected devices:

- **Speed** (km/h or mph)
- **RPM** (engine revolutions)
- **Temperature** (coolant, oil)
- **Fuel level**
- **Battery voltage**

### Supported OBD-II PIDs

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

- "Device not found": Ensure Bluetooth is on and location services enabled
- "Service discovery failed": Try resetting the OBD adapter (remove from OBD port 30s)
- "Missing permissions": Go to Settings > Apps > MIA > Permissions
- Connection drops: Move closer to the OBD adapter, check for BT interference

### API Connection Issues

- "Network error": Verify Wi-Fi connection and server is running
- "Authentication failed": Verify API credentials in build config

### Getting Logs

```bash
adb logcat -s BLEManager TelemetryWebSocket DeviceRepository
```

## FAQ

### Q: Which OBD-II adapters are supported?
**A:** BLE OBD-II adapters using Nordic UART Service (NUS). Compatible: Veepeak BLE OBD2, BAFX Bluetooth 4.0 OBD2, Vgate iCar Pro BLE.

### Q: Why does the app need location permission?
**A:** Android requires location permission for BLE scanning. The app does not track your location.

### Q: Can I use the app without internet?
**A:** Yes for BLE/OBD. API features (remote telemetry, device management) require internet.

### Q: What data is sent to the server?
**A:** Device telemetry readings, connection status, vehicle data (speed, RPM, etc.). All transmission controllable via app settings.

## Support

- GitHub Issues: https://github.com/sparesparrow/mia/issues
- See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
