# ANPR Quick Start Guide

Get your ANPR system up and running in 30 minutes.

## Step 1: Install Backend Dependencies (5 minutes)

```bash
cd /home/sparrow/projects/mia

# Install ANPR packages
pip install -r requirements.txt

# Verify
python -c "import easyocr; import cv2; print('✓ ANPR ready')"
```

## Step 2: Start Backend API (5 minutes)

```bash
# Terminal 1: Start ZeroMQ broker
cd /home/sparrow/projects/mia
python -m apps.rpi_backend.shared.messaging.broker

# Terminal 2: Start FastAPI server
cd /home/sparrow/projects/mia
PYTHONPATH=apps/rpi-backend/py-api python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 3: Test ANPR Endpoints (5 minutes)

### 3a: Health Check

```bash
curl http://localhost:8000/anpr/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "anpr": {
      "ready": true,
      "message": "ANPR OCR ready"
    },
    "edalnice": {
      "ready": true,
      "message": "Edalnice service available"
    }
  },
  "websocket_clients": 0
}
```

### 3b: Process Test Image

```bash
# Create test image or use existing
curl -X POST -F "file=@test_plate.jpg" \
  http://localhost:8000/anpr/process?auto_check_edalnice=true

# Expected response:
{
  "status": "success",
  "anpr": {
    "plates": [
      {
        "text": "AB12345CD",
        "confidence": 0.95,
        ...
      }
    ]
  },
  "scan_results": [
    {
      "plate": "AB12345CD",
      "is_exempted": false,
      ...
    }
  ]
}
```

### 3c: Test WebSocket Stream

```bash
# Using websocat or wscat
wscat -c ws://localhost:8000/anpr/stream

# Send ping to keep connection alive
{"type": "ping"}

# You should receive:
{"type": "pong", "timestamp": "2024-01-01T12:00:00"}
```

## Step 4: Configure ESP32 Camera (10 minutes)

### 4a: Edit Firmware Configuration

```bash
# Edit WiFi credentials
nano apps/esp32/main/camera_anpr.cpp

# Lines to modify:
31  const char* WIFI_SSID = "YOUR_SSID";              # ← Your WiFi SSID
32  const char* WIFI_PASSWORD = "YOUR_PASSWORD";      # ← Your WiFi password
33  const char* BACKEND_URL = "http://192.168.1.100:8000";  # ← Your backend IP
```

### 4b: Flash Firmware

```bash
cd /home/sparrow/projects/mia/apps/esp32

# Build and upload
pio run -e esp32cam-anpr -t upload --upload-port /dev/ttyUSB0

# Monitor serial output
pio device monitor -e esp32cam-anpr --baud 115200

# Expected output:
# === MIA ESP32 ANPR Camera ===
# Camera initialized successfully
# WiFi connected!
# IP address: 192.168.1.xxx
```

Set this IP on the backend so Android can trigger capture through `/anpr/capture`:

```bash
export ANPR_CAMERA_URL="http://192.168.1.xxx"
```

### 4c: Send Capture Command

```bash
# Via serial monitor or HTTP

# Serial command (type into monitor):
capture

# Or HTTP command:
curl -X POST http://localhost:8000/anpr/capture \
  -H "Content-Type: application/json" \
  -d '{"device_id": "esp32-camera", "capture_count": 1}'
```

## Step 5: Test Android App (5 minutes)

### 5a: Build Android App

```bash
cd /home/sparrow/projects/mia/apps/android

# Build debug APK
./gradlew assembleDebug

# Install on device/emulator
./gradlew installDebug
```

### 5b: Update Backend URL

```kotlin
// In apps/android/app/src/main/java/cz/mia/app/data/repository/ANPRRepository.kt
// Line 24:
private const val API_BASE_URL = "http://YOUR_BACKEND_IP:8000"
```

### 5c: Open ANPR Screen

1. Launch app
2. Navigate to "ANPR Camera" screen
3. Tap "Start Capture" button
4. Monitor real-time plate detections

## Step 6: End-to-End Test (10 minutes)

### Complete Flow

```
ESP32 Camera captures image
    ↓
