#!/bin/bash
set -e

echo "========================================"
echo "  AI-SERVIS Raspberry Pi Deployment"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for root privileges (needed for GPIO)
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Warning: Not running as root. GPIO access may be limited.${NC}"
    echo "Consider running with sudo for full GPIO access."
fi

# Install dependencies
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libcurl4-openssl-dev \
    libmosquitto-dev \
    libgpiod-dev \
    libjsoncpp-dev \
    libflatbuffers-dev \
    espeak \
    espeak-data \
    libespeak-dev \
    mosquitto \
    mosquitto-clients \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libzmq3-dev

# Create build directory
BUILD_DIR="build-raspberry-pi"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure CMake
echo ""
echo "Configuring CMake..."
cmake ../platforms/cpp/core \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER=g++ \
    -DCMAKE_C_COMPILER=gcc

# Build
echo ""
echo "Building..."
make -j$(nproc)

# Create installation directory
INSTALL_DIR="/opt/mia"
RPI_DIR="$INSTALL_DIR/rpi"
echo ""
echo "Installing to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR/bin"
sudo mkdir -p "$INSTALL_DIR/config"
sudo mkdir -p "$INSTALL_DIR/logs"
sudo mkdir -p "$RPI_DIR"

# Copy binaries
sudo cp mia-rpi "$INSTALL_DIR/bin/" 2>/dev/null || true
sudo cp hardware-server "$INSTALL_DIR/bin/" 2>/dev/null || true
sudo chmod +x "$INSTALL_DIR/bin/"* 2>/dev/null || true

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd ..
if [ -f "rpi/requirements.txt" ]; then
    sudo pip3 install -r rpi/requirements.txt
fi

# Copy Python code
if [ -d "rpi" ]; then
    echo "Copying Python services..."
    sudo cp -r rpi/* "$RPI_DIR/"
    sudo chown -R root:root "$RPI_DIR"
fi

# Create config directory with example config
sudo tee "$INSTALL_DIR/config/ai-servis.conf" > /dev/null <<EOF
# AI-SERVIS Configuration
ORCHESTRATOR_PORT=8080
HARDWARE_SERVER_PORT=8081
WEB_UI_PORT=8082
MQTT_HOST=localhost
MQTT_PORT=1883
WORKING_DIR=/tmp/ai-servis
LOG_DIR=$INSTALL_DIR/logs
EOF

# Create systemd services
echo ""
echo "Creating systemd services..."

# ZeroMQ Broker service
if [ -f "rpi/services/zmq-broker.service" ]; then
    sudo cp rpi/services/zmq-broker.service /etc/systemd/system/
    echo "  - Installed zmq-broker.service"
fi

# FastAPI service
if [ -f "rpi/services/mia-api.service" ]; then
    sudo cp rpi/services/mia-api.service /etc/systemd/system/
    echo "  - Installed mia-api.service"
fi

# GPIO Worker service
if [ -f "rpi/services/mia-gpio-worker.service" ]; then
    sudo cp rpi/services/mia-gpio-worker.service /etc/systemd/system/
    echo "  - Installed mia-gpio-worker.service"
fi

# Serial Bridge service (OBD Simulator)
if [ -f "rpi/services/mia-serial-bridge.service" ]; then
    sudo cp rpi/services/mia-serial-bridge.service /etc/systemd/system/
    echo "  - Installed mia-serial-bridge.service"
fi

# OBD Worker service (OBD Simulator)
if [ -f "rpi/services/mia-obd-worker.service" ]; then
    sudo cp rpi/services/mia-obd-worker.service /etc/systemd/system/
    echo "  - Installed mia-obd-worker.service"
fi

# Legacy C++ service (if binary exists)
if [ -f "$INSTALL_DIR/bin/mia-rpi" ]; then
    sudo tee /etc/systemd/system/ai-servis.service > /dev/null <<EOF
[Unit]
Description=AI-SERVIS Universal Raspberry Pi Service (C++)
After=network.target mosquitto.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/bin/mia-rpi
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "  - Installed ai-servis.service (C++)"
fi

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
echo ""
echo "Enabling services to start on boot..."
sudo systemctl enable zmq-broker.service 2>/dev/null || true
sudo systemctl enable mia-api.service 2>/dev/null || true
sudo systemctl enable mia-gpio-worker.service 2>/dev/null || true
sudo systemctl enable mia-serial-bridge.service 2>/dev/null || true
sudo systemctl enable mia-obd-worker.service 2>/dev/null || true
sudo systemctl enable ai-servis.service 2>/dev/null || true

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Services installed:"
echo "  - zmq-broker.service (ZeroMQ message broker)"
echo "  - mia-api.service (FastAPI REST API)"
echo "  - mia-gpio-worker.service (GPIO hardware control)"
echo "  - mia-serial-bridge.service (ESP32/Arduino serial bridge)"
echo "  - mia-obd-worker.service (OBD-II simulator)"
echo "  - ai-servis.service (Legacy C++ service, if available)"
echo ""
echo "To start all services:"
echo "  sudo systemctl start zmq-broker"
echo "  sudo systemctl start mia-api"
echo "  sudo systemctl start mia-gpio-worker"
echo "  sudo systemctl start mia-serial-bridge"
echo "  sudo systemctl start mia-obd-worker"
echo ""
echo "To start all at once:"
echo "  sudo systemctl start zmq-broker mia-api mia-gpio-worker mia-serial-bridge mia-obd-worker"
echo ""
echo "All services are enabled to start on boot automatically."
echo ""
echo "To check status:"
echo "  sudo systemctl status zmq-broker"
echo "  sudo systemctl status mia-api"
echo "  sudo systemctl status mia-gpio-worker"
echo "  sudo systemctl status mia-serial-bridge"
echo "  sudo systemctl status mia-obd-worker"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u zmq-broker -f"
echo "  sudo journalctl -u mia-api -f"
echo "  sudo journalctl -u mia-gpio-worker -f"
echo "  sudo journalctl -u mia-serial-bridge -f"
echo "  sudo journalctl -u mia-obd-worker -f"
echo ""
echo "API endpoints:"
echo "  - http://localhost:8000/docs (FastAPI documentation)"
echo "  - http://localhost:8000/devices"
echo "  - http://localhost:8000/status"
echo "  - ws://localhost:8000/ws (WebSocket telemetry)"
echo ""
