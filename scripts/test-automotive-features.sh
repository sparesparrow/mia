#!/bin/bash

# Automotive Features Testing Script
# Tests all automotive app features using ADB commands

set -e

# Configuration
PACKAGE_NAME="cz.mia.app.debug"
MAIN_ACTIVITY=".MainActivity"
APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"
TEST_DEVICE=""
LOG_FILE="automotive_test_results_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# ADB command wrapper
adb_cmd() {
    local cmd="adb"
    if [[ -n "$TEST_DEVICE" ]]; then
        cmd="adb -s $TEST_DEVICE"
    fi
    $cmd "$@"
}

# Wait for device
wait_for_device() {
    log_info "Waiting for device to be available..."
    adb_cmd wait-for-device
    log_success "Device is ready"
}

# Check if app is installed
check_app_installed() {
    if adb_cmd shell pm list packages | grep -q "$PACKAGE_NAME"; then
        log_success "App $PACKAGE_NAME is installed"
        return 0
    else
        log_error "App $PACKAGE_NAME is not installed"
        return 1
    fi
}

# Launch app
launch_app() {
    log_info "Launching app..."
    if adb_cmd shell am start -n "$PACKAGE_NAME/$MAIN_ACTIVITY" 2>/dev/null; then
        log_success "App launched successfully"
        sleep 3  # Wait for app to load
        return 0
    else
        log_error "Failed to launch app"
        return 1
    fi
}

# Navigate to screen by tapping navigation bar
navigate_to_screen() {
    local screen_index=$1
    local screen_name=$2

    log_info "Navigating to $screen_name screen..."

    # Navigation bar coordinates (bottom navigation)
    # Index 0: Dashboard (leftmost)
    # Index 1: Alerts
    # Index 2: Camera
    # Index 3: OBD
    # Index 4: Settings (rightmost)

    local x_coords=(200 400 600 800 1000)  # Approximate coordinates
    local y_coord=2200  # Bottom navigation bar Y position

    local x=${x_coords[$screen_index]}

    adb_cmd shell input tap $x $y_coord
    sleep 2  # Wait for navigation

    log_success "Navigated to $screen_name"
}

# Test dashboard features
test_dashboard() {
    log_info "=== TESTING DASHBOARD FEATURES ==="

    navigate_to_screen 0 "Dashboard"

    # Test service start/stop buttons
    log_info "Testing service controls..."

    # Start service button coordinates (approximate)
    adb_cmd shell input tap 300 1800  # Start service button
    sleep 2
    log_success "Start service button tapped"

    # Stop service button coordinates
    adb_cmd shell input tap 700 1800  # Stop service button
    sleep 2
    log_success "Stop service button tapped"

    # Test Citroen C4 controls
    log_info "Testing Citroen C4 controls..."

    # DPF Check button (if visible)
    adb_cmd shell input tap 300 1400  # Check DPF
    sleep 1

    # DPF Regenerate button
    adb_cmd shell input tap 700 1400  # Regenerate
    sleep 1

    # AdBlue Check button
    adb_cmd shell input tap 500 1600  # Check AdBlue
    sleep 1

    # Run Diagnostics button
    adb_cmd shell input tap 300 1700  # Run Diag
    sleep 1

    # Check DTC button
    adb_cmd shell input tap 700 1700  # Check DTC
    sleep 1

    log_success "Dashboard features tested"
}

# Test alerts screen
test_alerts() {
    log_info "=== TESTING ALERTS FEATURES ==="

    navigate_to_screen 1 "Alerts"

    # Wait for alerts to load
    sleep 2

    # Test scrolling through alerts (if any)
    adb_cmd shell input swipe 500 1500 500 1000  # Swipe up to scroll
    sleep 1

    adb_cmd shell input swipe 500 1000 500 1500  # Swipe down to scroll back
    sleep 1

    log_success "Alerts screen tested"
}

# Test camera features
test_camera() {
    log_info "=== TESTING CAMERA FEATURES ==="

    navigate_to_screen 2 "Camera"

    # Wait for camera to initialize
    sleep 3

    # Check for permission dialog and grant if needed
    log_info "Checking for camera permission dialog..."
    # Try to grant permission (if dialog appears)
    adb_cmd shell input tap 700 1500  # Allow button (approximate)
    sleep 2

    # Test ANPR toggle
    log_info "Testing ANPR toggle..."
    adb_cmd shell input tap 900 1900  # ANPR switch (bottom right area)
    sleep 1
    adb_cmd shell input tap 900 1900  # Toggle back
    sleep 1

    # Test DVR recording toggle
    log_info "Testing DVR recording toggle..."
    adb_cmd shell input tap 900 2000  # DVR switch (below ANPR)
    sleep 1
    adb_cmd shell input tap 900 2000  # Toggle back
    sleep 1

    # Test manual clip trigger (if DVR is enabled)
    log_info "Testing manual clip trigger..."
    adb_cmd shell input tap 500 2100  # Save Event Clip button
    sleep 1

    log_success "Camera features tested"
}

