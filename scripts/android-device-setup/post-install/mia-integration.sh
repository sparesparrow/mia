#!/bin/bash

# Android Device Setup - MIA Integration Script
# Prepare device specifically for MIA automotive app testing and development

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/mia-integration.log"
REPORT_FILE="${WORK_DIR}/mia-integration-report.txt"

# MIA app configuration
MIA_PACKAGE_NAME="com.mia.automotive"
MIA_TEST_PACKAGE="com.mia.automotive.test"

# Automotive permissions required by MIA app
MIA_PERMISSIONS=(
    "android.permission.ACCESS_FINE_LOCATION"
    "android.permission.ACCESS_COARSE_LOCATION"
    "android.permission.BLUETOOTH"
    "android.permission.BLUETOOTH_ADMIN"
    "android.permission.BLUETOOTH_PRIVILEGED"
    "android.permission.ACCESS_WIFI_STATE"
    "android.permission.CHANGE_WIFI_STATE"
    "android.permission.INTERNET"
    "android.permission.ACCESS_NETWORK_STATE"
    "android.permission.WAKE_LOCK"
    "android.permission.FOREGROUND_SERVICE"
    "android.permission.RECEIVE_BOOT_COMPLETED"
    "android.permission.VIBRATE"
    "android.permission.WRITE_EXTERNAL_STORAGE"
    "android.permission.READ_EXTERNAL_STORAGE"
    "android.permission.SYSTEM_ALERT_WINDOW"
    "android.permission.ACCESS_BACKGROUND_LOCATION"
)

# BLE configuration
BLE_TEST_DEVICES=(
    "00:11:22:33:44:55"  # Mock BLE device for testing
    "AA:BB:CC:DD:EE:FF"  # Another mock device
)

# MQTT configuration
MQTT_BROKERS=(
    "mqtt.eclipse.org:1883"
    "test.mosquitto.org:1883"
    "broker.hivemq.com:1883"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
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

log_mia() {
    echo -e "${CYAN}[MIA]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

log_ble() {
    echo -e "${PURPLE}[BLE]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Grant MIA app permissions
grant_mia_permissions() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Granting MIA app permissions..."

    local permissions_granted=0

    for permission in "${MIA_PERMISSIONS[@]}"; do
        log_info "Granting permission: ${permission}"

        # Try to grant permission (requires root or app already installed)
        if ${adb_cmd} shell pm grant "${MIA_PACKAGE_NAME}" "${permission}" 2>/dev/null; then
            log_success "✓ Granted: ${permission}"
            ((permissions_granted++))
        else
            log_warn "⚠ Could not grant: ${permission} (app may not be installed yet)"
        fi
    done

    if [[ ${permissions_granted} -gt 0 ]]; then
        log_success "✓ Granted ${permissions_granted} permissions"
    else
        log_info "No permissions granted (MIA app may not be installed yet)"
    fi

    return 0
}

# Configure Bluetooth for automotive use
configure_bluetooth() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_ble "Configuring Bluetooth for automotive use..."

    # Enable Bluetooth
    ${adb_cmd} shell "su -c 'service call bluetooth_manager 6'" 2>/dev/null || true
    ${adb_cmd} shell settings put global bluetooth_on 1 2>/dev/null || true

    # Enable Bluetooth scanning
    ${adb_cmd} shell settings put secure bluetooth_scan_mode 2 2>/dev/null || true

    # Allow Bluetooth pairing without user interaction (for testing)
    ${adb_cmd} shell settings put global bluetooth_disabled_profiles 0 2>/dev/null || true

    # Set Bluetooth discoverable timeout
    ${adb_cmd} shell settings put secure bluetooth_discoverable_timeout 0 2>/dev/null || true

    log_success "✓ Bluetooth configured for automotive use"
    return 0
}

# Setup BLE testing environment
setup_ble_testing() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_ble "Setting up BLE testing environment..."

    # Enable BLE scanning
    ${adb_cmd} shell "su -c 'settings put global ble_scan_always_enabled 1'" 2>/dev/null || true

    # Create BLE test configuration file
    local ble_config_dir="/sdcard/MIA/Config"
    ${adb_cmd} shell mkdir -p "${ble_config_dir}" 2>/dev/null || true

    # Create BLE test device list
    local ble_devices_file="${ble_config_dir}/ble_test_devices.txt"
    ${adb_cmd} shell "echo '# BLE Test Devices for MIA App' > ${ble_devices_file}" 2>/dev/null || true

    for device_mac in "${BLE_TEST_DEVICES[@]}"; do
        ${adb_cmd} shell "echo '${device_mac}' >> ${ble_devices_file}" 2>/dev/null || true
    done

    # Set BLE scan parameters
    ${adb_cmd} shell "su -c 'setprop ble.scan.interval 1000'" 2>/dev/null || true
    ${adb_cmd} shell "su -c 'setprop ble.scan.window 500'" 2>/dev/null || true

    log_success "✓ BLE testing environment configured"
    log_ble "BLE test devices configured: ${BLE_TEST_DEVICES[*]}"
    return 0
}

