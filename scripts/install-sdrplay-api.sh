#!/bin/bash
# SDRPLAY API Installation Helper Script
# This script helps with the manual SDRPLAY API installation process

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

echo ""
log_warning "SDRPLAY API Installation Helper"
echo ""
echo "This script will help you install the SDRPLAY API after you've downloaded it."
echo ""
echo "REQUIRED: You must first download the SDRPLAY API from:"
echo "  https://www.sdrplay.com/downloads"
echo ""
echo "Look for: SDRplay_RSP_API-Linux-*.deb"
echo ""
read -p "Have you downloaded the SDRPLAY API .deb file? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    log_info "Please download the SDRPLAY API first, then run this script again."
    exit 0
fi

echo ""
read -p "Enter the path to the downloaded .deb file (e.g., ~/Downloads/sdrplay-api_*.deb): " DEB_FILE

# Expand ~ if used
DEB_FILE="${DEB_FILE/#\~/$HOME}"

# Check if file exists
if [ ! -f "$DEB_FILE" ]; then
    log_error "File not found: $DEB_FILE"
    log_info "Please check the file path and try again."
    exit 1
fi

log_info "Installing SDRPLAY API from: $DEB_FILE"

# Install the .deb package
log_info "Installing SDRPLAY API package..."
dpkg -i "$DEB_FILE"

# Fix any missing dependencies
log_info "Fixing dependencies..."
apt-get install -f -y

# Verify installation
if command -v sdrplay_apiService &> /dev/null; then
    log_success "SDRPLAY API service installed successfully"
else
    log_warning "SDRPLAY API service not found in PATH"
fi

if ldconfig -p | grep -q sdrplay; then
    log_success "SDRPLAY libraries found in system"
else
    log_warning "SDRPLAY libraries not found in ldconfig"
fi

echo ""
log_success "SDRPLAY API installation completed!"
echo ""
log_info "Next steps:"
echo "1. Run the configuration script: sudo $SCRIPT_DIR/configure-sdrplay.sh"
echo "2. Test device detection: SoapySDRUtil --probe=\"driver=sdrplay\""
echo "3. Launch GQRX and test VHF reception"