Sends to Backend API (/anpr/process)
    ↓
Backend runs OCR → Detects plate
    ↓
Backend checks edalnice.cz → Gets status
    ↓
Broadcasts via WebSocket → Android app receives
    ↓
Android displays result with alert if exempted
```

### Test Commands

```bash
# Terminal 1: Monitor ESP32
pio device monitor -e esp32cam-anpr --baud 115200

# Terminal 2: Trigger capture
curl -X POST http://localhost:8000/anpr/capture \
  -H "Content-Type: application/json" \
  -d '{"device_id": "esp32-camera"}'

# Terminal 3: Check WebSocket (if clients connected)
curl http://localhost:8000/anpr/health | grep websocket_clients

# Terminal 4: Check history
curl http://localhost:8000/anpr/history
```

## Expected Outputs

### Successful Plate Detection

```json
{
  "status": "success",
  "anpr": {
    "plates": [
      {
        "text": "AB12345CD",
        "confidence": 0.95,
        "bbox": [[100, 50], [400, 50], [400, 200], [100, 200]]
      }
    ],
    "plate_count": 1,
    "timestamp": "2024-01-01T12:00:00.000Z"
  },
  "scan_results": [
    {
      "plate": "AB12345CD",
      "confidence": 0.95,
      "is_exempted": false,
      "edalnice_status": "success"
    }
  ]
}
```

### Exempted Vehicle Alert

```json
{
  "type": "plate_detected",
  "data": {
    "plate": "AB12345CD",
    "confidence": 0.95,
    "is_exempted": true,
    "exemption_reason": "Vozidlo osvobozeno"
  }
}
```

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| "EasyOCR not available" | `pip install easyocr` |
| ESP32 won't connect WiFi | Check SSID/password in camera_anpr.cpp |
| API returns 500 error | Check backend logs for import errors |
| No WebSocket connection | Verify backend is running on correct port |
| Low OCR accuracy | Improve lighting, increase JPEG quality to 90 |
| Android app crashes | Check API URL in ANPRRepository.kt matches backend |

## Next Steps

1. **Add Database**: Integrate with PostgreSQL for persistent storage
2. **Push Notifications**: Add alerts for exempted vehicles
3. **Historical Charts**: Track plate detection statistics
4. **Multiple Cameras**: Support multiple ESP32 devices
5. **Custom Models**: Train ML model specifically for Czech plates

## Help & Support

- Check logs: `tail -f /var/log/mia/api.log`
- View architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Full docs: [ANPR_IMPLEMENTATION.md](./ANPR_IMPLEMENTATION.md)
- Backend API: http://localhost:8000/docs
- WebSocket testing: `pip install websocat`

## Quick Commands Reference

```bash
# Check backend health
curl http://localhost:8000/anpr/health | jq .

# Check WebSocket connections
curl http://localhost:8000/anpr/health | jq '.websocket_clients'

# Trigger capture
curl -X POST http://localhost:8000/anpr/capture \
  -H "Content-Type: application/json" \
  -d '{"device_id": "esp32-camera", "camera_url": "http://ESP32_CAMERA_IP"}'

# Get scan history (last 10)
curl "http://localhost:8000/anpr/history?limit=10" | jq .

# Get vehicle alerts
curl http://localhost:8000/anpr/alerts | jq '.alerts'

# Monitor ESP32 logs
pio device monitor -e esp32cam-anpr --baud 115200 | grep -E "capture|WiFi|error"
```

## Performance Tips

- **Faster OCR**: Reduce confidence threshold to 0.5 (faster, less accurate)
- **Better Accuracy**: Increase confidence threshold to 0.8 (slower, more accurate)
- **Continuous Capture**: ESP32 captures every 5 seconds (adjustable in firmware)
- **Batch Processing**: Send multiple images for better throughput
- **Caching**: edalnice.cz results cached for 24 hours

## You're Done! 🎉

Your ANPR system is ready for production testing. Monitor the logs and adjust parameters based on real-world performance.

Happy plate hunting! 📸
