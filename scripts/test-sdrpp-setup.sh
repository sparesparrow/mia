#!/bin/bash
# SDR++ Setup Verification Script
# Tests SDR++ installation and SDRPLAY device detection

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
log_info "Testing SDR++ VHF Radio Setup"
echo "==============================="

# Test 1: SDR++ installation
log_info "1. Testing SDR++ installation..."
if command -v sdrpp &> /dev/null; then
    log_success "✓ SDR++ installed and available"
    SDRPP_VERSION=$(timeout 2 sdrpp --help 2>&1 | grep "SDR++ v" | head -1 | sed 's/.*SDR++ v//')
    echo "  Version: $SDRPP_VERSION"
else
    log_error "✗ SDR++ not found"
    exit 1
fi

# Test 2: Hardware detection
log_info "2. Testing hardware detection..."
if lsusb | grep -i sdrplay &> /dev/null; then
    log_success "✓ SDRPLAY device detected via USB"
    lsusb | grep -i sdrplay
else
    log_error "✗ SDRPLAY device not found"
    exit 1
fi

# Test 3: Library dependencies
log_info "3. Testing library dependencies..."
MISSING_LIBS=""
if ! ldconfig -p | grep -q libvolk; then
    MISSING_LIBS="$MISSING_LIBS libvolk"
fi
if ! ldconfig -p | grep -q libfftw3; then
    MISSING_LIBS="$MISSING_LIBS libfftw3"
fi
if ! ldconfig -p | grep -q libglfw; then
    MISSING_LIBS="$MISSING_LIBS libglfw"
fi

if [ -z "$MISSING_LIBS" ]; then
    log_success "✓ All required libraries found"
else
    log_warning "⚠ Missing libraries:$MISSING_LIBS"
fi

# Test 4: SDRPLAY API check
log_info "4. Checking SDRPLAY API status..."
if command -v sdrplay_apiService &> /dev/null; then
    log_success "✓ SDRPLAY API service found (full support available)"
    API_STATUS="Full SDRPLAY API support"
else
    log_warning "⚠ SDRPLAY API not found (limited MiriSDR support only)"
    API_STATUS="Limited MiriSDR support only"
fi

# Test 5: Configuration files
log_info "5. Testing configuration files..."
if [ -f "$PROJECT_ROOT/config/sdr-config.json" ]; then
    log_success "✓ SDR configuration file exists"
else
    log_warning "⚠ SDR configuration file missing"
fi

echo ""
log_success "SDR++ setup verification completed!"
echo ""
echo "📊 SUMMARY:"
echo "  SDR++ Version: $SDRPP_VERSION"
echo "  SDRPLAY Device: Detected"
echo "  API Support: $API_STATUS"
echo "  VHF Range: 169.775-170.450 MHz (pre-configured)"
echo ""
log_info "To start SDR++ for VHF radio listening:"
echo "  sdrpp"
echo ""
echo "In SDR++ interface:"
echo "1. Select SDRPLAY/MiriSDR source"
echo "2. Set frequency to ~170 MHz"
echo "3. Configure demodulator for AM/NFM"
echo "4. Adjust gain and bandwidth for VHF signals"
echo ""
log_info "SDR++ provides an alternative to GQRX with modern interface!"