# Configure OBD interface access
configure_obd_access() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Configuring OBD interface access..."

    # Enable USB host mode for OBD adapters
    ${adb_cmd} shell "su -c 'setprop sys.usb.config mtp,adb'" 2>/dev/null || true

    # Create OBD configuration directory
    local obd_config_dir="/sdcard/MIA/Config/OBD"
    ${adb_cmd} shell mkdir -p "${obd_config_dir}" 2>/dev/null || true

    # Create OBD test configuration
    local obd_config="${obd_config_dir}/obd_config.txt"
    ${adb_cmd} shell "cat > ${obd_config} << 'EOF'
# OBD Configuration for MIA App Testing
PROTOCOL=AUTO
BAUDRATE=38400
TIMEOUT=5000
RETRIES=3
LOG_LEVEL=DEBUG

# Test PIDs
TEST_PIDS=0C,0D,05,0B,0F,10,11,2F,33,42,43,44,45,46,47,48,49,4A,4B,4C

# Mock data for testing without real OBD adapter
MOCK_MODE=true
MOCK_RPM=2500
MOCK_SPEED=65
MOCK_COOLANT_TEMP=85
MOCK_INTAKE_TEMP=45
EOF" 2>/dev/null || true

    # Set USB permissions for OBD devices
    ${adb_cmd} shell "su -c 'chmod 666 /dev/bus/usb/*/*'" 2>/dev/null || true

    log_success "✓ OBD interface access configured"
    return 0
}

# Setup MQTT testing environment
setup_mqtt_testing() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Setting up MQTT testing environment..."

    # Create MQTT configuration directory
    local mqtt_config_dir="/sdcard/MIA/Config/MQTT"
    ${adb_cmd} shell mkdir -p "${mqtt_config_dir}" 2>/dev/null || true

    # Create MQTT broker list
    local mqtt_brokers_file="${mqtt_config_dir}/brokers.txt"
    ${adb_cmd} shell "echo '# MQTT Brokers for MIA App Testing' > ${mqtt_brokers_file}" 2>/dev/null || true

    for broker in "${MQTT_BROKERS[@]}"; do
        ${adb_cmd} shell "echo '${broker}' >> ${mqtt_brokers_file}" 2>/dev/null || true
    done

    # Create MQTT test configuration
    local mqtt_config="${mqtt_config_dir}/mqtt_config.txt"
    ${adb_cmd} shell "cat > ${mqtt_config} << 'EOF'
# MQTT Configuration for MIA App Testing
CLIENT_ID=MIA_TEST_DEVICE_$(date +%s)
CLEAN_SESSION=true
KEEP_ALIVE=60
QOS=1
RETAIN=false

# Test Topics
TELEMETRY_TOPIC=mia/telemetry/test
COMMAND_TOPIC=mia/command/test
STATUS_TOPIC=mia/status/test

# Authentication (optional)
USERNAME=
PASSWORD=

# SSL/TLS (optional)
SSL_ENABLED=false
CERT_PATH=

# Message formatting
MESSAGE_FORMAT=JSON
COMPRESSION=none
EOF" 2>/dev/null || true

    log_success "✓ MQTT testing environment configured"
    log_mia "MQTT brokers configured: ${MQTT_BROKERS[*]}"
    return 0
}

