#!/bin/bash

# Android Device Setup - Device Connection Manager
# Handles all device connection and verification logic for HTC One M7

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/device-manager.log"
REPORT_FILE="${WORK_DIR}/device-report.txt"

# HTC One M7 device specifications
HTC_M7_MODELS=("HTC One" "HTC6500LVW" "HTC One M7" "m7")
HTC_M7_DEVICE_ID="m7"
HTC_M7_USB_VENDORS=("0bb4")  # HTC vendor ID

# Connection timeouts and retries
CONNECTION_TIMEOUT=30
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Check if ADB is available and functional
check_adb() {
    if ! command -v adb >/dev/null 2>&1; then
        log_error "ADB command not found. Run verify-environment.sh first."
        return 1
    fi

    if ! adb version >/dev/null 2>&1; then
        log_error "ADB is not functional"
        return 1
    fi

    log_info "ADB is available and functional"
    return 0
}

# List connected devices
list_devices() {
    log_info "Listing connected devices..."

    local devices
    devices=$(adb devices | grep -v "List of devices" | grep -v "^$" | awk '{print $1}')

    if [[ -z "${devices}" ]]; then
        log_warn "No devices connected"
        return 1
    fi

    local device_count=$(echo "${devices}" | wc -l)
    log_info "Found ${device_count} device(s):"
    echo "${devices}" | while read -r device; do
        log_info "  - ${device}"
    done

    echo "${devices}"
    return 0
}

# Wait for device connection with timeout
wait_for_device() {
    local timeout=${1:-${CONNECTION_TIMEOUT}}
    local start_time=$(date +%s)

    log_info "Waiting for device connection (timeout: ${timeout}s)..."

    while true; do
        if adb devices | grep -q "device$"; then
            log_success "Device connected"
            return 0
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ ${elapsed} -ge ${timeout} ]]; then
            log_error "Device connection timeout after ${timeout} seconds"
            return 1
        fi

        sleep 2
    done
}

# Get device properties
get_device_info() {
    local device=${1:-""}

    log_info "Getting device information..."

    # Build ADB command
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Get basic device info
    local manufacturer=$(${adb_cmd} shell getprop ro.product.manufacturer 2>/dev/null | tr -d '\r')
    local model=$(${adb_cmd} shell getprop ro.product.model 2>/dev/null | tr -d '\r')
    local device_name=$(${adb_cmd} shell getprop ro.product.device 2>/dev/null | tr -d '\r')
    local android_version=$(${adb_cmd} shell getprop ro.build.version.release 2>/dev/null | tr -d '\r')
    local build_id=$(${adb_cmd} shell getprop ro.build.id 2>/dev/null | tr -d '\r')
    local serial=$(${adb_cmd} shell getprop ro.serialno 2>/dev/null | tr -d '\r')
    local bootloader=$(${adb_cmd} shell getprop ro.bootloader 2>/dev/null | tr -d '\r')

    # Create device info associative array
    declare -gA DEVICE_INFO=(
        ["manufacturer"]="${manufacturer}"
        ["model"]="${model}"
        ["device_name"]="${device_name}"
        ["android_version"]="${android_version}"
        ["build_id"]="${build_id}"
        ["serial"]="${serial}"
        ["bootloader"]="${bootloader}"
    )

    log_info "Device Info:"
    log_info "  Manufacturer: ${manufacturer}"
    log_info "  Model: ${model}"
    log_info "  Device: ${device_name}"
    log_info "  Android Version: ${android_version}"
    log_info "  Build ID: ${build_id}"
    log_info "  Serial: ${serial}"
    log_info "  Bootloader: ${bootloader}"

    return 0
}

# Validate HTC One M7 device
validate_htc_m7() {
    log_info "Validating HTC One M7 device..."

    # Check manufacturer
    if [[ "${DEVICE_INFO['manufacturer'],,}" != "htc" ]]; then
        log_error "Device is not HTC. Manufacturer: ${DEVICE_INFO['manufacturer']}"
        return 1
    fi

    # Check model variations
    local model_match=false
    for valid_model in "${HTC_M7_MODELS[@]}"; do
        if [[ "${DEVICE_INFO['model'],,}" == "${valid_model,,}" ]]; then
            model_match=true
            break
        fi
    done

    if [[ "${model_match}" != true ]]; then
        log_warn "Device model '${DEVICE_INFO['model']}' may not be HTC One M7"
        log_warn "Expected models: ${HTC_M7_MODELS[*]}"
        log_warn "Proceeding anyway, but functionality is not guaranteed"
    else
        log_success "HTC One M7 device confirmed"
    fi

    # Check device name
    if [[ "${DEVICE_INFO['device_name']}" != "${HTC_M7_DEVICE_ID}" ]]; then
        log_warn "Device name '${DEVICE_INFO['device_name']}' does not match expected '${HTC_M7_DEVICE_ID}'"
    fi

    return 0
}

