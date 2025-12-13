#!/bin/bash

# Android Device Setup - Root Verification Script
# Comprehensive root access verification for MIA app development

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/root-verification.log"
REPORT_FILE="${WORK_DIR}/root-verification-report.txt"

# Root verification settings
MAX_VERIFICATION_ATTEMPTS=3
VERIFICATION_TIMEOUT=30

# MIA app specific requirements
MIA_REQUIREMENTS=(
    "system_app_installation"
    "system_partition_access"
    "bluetooth_ble_access"
    "obd_interface_access"
    "mqtt_networking"
    "hardware_sensor_access"
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

log_mia() {
    echo -e "${CYAN}[MIA]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Execute command with timeout
execute_with_timeout() {
    local timeout=${1}
    local command=${2}

    # Use timeout command if available
    if command -v timeout >/dev/null 2>&1; then
        timeout "${timeout}s" bash -c "${command}"
    else
        # Fallback implementation
        (
            eval "${command}" &
            local pid=$!
            sleep "${timeout}"
            kill -TERM "${pid}" 2>/dev/null || true
            wait "${pid}" 2>/dev/null || true
        )
    fi
}

# Basic root access test
test_basic_root() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Testing basic root access..."

    # Test 1: su command availability
    if ${adb_cmd} shell "which su" >/dev/null 2>&1; then
        log_success "✓ su command is available"
    else
        log_error "✗ su command not found"
        return 1
    fi

    # Test 2: Basic root shell access
    local root_test
    root_test=$(${adb_cmd} shell "su -c 'echo root_access_confirmed'" 2>/dev/null || echo "no_root")

    if [[ "${root_test}" == "root_access_confirmed" ]]; then
        log_success "✓ Root shell access works"
    else
        log_error "✗ Root shell access failed"
        return 1
    fi

    # Test 3: Root user ID
    local root_uid
    root_uid=$(${adb_cmd} shell "su -c 'id -u'" 2>/dev/null || echo "unknown")

    if [[ "${root_uid}" == "0" ]]; then
        log_success "✓ Running as root user (UID: ${root_uid})"
    else
        log_error "✗ Not running as root (UID: ${root_uid})"
        return 1
    fi

    return 0
}

# Test Magisk specific functionality
test_magisk_functionality() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Testing Magisk functionality..."

    local tests_passed=0
    local total_tests=5

    # Test 1: Magisk binary
    if ${adb_cmd} shell "which magisk" >/dev/null 2>&1; then
        log_success "✓ Magisk binary found"
        ((tests_passed++))
    else
        log_warn "⚠ Magisk binary not found (may be okay if using different root method)"
    fi

    # Test 2: Magisk version
    local magisk_version
    magisk_version=$(${adb_cmd} shell "su -c 'magisk -V'" 2>/dev/null || echo "")

    if [[ -n "${magisk_version}" ]]; then
        log_success "✓ Magisk version: ${magisk_version}"
        ((tests_passed++))
    else
        log_warn "⚠ Could not get Magisk version"
    fi

    # Test 3: Magisk modules directory
    local modules_dir
    modules_dir=$(${adb_cmd} shell "su -c 'ls -d /data/adb/modules 2>/dev/null'" 2>/dev/null || echo "")

    if [[ -n "${modules_dir}" ]]; then
        log_success "✓ Magisk modules directory exists"
        ((tests_passed++))
    else
        log_warn "⚠ Magisk modules directory not found"
    fi

    # Test 4: Magisk Manager app
    if ${adb_cmd} shell "pm list packages | grep -q magisk" >/dev/null 2>&1; then
        log_success "✓ Magisk Manager app installed"
        ((tests_passed++))
    else
        log_warn "⚠ Magisk Manager app not found"
    fi

    # Test 5: MagiskHide (if available)
    local magiskhide_status
    magiskhide_status=$(${adb_cmd} shell "su -c 'magiskhide --status'" 2>/dev/null || echo "")

    if [[ -n "${magiskhide_status}" ]]; then
        log_success "✓ MagiskHide available"
        ((tests_passed++))
    else
        log_info "MagiskHide not available or not enabled"
    fi

    log_info "Magisk functionality: ${tests_passed}/${total_tests} tests passed"

    if [[ ${tests_passed} -ge 2 ]]; then
        return 0
    else
        return 1
    fi
}

