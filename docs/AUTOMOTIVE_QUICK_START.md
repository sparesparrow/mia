# MIA Automotive Integration - Quick Start Guide

> **Audience**: End users, vehicle integrators, mechanics

## Overview

MIA Automotive Integration enables real-time vehicle diagnostics through Bluetooth Low Energy (BLE) communication between your Android device and a Raspberry Pi-based OBD-II adapter.

**Primary prototype vehicle**: Audi A4 B3 Cabriolet (2004)

## System Components

- **Raspberry Pi**: Acts as BLE OBD-II adapter, connects to vehicle's OBD-II port
- **Android App**: Connects to Raspberry Pi via BLE, displays real-time vehicle data
- **OBD-II Protocol**: Standard automotive diagnostic protocol

## Quick Start

### 1. Install MIA App

1. Download MIA app from Google Play Store (or install APK from GitHub Releases)
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

### 3. Connect Android App

1. Open MIA app on Android device
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

- **Audi A4 B3 Cabriolet (2004)**: Primary prototype — full VAG read-only diagnostics
- **Generic OBD-II**: Any vehicle with ELM327-compatible OBD-II adapter
- **Citroën C4 (PSA)**: Legacy support via dedicated bridge module
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

## Support

For additional help:
- **Documentation**: [Full Documentation](../README.md)
- **Issues**: [GitHub Issues](https://github.com/sparesparrow/mia/issues)
- **Email**: info@mia.cz

## Next Steps

- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