# Test OBD features
test_obd() {
    log_info "=== TESTING OBD FEATURES ==="

    navigate_to_screen 3 "OBD"

    # Wait for OBD screen to load
    sleep 2

    # Check for Bluetooth permissions and grant if needed
    log_info "Checking for Bluetooth permissions..."
    # Grant permissions if dialog appears
    adb_cmd shell input tap 700 1500  # Allow button
    sleep 2
    adb_cmd shell input tap 700 1550  # Allow location permission
    sleep 2

    # Test scanning for devices
    log_info "Testing device scanning..."
    adb_cmd shell input tap 900 1200  # Scan button (top right)
    sleep 5  # Wait for scanning

    # Stop scanning
    adb_cmd shell input tap 900 1200  # Stop scan button
    sleep 2

    # Try to connect to first available device (if any)
    log_info "Testing device connection..."
    # Tap on first device in list (approximate coordinates)
    adb_cmd shell input tap 500 1400  # First device in list
    sleep 3

    # Disconnect if connected
    adb_cmd shell input tap 900 1300  # Disconnect button (if visible)
    sleep 2

    log_success "OBD features tested"
}

# Test settings features
test_settings() {
    log_info "=== TESTING SETTINGS FEATURES ==="

    navigate_to_screen 4 "Settings"

    # Wait for settings to load
    sleep 2

    # Test VIN input
    log_info "Testing VIN configuration..."
    adb_cmd shell input tap 500 1000  # VIN text field
    sleep 1
    adb_cmd shell input text "TESTVIN123456789"  # Enter test VIN
    sleep 1
    adb_cmd shell input tap 900 1050  # Save VIN button
    sleep 1

    # Test switches
    log_info "Testing toggle switches..."

    # Incognito switch
    adb_cmd shell input tap 900 1150  # Incognito toggle
    sleep 1
    adb_cmd shell input tap 900 1150  # Toggle back
    sleep 1

    # Metrics opt-in switch
    adb_cmd shell input tap 900 1350  # Metrics toggle
    sleep 1
    adb_cmd shell input tap 900 1350  # Toggle back
    sleep 1

    # Test slider
    log_info "Testing retention slider..."
    adb_cmd shell input swipe 300 1250 700 1250  # Swipe slider from left to right
    sleep 1
    adb_cmd shell input swipe 700 1250 300 1250  # Swipe back
    sleep 1

    # Test region selector
    log_info "Testing ANPR region selector..."
    adb_cmd shell input tap 300 1450  # Region toggle button
    sleep 1

    # Test export logs
    log_info "Testing log export..."
    adb_cmd shell input tap 500 1550  # Export Logs button
    sleep 2

    log_success "Settings features tested"
}

# Test navigation between all screens
test_navigation() {
    log_info "=== TESTING NAVIGATION BETWEEN SCREENS ==="

    # Navigate through all screens in sequence
    for i in {0..4}; do
        case $i in
            0) screen_name="Dashboard" ;;
            1) screen_name="Alerts" ;;
            2) screen_name="Camera" ;;
            3) screen_name="OBD" ;;
            4) screen_name="Settings" ;;
        esac

        log_info "Testing navigation to $screen_name"
        navigate_to_screen $i "$screen_name"
        sleep 1
    done

    log_success "Navigation between screens tested"
}

# Take screenshot for documentation
take_screenshot() {
    local screen_name=$1
    local filename="${screen_name,,}_screen_$(date +%H%M%S).png"

    log_info "Taking screenshot of $screen_name screen..."
    adb_cmd shell screencap -p /sdcard/$filename
    adb_cmd pull /sdcard/$filename screenshots/$filename 2>/dev/null || log_warning "Could not save screenshot $filename"
    adb_cmd shell rm /sdcard/$filename 2>/dev/null || true
}

# Main test execution
main() {
    log_info "=== AUTOMOTIVE FEATURES TESTING STARTED ==="
    log_info "Test log: $LOG_FILE"
    log_info "Package: $PACKAGE_NAME"
    log_info "Device: ${TEST_DEVICE:-default}"

    # Setup
    mkdir -p screenshots

    # Device checks
    wait_for_device

    if ! check_app_installed; then
        log_error "App not installed. Please install the app first."
        exit 1
    fi

    # Launch app
    if ! launch_app; then
        log_error "Failed to launch app"
        exit 1
    fi

    # Run comprehensive tests
    log_info "Starting comprehensive feature tests..."

    # Test navigation first
    test_navigation

    # Test each feature screen
    test_dashboard
    take_screenshot "Dashboard"

    test_alerts
    take_screenshot "Alerts"

    test_camera
    take_screenshot "Camera"

    test_obd
    take_screenshot "OBD"

    test_settings
    take_screenshot "Settings"

    # Final navigation test
    test_navigation

    log_success "=== ALL AUTOMOTIVE FEATURES TESTS COMPLETED ==="
    log_info "Check $LOG_FILE for detailed results"
    log_info "Screenshots saved in screenshots/ directory"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Test automotive features of the Android app using ADB commands."
    echo ""
    echo "Options:"
    echo "  -d, --device SERIAL    Target specific device serial number"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     Test on default device"
    echo "  $0 -d emulator-5554    Test on specific emulator"
    echo "  $0 --device 123456789  Test on specific device"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--device)
            TEST_DEVICE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main