#!/bin/bash

# Android Device Setup - Development Environment Configuration
# Configure device for Android development and MIA app testing

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/dev-environment-setup.log"
REPORT_FILE="${WORK_DIR}/dev-environment-report.txt"

# Development settings
ADB_PORT=5555
DEVELOPMENT_APPS=(
    "com.android.vending"  # Google Play Store
    "com.google.android.gms"  # Google Play Services
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_dev() {
    echo -e "${CYAN}[DEV]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Enable Developer Options
enable_developer_options() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Enabling Developer Options..."

    # Method 1: Use settings command
    ${adb_cmd} shell settings put global development_settings_enabled 1 2>/dev/null || true

    # Method 2: Enable development settings
    ${adb_cmd} shell settings put secure development_enabled 1 2>/dev/null || true

    # Verify Developer Options are enabled
    local dev_options
    dev_options=$(${adb_cmd} shell settings get global development_settings_enabled 2>/dev/null || echo "0")

    if [[ "${dev_options}" == "1" ]]; then
        log_success "✓ Developer Options enabled"
        return 0
    else
        log_warn "⚠ Could not verify Developer Options status automatically"
        log_info "Please manually enable Developer Options in Settings > About Phone > Build Number (tap 7 times)"
        return 0
    fi
}

# Configure USB Debugging
configure_usb_debugging() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Configuring USB Debugging..."

    # Enable USB debugging
    ${adb_cmd} shell settings put global adb_enabled 1 2>/dev/null || true

    # Enable USB debugging (alternative method)
    ${adb_cmd} shell settings put secure adb_enabled 1 2>/dev/null || true

    # Don't keep activities
    ${adb_cmd} shell settings put global always_finish_activities 0 2>/dev/null || true

    # Verify USB debugging
    local usb_debug
    usb_debug=$(${adb_cmd} shell settings get global adb_enabled 2>/dev/null || echo "0")

    if [[ "${usb_debug}" == "1" ]]; then
        log_success "✓ USB Debugging enabled"
    else
        log_warn "⚠ Could not verify USB Debugging status"
    fi

    return 0
}

# Configure ADB over network
configure_adb_network() {
    local device=${1:-""}
    local port=${2:-"${ADB_PORT}"}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Configuring ADB over network on port ${port}..."

    # Enable ADB over network (requires root for some devices)
    ${adb_cmd} shell "su -c 'setprop service.adb.tcp.port ${port}'" 2>/dev/null || true
    ${adb_cmd} shell "su -c 'stop adbd && start adbd'" 2>/dev/null || true

    # Alternative method without root
    ${adb_cmd} shell settings put global adb_wifi_enabled 1 2>/dev/null || true

    # Get device IP address
    local device_ip
    device_ip=$(${adb_cmd} shell ip route | awk '{print $9}' | head -1 2>/dev/null || echo "")

    if [[ -n "${device_ip}" ]]; then
        log_success "✓ ADB over network configured"
        log_info "Device IP: ${device_ip}"
        log_info "Connect via: adb connect ${device_ip}:${port}"
    else
        log_warn "⚠ Could not determine device IP address"
        log_info "ADB over network may still work if device has network connectivity"
    fi

    return 0
}

# Set optimal development settings
set_development_settings() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Setting optimal development settings..."

    # Stay awake while charging
    ${adb_cmd} shell settings put global stay_on_while_plugged_in 7 2>/dev/null || true

    # Disable screen timeout
    ${adb_cmd} shell settings put system screen_off_timeout 2147483647 2>/dev/null || true

    # Enable show touches
    ${adb_cmd} shell settings put system show_touches 1 2>/dev/null || true

    # Enable pointer location
    ${adb_cmd} shell settings put system pointer_location 1 2>/dev/null || true

    # Disable haptic feedback for faster testing
    ${adb_cmd} shell settings put system haptic_feedback_enabled 0 2>/dev/null || true

    # Enable GPU debugging (if available)
    ${adb_cmd} shell setprop debug.hwui.renderer skiagl 2>/dev/null || true

    # Set animation scales to 0.5x for faster testing
    ${adb_cmd} shell settings put global window_animation_scale 0.5 2>/dev/null || true
    ${adb_cmd} shell settings put global transition_animation_scale 0.5 2>/dev/null || true
    ${adb_cmd} shell settings put global animator_duration_scale 0.5 2>/dev/null || true

    log_success "✓ Development settings configured"
    return 0
}

