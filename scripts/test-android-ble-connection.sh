#!/bin/bash
# Test Android App BLE Connection to Raspberry Pi
# Uses scrcpy to show screen during testing
# Usage: ./scripts/test-android-ble-connection.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
PACKAGE_NAME="cz.mia.app.debug"
MAIN_ACTIVITY="cz.mia.app.MainActivity"
FULL_ACTIVITY="${PACKAGE_NAME}/${MAIN_ACTIVITY}"
RPI_HOST="mia.local"
SCRCPY_PID=""

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [ -n "$SCRCPY_PID" ] && kill -0 "$SCRCPY_PID" 2>/dev/null; then
        log_info "Stopping scrcpy (PID: $SCRCPY_PID)..."
        kill "$SCRCPY_PID" 2>/dev/null || true
        wait "$SCRCPY_PID" 2>/dev/null || true
    fi
    # Kill any remaining scrcpy processes
    pkill -f scrcpy 2>/dev/null || true
    log_info "Cleanup complete"
}
trap cleanup EXIT INT TERM

# Check ADB connection
log_info "Checking ADB connection..."
# Try to connect via network if not already connected
if ! adb devices | grep -q "device$"; then
    log_info "No device found, trying network ADB..."
    # Try common network ADB addresses
    for addr in "192.168.200.130:5555" "192.168.1.100:5555" "192.168.0.100:5555"; do
        log_info "Trying $addr..."
        if adb connect "$addr" 2>/dev/null && sleep 2 && adb devices | grep -q "$addr.*device"; then
            log_success "Connected to $addr"
            break
        fi
    done
fi

MAX_WAIT=10
WAITED=0
while ! adb devices | grep -q "device$"; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        log_error "No Android device connected via ADB"
        log_info "Please connect device via:"
        log_info "  adb connect <IP>:5555"
        exit 1
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

DEVICE_SERIAL=$(adb devices | grep "device$" | head -1 | awk '{print $1}')
log_success "Found Android device: $DEVICE_SERIAL"

# Check if scrcpy is available
if command -v scrcpy &> /dev/null; then
    log_info "Starting scrcpy in background to show device screen..."
    scrcpy --stay-awake --turn-screen-off &
    SCRCPY_PID=$!
    sleep 2
    log_success "scrcpy started (PID: $SCRCPY_PID)"
    log_info "You should see your device screen now. Tests will be visible."
else
    log_warning "scrcpy not found - screen mirroring disabled"
    log_info "Install scrcpy for screen mirroring: sudo apt install scrcpy"
fi

# Check if app is installed
log_info "Checking if app is installed..."
if ! adb shell pm list packages | grep -q "$PACKAGE_NAME"; then
    log_error "App $PACKAGE_NAME is not installed"
    log_info "Please install the app first:"
    log_info "  cd android && ./tools/build-in-docker.sh"
    log_info "  adb install -r app/build/outputs/apk/debug/app-debug.apk"
    exit 1
fi
log_success "App is installed"

# Grant necessary permissions (only runtime permissions)
log_info "Granting Bluetooth and location permissions..."
# Note: BLUETOOTH and BLUETOOTH_ADMIN are not runtime permissions on Android 10
# They are granted at install time
adb shell pm grant "$PACKAGE_NAME" android.permission.BLUETOOTH_CONNECT 2>/dev/null || log_warning "BLUETOOTH_CONNECT grant failed (may need Android 12+)"
adb shell pm grant "$PACKAGE_NAME" android.permission.BLUETOOTH_SCAN 2>/dev/null || log_warning "BLUETOOTH_SCAN grant failed (may need Android 12+)"
adb shell pm grant "$PACKAGE_NAME" android.permission.ACCESS_FINE_LOCATION || log_warning "ACCESS_FINE_LOCATION grant failed"
log_success "Permissions granted (some may require Android 12+)"

# Enable Bluetooth on device
log_info "Enabling Bluetooth on Android device..."
adb shell svc bluetooth enable
sleep 2
log_success "Bluetooth enabled"

# Check RPi BLE service status
log_info "Checking Raspberry Pi BLE service status..."
if ssh -o ConnectTimeout=5 mia@$RPI_HOST 'sudo systemctl is-active --quiet mia-ble-obd' 2>/dev/null; then
    log_success "RPi BLE service is running"
else
    log_warning "RPi BLE service may not be running"
    log_info "Checking service status on RPi..."
    ssh mia@$RPI_HOST 'sudo systemctl status mia-ble-obd --no-pager -l | head -20' || true
fi

# Launch the app
log_info "Launching Android app..."
adb shell am force-stop "$PACKAGE_NAME" 2>/dev/null || true
sleep 1
adb shell am start -n "$FULL_ACTIVITY"
sleep 3
log_success "App launched"

# Wait for app to initialize
log_info "Waiting for app to initialize..."
sleep 5

# Check if we can navigate to BLE devices screen
log_info "Attempting to navigate to BLE devices screen..."
log_info "Please manually navigate to the BLE/OBD devices screen in the app"
log_info "Waiting 10 seconds for you to navigate..."
sleep 10

# Check logcat for BLE-related activity
log_info "Monitoring logcat for BLE activity..."
log_info "Starting BLE scan test - please tap 'Scan' in the app"
sleep 5

# Monitor logcat for BLE scan results
log_info "Checking for BLE scan results..."
timeout 15 adb logcat -d | grep -i "ble\|bluetooth\|obd\|mia" | tail -20 || true

# Check if device is discoverable
log_info "Checking if RPi BLE device is advertising..."
if ssh mia@$RPI_HOST 'hciconfig hci0 | grep -q "UP RUNNING"' 2>/dev/null; then
    log_success "RPi Bluetooth adapter is UP"
    log_info "Device should be advertising as 'MIA OBD-II Adapter'"
else
    log_warning "RPi Bluetooth adapter may not be UP"
fi

# Check RPi BLE service logs
log_info "Checking recent RPi BLE service logs..."
ssh mia@$RPI_HOST 'sudo journalctl -u mia-ble-obd --no-pager -n 10' || true

# Test connection attempt
log_info "=== Connection Test ==="
log_info "Please try to connect to 'MIA OBD-II Adapter' in the app"
log_info "Waiting 15 seconds for connection attempt..."
sleep 15

# Check logs for connection
log_info "Checking connection logs..."
log_info "Android app logs (BLE related):"
adb logcat -d | grep -iE "ble|bluetooth|obd|connect|gatt" | tail -30 || true

log_info "RPi BLE service logs:"
ssh mia@$RPI_HOST 'sudo journalctl -u mia-ble-obd --no-pager -n 20' || true

# Check if connection was successful
log_info "=== Test Summary ==="
log_info "Please verify in the app:"
log_info "  1. Can you see 'MIA OBD-II Adapter' in the scan results?"
log_info "  2. Can you connect to the device?"
log_info "  3. Do you see any OBD data after connection?"

# Keep scrcpy running for manual verification
log_info "Keeping scrcpy running for manual verification..."
log_info "Press Ctrl+C when done testing"
log_info "scrcpy will be automatically closed"

# Wait for user to finish testing
log_info "Waiting 30 seconds for final verification..."
sleep 30

log_success "Test completed!"
log_info "Check the logs above for any errors"
log_info "scrcpy will close automatically"