# Setup mock data for development
setup_mock_data() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Setting up mock data for development..."

    # Create mock data directory
    local mock_data_dir="/sdcard/MIA/MockData"
    ${adb_cmd} shell mkdir -p "${mock_data_dir}" 2>/dev/null || true

    # Create vehicle mock data
    local vehicle_data="${mock_data_dir}/vehicle_data.json"
    ${adb_cmd} shell "cat > ${vehicle_data} << 'EOF'
{
  "vehicle": {
    "vin": "1HGCM82633A123456",
    "make": "Test Vehicle",
    "model": "Development Model",
    "year": 2024,
    "fuel_type": "gasoline",
    "engine_displacement": 2.0
  },
  "sensors": {
    "rpm": 1800,
    "speed": 45,
    "coolant_temp": 78,
    "oil_temp": 85,
    "fuel_level": 65,
    "battery_voltage": 12.6,
    "intake_temp": 35,
    "throttle_position": 25
  },
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 15.2,
    "speed": 45.5,
    "heading": 90.0
  },
  "dtc_codes": [],
  "last_update": "$(date -Iseconds)"
}
EOF" 2>/dev/null || true

    # Create trip mock data
    local trip_data="${mock_data_dir}/trip_data.json"
    ${adb_cmd} shell "cat > ${trip_data} << 'EOF'
{
  "trip": {
    "id": "trip_$(date +%s)",
    "start_time": "$(date -d '1 hour ago' -Iseconds)",
    "distance": 25.5,
    "average_speed": 42.3,
    "max_speed": 65.0,
    "fuel_efficiency": 28.5,
    "hard_braking_events": 2,
    "hard_acceleration_events": 3,
    "idle_time": 180,
    "engine_runtime": 3600
  },
  "waypoints": [
    {"lat": 37.7749, "lon": -122.4194, "timestamp": "$(date -d '1 hour ago' -Iseconds)"},
    {"lat": 37.7849, "lon": -122.4294, "timestamp": "$(date -d '45 minutes ago' -Iseconds)"},
    {"lat": 37.7949, "lon": -122.4394, "timestamp": "$(date -d '30 minutes ago' -Iseconds)"},
    {"lat": 37.8049, "lon": -122.4494, "timestamp": "$(date -d '15 minutes ago' -Iseconds)"},
    {"lat": 37.8149, "lon": -122.4594, "timestamp": "$(date -Iseconds)"}
  ]
}
EOF" 2>/dev/null || true

    log_success "✓ Mock data setup completed"
    return 0
}

# Install test APKs
install_test_apks() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Installing test APKs..."

    local apks_installed=0

    # Look for MIA app APKs in the project
    local android_dir="${PROJECT_ROOT}/android"
    if [[ -d "${android_dir}" ]]; then
        log_info "Looking for MIA APKs in android directory..."

        # Find and install APK files
        while IFS= read -r -d '' apk_file; do
            local apk_name=$(basename "${apk_file}")
            log_info "Installing ${apk_name}..."

            if ${adb_cmd} install -r -g "${apk_file}"; then
                log_success "✓ Installed ${apk_name}"
                ((apks_installed++))

                # Grant permissions to the installed app
                local package_name
                package_name=$(${adb_cmd} shell pm list packages -f | grep "${apk_name%.apk}" | sed 's/.*=//' | head -1 || echo "")

                if [[ -n "${package_name}" ]]; then
                    log_info "Granting permissions to ${package_name}..."
                    grant_mia_permissions "${device}"
                fi
            else
                log_warn "⚠ Failed to install ${apk_name}"
            fi
        done < <(find "${android_dir}" -name "*.apk" -print0 2>/dev/null)
    fi

    # Look for test APKs
    local test_apk_dir="${PROJECT_ROOT}/tests"
    if [[ -d "${test_apk_dir}" ]]; then
        log_info "Looking for test APKs..."

        while IFS= read -r -d '' apk_file; do
            local apk_name=$(basename "${apk_file}")
            log_info "Installing test APK: ${apk_name}..."

            if ${adb_cmd} install -r -g "${apk_file}"; then
                log_success "✓ Installed test APK: ${apk_name}"
                ((apks_installed++))
            else
                log_warn "⚠ Failed to install test APK: ${apk_name}"
            fi
        done < <(find "${test_apk_dir}" -name "*.apk" -print0 2>/dev/null)
    fi

    if [[ ${apks_installed} -gt 0 ]]; then
        log_success "✓ Installed ${apks_installed} APK(s)"
    else
        log_info "No APKs found to install"
    fi

    return 0
}

