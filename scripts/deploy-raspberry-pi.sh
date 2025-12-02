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
    mosquitto-clients

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
INSTALL_DIR="/opt/ai-servis"
echo ""
echo "Installing to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR/bin"
sudo mkdir -p "$INSTALL_DIR/config"
sudo mkdir -p "$INSTALL_DIR/logs"

# Copy binaries
sudo cp ai-servis-rpi "$INSTALL_DIR/bin/"
sudo cp hardware-server "$INSTALL_DIR/bin/" 2>/dev/null || true
sudo chmod +x "$INSTALL_DIR/bin/"*

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

# Create systemd service
echo ""
echo "Creating systemd service..."
sudo tee /etc/systemd/system/ai-servis.service > /dev/null <<EOF
[Unit]
Description=AI-SERVIS Universal Raspberry Pi Service
After=network.target mosquitto.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/bin/ai-servis-rpi
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "To start the service:"
echo "  sudo systemctl start ai-servis"
echo ""
echo "To enable on boot:"
echo "  sudo systemctl enable ai-servis"
echo ""
echo "To check status:"
echo "  sudo systemctl status ai-servis"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ai-servis -f"
echo ""
