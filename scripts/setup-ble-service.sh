#!/bin/bash
# Setup BLE Service for Raspberry Pi OBD-II Adapter
# This script installs dependencies and configures BLE services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Install system dependencies
log_info "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-dev \
    libbluetooth-dev \
    bluez \
    bluez-tools \
    python3-dbus

# Install Python dependencies
log_info "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install \
    bleak \
    bluepy \
    dbus-python \
    pybluez \
    pygatt

# Create service user if it doesn't exist
if ! id "mia" &>/dev/null; then
    log_info "Creating mia user..."
    useradd -r -s /bin/bash -m -G bluetooth,dialout mia
else
    log_info "User 'mia' already exists, adding to bluetooth group..."
    usermod -a -G bluetooth,dialout mia
fi

# Create directories
log_info "Creating service directories..."
mkdir -p /opt/ai-servis/rpi/services
mkdir -p /var/log/ai-servis

# Copy service files
log_info "Installing service files..."
if [ -f "$PROJECT_ROOT/rpi/services/ble_obd_service.py" ]; then
    cp "$PROJECT_ROOT/rpi/services/ble_obd_service.py" /opt/ai-servis/rpi/services/
    chmod +x /opt/ai-servis/rpi/services/ble_obd_service.py
fi

if [ -f "$PROJECT_ROOT/rpi/services/ble_advertiser.py" ]; then
    cp "$PROJECT_ROOT/rpi/services/ble_advertiser.py" /opt/ai-servis/rpi/services/
    chmod +x /opt/ai-servis/rpi/services/ble_advertiser.py
fi

# Copy systemd service files
log_info "Installing systemd services..."
if [ -f "$PROJECT_ROOT/rpi/services/mia-ble-obd.service" ]; then
    cp "$PROJECT_ROOT/rpi/services/mia-ble-obd.service" /etc/systemd/system/
fi

if [ -f "$PROJECT_ROOT/rpi/services/mia-ble-advertiser.service" ]; then
    cp "$PROJECT_ROOT/rpi/services/mia-ble-advertiser.service" /etc/systemd/system/
fi

# Set permissions
chown -R mia:mia /opt/ai-servis
chown -R mia:mia /var/log/ai-servis

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
