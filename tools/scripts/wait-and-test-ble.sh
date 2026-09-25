#!/bin/bash
# Interactive script to wait for Android device and test BLE connection
# This script will wait indefinitely for device connection

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

PACKAGE_NAME="cz.mia.app.debug"
MAIN_ACTIVITY="cz.mia.app.MainActivity"
FULL_ACTIVITY="${PACKAGE_NAME}/${MAIN_ACTIVITY}"
RPI_HOST="mia.local"
SCRCPY_PID=""

cleanup() {
    log_info "Cleaning up..."
    if [ -n "$SCRCPY_PID" ] && kill -0 "$SCRCPY_PID" 2>/dev/null; then
        kill "$SCRCPY_PID" 2>/dev/null || true
        wait "$SCRCPY_PID" 2>/dev/null || true
    fi
    pkill -f scrcpy 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Restart ADB server
log_info "Restarting ADB server..."
adb kill-server 2>/dev/null || true
sleep 1
adb start-server
sleep 2

# Wait for device
log_info "Waiting for Android device to connect..."
log_info "Please ensure:"
log_info "  1. Phone is connected via USB"
log_info "  2. USB debugging is enabled"
log_info "  3. Authorization prompt is accepted"
log_info "  4. USB mode is set to 'File Transfer' or 'MTP'"
log_info ""
log_info "Press Ctrl+C to cancel"
log_info ""

while true; do
    if adb devices | grep -q "device$"; then
        DEVICE_SERIAL=$(adb devices | grep "device$" | head -1 | awk '{print $1}')
        log_success "Device detected: $DEVICE_SERIAL"
        break
    fi
    
    # Show current status
    echo -ne "\r[$(date +%H:%M:%S)] Waiting for device... (checking USB and ADB)"
    sleep 2
done

echo ""
log_success "Device connected! Proceeding with test..."

# Check if scrcpy is available
if command -v scrcpy &> /dev/null; then
    log_info "Starting scrcpy..."
    scrcpy --stay-awake --turn-screen-off > /dev/null 2>&1 &
    SCRCPY_PID=$!
    sleep 3
    log_success "scrcpy started (PID: $SCRCPY_PID)"
else
    log_warning "scrcpy not available"
fi

# Check if app is installed
log_info "Checking if app is installed..."
if ! adb shell pm list packages | grep -q "$PACKAGE_NAME"; then
    log_error "App not installed!"
    log_info "Installing app..."
    if [ -f "android/app/build/outputs/apk/debug/app-debug.apk" ]; then
        adb install -r android/app/build/outputs/apk/debug/app-debug.apk
    else
        log_error "APK not found. Please build the app first:"
        log_info "  cd android && ./tools/build-in-docker.sh"
        exit 1
    fi
fi
log_success "App is installed"

# Grant permissions
log_info "Granting permissions..."
adb shell pm grant "$PACKAGE_NAME" android.permission.BLUETOOTH
adb shell pm grant "$PACKAGE_NAME" android.permission.BLUETOOTH_ADMIN
adb shell pm grant "$PACKAGE_NAME" android.permission.BLUETOOTH_CONNECT
adb shell pm grant "$PACKAGE_NAME" android.permission.BLUETOOTH_SCAN
adb shell pm grant "$PACKAGE_NAME" android.permission.ACCESS_FINE_LOCATION
log_success "Permissions granted"

# Enable Bluetooth
log_info "Enabling Bluetooth..."
adb shell svc bluetooth enable
sleep 2

# Check RPi status
log_info "Checking RPi BLE service..."
if ssh -o ConnectTimeout=5 mia@$RPI_HOST 'sudo systemctl is-active --quiet mia-ble-obd' 2>/dev/null; then
    log_success "RPi BLE service is running"
else
    log_warning "RPi BLE service may not be running"
fi

# Launch app
log_info "Launching app..."
adb shell am force-stop "$PACKAGE_NAME" 2>/dev/null || true
sleep 1
adb shell am start -n "$FULL_ACTIVITY"
sleep 5
log_success "App launched"

log_info "=== Test Instructions ==="
log_info "1. Navigate to BLE/OBD devices screen in the app"
log_info "2. Tap 'Scan' to search for BLE devices"
log_info "3. Look for 'MIA OBD-II Adapter' in the results"
log_info "4. Try to connect to it"
log_info ""
log_info "Monitoring logs... (Press Ctrl+C when done)"

# Monitor logs
log_info "=== Android Logs (BLE related) ==="
adb logcat -c  # Clear log buffer
timeout 60 adb logcat | grep -iE "ble|bluetooth|obd|gatt|connect|mia" --line-buffered || true

log_info ""
log_info "=== RPi BLE Service Logs ==="
ssh mia@$RPI_HOST 'sudo journalctl -u mia-ble-obd --no-pager -n 30' || true

log_success "Test completed!"
