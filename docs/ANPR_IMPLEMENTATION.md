# ANPR (Automatic Number Plate Recognition) Implementation

Complete ANPR system for MIA vehicle telemetry platform with Czech license plate detection and edalnice.cz integration.

## 🎯 Features

- **License Plate Detection**: Real-time OCR for vehicle license plates using EasyOCR
- **Czech Plate Recognition**: Optimized for Czech plate format (2 letters + 3-5 digits + 2 letters)
- **Vehicle Status Checking**: Integration with edalnice.cz for vehicle exemption status
- **Live Alert System**: Real-time notifications for exempted vehicles ("Vozidlo osvobozeno")
- **WebSocket Streaming**: Real-time plate detection stream to Android app
- **Local Caching**: Intelligent caching of edalnice.cz lookups (24h TTL)
- **Image Preprocessing**: Contrast enhancement for improved OCR accuracy

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ ESP32-CAM (OV2640)                                           │
│ • Image capture on command                                   │
│ • JPEG compression (quality 85)                              │
│ • HTTP POST to backend                                       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────────────┐
│ RPi FastAPI Backend (Port 8000)                             │
│ ┌──────────────────────────────────────────────────────────┤
│ │ /anpr/* Routes                                            │
│ ├──────────────────────────────────────────────────────────┤
│ │ • POST /anpr/capture          - Trigger ESP32            │
│ │ • POST /anpr/process          - Process image + OCR      │
│ │ • GET  /anpr/history          - Scan history             │
│ │ • GET  /anpr/alerts           - Exempted vehicles        │
│ │ • WS   /anpr/stream           - Real-time stream         │
│ ├──────────────────────────────────────────────────────────┤
│ │ Services:                                                 │
│ │ • anpr_service.py             - OCR engine               │
│ │ • edalnice_service.py         - Czech vehicle API        │
│ └──────────────────────────────────────────────────────────┘
└────────────────────┬────────────────────────────────────────┘
                     │ WebSocket / API
┌────────────────────▼────────────────────────────────────────┐
│ Android App                                                  │
│ • ANPRScreen composable                                      │
│ • Real-time detection display                               │
│ • Capture control buttons                                    │
│ • Alert notifications                                        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Setup Instructions

### 1. Backend Dependencies (RPi)

Install Python ANPR packages:

```bash
cd /home/sparrow/projects/mia

# Install new dependencies
pip install easyocr opencv-python Pillow

# Verify installation
python -c "import easyocr; import cv2; print('ANPR dependencies OK')"
```

### 2. Backend Integration

The ANPR router is already integrated into FastAPI:

```python
# Added to apps/rpi-backend/py-api/api/main.py
from api.routers.anpr import router as anpr_router
app.include_router(anpr_router)
```

### 3. ESP32 Camera Setup

#### Hardware Requirements
- ESP32-CAM with OV2640 camera
- USB-to-UART adapter for programming
- 5V power supply (>1A)

#### Flash Firmware

```bash
cd /home/sparrow/projects/mia/apps/esp32

# Build with PlatformIO
pio run -e esp32cam-anpr -t upload

# Or configure WiFi and compile
# Edit main/camera_anpr.cpp:
# - Line 31: WIFI_SSID = "Your WiFi SSID"
# - Line 32: WIFI_PASSWORD = "Your WiFi Password"  
# - Line 33: BACKEND_URL = "http://YOUR_BACKEND_IP:8000"

# Configure backend control path (used by POST /anpr/capture)
export ANPR_CAMERA_URL="http://ESP32_CAMERA_IP"
```

#### Serial Monitor

```bash
# View ESP32 logs
pio device monitor -e esp32cam-anpr --baud 115200
```

### 4. Android App Integration

The ANPR screen is ready to use. Add it to your navigation:

```kotlin
// Add to your app navigation
NavHost(navController, startDestination = "home") {
    composable("home") { HomeScreen(navController) }
    composable("anpr") { ANPRScreen() }
    // ... other screens
}
```

## 📱 API Endpoints

### Trigger Camera Capture

```bash
POST /anpr/capture
Content-Type: application/json

{
  "device_id": "esp32-camera",
  "camera_url": "http://ESP32_CAMERA_IP",
  "capture_count": 1,
  "quality": 85,
  "auto_process": true
}

Response:
{
  "status": "success",
  "job_id": "capture_esp32-camera_1704067200.123",
  "message": "capture triggered"
}
```

### Process Image

```bash
POST /anpr/process
Content-Type: multipart/form-data

file: <image.jpg>
auto_check_edalnice: true

Response:
{
  "status": "success",
  "anpr": {
    "plates": [
      {
        "text": "AB12345CD",
        "confidence": 0.95,
        "raw_text": "AB 12345 CD",
        "bbox": [[100, 50], [400, 50], [400, 200], [100, 200]]
      }
    ],
    "plate_count": 1
  },
  "scan_results": [
    {
      "plate": "AB12345CD",
      "confidence": 0.95,
      "is_exempted": true,
      "exemption_reason": "Vozidlo osvobozeno",
      "edalnice_status": "success"
    }
  ]
}
```

### WebSocket Stream

```bash
ws://localhost:8000/anpr/stream

Messages:
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

### Get Alerts

```bash
GET /anpr/alerts?limit=20

Response:
{
  "status": "success",
  "alerts": [
    {
      "plate": "AB12345CD",
      "alert_type": "exempted",
      "message": "Vozidlo osvobozeno",
      "timestamp": "2024-01-01T12:00:00"
    }
  ]
}
```

## 🔧 ESP32 Serial Commands

Connect via serial monitor (115200 baud):

```bash
# Capture single image
capture

# Enable continuous capture (5s interval)
start

# Disable continuous capture
stop

# Get device status
status

# Reboot ESP32
reboot
```

## 📊 Database Schema (Future)

When database integration is added:

```sql
-- License plate scans
CREATE TABLE license_plate_scans (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    plate_text VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    device_id VARCHAR(50),
    image_path VARCHAR(255),
    image_hash VARCHAR(64) UNIQUE
);

-- Scan results (edalnice.cz lookups)
CREATE TABLE scan_results (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER REFERENCES license_plate_scans(id),
    vehicle_info JSONB,
    edalnice_status VARCHAR(50),
    is_exempted BOOLEAN,
    exemption_reason TEXT,
    alert_sent BOOLEAN DEFAULT FALSE,
    checked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP  -- Cache expiration
);

-- Alerts
CREATE TABLE anpr_alerts (
    id SERIAL PRIMARY KEY,
    plate VARCHAR(20),
    alert_type VARCHAR(50),  -- 'exempted', 'debt', 'not_found'
    message TEXT,
    alert_sent_at TIMESTAMP DEFAULT NOW(),
    driver_id VARCHAR(50)
);
```

## 🧪 Testing

### Test OCR Engine

```python
# Test ANPR service
from services.anpr_service import ANPRService

service = ANPRService()
with open("test_plate.jpg", "rb") as f:
    result = await service.process_image(f.read())
    print(result)
```

### Test Edalnice Integration

```python
# Test edalnice.cz API
from services.edalnice_service import get_edalnice_service

service = get_edalnice_service()
await service.initialize()
result = await service.query_vehicle("AB 12345 CD")
print(result)
```

### Test Android Integration

```kotlin
// Test ANPR repository
val repo = ANPRRepository()
repo.connectToWebSocket(
    onPlateDetected = { plate -> println("Detected: ${plate.plate}") },
    onError = { error -> println("Error: $error") },
    onConnected = { println("Connected") }
)
```

## 🔐 Privacy & Security

- **Image Storage**: Images are processed in-memory only, not persisted
- **Plate Data Retention**: Plate text stored for 30 days max, then auto-deleted
- **API Authentication**: Integrate with existing auth system for production
- **edalnice.cz Cache**: 24-hour TTL prevents excessive API calls
- **SSL/TLS**: Use HTTPS in production environment

## 📈 Performance Tuning

### OCR Optimization

```python
# Adjust for speed vs accuracy
service = ANPRService()

# Faster: Lower confidence threshold
service.reader.readtext(image, min_confidence=0.3)

# More accurate: Higher threshold
service.reader.readtext(image, min_confidence=0.7)
```

### Image Preprocessing

```python
# Current: CLAHE + sharpening
# For faster processing: Use grayscale only
# For better accuracy: Add Canny edge detection
```

### WebSocket Optimization

- Batch WebSocket messages if volume is high
- Use compression for large payloads
- Implement heartbeat (ping/pong) for connection health

## 🚨 Common Issues

### Issue: "EasyOCR not available"

**Solution**: Install dependencies
```bash
pip install easyocr opencv-python
```

### Issue: ESP32 WiFi connection fails

**Solution**: Check WiFi credentials in camera_anpr.cpp:
```cpp
const char* WIFI_SSID = "YOUR_SSID";      // ← Set this
const char* WIFI_PASSWORD = "YOUR_PASSWORD";  // ← Set this
```

### Issue: OCR accuracy is low

**Solution**: 
1. Improve lighting in test environment
2. Increase JPEG quality (change JPEG_QUALITY to 90)
3. Adjust image preprocessing (line 150-170 in anpr_service.py)
4. Check plate image is 640x480 or larger

### Issue: edalnice.cz API timeout

**Solution**: Already handled with 5-second timeout and fallback to "unknown" status

## 📚 Documentation

- [MIA Architecture Overview](../ARCHITECTURE.md)
- [ESP32 Firmware Guide](../docs/esp32-setup.md)
- [Android App Development](../apps/android/README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [EasyOCR Documentation](https://github.com/JaidedAI/EasyOCR)

## 🤝 Future Enhancements

1. **Database Integration**: Persist scans and results in PostgreSQL
2. **Machine Learning**: Train custom model for Czech plates only
3. **Vehicle Tracking**: Track same vehicle across multiple scans
4. **Alert System**: Push notifications for exempted vehicles
5. **Batch Processing**: Handle multiple cameras simultaneously
6. **Performance Analytics**: Track OCR accuracy metrics
7. **Integration with MCP**: Add as cognitive module for voice commands

## 📝 License

Part of MIA vehicle telemetry system. See root LICENSE file.