# Check bootloader status
check_bootloader_status() {
    log_info "Checking bootloader status..."

    local adb_cmd="adb"
    if [[ -n "${1:-}" ]]; then
        adb_cmd="${adb_cmd} -s $1"
    fi

    # Try to get bootloader status from device
    local bootloader_status
    bootloader_status=$(${adb_cmd} shell getprop ro.boot.verifiedbootstate 2>/dev/null | tr -d '\r')

    if [[ -n "${bootloader_status}" ]]; then
        log_info "Bootloader verification state: ${bootloader_status}"
    else
        log_warn "Could not determine bootloader verification state"
    fi

    # Check if device is rooted (simple check)
    local root_check
    root_check=$(${adb_cmd} shell su -c 'echo "root access available"' 2>/dev/null || echo "no root")

    if [[ "${root_check}" == "root access available" ]]; then
        log_info "Device appears to be rooted"
    else
        log_info "Device does not appear to be rooted"
    fi

    return 0
}

# Check device USB connection health
check_connection_health() {
    log_info "Checking device connection health..."

    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Test basic connectivity
    if ! ${adb_cmd} shell echo "test" >/dev/null 2>&1; then
        log_error "Device connection test failed"
        return 1
    fi

    # Test file system access
    if ! ${adb_cmd} shell ls /sdcard >/dev/null 2>&1; then
        log_warn "Limited file system access - may be in recovery mode"
    else
        log_info "File system access confirmed"
    fi

    # Check battery level
    local battery_level
    battery_level=$(${adb_cmd} shell dumpsys battery | grep "level:" | awk '{print $2}' 2>/dev/null || echo "unknown")

    if [[ "${battery_level}" != "unknown" ]]; then
        log_info "Battery level: ${battery_level}%"
        if [[ ${battery_level} -lt 20 ]]; then
            log_warn "Battery level is low (${battery_level}%). Consider charging before flashing."
        fi
    fi

    log_success "Device connection health check passed"
    return 0
}

# Enable USB debugging if possible
enable_usb_debugging() {
    log_info "Checking USB debugging status..."

    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Check if USB debugging is enabled
    local usb_debugging
    usb_debugging=$(${adb_cmd} shell settings get global adb_enabled 2>/dev/null | tr -d '\r')

    if [[ "${usb_debugging}" == "1" ]]; then
        log_success "USB debugging is enabled"
    elif [[ "${usb_debugging}" == "0" ]]; then
        log_warn "USB debugging is disabled"
        log_info "Please enable USB debugging in Developer Options on your device"
        log_info "Settings > Developer Options > USB Debugging"
        return 1
    else
        log_warn "Could not determine USB debugging status"
    fi

    return 0
}

# Authorize device connection
authorize_device() {
    log_info "Checking device authorization..."

    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Check if device is authorized
    local auth_status
    auth_status=$(${adb_cmd} shell echo "authorized" 2>&1)

    if [[ "${auth_status}" == *"unauthorized"* ]] || [[ "${auth_status}" == *"no permissions"* ]]; then
        log_warn "Device is not authorized"
        log_info "Please check your device and authorize the USB debugging connection"
        log_info "Look for the 'Allow USB debugging?' prompt on your device"

        # Wait for authorization
        local attempts=0
        while [[ ${attempts} -lt ${MAX_RETRY_ATTEMPTS} ]]; do
            sleep ${RETRY_DELAY}
            auth_status=$(${adb_cmd} shell echo "authorized" 2>&1)

            if [[ "${auth_status}" != *"unauthorized"* ]] && [[ "${auth_status}" != *"no permissions"* ]]; then
                log_success "Device authorized successfully"
                return 0
            fi

            ((attempts++))
        done

        log_error "Device authorization failed after ${MAX_RETRY_ATTEMPTS} attempts"
        return 1
    else
        log_success "Device is authorized"
    fi

    return 0
}