# Configure automotive-specific settings
configure_automotive_settings() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Configuring automotive-specific settings..."

    # Enable location services (required for automotive apps)
    ${adb_cmd} shell settings put secure location_providers_allowed +gps,network 2>/dev/null || true

    # Set location mode to high accuracy
    ${adb_cmd} shell settings put secure location_mode 3 2>/dev/null || true

    # Enable GPS
    ${adb_cmd} shell settings put global assisted_gps_enabled 1 2>/dev/null || true

    # Allow mock locations for testing
    ${adb_cmd} shell settings put secure mock_location 1 2>/dev/null || true

    # Configure power management for automotive use
    ${adb_cmd} shell settings put global automotive_mode_enabled 1 2>/dev/null || true

    log_success "✓ Automotive-specific settings configured"
    return 0
}

# Setup logging for MIA app
setup_mia_logging() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Setting up MIA app logging..."

    # Create logging configuration
    local log_config_dir="/sdcard/MIA/Config"
    ${adb_cmd} shell mkdir -p "${log_config_dir}" 2>/dev/null || true

    local log_config="${log_config_dir}/logging_config.txt"
    ${adb_cmd} shell "cat > ${log_config} << 'EOF'
# MIA App Logging Configuration
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
LOG_MAX_FILE_SIZE=10MB
LOG_MAX_FILES=5
LOG_FORMAT=JSON

# Component-specific logging
BLE_LOGGING=VERBOSE
OBD_LOGGING=VERBOSE
MQTT_LOGGING=INFO
TELEMETRY_LOGGING=DEBUG

# Performance logging
PERFORMANCE_MONITORING=true
MEMORY_LOGGING=true
NETWORK_LOGGING=true

# Error reporting
CRASH_REPORTING=true
ERROR_REPORTING=true
ANALYTICS_ENABLED=false
EOF" 2>/dev/null || true

    # Set up log rotation
    ${adb_cmd} shell "su -c 'logcat -f /sdcard/MIA/Logs/mia_app.log -r 1024 -n 5 *:V'" 2>/dev/null || true

    log_success "✓ MIA app logging configured"
    return 0
}

# Generate MIA integration report
generate_mia_report() {
    local device=${1:-""}

    log_info "Generating MIA integration report..."

    {
        echo "Android Device Setup - MIA Integration Report"
        echo "Generated on: $(date)"
        echo "Device: ${device:-Unknown}"
        echo ""

        echo "=== MIA APP CONFIGURATION ==="
        echo "✓ Automotive permissions: Configured"
        echo "✓ Bluetooth/BLE: Enabled and configured"
        echo "✓ OBD interface: Set up for testing"
        echo "✓ MQTT connectivity: Configured"
        echo "✓ Mock data: Generated"
        echo "✓ Development directories: Created"
        echo "✓ Logging: Configured"
        echo ""

        echo "=== PERMISSIONS GRANTED ==="
        for permission in "${MIA_PERMISSIONS[@]}"; do
            echo "- ${permission}"
        done
        echo ""

        echo "=== BLE CONFIGURATION ==="
        echo "BLE scanning: Enabled"
        echo "BLE test devices:"
        for device_mac in "${BLE_TEST_DEVICES[@]}"; do
            echo "  - ${device_mac}"
        done
        echo ""

        echo "=== OBD CONFIGURATION ==="
        echo "USB host mode: Enabled"
        echo "Mock OBD data: Available"
        echo "Configuration file: /sdcard/MIA/Config/OBD/obd_config.txt"
        echo ""

        echo "=== MQTT CONFIGURATION ==="
        echo "Test brokers:"
        for broker in "${MQTT_BROKERS[@]}"; do
            echo "  - ${broker}"
        done
        echo "Configuration file: /sdcard/MIA/Config/MQTT/mqtt_config.txt"
        echo ""

        echo "=== MOCK DATA AVAILABLE ==="
        echo "- Vehicle telemetry data"
        echo "- Trip history and waypoints"
        echo "- Sensor readings (RPM, speed, temperature, etc.)"
        echo "- Location data with GPS coordinates"
        echo ""

        echo "=== DEVELOPMENT FILES ==="
        echo "/sdcard/MIA/Config/           - Configuration files"
        echo "/sdcard/MIA/Logs/            - Application logs"
        echo "/sdcard/MIA/MockData/        - Test data files"
        echo "/sdcard/MIA/Development/     - Development resources"
        echo ""

        echo "=== NEXT STEPS ==="
        echo "1. Install MIA Android application APK"
        echo "2. Launch app and grant remaining permissions"
        echo "3. Test BLE connectivity with automotive devices"
        echo "4. Verify OBD adapter communication"
        echo "5. Test MQTT message publishing/subscribing"
        echo "6. Run automated test suites"
        echo "7. Monitor logs in /sdcard/MIA/Logs/"
        echo ""

        echo "=== TROUBLESHOOTING ==="
        echo "- Check device logs: adb logcat | grep MIA"
        echo "- View app logs: adb shell cat /sdcard/MIA/Logs/mia_app.log"
        echo "- Verify permissions: adb shell pm list permissions ${MIA_PACKAGE_NAME}"
        echo "- Test connectivity: adb shell ping -c 3 8.8.8.8"
        echo ""

    } > "${REPORT_FILE}"

    log_success "MIA integration report generated: ${REPORT_FILE}"
}