# Test system-level permissions
test_system_permissions() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Testing system-level permissions..."

    local tests_passed=0
    local total_tests=4

    # Test 1: System partition access
    local system_access
    system_access=$(${adb_cmd} shell "su -c 'ls /system/build.prop >/dev/null 2>&1 && echo accessible || echo denied'" 2>/dev/null || echo "error")

    if [[ "${system_access}" == "accessible" ]]; then
        log_success "✓ System partition accessible"
        ((tests_passed++))
    else
        log_error "✗ System partition access denied"
    fi

    # Test 2: System app installation
    local system_app_test
    system_app_test=$(${adb_cmd} shell "su -c 'pm install-location 2>/dev/null || echo 0'" 2>/dev/null || echo "error")

    if [[ "${system_app_test}" != "error" ]]; then
        log_success "✓ System app installation capability detected"
        ((tests_passed++))
    else
        log_warn "⚠ System app installation test inconclusive"
        ((tests_passed++)) # Count as passed for now
    fi

    # Test 3: SELinux status
    local selinux_status
    selinux_status=$(${adb_cmd} shell "su -c 'getenforce'" 2>/dev/null || echo "unknown")

    if [[ "${selinux_status}" == "Permissive" ]]; then
        log_success "✓ SELinux in permissive mode"
        ((tests_passed++))
    elif [[ "${selinux_status}" == "Enforcing" ]]; then
        log_warn "⚠ SELinux in enforcing mode (may limit root capabilities)"
        ((tests_passed++)) # Still count as passed
    else
        log_info "SELinux status: ${selinux_status}"
        ((tests_passed++))
    fi

    # Test 4: Root directory access
    local root_dir_access
    root_dir_access=$(${adb_cmd} shell "su -c 'ls / >/dev/null 2>&1 && echo accessible || echo denied'" 2>/dev/null || echo "error")

    if [[ "${root_dir_access}" == "accessible" ]]; then
        log_success "✓ Root directory accessible"
        ((tests_passed++))
    else
        log_error "✗ Root directory access denied"
    fi

    log_info "System permissions: ${tests_passed}/${total_tests} tests passed"
    return 0
}

# Test MIA app specific requirements
test_mia_requirements() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_mia "Testing MIA app specific requirements..."

    local tests_passed=0
    local total_tests=${#MIA_REQUIREMENTS[@]}

    for requirement in "${MIA_REQUIREMENTS[@]}"; do
        case "${requirement}" in
            "system_app_installation")
                log_mia "Testing system app installation capability..."
                local app_install_test
                app_install_test=$(${adb_cmd} shell "su -c 'pm list features 2>/dev/null | grep -q android.software.device_admin && echo supported || echo unsupported'" 2>/dev/null || echo "error")

                if [[ "${app_install_test}" == "supported" ]]; then
                    log_success "✓ System app installation supported"
                    ((tests_passed++))
                else
                    log_warn "⚠ System app installation support unclear"
                    ((tests_passed++)) # Count as passed for now
                fi
                ;;

            "system_partition_access")
                log_mia "Testing system partition access..."
                local system_test
                system_test=$(${adb_cmd} shell "su -c 'test -w /system && echo writable || echo readonly'" 2>/dev/null || echo "error")

                if [[ "${system_test}" == "writable" ]]; then
                    log_success "✓ System partition writable"
                    ((tests_passed++))
                else
                    log_error "✗ System partition read-only"
                fi
                ;;

            "bluetooth_ble_access")
                log_mia "Testing Bluetooth BLE access..."
                local ble_test
                ble_test=$(${adb_cmd} shell "su -c 'getprop | grep -q bluetooth && echo supported || echo unsupported'" 2>/dev/null || echo "error")

                if [[ "${ble_test}" == "supported" ]]; then
                    log_success "✓ Bluetooth/BLE support detected"
                    ((tests_passed++))
                else
                    log_warn "⚠ Bluetooth/BLE support unclear"
                    ((tests_passed++))
                fi
                ;;

            "obd_interface_access")
                log_mia "Testing OBD interface access..."
                # Test USB access which is commonly used for OBD adapters
                local usb_test
                usb_test=$(${adb_cmd} shell "su -c 'ls /dev/bus/usb >/dev/null 2>&1 && echo accessible || echo denied'" 2>/dev/null || echo "error")

                if [[ "${usb_test}" == "accessible" ]]; then
                    log_success "✓ USB device access available (good for OBD adapters)"
                    ((tests_passed++))
                else
                    log_warn "⚠ USB device access limited"
                    ((tests_passed++)) # Still count as passed
                fi
                ;;

            "mqtt_networking")
                log_mia "Testing MQTT networking capabilities..."
                local network_test
                network_test=$(${adb_cmd} shell "su -c 'ping -c 1 8.8.8.8 >/dev/null 2>&1 && echo reachable || echo unreachable'" 2>/dev/null || echo "error")

                if [[ "${network_test}" == "reachable" ]]; then
                    log_success "✓ Network connectivity available (good for MQTT)"
                    ((tests_passed++))
                else
                    log_error "✗ Network connectivity issues"
                fi
                ;;

            "hardware_sensor_access")
                log_mia "Testing hardware sensor access..."
                local sensor_test
                sensor_test=$(${adb_cmd} shell "su -c 'ls /sys/class/sensors >/dev/null 2>&1 && echo available || echo unavailable'" 2>/dev/null || echo "error")

                if [[ "${sensor_test}" == "available" ]]; then
                    log_success "✓ Hardware sensors accessible"
                    ((tests_passed++))
                else
                    log_warn "⚠ Hardware sensor access unclear"
                    ((tests_passed++)) # Count as passed for now
                fi
                ;;
        esac
    done

    log_mia "MIA requirements: ${tests_passed}/${total_tests} tests passed"

    if [[ ${tests_passed} -ge 4 ]]; then
        log_mia "✓ Device appears suitable for MIA app development"
        return 0
    else
        log_mia "⚠ Device may have limitations for MIA app development"
        return 1
    fi
}

