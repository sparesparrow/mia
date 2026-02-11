# AI-Servis Automotive Integration - Quick Start Guide

## Overview

AI-Servis Automotive Integration enables real-time vehicle diagnostics through Bluetooth Low Energy (BLE) communication between your Android device and a Raspberry Pi-based OBD-II adapter.

## System Components

- **Raspberry Pi**: Acts as BLE OBD-II adapter, connects to vehicle's OBD-II port
- **Android App**: Connects to Raspberry Pi via BLE, displays real-time vehicle data
- **OBD-II Protocol**: Standard automotive diagnostic protocol

## Quick Start

### 1. Install AI-Servis App

1. Download AI-Servis app from Google Play Store (or install APK from GitHub Releases)
2. Open the app and grant Bluetooth permissions when prompted
3. Navigate to the OBD screen

### 2. Power On Raspberry Pi

The Raspberry Pi should automatically start BLE services on boot:

```bash
# On Raspberry Pi, verify services are running
sudo systemctl status mia-ble-obd
sudo systemctl status mia-ble-advertiser
```

If services are not running, start them:

```bash
sudo systemctl start mia-ble-obd
sudo systemctl start mia-ble-advertiser
```

### 3. Connect Android Device to Raspberry Pi

1. Open AI-Servis app on Android device
2. Navigate to OBD screen
3. Tap "Scan" button
4. Wait for "MIA OBD-II Adapter" to appear in the device list
5. Tap on "MIA OBD-II Adapter" to connect
6. Wait for connection to establish (status will show "Connected")

### 4. View Real-Time Vehicle Data

Once connected, the app will automatically start monitoring:
- **Engine RPM**: Current engine revolutions per minute
- **Vehicle Speed**: Current speed in km/h
- **Coolant Temperature**: Engine coolant temperature in °C
- **Fuel Level**: Current fuel level percentage
- **Engine Load**: Current engine load percentage

## Supported Vehicles

- **Citroën C4**: Full PSA protocol support
- **Generic OBD-II**: Any vehicle with ELM327-compatible OBD-II adapter
- **Protocols**: ISO 15765-4 (CAN), ISO 14230-4 (KWP2000), ISO 9141-2

## Troubleshooting

### No Devices Found During Scan

**Problem**: Android app cannot find "MIA OBD-II Adapter"

**Solutions**:
1. Verify Raspberry Pi is powered on and in Bluetooth range (within 10 meters)
2. Check that BLE services are running:
   ```bash
   sudo systemctl status mia-ble-advertiser
   ```
3. Verify Bluetooth adapter is enabled:
   ```bash
   hciconfig hci0
   # Should show "UP RUNNING"
   ```
4. Make Bluetooth discoverable:
   ```bash
   sudo hciconfig hci0 piscan
   ```

### Connection Fails

**Problem**: Android app cannot connect to Raspberry Pi

**Solutions**:
1. Check Bluetooth permissions in Android app settings
2. Verify BLE OBD service is running:
   ```bash
   sudo systemctl status mia-ble-obd
   ```
3. Check service logs for errors:
   ```bash
   sudo journalctl -u mia-ble-obd -n 50
   ```
4. Restart BLE services:
   ```bash
   sudo systemctl restart mia-ble-obd
   sudo systemctl restart mia-ble-advertiser
   ```

### No Data Received

**Problem**: Connected but no OBD data is displayed

**Solutions**:
1. Verify OBD-II adapter is connected to vehicle's OBD-II port
2. Check that vehicle ignition is ON (engine may need to be running)
3. Verify OBD worker is running:
   ```bash
   sudo systemctl status mia-obd-worker
   ```
4. Check ZeroMQ broker is running:
   ```bash
   sudo systemctl status zmq-broker
   ```
5. Review logs:
   ```bash
   sudo journalctl -u mia-obd-worker -f
   ```

### Bluetooth Range Issues

**Problem**: Connection drops or unstable

**Solutions**:
1. Ensure devices are within 10 meters of each other
2. Avoid physical obstructions between devices
3. Check for interference from other Bluetooth devices
4. Verify Raspberry Pi has adequate power supply (use official power adapter)

## Advanced Configuration

### Change Device Name

To change the advertised device name:

1. Edit `/opt/ai-servis/rpi/services/ble_advertiser.py`:
   ```python
   DEVICE_NAME = "Your Custom Name"
   ```

2. Restart service:
   ```bash
   sudo systemctl restart mia-ble-advertiser
   ```

### Adjust OBD Polling Rate

The Android app supports three sampling modes:
- **Normal**: 500ms intervals (default)
- **Reduced**: 2000ms intervals
- **Minimal**: 10000ms intervals

Change mode in the app's OBD settings screen.

### Enable Debug Logging

To enable verbose logging:

1. Edit service files to change log level:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. Restart services:
   ```bash
   sudo systemctl restart mia-ble-obd
   sudo systemctl restart mia-ble-advertiser
   ```

3. View logs:
   ```bash
   sudo journalctl -u mia-ble-obd -f
   ```

## System Requirements

### Raspberry Pi
- Raspberry Pi 4B (recommended) or Pi 3B+
- Bluetooth 4.0+ (BLE support)
- Raspberry Pi OS (Bullseye or later)
- Python 3.8+
- Root access for Bluetooth configuration

### Android Device
- Android 5.0 (API 22) or later
- Bluetooth 4.0+ (BLE support)
- Location permission (required for BLE scanning on Android 6.0+)

### Vehicle
- OBD-II compliant vehicle (1996+ in USA, 2001+ in Europe)
- OBD-II port accessible
- Vehicle ignition ON for diagnostics

## Support

For additional help:
- **Documentation**: [Full Documentation](../README.md)
- **Issues**: [GitHub Issues](https://github.com/sparesparrow/mia/issues)
- **Email**: info@ai-servis.cz

## Next Steps

- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