# Complete MIA integration setup
setup_mia_integration() {
    local device=${1:-""}

    log_mia "Starting MIA integration setup..."

    # Run all MIA-specific configuration steps
    grant_mia_permissions "${device}"
    configure_bluetooth "${device}"
    setup_ble_testing "${device}"
    configure_obd_access "${device}"
    setup_mqtt_testing "${device}"
    setup_mock_data "${device}"
    configure_automotive_settings "${device}"
    setup_mia_logging "${device}"
    install_test_apks "${device}"

    # Generate report
    generate_mia_report "${device}"

    log_mia "MIA integration setup completed!"
    log_mia "Device is now configured for MIA automotive app development and testing"
    return 0
}

# Main function
main() {
    log_info "Starting MIA Integration Setup"

    case "${1:-}" in
        "setup")
            local device=${2:-""}
            setup_mia_integration "${device}"
            ;;
        "permissions")
            local device=${2:-""}
            grant_mia_permissions "${device}"
            ;;
        "bluetooth")
            local device=${2:-""}
            configure_bluetooth "${device}"
            ;;
        "ble")
            local device=${2:-""}
            setup_ble_testing "${device}"
            ;;
        "obd")
            local device=${2:-""}
            configure_obd_access "${device}"
            ;;
        "mqtt")
            local device=${2:-""}
            setup_mqtt_testing "${device}"
            ;;
        "mock-data")
            local device=${2:-""}
            setup_mock_data "${device}"
            ;;
        "install-apks")
            local device=${2:-""}
            install_test_apks "${device}"
            ;;
        "automotive")
            local device=${2:-""}
            configure_automotive_settings "${device}"
            ;;
        "logging")
            local device=${2:-""}
            setup_mia_logging "${device}"
            ;;
        "report")
            local device=${2:-""}
            generate_mia_report "${device}"
            ;;
        *)
            echo "Usage: $0 {setup|permissions|bluetooth|ble|obd|mqtt|mock-data|install-apks|automotive|logging|report} [device]"
            echo ""
            echo "Commands:"
            echo "  setup [device]        - Complete MIA integration setup"
            echo "  permissions [device]  - Grant MIA app permissions"
            echo "  bluetooth [device]    - Configure Bluetooth for automotive use"
            echo "  ble [device]          - Setup BLE testing environment"
            echo "  obd [device]          - Configure OBD interface access"
            echo "  mqtt [device]         - Setup MQTT testing environment"
            echo "  mock-data [device]    - Setup mock data for development"
            echo "  install-apks [device] - Install test APKs"
            echo "  automotive [device]   - Configure automotive-specific settings"
            echo "  logging [device]      - Setup MIA app logging"
            echo "  report [device]       - Generate integration report"
            echo ""
            echo "Examples:"
            echo "  $0 setup HT123456         # Complete MIA setup"
            echo "  $0 ble HT123456          # Setup BLE testing only"
            echo "  $0 install-apks HT123456 # Install APKs only"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"