#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BUILD_DIR="$PROJECT_ROOT/build-raspberry-pi"
INSTALL_DIR="${MIA_INSTALL_DIR:-/opt/mia}"
SYSTEMD_SOURCE_DIR="$PROJECT_ROOT/infra/systemd"
PY_API_SOURCE_DIR="$PROJECT_ROOT/apps/rpi-backend/py-api"
SHARED_SOURCE_DIR="$PROJECT_ROOT/apps/rpi-backend/shared"

get_cpu_count() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif command -v sysctl >/dev/null 2>&1; then
        sysctl -n hw.ncpu
    else
        printf '1\n'
    fi
}

run_privileged() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    else
        if ! command -v sudo >/dev/null 2>&1; then
            echo "sudo is required for deployment actions" >&2
            exit 1
        fi

        sudo "$@"
    fi
}

install_python_requirements() {
    local requirements_file="$1"

    if ! run_privileged python3 -m pip install -r "$requirements_file"; then
        run_privileged python3 -m pip install --break-system-packages -r "$requirements_file"
    fi
}

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
run_privileged env DEBIAN_FRONTEND=noninteractive apt-get update
run_privileged env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
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
cmake --build . --parallel "$(get_cpu_count)"

# Create installation directory
RPI_DIR="$INSTALL_DIR/rpi"
PY_API_TARGET_DIR="$INSTALL_DIR/apps/rpi-backend/py-api"
SHARED_TARGET_DIR="$INSTALL_DIR/apps/rpi-backend/shared"
echo ""
echo "Installing to $INSTALL_DIR..."
run_privileged mkdir -p "$INSTALL_DIR/bin"
run_privileged mkdir -p "$INSTALL_DIR/config"
run_privileged mkdir -p "$INSTALL_DIR/logs"
run_privileged mkdir -p "$RPI_DIR"
run_privileged mkdir -p "$PY_API_TARGET_DIR"
run_privileged mkdir -p "$SHARED_TARGET_DIR"
run_privileged mkdir -p "$INSTALL_DIR/Mia"

# Copy binaries
run_privileged cp mia-rpi "$INSTALL_DIR/bin/" 2>/dev/null || true
run_privileged cp hardware-server "$INSTALL_DIR/bin/" 2>/dev/null || true
run_privileged chmod +x "$INSTALL_DIR/bin/"* 2>/dev/null || true

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd "$PROJECT_ROOT"
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    install_python_requirements "$PROJECT_ROOT/requirements.txt"
fi

# Copy Python code
if [ -d "$PY_API_SOURCE_DIR" ]; then
    echo "Copying Python services..."
    run_privileged cp -r "$PY_API_SOURCE_DIR/." "$PY_API_TARGET_DIR/"
fi

if [ -d "$SHARED_SOURCE_DIR" ]; then
    run_privileged cp -r "$SHARED_SOURCE_DIR/." "$SHARED_TARGET_DIR/"
fi

if [ -d "$PROJECT_ROOT/Mia" ]; then
    run_privileged cp -r "$PROJECT_ROOT/Mia/." "$INSTALL_DIR/Mia/"
fi

if [ -d "$PROJECT_ROOT/config" ]; then
    run_privileged cp -r "$PROJECT_ROOT/config/." "$INSTALL_DIR/config/"
fi

# Create config directory with example config
run_privileged tee "$INSTALL_DIR/config/ai-servis.conf" > /dev/null <<EOF
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

for service in \
    zmq-broker.service \
    mia-api.service \
    mia-gpio-worker.service \
    mia-serial-bridge.service \
    mia-obd-worker.service
do
    if [ -f "$SYSTEMD_SOURCE_DIR/$service" ]; then
        run_privileged cp "$SYSTEMD_SOURCE_DIR/$service" /etc/systemd/system/
        echo "  - Installed $service"
    fi
done

# Legacy C++ service (if binary exists)
if [ -f "$INSTALL_DIR/bin/mia-rpi" ]; then
    run_privileged tee /etc/systemd/system/ai-servis.service > /dev/null <<EOF
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
run_privileged systemctl daemon-reload

# Enable services to start on boot
echo ""
echo "Enabling services to start on boot..."
run_privileged systemctl enable zmq-broker.service 2>/dev/null || true
run_privileged systemctl enable mia-api.service 2>/dev/null || true
run_privileged systemctl enable mia-gpio-worker.service 2>/dev/null || true
run_privileged systemctl enable mia-serial-bridge.service 2>/dev/null || true
run_privileged systemctl enable mia-obd-worker.service 2>/dev/null || true
run_privileged systemctl enable ai-servis.service 2>/dev/null || true

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

# Ensure bundled CPython is properly configured
echo "🔧 Setting up bundled CPython environment..."
if [[ -f "$PROJECT_ROOT/scripts/ensure-bundled-cpython.sh" ]]; then
    bash "$PROJECT_ROOT/scripts/ensure-bundled-cpython.sh" "$INSTALL_DIR"
else
    echo "⚠️  Bundled CPython setup script not found, skipping..."
fi

echo ""
