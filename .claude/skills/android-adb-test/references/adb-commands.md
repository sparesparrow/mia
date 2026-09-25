# ADB Commands Reference for MIA Android Testing

## Device Management

### List connected devices
```bash
adb devices
adb devices -l  # With model/status
```

### Select device for commands
```bash
adb -s <serial> <command>
adb -e <command>  # Emulator only
adb -d <command>  # Physical device only
```

### Restart ADB server
```bash
adb kill-server
adb start-server
```

## APK Installation

### Install/reinstall APK
```bash
adb install path/to/app.apk
adb install -r path/to/app.apk  # Replace existing
adb install -g path/to/app.apk  # Grant permissions
adb install -r -g path/to/app.apk  # Both
```

### Uninstall app
```bash
adb uninstall <package_name>
adb uninstall -k <package_name>  # Keep data
```

### Check if app installed
```bash
adb shell pm list packages | grep <package>
```

## App Launch & Control

### Start app
```bash
adb shell am start -n <package>/<activity>
adb shell am start -n cz.mia.app/.MainActivity
```

### Kill app
```bash
adb shell am force-stop <package>
adb shell am kill cz.mia.app
```

### Get app process ID
```bash
adb shell pidof -s <package>
adb shell pidof -s cz.mia.app
```

### Clear app data
```bash
adb shell pm clear <package>
```

## UI Input Simulation

### Tap at coordinates
```bash
adb shell input tap 540 800
```

### Swipe gesture
```bash
adb shell input swipe 100 500 900 500
# Swipe left to right (100→900)
adb shell input swipe 900 500 100 500
# Swipe up to down
adb shell input swipe 500 100 500 900
# Long swipe (3 seconds)
adb shell input swipe 500 500 500 800 3000
```

### Text input
```bash
adb shell input text "hello world"
```

### Key events
```bash
adb shell input keyevent KEYCODE_BACK      # Back button
adb shell input keyevent KEYCODE_HOME      # Home
adb shell input keyevent KEYCODE_ENTER     # Enter/OK
adb shell input keyevent KEYCODE_MENU      # Menu
adb shell input keyevent KEYCODE_POWER     # Power button
```

## Screenshots & Video

### Screenshot
```bash
adb exec-out screencap -p > screen.png
adb shell screencap /sdcard/screen.png
adb pull /sdcard/screen.png .
```

### Screen recording
```bash
adb shell screenrecord --time-limit 30 /sdcard/video.mp4
adb pull /sdcard/video.mp4 .
```

## Logs & Debugging

### View logcat
```bash
adb logcat
adb logcat -v time              # With timestamps
adb logcat -v threadtime        # With thread ID
```

### Filter logcat
```bash
adb logcat -s "tag:*"           # Specific tag
adb logcat -s "tag1:*" "tag2:*" # Multiple tags
adb logcat | grep "pattern"     # grep filter
```

### Filter by app process
```bash
PID=$(adb shell pidof -s cz.mia.app)
adb logcat --pid=$PID
```

### Dump logcat to file
```bash
adb logcat -d > logcat.txt      # Dump current
adb logcat > logcat.txt         # Stream (Ctrl+C to stop)
```

### Clear logcat buffer
```bash
adb logcat -c
```

### View only errors
```bash
adb logcat *:E
adb logcat -s "*:E"
```

## File Transfer

### Push file to device
```bash
adb push local.txt /sdcard/
adb push file.apk /data/local/tmp/
```

### Pull file from device
```bash
adb pull /sdcard/file.txt .
adb pull /data/system/packages.list .
```

## System Information

### Get device properties
```bash
adb shell getprop              # All properties
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release  # Android version
adb shell getprop ro.serialno              # Serial number
```

### Check storage
```bash
adb shell df -h
adb shell du -sh /sdcard
```

### Memory info
```bash
adb shell dumpsys meminfo <package>
adb shell dumpsys meminfo cz.mia.app | head -20
```

### CPU info
```bash
adb shell dumpsys cpuinfo | grep cz.mia.app
```

### Running processes
```bash
adb shell ps
adb shell ps | grep cz.mia.app
```

## Permissions

### List app permissions
```bash
adb shell pm list permissions -g
adb shell pm list permissions -g | grep BLUETOOTH
```

### Grant/revoke permissions
```bash
adb shell pm grant <package> <permission>
adb shell pm grant cz.mia.app android.permission.BLUETOOTH_SCAN
adb shell pm revoke <package> <permission>
```

### Check granted permissions
```bash
adb shell dumpsys package <package> | grep -A10 "Permissions:"
```

## Bluetooth/Networking

### Enable/disable Bluetooth
```bash
adb shell settings put global bluetooth_on 1  # Enable
adb shell settings put global bluetooth_on 0  # Disable
```

### Check connected Bluetooth devices
```bash
adb shell dumpsys bluetooth_manager
```

### Check network
```bash
adb shell ping -c 4 8.8.8.8
adb shell netstat
```

### Check ADB connection mode
```bash
adb shell getprop ro.secure
adb shell getprop ro.debuggable
```

## Reverse Port Forwarding

For connecting Android app to localhost services during testing:

```bash
# Forward device port to host port
adb reverse tcp:5000 tcp:5000

# List all reversals
adb reverse --list

# Remove reversal
adb reverse --remove tcp:5000
```

Example: If you have OBD simulator on host:35000, make it accessible to app:
```bash
adb reverse tcp:35000 tcp:35000
# Then app connects to localhost:35000 (which reverses to host:35000)
```

## Common Testing Workflows

### Build, deploy, test, and capture logs
```bash
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n cz.mia.app/.MainActivity
adb logcat -c
sleep 2
timeout 30 adb logcat -v time > logcat.txt &
# ... perform manual interactions ...
```

### Take screenshot after action
```bash
adb shell input tap 540 800
sleep 1
adb exec-out screencap -p > screenshot_after_tap.png
```

### Monitor app startup time
```bash
adb logcat -c
adb shell am start -n cz.mia.app/.MainActivity
# Look for first UI log or activity lifecycle message
adb logcat -d | grep -E "onCreate|onResume|UI"
```
