#!/bin/bash
# Setup BLE Service for Raspberry Pi OBD-II Adapter
# This script installs dependencies and configures BLE services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="${MIA_INSTALL_DIR:-/opt/mia}"
PY_API_DIR="$INSTALL_DIR/apps/rpi-backend/py-api"
BLE_SERVICE_DIR="$PY_API_DIR/services"
LOG_DIR="${MIA_LOG_DIR:-/var/log/mia}"
SERVICE_USER="${MIA_USER:-mia}"
SYSTEMD_DIR="${MIA_SYSTEMD_DIR:-/etc/systemd/system}"
SERVICE_SOURCE_DIR="$PROJECT_ROOT/apps/rpi-backend/py-api/services"
SYSTEMD_SOURCE_DIR="$PROJECT_ROOT/infra/systemd"

install_pip_packages() {
    if ! python3 -m pip install "$@"; then
        python3 -m pip install --break-system-packages "$@"
    fi
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    log_warning "This script is designed for Raspberry Pi. Continuing anyway..."
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root (use sudo)"
    exit 1
fi

log_info "Setting up BLE services for MIA OBD-II Adapter..."

for required_file in \
    "$SERVICE_SOURCE_DIR/ble_obd_service.py" \
    "$SERVICE_SOURCE_DIR/ble_advertiser.py" \
    "$SYSTEMD_SOURCE_DIR/mia-ble-obd.service" \
    "$SYSTEMD_SOURCE_DIR/mia-ble-advertiser.service"
do
    if [ ! -f "$required_file" ]; then
        log_error "Required BLE asset not found: $required_file"
        exit 1
    fi
done

# Install system dependencies
log_info "Installing system dependencies..."
env DEBIAN_FRONTEND=noninteractive apt-get update
env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-pip \
    python3-dev \
    libbluetooth-dev \
    bluez \
    bluez-tools \
    python3-dbus

# Install Python dependencies
log_info "Installing Python dependencies..."
install_pip_packages --upgrade pip
install_pip_packages \
    bleak \
    bluepy \
    dbus-python \
    pybluez \
    pygatt

# Create service user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    log_info "Creating $SERVICE_USER user..."
    useradd -r -s /bin/bash -m -G bluetooth,dialout "$SERVICE_USER"
else
    log_info "User '$SERVICE_USER' already exists, adding to bluetooth group..."
    usermod -a -G bluetooth,dialout "$SERVICE_USER"
fi

# Create directories
log_info "Creating service directories..."
mkdir -p "$BLE_SERVICE_DIR"
mkdir -p "$LOG_DIR"

# Copy service files
log_info "Installing service files..."
cp "$SERVICE_SOURCE_DIR/ble_obd_service.py" "$BLE_SERVICE_DIR/"
chmod +x "$BLE_SERVICE_DIR/ble_obd_service.py"

cp "$SERVICE_SOURCE_DIR/ble_advertiser.py" "$BLE_SERVICE_DIR/"
chmod +x "$BLE_SERVICE_DIR/ble_advertiser.py"

# Copy systemd service files
log_info "Installing systemd services..."
cp "$SYSTEMD_SOURCE_DIR/mia-ble-obd.service" "$SYSTEMD_DIR/"
cp "$SYSTEMD_SOURCE_DIR/mia-ble-advertiser.service" "$SYSTEMD_DIR/"

# Set permissions
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"

# Enable Bluetooth
log_info "Enabling Bluetooth..."
systemctl enable bluetooth
systemctl start bluetooth

# Wait for Bluetooth to be ready
sleep 2

# Check if Bluetooth is available
if ! hciconfig &>/dev/null; then
    log_warning "Bluetooth hardware not detected. Services may not work."
else
    log_info "Configuring Bluetooth adapter..."
    # Make Bluetooth discoverable
    hciconfig hci0 piscan || log_warning "Could not set Bluetooth to discoverable mode"
    
    # Set Bluetooth class (OBD-II adapter)
    hciconfig hci0 class 0x002540 || log_warning "Could not set Bluetooth class"
fi

# Reload systemd
log_info "Reloading systemd daemon..."
systemctl daemon-reload

log_success "BLE service setup complete!"
log_info "To enable and start services, run:"
echo "  sudo systemctl enable mia-ble-obd"
echo "  sudo systemctl enable mia-ble-advertiser"
echo "  sudo systemctl start mia-ble-obd"
echo "  sudo systemctl start mia-ble-advertiser"
