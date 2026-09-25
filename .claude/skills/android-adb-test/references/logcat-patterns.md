# Logcat Patterns for MIA Android App

## MIA App Tags

### Core Tags
| Tag | Source | Purpose |
|-----|--------|---------|
| `cz.mia.app` | Main app | Application-level logs |
| `BLEManager` | core/background/BLEManager.kt | Bluetooth LE operations |
| `OBDManager` | core/background/OBDManager.kt | OBD-II protocol handling |
| `DVRManager` | core/background/DVRManager.kt | Video recording |
| `ANPRManager` | core/background/ANPRManager.kt | License plate recognition |
| `VoiceManager` | core/voice/ | Text-to-speech |
| `DashboardVM` | features/dashboard/ | Dashboard ViewModel |
| `WebSocketClient` | core/networking/ | WebSocket communication |

### System Tags
| Tag | Source | Purpose |
|-----|--------|---------|
| `AndroidRuntime` | System | Crashes and exceptions |
| `ActivityManager` | System | App lifecycle |
| `BluetoothAdapter` | System | Bluetooth hardware |
| `ConnectivityManager` | System | Network state |

## Success Indicators

### App Launch
```
I/ActivityManager: Start cz.mia.app/.MainActivity
I/cz.mia.app: MainActivity onCreate
I/cz.mia.app: MainActivity onResume
I/cz.mia.app: Dashboard screen loaded
```

### BLE Operations
```
I/BLEManager: Bluetooth adapter initialized
I/BLEManager: Starting device scan
I/BLEManager: Device discovered: <name> (<address>)
I/BLEManager: Connecting to <address>
I/BLEManager: Connected to <address>
I/BLEManager: GATT services discovered
I/BLEManager: Subscribed to characteristic <uuid>
```

### OBD Connection
```
I/OBDManager: Connecting to OBD adapter
I/OBDManager: OBD handshake successful
I/OBDManager: Protocol: CAN
I/OBDManager: Telemetry update: RPM=1200 Speed=45
```

### WebSocket
```
I/WebSocketClient: Connecting to ws://...
I/WebSocketClient: Connected
I/WebSocketClient: Message sent: <type>
I/WebSocketClient: Message received: <type>
```

### Voice/TTS
```
I/VoiceManager: Speaking: "<text>"
I/VoiceManager: Speech complete
I/VoiceManager: Audio focus acquired
```

### Video/DVR
```
I/DVRManager: Recording started
I/DVRManager: Recording stopped
I/DVRManager: Event clip extracted
```

## Error Indicators

### Crashes
```
E/AndroidRuntime: FATAL EXCEPTION: main
E/AndroidRuntime: Process: cz.mia.app, PID: <pid>
E/AndroidRuntime: java.lang.NullPointerException: Attempt to invoke virtual method on null object
```

Pattern: `AndroidRuntime.*FATAL` indicates app crash.

### Permission Errors
```
E/cz.mia.app: Permission denied: android.permission.BLUETOOTH_SCAN
E/ActivityManager: Permission Denial: opening provider com.android.launcher3 requires android.permission.READ_EXTERNAL_STORAGE
W/PermissionHelper: Missing permission: BLUETOOTH
```

Pattern: `Permission denied`, `Permission Denial`, `PERMISSION_DENIED`

### Bluetooth Failures
```
E/BLEManager: Bluetooth adapter null or not enabled
E/BLEManager: Connection timeout to <address>
E/BLEManager: GATT callback: status=<code> (connection refused)
E/BLEManager: Characteristic read failed: <uuid>
E/BluetoothAdapter: Error requesting power state change
W/BluetoothAdapter: Bluetooth adapter unavailable
```

Pattern: `BLEManager: Connection`, `BluetoothAdapter: Error`

### OBD Protocol Errors
```
E/OBDManager: Failed to parse OBD response: <data>
E/OBDManager: ELM327 error: NO DATA
E/OBDManager: OBD timeout waiting for response
E/OBDManager: Invalid PID response: <hex>
W/OBDManager: Partial response received
```

Pattern: `OBDManager:.*Error`, `OBDManager:.*timeout`, `OBDManager:.*Invalid`

