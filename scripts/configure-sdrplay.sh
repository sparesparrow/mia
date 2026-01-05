#!/bin/bash
# SDRPLAY Device Configuration Script
# This script configures SDRPLAY device access and tests functionality

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use sudo)"
    exit 1
fi

log_info "Configuring SDRPLAY device for VHF radio listening..."

# Check for SDRPLAY device
if ! lsusb | grep -i sdrplay &> /dev/null; then
    log_error "No SDRPLAY device detected. Please ensure the device is connected."
    exit 1
fi

log_info "Detected SDRPLAY device:"
lsusb | grep -i sdrplay

# Check if SDRPLAY API is installed
if ! command -v sdrplay_apiService &> /dev/null && ! ldconfig -p | grep -q sdrplay; then
    log_error "SDRPLAY API not found. Please install SDRPLAY API first."
    log_error "Download from: https://www.sdrplay.com/downloads"
    exit 1
fi

# Create udev rules for SDRPLAY device access
log_info "Creating udev rules for SDRPLAY device access..."

UDEV_RULES_FILE="/etc/udev/rules.d/99-sdrplay.rules"

if [ ! -f "$UDEV_RULES_FILE" ]; then
    cat > "$UDEV_RULES_FILE" << 'EOF'
# SDRPLAY RSP devices
SUBSYSTEM=="usb", ATTRS{idVendor}=="1df7", ATTRS{idProduct}=="2500", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1df7", ATTRS{idProduct}=="3000", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1df7", ATTRS{idProduct}=="3010", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1df7", ATTRS{idProduct}=="3020", MODE="0666"
EOF
    log_success "Created udev rules file: $UDEV_RULES_FILE"
else
    log_info "Udev rules file already exists: $UDEV_RULES_FILE"
fi

# Reload udev rules
log_info "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

# Test SDRPLAY device detection with SoapySDR
log_info "Testing SDRPLAY device detection..."

if command -v SoapySDRUtil &> /dev/null; then
    log_info "Testing with SoapySDRUtil..."
    if SoapySDRUtil --probe="driver=sdrplay" 2>/dev/null; then
        log_success "SDRPLAY device detected by SoapySDR"
    else
        log_warning "SoapySDR probe failed. This may be normal if SDRPLAY API is not fully configured."
    fi
else
    log_warning "SoapySDRUtil not found. Skipping SoapySDR test."
fi

# Test with rtl_test (if available)
if command -v rtl_test &> /dev/null; then
    log_info "Testing RTL-SDR compatibility layer..."
    # Note: This may not work with SDRPLAY, but worth checking
    timeout 5 rtl_test -t 2>/dev/null || log_info "RTL-SDR test completed (expected to timeout)"
else
    log_info "rtl_test not available"
fi

# Start SDRPLAY API service if available
if command -v sdrplay_apiService &> /dev/null; then
    log_info "Starting SDRPLAY API service..."
    systemctl start sdrplay_apiService 2>/dev/null || {
        log_warning "Could not start SDRPLAY API service via systemctl"
        log_info "You may need to start it manually or configure it to start on boot"
    }
fi

# Create SDR configuration file
CONFIG_FILE="$PROJECT_ROOT/config/sdr-config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    log_info "Creating SDR configuration file..."
    cat > "$CONFIG_FILE" << 'EOF'
{
  "device": {
    "type": "sdrplay",
    "model": "RSP1",
    "frequency_range_mhz": {
      "min": 169.775,
      "max": 170.450,
      "center": 170.0
    }
  },
  "gqrx": {
    "sample_rate": 2000000,
    "bandwidth": 200000,
    "mode": "AM",
    "gain": "auto",
    "filter": "Normal"
  },
  "vhf_settings": {
    "frequency_range": "169.775-170.450 MHz",
    "typical_use": "specialized communications, aircraft, marine radio",
    "recommended_settings": {
      "sample_rate": "2MS/s",
      "filter": "50kHz-200kHz",
      "agc": "Fast or Manual"
    }
  }
}
EOF
    log_success "Created SDR configuration file: $CONFIG_FILE"
fi

log_success "SDRPLAY device configuration completed."
echo ""
log_info "Next steps:"
echo "1. Launch GQRX: gqrx"
echo "2. Select SDRPLAY device from the device list"
echo "3. Configure for VHF range:"
echo "   - Center frequency: ~170 MHz"
echo "   - Bandwidth: Wide enough to cover 169.775–170.450 MHz"
echo "   - Mode: AM or NFM depending on signal type"
echo "4. Set gain appropriately for VHF reception"
echo ""
log_info "Test the setup by tuning to known local VHF frequencies."