# Generate device report
generate_device_report() {
    log_info "Generating device report..."

    {
        echo "Android Device Setup - Device Report"
        echo "Generated on: $(date)"
        echo "Device Serial: ${DEVICE_INFO['serial']}"
        echo ""

        echo "=== DEVICE INFORMATION ==="
        echo "Manufacturer: ${DEVICE_INFO['manufacturer']}"
        echo "Model: ${DEVICE_INFO['model']}"
        echo "Device Name: ${DEVICE_INFO['device_name']}"
        echo "Android Version: ${DEVICE_INFO['android_version']}"
        echo "Build ID: ${DEVICE_INFO['build_id']}"
        echo "Bootloader: ${DEVICE_INFO['bootloader']}"
        echo ""

        echo "=== CONNECTION STATUS ==="
        if list_devices >/dev/null 2>&1; then
            echo "✓ Device connected and detected"
        else
            echo "✗ No device connected"
        fi

        if enable_usb_debugging >/dev/null 2>&1; then
            echo "✓ USB debugging enabled"
        else
            echo "✗ USB debugging disabled"
        fi

        if authorize_device >/dev/null 2>&1; then
            echo "✓ Device authorized"
        else
            echo "✗ Device not authorized"
        fi
        echo ""

        echo "=== DEVICE VALIDATION ==="
        if validate_htc_m7 >/dev/null 2>&1; then
            echo "✓ HTC One M7 device confirmed"
        else
            echo "✗ Device validation failed"
        fi
        echo ""

        echo "=== RECOMMENDATIONS ==="
        echo "- Ensure device is charged above 20%"
        echo "- Keep device connected during installation"
        echo "- Backup important data before proceeding"
        echo "- Close other ADB connections"
        echo ""

    } > "${REPORT_FILE}"

    log_success "Device report generated: ${REPORT_FILE}"
    return 0
}

# Interactive device setup
interactive_setup() {
    log_info "Starting interactive device setup..."

    echo ""
    echo "=== HTC One M7 Device Setup ==="
    echo ""
    echo "Please ensure:"
    echo "1. HTC One M7 is connected via USB cable"
    echo "2. USB debugging is enabled (Settings > Developer Options > USB Debugging)"
    echo "3. Screen is unlocked"
    echo "4. You have authorized this computer for USB debugging"
    echo ""
    read -p "Press Enter when ready to continue..."

    # Wait for device
    if ! wait_for_device; then
        log_error "No device detected. Please check connection and try again."
        return 1
    fi

    # Get device information
    if ! get_device_info; then
        log_error "Failed to get device information"
        return 1
    fi

    # Validate device
    if ! validate_htc_m7; then
        log_warn "Device validation failed, but continuing..."
    fi

    # Check bootloader and connection
    check_bootloader_status
    check_connection_health
    enable_usb_debugging
    authorize_device

    # Generate report
    generate_device_report

    log_success "Device setup completed successfully"
    return 0
}

# Main function
main() {
    log_info "Starting Android Device Manager"
    log_info "Working directory: ${WORK_DIR}"

    # Ensure log directory exists
    mkdir -p "${WORK_DIR}/logs"

    case "${1:-}" in
        "list")
            list_devices
            ;;
        "info")
            check_adb
            if wait_for_device; then
                get_device_info "${2:-}"
                generate_device_report
            fi
            ;;
        "validate")
            check_adb
            if wait_for_device; then
                get_device_info "${2:-}"
                validate_htc_m7
                check_bootloader_status "${2:-}"
                check_connection_health "${2:-}"
                generate_device_report
            fi
            ;;
        "setup")
            interactive_setup
            ;;
        "health")
            check_adb
            if wait_for_device; then
                get_device_info "${2:-}"
                check_connection_health "${2:-}"
            fi
            ;;
        *)
            echo "Usage: $0 {list|info|validate|setup|health} [device_serial]"
            echo ""
            echo "Commands:"
            echo "  list     - List connected devices"
            echo "  info     - Get device information"
            echo "  validate - Validate HTC One M7 device"
            echo "  setup    - Interactive device setup"
            echo "  health   - Check connection health"
            echo ""
            echo "Examples:"
            echo "  $0 setup                    # Interactive setup"
            echo "  $0 validate HT123456        # Validate specific device"
            echo "  $0 info                     # Get info for first device"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"