### Network/WebSocket Errors
```
E/WebSocketClient: Connection failed: java.net.SocketTimeoutException
E/WebSocketClient: WebSocket closed: code=1000 reason=...
E/Retrofit: HTTP 500 Internal Server Error
E/OkHttp: Connection refused: <host>:<port>
W/ConnectivityManager: No default network available
```

Pattern: `WebSocketClient:.*fail`, `Retrofit:.*Error`, `timeout`

### Memory/ANR
```
W/cz.mia.app: Low memory: <available_mb> MB
E/ActivityManager: ANR in cz.mia.app (cz.mia.app/.MainActivity)
E/ActivityManager: Application Not Responding: cz.mia.app is not responding
D/MemoryTracker: OutOfMemoryError: Java heap space
```

Pattern: `Low memory`, `ANR`, `OutOfMemory`

### Video/Camera Errors
```
E/DVRManager: Camera unavailable
E/CameraX: Camera initialization failed
E/CameraX: Capture request failed
W/MediaRecorder: setAudioSource called in wrong state
```

Pattern: `DVRManager:.*fail`, `CameraX:.*fail`

### ANPR/ML Errors
```
E/ANPRManager: ML Kit failed to initialize
E/ANPRManager: Text recognition timeout
E/MLKit: Model loading failed
W/ANPRManager: Low confidence detection (<threshold>%)
```

Pattern: `ANPRManager:.*fail`, `MLKit:.*Error`

## Warning Indicators

### Performance Issues
```
W/cz.mia.app: Slow frame: took <ms>ms (target: 16ms for 60fps)
W/ActivityManager: Excessive CPU usage by cz.mia.app
D/Choreographer: Skipped <n> frames! The application may be doing too much work.
```

Pattern: `Slow frame`, `Excessive CPU`, `Skipped.*frames`

### Battery/Power
```
W/BatteryManager: High discharge rate
W/PowerManager: Excessive wake lock held
I/PowerManager: Turning off screen (uid=<uid> reason=<reason>)
```

### Deprecated API Usage
```
W/System: ignoreFileProvider is true
D/deprecation: Method getMasterVolume in class AudioManager is deprecated
```

### Storage Issues
```
W/cz.mia.app: Low disk space (<available_mb> MB)
E/DVRManager: Failed to write video: No space left on device
W/DataStore: Failed to migrate old data
```

## Log Level Guide

| Level | Symbol | Meaning | Action |
|-------|--------|---------|--------|
| Verbose | V | Detailed debug info | Ignore in production tests |
| Debug | D | Debug-level info | Use for detailed analysis |
| Info | I | General information | Normal/expected events |
| Warning | W | Warning condition | Investigate if unexpected |
| Error | E | Error condition | Test fails if present |
| Fatal | F | Fatal error | Always indicates crash |

## Filtering Examples

### View only MIA app errors
```bash
adb logcat -s "cz.mia.app:*" "BLEManager:*" "OBDManager:*" "*:E"
```

### Monitor BLE operations with debug info
```bash
adb logcat -s "BLEManager:D" "BluetoothAdapter:D"
```

### Catch crashes and permission errors
```bash
adb logcat "*:E" | grep -E "AndroidRuntime|Permission|FATAL"
```

### Filter by app process only
```bash
PID=$(adb shell pidof -s cz.mia.app)
adb logcat --pid=$PID -v threadtime
```

### Real-time monitoring during development
```bash
adb logcat -v time | grep -E "cz.mia.app|BLEManager|OBDManager|AndroidRuntime"
```

## Parsing for Automation

### Extract crashes
```bash
adb logcat -d | grep "AndroidRuntime: FATAL" -A 10
```

### Count errors by type
```bash
adb logcat -d | grep -c "^E/BLEManager"
adb logcat -d | grep -c "Permission denied"
adb logcat -d | grep -c "timeout"
```

### Export structured logs
```bash
adb logcat -d -v json > logcat.json
```

### Monitor specific operation
```bash
adb logcat -c
# Perform action...
sleep 2
adb logcat -d -s "BLEManager:*" -v time
```