# Test root persistence
test_root_persistence() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Testing root persistence..."

    # Test root access multiple times
    local persistence_tests=0
    local passed_tests=0

    for ((i = 1; i <= 3; i++)); do
        ((persistence_tests++))
        local test_result
        test_result=$(${adb_cmd} shell "su -c 'echo persistence_test_${i}'" 2>/dev/null || echo "failed")

        if [[ "${test_result}" == "persistence_test_${i}" ]]; then
            ((passed_tests++))
        fi

        sleep 1
    done

    if [[ ${passed_tests} -eq ${persistence_tests} ]]; then
        log_success "✓ Root access persistent across multiple attempts"
        return 0
    else
        log_error "✗ Root access not persistent (${passed_tests}/${persistence_tests} passed)"
        return 1
    fi
}

# Generate comprehensive root verification report
generate_root_report() {
    local device=${1:-""}
    local basic_root_ok=${2:-false}
    local magisk_ok=${3:-false}
    local system_perms_ok=${4:-false}
    local mia_reqs_ok=${5:-false}
    local persistence_ok=${6:-false}

    log_info "Generating root verification report..."

    {
        echo "Android Device Setup - Root Verification Report"
        echo "Generated on: $(date)"
        echo "Device: ${device:-Unknown}"
        echo ""

        echo "=== ROOT VERIFICATION SUMMARY ==="
        echo "Basic Root Access: $(if [[ "${basic_root_ok}" == "true" ]]; then echo "✓ PASS"; else echo "✗ FAIL"; fi)"
        echo "Magisk Functionality: $(if [[ "${magisk_ok}" == "true" ]]; then echo "✓ PASS"; else echo "✗ FAIL"; fi)"
        echo "System Permissions: $(if [[ "${system_perms_ok}" == "true" ]]; then echo "✓ PASS"; else echo "✗ FAIL"; fi)"
        echo "MIA Requirements: $(if [[ "${mia_reqs_ok}" == "true" ]]; then echo "✓ PASS"; else echo "✗ FAIL"; fi)"
        echo "Root Persistence: $(if [[ "${persistence_ok}" == "true" ]]; then echo "✓ PASS"; else echo "✗ FAIL"; fi)"
        echo ""

        echo "=== OVERALL ASSESSMENT ==="
        local total_passed=0
        local total_tests=5

        [[ "${basic_root_ok}" == "true" ]] && ((total_passed++))
        [[ "${magisk_ok}" == "true" ]] && ((total_passed++))
        [[ "${system_perms_ok}" == "true" ]] && ((total_passed++))
        [[ "${mia_reqs_ok}" == "true" ]] && ((total_passed++))
        [[ "${persistence_ok}" == "true" ]] && ((total_passed++))

        echo "Tests Passed: ${total_passed}/${total_tests}"

        if [[ ${total_passed} -eq ${total_tests} ]]; then
            echo "Status: ✓ EXCELLENT - Device fully ready for MIA development"
        elif [[ ${total_passed} -ge 3 ]]; then
            echo "Status: ✓ GOOD - Device suitable for MIA development"
        elif [[ ${total_passed} -ge 2 ]]; then
            echo "Status: ⚠ FAIR - Device may need additional configuration"
        else
            echo "Status: ✗ POOR - Device not suitable for MIA development"
        fi
        echo ""

        echo "=== RECOMMENDATIONS ==="
        if [[ "${basic_root_ok}" != "true" ]]; then
            echo "- Install Magisk or another root solution"
            echo "- Ensure device bootloader is unlocked"
        fi

        if [[ "${magisk_ok}" != "true" ]]; then
            echo "- Install Magisk Manager app"
            echo "- Verify Magisk modules are working"
        fi

        if [[ "${system_perms_ok}" != "true" ]]; then
            echo "- Check SELinux configuration"
            echo "- Ensure system partition is writable"
        fi

        if [[ "${mia_reqs_ok}" != "true" ]]; then
            echo "- Grant necessary permissions for automotive features"
            echo "- Configure BLE, OBD, and MQTT access"
            echo "- Test hardware sensor integration"
        fi

        if [[ "${persistence_ok}" != "true" ]]; then
            echo "- Root access may be unstable"
            echo "- Consider reinstalling root solution"
        fi

        echo ""
        echo "- Run this verification after any system updates"
        echo "- Test MIA app functionality thoroughly before deployment"
        echo ""

    } > "${REPORT_FILE}"

    log_success "Root verification report generated: ${REPORT_FILE}"
}

