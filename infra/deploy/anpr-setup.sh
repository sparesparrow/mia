#!/bin/bash
# Setup script for ANPR feature deployment on Raspberry Pi
# Run this script to configure ANPR for production deployment

set -e

echo "🔧 MIA ANPR Setup Script"
echo "======================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Configuration
MIA_ROOT="/opt/mia"
VENV_PATH="/opt/mia/venv"
SERVICE_USER="pi"
SERVICE_GROUP="pi"

echo "📦 Step 1: Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-opencv \
    libopencv-dev \
    python3-dev \
    libatlas-base-dev \
    libjasper-dev \
    libtiff-dev \
    libjasper-dev \
    libharfmaff0 \
    libwebp6 \
    libtiff5 \
    libjasper1 \
    libharfbuzz0b \
    libwebp6 \
    libjasper1 \
    libatlas3-base

echo "✓ System dependencies installed"
echo ""

echo "📚 Step 2: Installing Python ANPR dependencies..."
sudo -u $SERVICE_USER bash << EOF
source "$VENV_PATH/bin/activate"
pip install --no-cache-dir \
    easyocr>=1.7.0 \
    opencv-python>=4.8.0 \
  Pillow>=10.0.0
echo "✓ Python dependencies installed"
EOF

echo ""
echo "📝 Step 3: Configuring mia-api ANPR environment..."

mkdir -p /etc/mia /etc/systemd/system/mia-api.service.d

cat > /etc/mia/anpr.env << 'ANPR_ENV'
# Set this after flashing the ESP32-CAM, for example:
# ANPR_CAMERA_URL=http://192.168.1.123
ANPR_ENV

cat > /etc/systemd/system/mia-api.service.d/anpr.conf << 'SYSTEMD_OVERRIDE'
[Service]
EnvironmentFile=-/etc/mia/anpr.env
SYSTEMD_OVERRIDE

chmod 644 /etc/mia/anpr.env /etc/systemd/system/mia-api.service.d/anpr.conf

echo "✓ mia-api environment override created at /etc/systemd/system/mia-api.service.d/anpr.conf"
echo ""

echo "🔌 Step 4: Creating ANPR device configuration..."

# Create device configuration directory
mkdir -p $MIA_ROOT/config/devices

# Create ANPR device config
cat > $MIA_ROOT/config/devices/anpr.yaml << 'DEVICE_CONFIG'
---
# ANPR Device Configuration
device:
  id: esp32-camera
  type: camera
  name: ESP32 ANPR Camera
  enabled: true
  
camera:
  model: "OV2640"
  resolution: "640x480"
  jpeg_quality: 85
  
capture:
  mode: "on-demand"  # on-demand, continuous, trigger-based
  interval_ms: 5000  # For continuous mode
  auto_process: true
  auto_check_edalnice: true
  
ocr:
  languages:
    - cs  # Czech
    - en  # English
  min_confidence: 0.5
  plate_format: czech  # Czech: 2 letters + 3-5 digits + 2 letters
  
edalnice:
  enabled: true
  cache_ttl_hours: 24
  timeout_seconds: 5
  
storage:
  images:
    keep_days: 7
    location: "/opt/mia/data/anpr/images"
  database:
    enable: false  # Set to true when DB is integrated
    retention_days: 30
    
alerts:
  enabled: true
  on_exempted: true
  on_debt: true
  on_not_found: false
  push_notifications: false  # Enable when notification system is ready
  
logging:
  level: INFO
  file: "/var/log/mia/anpr.log"
  max_size_mb: 100
  backup_count: 5
DEVICE_CONFIG

echo "✓ Device configuration created at $MIA_ROOT/config/devices/anpr.yaml"
echo ""

echo "📂 Step 5: Creating data directories..."

# Create data directories with proper permissions
mkdir -p $MIA_ROOT/data/anpr/{images,cache}
mkdir -p /var/log/mia

chown -R $SERVICE_USER:$SERVICE_GROUP $MIA_ROOT/data/anpr
chown -R $SERVICE_USER:$SERVICE_GROUP /var/log/mia

chmod 755 $MIA_ROOT/data/anpr
chmod 755 /var/log/mia

echo "✓ Data directories created"
echo ""

echo "🔑 Step 6: Setting up log rotation..."

cat > /etc/logrotate.d/mia-anpr << 'LOGROTATE'
/var/log/mia/anpr.log {
    daily
    rotate 14
    size 100M
    compress
    delaycompress
    notifempty
    create 0640 pi pi
    sharedscripts
    postrotate
      systemctl reload mia-api > /dev/null 2>&1 || true
    endscript
}
LOGROTATE

echo "✓ Log rotation configured"
echo ""

echo "⚙️ Step 7: Reloading systemd daemon..."
systemctl daemon-reload
echo "✓ Systemd reloaded"
echo ""

echo "🧪 Step 8: Testing service..."

# Test import
echo "Testing Python imports..."
sudo -u $SERVICE_USER bash << EOF
source "$VENV_PATH/bin/activate"
export PYTHONPATH="$MIA_ROOT/apps/rpi-backend/py-api:$MIA_ROOT"
python -c "from services.anpr_service import ANPRService; print('✓ ANPR service imported')"
python -c "from services.edalnice_service import EdalniceCzService; print('✓ Edalnice service imported')"
python -c "from api.routers.anpr import router; print('✓ ANPR router imported')"
EOF

echo ""
echo "✅ ANPR Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure ESP32 camera WiFi credentials:"
echo "   sudo nano /home/sparrow/projects/mia/apps/esp32/main/camera_anpr.cpp"
echo ""
echo "2. Flash ESP32 firmware:"
echo "   cd /home/sparrow/projects/mia/apps/esp32"
echo "   pio run -e esp32cam-anpr -t upload --upload-port /dev/ttyUSB0"
echo "   sudo sed -i 's|# ANPR_CAMERA_URL=.*|ANPR_CAMERA_URL=http://ESP32_CAMERA_IP|' /etc/mia/anpr.env"
echo ""
echo "3. Restart API service to load ANPR settings:"
echo "   sudo systemctl restart mia-api"
echo ""
echo "4. Check API service status:"
echo "   sudo systemctl status mia-api"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u mia-api -f"
echo ""
echo "6. Test API endpoints:"
echo "   curl http://localhost:8000/anpr/health | jq ."
echo ""
echo "🚀 Your ANPR system is ready for production!"
