#!/bin/bash
# SDRPLAY Installation Script for VHF Radio Listening Setup
# This script installs SDRPLAY API drivers and GQRX SDR software

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

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use sudo)"
    exit 1
fi

log_info "Starting SDRPLAY installation for VHF radio listening setup..."

# Check system requirements
log_info "Checking system requirements..."
if ! command -v apt-get &> /dev/null; then
    log_error "This script requires apt-get (Debian/Ubuntu-based systems)"
    exit 1
fi

# Check for SDRPLAY device
if ! lsusb | grep -i sdrplay &> /dev/null; then
    log_warning "No SDRPLAY device detected. Please ensure the device is connected."
    log_warning "Installation will continue but device configuration may fail."
fi

# Update package lists
log_info "Updating package lists..."
apt-get update

# Install SDR software and libraries
log_info "Installing GQRX SDR software..."
apt-get install -y gqrx-sdr

log_info "Installing additional SDR libraries..."
apt-get install -y \
    rtl-sdr \
    sox \
    libsoapysdr-dev \
    soapysdr-tools \
    libmirisdr-dev

log_success "Basic SDR software installation completed."

# SDRPLAY API Installation Instructions
log_warning "SDRPLAY API Installation requires manual steps:"
echo ""
echo "1. Visit the SDRPLAY website: https://www.sdrplay.com/downloads"
echo "2. Register for an account if you don't have one"
echo "3. Download the SDRPLAY API for Linux"
echo "4. Save the .deb file to your Downloads directory"
echo "5. Run the following commands:"
echo "   sudo dpkg -i ~/Downloads/sdrplay-api_*.deb"
echo "   sudo apt-get install -f  # Fix any dependencies"
echo ""
echo "After installing the SDRPLAY API, run the configuration script:"
echo "   sudo $SCRIPT_DIR/configure-sdrplay.sh"
echo ""

log_info "To complete the setup after SDRPLAY API installation:"
echo "1. Run: sudo $SCRIPT_DIR/configure-sdrplay.sh"
echo "2. Test device detection: SoapySDRUtil --probe=\"driver=sdrplay\""
echo "3. Launch GQRX and configure for VHF frequencies"

log_success "SDRPLAY installation script completed."
log_warning "Remember to manually install SDRPLAY API from the official website."