#!/bin/bash
# SDRPLAY Setup Verification Script
# Tests the complete SDRPLAY installation and functionality

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

echo ""
log_info "Testing SDRPLAY VHF Radio Setup"
echo "=================================="

# Test 1: Hardware detection
log_info "1. Testing hardware detection..."
if lsusb | grep -i sdrplay &> /dev/null; then
    log_success "✓ SDRPLAY device detected via USB"
    lsusb | grep -i sdrplay
else
    log_error "✗ SDRPLAY device not found"
    exit 1
fi

# Test 2: SDRPLAY API installation
log_info "2. Testing SDRPLAY API installation..."
if command -v sdrplay_apiService &> /dev/null; then
    log_success "✓ SDRPLAY API service found"
else
    log_error "✗ SDRPLAY API service not found"
    log_info "Please install SDRPLAY API from https://www.sdrplay.com/api"
    exit 1
fi

# Test 3: SoapySDR SDRPLAY support
log_info "3. Testing SoapySDR SDRPLAY support..."
if SoapySDRUtil --find 2>/dev/null | grep -i sdrplay &> /dev/null; then
    log_success "✓ SDRPLAY device found in SoapySDR"
    SoapySDRUtil --find | grep -i sdrplay
else
    log_warning "⚠ SDRPLAY not found in SoapySDR (may still work with MiriSDR)"
fi

# Test 4: SDRPLAY SoapySDR probe
log_info "4. Testing SDRPLAY SoapySDR probe..."
if SoapySDRUtil --probe="driver=sdrplay" 2>/dev/null; then
    log_success "✓ SDRPLAY SoapySDR probe successful"
else
    log_warning "⚠ SDRPLAY SoapySDR probe failed (may still work)"
fi

# Test 5: GQRX availability
log_info "5. Testing GQRX availability..."
if command -v gqrx &> /dev/null; then
    log_success "✓ GQRX installed and available"
    gqrx --version 2>/dev/null || echo "GQRX version check completed"
else
    log_error "✗ GQRX not found"
fi

# Test 6: Configuration files
log_info "6. Testing configuration files..."
if [ -f "$PROJECT_ROOT/config/sdr-config.json" ]; then
    log_success "✓ SDR configuration file exists"
else
    log_warning "⚠ SDR configuration file missing"
fi

echo ""
log_success "SDRPLAY setup verification completed!"
echo ""
log_info "To start listening to VHF radio:"
echo "1. Launch GQRX: gqrx"
echo "2. Select SDRPLAY device from device list"
echo "3. Configure for VHF range (169.775-170.450 MHz)"
echo "4. Set center frequency to ~170 MHz"
echo "5. Adjust gain and listen for signals"
echo ""
log_info "Happy listening! 📻"