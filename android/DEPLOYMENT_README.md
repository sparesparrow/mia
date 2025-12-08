# Android APK Deployment Guide

This guide covers deploying the MIA Universal Android app to devices and emulators.

## Prerequisites

### Hardware Requirements
- Android device with USB debugging enabled, or
- Android emulator (AVD) running

### Software Requirements
- Android SDK Platform Tools (ADB)
- PowerShell 7+ (for deployment scripts)
- Built APK (see Build Guide)

## Quick Deployment

### Using PowerShell Script (Recommended)

```powershell
# Deploy debug APK to auto-detected device
.\android\tools\deploy-apk.ps1 -BuildType Debug -Launch

# Deploy release APK to specific device
.\android\tools\deploy-apk.ps1 -BuildType Release -DeviceId "emulator-5554" -Launch

# Uninstall and reinstall
.\android\tools\deploy-apk.ps1 -BuildType Debug -UninstallFirst -Launch
```

### Manual ADB Commands

```bash
# List connected devices
adb devices

# Install debug APK
adb install -r android/app/build/outputs/apk/debug/app-debug.apk

# Install release APK
adb install -r android/app/build/outputs/apk/release/app-release.apk

# Launch app
adb shell am start -n cz.mia.app/.MainActivity

# View logs
adb logcat -s "MIA:*" "AndroidRuntime:E"
```

## Device Setup

### Physical Android Device

1. **Enable Developer Options**:
   - Go to Settings → About Phone
   - Tap "Build number" 7 times

2. **Enable USB Debugging**:
   - Settings → Developer Options
   - Enable "USB debugging"

3. **Connect Device**:
   - Connect via USB cable
   - Allow USB debugging when prompted
   - Verify: `adb devices` shows device

### Android Emulator

1. **Start Emulator**:
   ```bash
   # Via Android Studio or command line
   emulator -avd <avd_name>
   ```

2. **Verify Connection**:
   ```bash
   adb devices  # Should show emulator-5554
   ```

### Wireless ADB (Advanced)

```bash
# Connect device via USB first
adb tcpip 5555

# Disconnect USB, connect wirelessly
adb connect <device_ip>:5555

# Verify wireless connection
adb devices
```

## Troubleshooting

### Common Issues

**"Device not found"**
```bash
# Check USB connection
adb devices

# Restart ADB server
adb kill-server && adb start-server

# Check device permissions (Linux/Mac)
ls -la /dev/bus/usb/
```

**"INSTALL_FAILED_USER_RESTRICTED"**
- Disable "Verify apps over USB" in Developer Options
- Or use debug APK instead of release

**"INSTALL_PARSE_FAILED_MANIFEST_MALFORMED"**
- Check AndroidManifest.xml syntax
- Verify package name matches: `cz.mia.app`

### Log Analysis

```bash
# View app logs
adb logcat -s "MIA:*"

# View system logs
adb logcat -s "AndroidRuntime:*"

# Save logs to file
adb logcat -s "MIA:*" > app_logs.txt
```

## Citroën C4 Integration Testing

When testing with real Citroën C4 data:

1. **Connect ELM327 Adapter**:
   - OBD-II port under steering wheel
   - Use powered USB hub if needed

2. **Start Telemetry Bridge**:
   ```bash
   # From project root
   python modules/citroen-c4-bridge/main.py
   ```

3. **Monitor DPF Data**:
   - Check DPF soot mass readings
   - Monitor AdBlue levels
   - Test regeneration commands

4. **Voice Commands**:
   - "Check DPF status"
   - "Check AdBlue level"
   - "Run diagnostics"

## Performance Monitoring

### Battery Impact
- Monitor battery drain during telemetry streaming
- Typical impact: <5% additional drain

### Memory Usage
```bash
# Check app memory
adb shell dumpsys meminfo cz.mia.app
```

### Network Usage
```bash
# Monitor data usage
adb shell dumpsys netstats
```

## Release Deployment

### Google Play Store
1. Generate signed release APK
2. Upload to Play Console
3. Configure store listing
4. Publish to production

### Direct APK Distribution
1. Host APK on secure server
2. Provide download link
3. Users install via browser/adb

## Security Notes

- **Never distribute debug APKs** in production
- **Always use release signing** for public distribution
- **Store keystore securely** (offline, encrypted)
- **Rotate keys periodically** for security

## Support

For deployment issues:
1. Check device logs: `adb logcat`
2. Verify APK integrity: `unzip -t apk_file.apk`
3. Test on different devices/emulators
4. Review AndroidManifest.xml permissions