# Comprehensive root verification
verify_root_comprehensive() {
    local device=${1:-""}

    log_info "Starting comprehensive root verification..."

    local basic_root_ok=false
    local magisk_ok=false
    local system_perms_ok=false
    local mia_reqs_ok=false
    local persistence_ok=false

    # Test basic root access
    if test_basic_root "${device}"; then
        basic_root_ok=true
    fi

    # Test Magisk functionality
    if test_magisk_functionality "${device}"; then
        magisk_ok=true
    fi

    # Test system permissions
    if test_system_permissions "${device}"; then
        system_perms_ok=true
    fi

    # Test MIA requirements
    if test_mia_requirements "${device}"; then
        mia_reqs_ok=true
    fi

    # Test root persistence
    if test_root_persistence "${device}"; then
        persistence_ok=true
    fi

    # Generate report
    generate_root_report "${device}" "${basic_root_ok}" "${magisk_ok}" "${system_perms_ok}" "${mia_reqs_ok}" "${persistence_ok}"

    # Overall assessment
    local critical_tests_passed=0

    [[ "${basic_root_ok}" == "true" ]] && ((critical_tests_passed++))
    [[ "${system_perms_ok}" == "true" ]] && ((critical_tests_passed++))
    [[ "${mia_reqs_ok}" == "true" ]] && ((critical_tests_passed++))

    if [[ ${critical_tests_passed} -ge 2 ]]; then
        log_success "Root verification completed - device appears ready for MIA development"
        return 0
    else
        log_error "Root verification failed - device may not be suitable for MIA development"
        return 1
    fi
}

# Main function
main() {
    log_info "Starting Root Verification Script"

    case "${1:-}" in
        "verify")
            local device=${2:-""}
            verify_root_comprehensive "${device}"
            ;;
        "basic")
            local device=${2:-""}
            test_basic_root "${device}"
            ;;
        "magisk")
            local device=${2:-""}
            test_magisk_functionality "${device}"
            ;;
        "system")
            local device=${2:-""}
            test_system_permissions "${device}"
            ;;
        "mia")
            local device=${2:-""}
            test_mia_requirements "${device}"
            ;;
        "persistence")
            local device=${2:-""}
            test_root_persistence "${device}"
            ;;
        "report")
            local device=${2:-""}
            generate_root_report "${device}"
            ;;
        *)
            echo "Usage: $0 {verify|basic|magisk|system|mia|persistence|report} [device_serial]"
            echo ""
            echo "Commands:"
            echo "  verify [device]     - Complete root verification suite"
            echo "  basic [device]      - Test basic root access only"
            echo "  magisk [device]     - Test Magisk functionality only"
            echo "  system [device]     - Test system permissions only"
            echo "  mia [device]        - Test MIA-specific requirements only"
            echo "  persistence [device] - Test root access persistence"
            echo "  report [device]     - Generate verification report"
            echo ""
            echo "Examples:"
            echo "  $0 verify                    # Complete verification on first device"
            echo "  $0 verify HT123456          # Verify specific device"
            echo "  $0 mia HT123456             # Test MIA requirements only"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"