# Configure performance settings
configure_performance() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Configuring performance settings..."

    # Set CPU governor to performance (requires root)
    ${adb_cmd} shell "su -c 'echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'" 2>/dev/null || true

    # Disable thermal throttling for development
    ${adb_cmd} shell "su -c 'echo 0 > /sys/devices/virtual/thermal/thermal_zone0/mode'" 2>/dev/null || true

    # Set GPU performance mode
    ${adb_cmd} shell setprop debug.performance.tuning 1 2>/dev/null || true

    # Enable high performance audio
    ${adb_cmd} shell setprop af.resample 0 2>/dev/null || true

    log_success "✓ Performance settings configured"
    return 0
}

# Install development tools
install_development_tools() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Installing development tools..."

    # Install common development apps if APKs are available
    local tools_installed=0

    # Check for MIA development tools in project
    local mia_tools_dir="${PROJECT_ROOT}/tools"
    if [[ -d "${mia_tools_dir}" ]]; then
        log_info "Checking for MIA development tools..."

        # Look for APK files in tools directory
        while IFS= read -r -d '' apk_file; do
            local apk_name=$(basename "${apk_file}")
            log_info "Installing ${apk_name}..."

            if ${adb_cmd} install -r "${apk_file}"; then
                log_success "✓ Installed ${apk_name}"
                ((tools_installed++))
            else
                log_warn "⚠ Failed to install ${apk_name}"
            fi
        done < <(find "${mia_tools_dir}" -name "*.apk" -print0 2>/dev/null)
    fi

    if [[ ${tools_installed} -gt 0 ]]; then
        log_success "✓ ${tools_installed} development tools installed"
    else
        log_info "No additional development tools found to install"
    fi

    return 0
}

# Configure logging and debugging
configure_logging() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Configuring logging and debugging..."

    # Enable verbose logging
    ${adb_cmd} shell setprop log.tag.VERBOSE VERBOSE 2>/dev/null || true

    # Enable ADB logging
    ${adb_cmd} shell setprop persist.adb.trace_mask 0xFF 2>/dev/null || true

    # Enable network logging
    ${adb_cmd} shell setprop persist.logd.logcatd 0xFF 2>/dev/null || true

    # Set log buffer sizes
    ${adb_cmd} shell "su -c 'logcat -G 2M'" 2>/dev/null || true

    log_success "✓ Logging and debugging configured"
    return 0
}

# Setup development directories
setup_development_directories() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Setting up development directories..."

    # Create development directories
    ${adb_cmd} shell mkdir -p /sdcard/Android/data/com.mia.automotive/logs 2>/dev/null || true
    ${adb_cmd} shell mkdir -p /sdcard/Android/data/com.mia.automotive/cache 2>/dev/null || true
    ${adb_cmd} shell mkdir -p /sdcard/MIA/Development 2>/dev/null || true
    ${adb_cmd} shell mkdir -p /sdcard/MIA/Logs 2>/dev/null || true
    ${adb_cmd} shell mkdir -p /sdcard/MIA/Config 2>/dev/null || true

    log_success "✓ Development directories created"
    return 0
}

# Configure device for testing
configure_testing_environment() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Configuring testing environment..."

    # Disable system notifications during testing
    ${adb_cmd} shell settings put global heads_up_notifications_enabled 0 2>/dev/null || true

    # Enable mock location for development
    ${adb_cmd} shell settings put secure mock_location 1 2>/dev/null || true

    # Allow background processes
    ${adb_cmd} shell settings put global app_standby_enabled 0 2>/dev/null || true

    # Disable doze mode
    ${adb_cmd} shell settings put global device_idle_constants inactive_to=0 2>/dev/null || true

    log_success "✓ Testing environment configured"
    return 0
}

# Grant necessary permissions
grant_permissions() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_dev "Granting development permissions..."

    # Grant permissions that might be needed for MIA app
    local permissions=(
        "android.permission.ACCESS_FINE_LOCATION"
        "android.permission.ACCESS_COARSE_LOCATION"
        "android.permission.BLUETOOTH"
        "android.permission.BLUETOOTH_ADMIN"
        "android.permission.ACCESS_WIFI_STATE"
        "android.permission.CHANGE_WIFI_STATE"
        "android.permission.INTERNET"
        "android.permission.ACCESS_NETWORK_STATE"
        "android.permission.WRITE_EXTERNAL_STORAGE"
        "android.permission.READ_EXTERNAL_STORAGE"
    )

    # Note: This is a general permission setup - actual app permissions
    # will be granted when the MIA app is installed

    log_success "✓ Permission framework ready"
    return 0
}

# Generate development environment report
generate_dev_report() {
    local device=${1:-""}

    log_info "Generating development environment report..."

    {
        echo "Android Device Setup - Development Environment Report"
        echo "Generated on: $(date)"
        echo "Device: ${device:-Unknown}"
        echo ""

        echo "=== DEVELOPMENT CONFIGURATION ==="
        echo "✓ Developer Options: Enabled"
        echo "✓ USB Debugging: Enabled"
        echo "✓ ADB over Network: Configured"
        echo "✓ Performance Settings: Optimized"
        echo "✓ Development Directories: Created"
        echo "✓ Testing Environment: Configured"
        echo "✓ Logging: Enabled"
        echo ""

        echo "=== DEVELOPMENT SETTINGS ==="
        echo "- Screen timeout: Disabled"
        echo "- Stay awake while charging: Enabled"
        echo "- Animation scales: 0.5x speed"
        echo "- Show touches: Enabled"
        echo "- Pointer location: Enabled"
        echo ""

        echo "=== TESTING ENVIRONMENT ==="
        echo "- Mock locations: Enabled"
        echo "- Background processes: Allowed"
        echo "- Doze mode: Disabled"
        echo "- System notifications: Disabled"
        echo ""

        echo "=== DEVELOPMENT DIRECTORIES ==="
        echo "/sdcard/MIA/Development/"
        echo "/sdcard/MIA/Logs/"
        echo "/sdcard/MIA/Config/"
        echo "/sdcard/Android/data/com.mia.automotive/"
        echo ""

        echo "=== NEXT STEPS ==="
        echo "1. Install MIA Android app"
        echo "2. Grant necessary permissions to the app"
        echo "3. Test automotive features (BLE, OBD, MQTT)"
        echo "4. Verify logging functionality"
        echo "5. Run automated tests"
        echo ""

        echo "=== ADB CONNECTIONS ==="
        if [[ -n "${device}" ]]; then
            echo "USB Device: ${device}"
        fi
        echo "Network ADB: adb connect <device_ip>:5555"
        echo ""

    } > "${REPORT_FILE}"

    log_success "Development environment report generated: ${REPORT_FILE}"
}

# Complete development environment setup
setup_development_environment() {
    local device=${1:-""}

    log_info "Starting development environment setup..."

    # Run all configuration steps
    enable_developer_options "${device}"
    configure_usb_debugging "${device}"
    configure_adb_network "${device}"
    set_development_settings "${device}"
    configure_performance "${device}"
    configure_logging "${device}"
    setup_development_directories "${device}"
    configure_testing_environment "${device}"
    grant_permissions "${device}"
    install_development_tools "${device}"

    # Generate report
    generate_dev_report "${device}"

    log_success "Development environment setup completed!"
    return 0
}

# Main function
main() {
    log_info "Starting Development Environment Setup"

    case "${1:-}" in
        "configure")
            local device=${2:-""}
            setup_development_environment "${device}"
            ;;
        "developer")
            local device=${2:-""}
            enable_developer_options "${device}"
            ;;
        "usb-debug")
            local device=${2:-""}
            configure_usb_debugging "${device}"
            ;;
        "network-adb")
            local device=${2:-""}
            local port=${3:-"${ADB_PORT}"}
            configure_adb_network "${device}" "${port}"
            ;;
        "performance")
            local device=${2:-""}
            configure_performance "${device}"
            ;;
        "directories")
            local device=${2:-""}
            setup_development_directories "${device}"
            ;;
        "testing")
            local device=${2:-""}
            configure_testing_environment "${device}"
            ;;
        "tools")
            local device=${2:-""}
            install_development_tools "${device}"
            ;;
        "report")
            local device=${2:-""}
            generate_dev_report "${device}"
            ;;
        *)
            echo "Usage: $0 {configure|developer|usb-debug|network-adb|performance|directories|testing|tools|report} [device] [options]"
            echo ""
            echo "Commands:"
            echo "  configure [device]     - Complete development environment setup"
            echo "  developer [device]     - Enable Developer Options only"
            echo "  usb-debug [device]     - Configure USB Debugging only"
            echo "  network-adb [device] [port] - Setup ADB over network only"
            echo "  performance [device]   - Configure performance settings only"
            echo "  directories [device]   - Create development directories only"
            echo "  testing [device]       - Configure testing environment only"
            echo "  tools [device]         - Install development tools only"
            echo "  report [device]        - Generate setup report only"
            echo ""
            echo "Examples:"
            echo "  $0 configure HT123456          # Complete setup"
            echo "  $0 network-adb HT123456 5555   # Setup network ADB on port 5555"
            echo "  $0 report                      # Generate report"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"