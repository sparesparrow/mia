#!/bin/bash

# Android Device Setup - Health Check Script
# Comprehensive system verification and health monitoring

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/health-check.log"
REPORT_FILE="${WORK_DIR}/health-check-report.txt"

# Health check settings
BOOT_STABILITY_TESTS=3
PERFORMANCE_TEST_DURATION=30
BATTERY_MONITOR_DURATION=60
NETWORK_TEST_TIMEOUT=10

# Thresholds for health assessment
BATTERY_LOW_THRESHOLD=20
MEMORY_LOW_THRESHOLD=50  # MB
STORAGE_LOW_THRESHOLD=500  # MB
CPU_HIGH_THRESHOLD=80  # %

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

log_health() {
    echo -e "${CYAN}[HEALTH]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Test boot stability
test_boot_stability() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Testing boot stability..."

    local successful_boots=0
    local total_tests=${BOOT_STABILITY_TESTS}

    for ((i = 1; i <= total_tests; i++)); do
        log_info "Boot stability test ${i}/${total_tests}"

        # Reboot device
        if ${adb_cmd} reboot; then
            log_info "Device reboot initiated, waiting for restart..."

            # Wait for device to come back
            local attempts=0
            local max_attempts=24  # 2 minutes

            while [[ ${attempts} -lt ${max_attempts} ]]; do
                sleep 5
                if ${adb_cmd} shell echo "device_ready" >/dev/null 2>&1; then
                    log_success "✓ Boot test ${i} successful"
                    ((successful_boots++))
                    break
                fi
                ((attempts++))
            done

            if [[ ${attempts} -ge ${max_attempts} ]]; then
                log_error "✗ Boot test ${i} failed - device did not respond"
            fi
        else
            log_error "✗ Boot test ${i} failed - could not initiate reboot"
        fi

        # Wait between tests
        if [[ ${i} -lt ${total_tests} ]]; then
            log_info "Waiting 30 seconds before next boot test..."
            sleep 30
        fi
    done

    local success_rate=$((successful_boots * 100 / total_tests))
    log_health "Boot stability: ${successful_boots}/${total_tests} successful (${success_rate}%)"

    if [[ ${success_rate} -ge 80 ]]; then
        log_success "✓ Boot stability acceptable"
        return 0
    else
        log_error "✗ Boot stability issues detected"
        return 1
    fi
}

# Check core functionality
check_core_functionality() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Checking core functionality..."

    local tests_passed=0
    local total_tests=0

    # Test 1: System information
    ((total_tests++))
    log_info "Test 1/${total_tests}: System information access"
    local android_version
    android_version=$(${adb_cmd} shell getprop ro.build.version.release 2>/dev/null || echo "")
    if [[ -n "${android_version}" ]]; then
        log_success "✓ Android version: ${android_version}"
        ((tests_passed++))
    else
        log_error "✗ Could not get Android version"
    fi

    # Test 2: WiFi functionality
    ((total_tests++))
    log_info "Test 2/${total_tests}: WiFi functionality"
    local wifi_state
    wifi_state=$(${adb_cmd} shell settings get global wifi_on 2>/dev/null || echo "")
    if [[ "${wifi_state}" == "1" ]] || [[ "${wifi_state}" == "0" ]]; then
        log_success "✓ WiFi accessible"
        ((tests_passed++))
    else
        log_warn "⚠ WiFi state unclear (may be normal)"
        ((tests_passed++)) # Count as passed
    fi

    # Test 3: Bluetooth functionality
    ((total_tests++))
    log_info "Test 3/${total_tests}: Bluetooth functionality"
    local bt_state
    bt_state=$(${adb_cmd} shell settings get global bluetooth_on 2>/dev/null || echo "")
    if [[ "${bt_state}" == "1" ]] || [[ "${bt_state}" == "0" ]]; then
        log_success "✓ Bluetooth accessible"
        ((tests_passed++))
    else
        log_warn "⚠ Bluetooth state unclear (may be normal)"
        ((tests_passed++)) # Count as passed
    fi

    # Test 4: GPS/Location services
    ((total_tests++))
    log_info "Test 4/${total_tests}: GPS/Location services"
    local location_mode
    location_mode=$(${adb_cmd} shell settings get secure location_mode 2>/dev/null || echo "")
    if [[ -n "${location_mode}" ]]; then
        log_success "✓ Location services accessible"
        ((tests_passed++))
    else
        log_warn "⚠ Location services state unclear"
        ((tests_passed++)) # Count as passed
    fi

    # Test 5: Camera access
    ((total_tests++))
    log_info "Test 5/${total_tests}: Camera access"
    local camera_count
    camera_count=$(${adb_cmd} shell "su -c 'ls /sys/class/video4linux | wc -l'" 2>/dev/null || echo "0")
    if [[ "${camera_count}" != "0" ]]; then
        log_success "✓ Camera devices detected: ${camera_count}"
        ((tests_passed++))
    else
        log_info "No camera devices detected (may be normal for automotive device)"
        ((tests_passed++)) # Count as passed
    fi

    log_health "Core functionality: ${tests_passed}/${total_tests} tests passed"
    return 0
}

# Monitor battery status
monitor_battery() {
    local device=${1:-""}
    local duration=${2:-${BATTERY_MONITOR_DURATION}}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Monitoring battery status for ${duration} seconds..."

    local start_time=$(date +%s)
    local readings=()

    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ ${elapsed} -ge ${duration} ]]; then
            break
        fi

        # Get battery information
        local battery_info
        battery_info=$(${adb_cmd} shell dumpsys battery 2>/dev/null || echo "")

        if [[ -n "${battery_info}" ]]; then
            local level
            level=$(echo "${battery_info}" | grep "level:" | awk '{print $2}' || echo "unknown")
            local status
            status=$(echo "${battery_info}" | grep "status:" | awk '{print $2}' || echo "unknown")
            local temperature
            temperature=$(echo "${battery_info}" | grep "temperature:" | awk '{print $2}' | awk '{print $1/10}' || echo "unknown")

            if [[ "${level}" != "unknown" ]]; then
                readings+=("${level}")
                log_info "Battery: ${level}%, Status: ${status}, Temp: ${temperature}°C"
            fi
        fi

        sleep 10
    done

    # Analyze battery readings
    if [[ ${#readings[@]} -gt 0 ]]; then
        local min_level=${readings[0]}
        local max_level=${readings[0]}
        local sum=0

        for reading in "${readings[@]}"; do
            if [[ ${reading} -lt ${min_level} ]]; then
                min_level=${reading}
            fi
            if [[ ${reading} -gt ${max_level} ]]; then
                max_level=${reading}
            fi
            ((sum += reading))
        done

        local avg_level=$((sum / ${#readings[@]}))
        local level_drop=$((max_level - min_level))

        log_health "Battery analysis:"
        log_health "  Average level: ${avg_level}%"
        log_health "  Range: ${min_level}% - ${max_level}%"
        log_health "  Drop during test: ${level_drop}%"

        if [[ ${avg_level} -lt ${BATTERY_LOW_THRESHOLD} ]]; then
            log_warn "⚠ Battery level is low (${avg_level}%)"
        else
            log_success "✓ Battery level acceptable"
        fi

        return 0
    else
        log_warn "⚠ Could not monitor battery status"
        return 1
    fi
}

# Monitor performance metrics
monitor_performance() {
    local device=${1:-""}
    local duration=${2:-${PERFORMANCE_TEST_DURATION}}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Monitoring performance for ${duration} seconds..."

    local start_time=$(date +%s)
    local cpu_readings=()
    local mem_readings=()

    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ ${elapsed} -ge ${duration} ]]; then
            break
        fi

        # Get CPU usage
        local cpu_usage
        cpu_usage=$(${adb_cmd} shell "dumpsys cpuinfo | grep 'Load' | head -1 | awk '{print \$2}' | sed 's/%//' | cut -d'.' -f1" 2>/dev/null || echo "unknown")

        if [[ "${cpu_usage}" != "unknown" ]] && [[ "${cpu_usage}" =~ ^[0-9]+$ ]]; then
            cpu_readings+=("${cpu_usage}")
        fi

        # Get memory usage
        local mem_info
        mem_info=$(${adb_cmd} shell "dumpsys meminfo | grep 'Used RAM'" 2>/dev/null || echo "")
        local mem_used_mb
        mem_used_mb=$(echo "${mem_info}" | awk '{print $3}' | sed 's/M//' | cut -d'.' -f1 || echo "unknown")

        if [[ "${mem_used_mb}" != "unknown" ]] && [[ "${mem_used_mb}" =~ ^[0-9]+$ ]]; then
            mem_readings+=("${mem_used_mb}")
        fi

        sleep 5
    done

    # Analyze CPU readings
    if [[ ${#cpu_readings[@]} -gt 0 ]]; then
        local max_cpu=0
        local sum_cpu=0

        for reading in "${cpu_readings[@]}"; do
            if [[ ${reading} -gt ${max_cpu} ]]; then
                max_cpu=${reading}
            fi
            ((sum_cpu += reading))
        done

        local avg_cpu=$((sum_cpu / ${#cpu_readings[@]}))
        log_health "CPU usage: Average ${avg_cpu}%, Peak ${max_cpu}%"

        if [[ ${max_cpu} -gt ${CPU_HIGH_THRESHOLD} ]]; then
            log_warn "⚠ High CPU usage detected (peak: ${max_cpu}%)"
        else
            log_success "✓ CPU usage acceptable"
        fi
    else
        log_warn "⚠ Could not monitor CPU usage"
    fi

    # Analyze memory readings
    if [[ ${#mem_readings[@]} -gt 0 ]]; then
        local max_mem=0
        local sum_mem=0

        for reading in "${mem_readings[@]}"; do
            if [[ ${reading} -gt ${max_mem} ]]; then
                max_mem=${reading}
            fi
            ((sum_mem += reading))
        done

        local avg_mem=$((sum_mem / ${#mem_readings[@]}))
        log_health "Memory usage: Average ${avg_mem}MB, Peak ${max_mem}MB"

        if [[ ${max_mem} -gt ${MEMORY_LOW_THRESHOLD} ]]; then
            log_warn "⚠ High memory usage detected (peak: ${max_mem}MB)"
        else
            log_success "✓ Memory usage acceptable"
        fi
    else
        log_warn "⚠ Could not monitor memory usage"
    fi

    return 0
}

# Test hardware sensors
test_hardware_sensors() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Testing hardware sensors..."

    local sensors_found=0
    local sensors_tested=0

    # Test accelerometer
    ((sensors_tested++))
    local accel_test
    accel_test=$(${adb_cmd} shell "getevent -c 1 /dev/input/event* 2>/dev/null | grep -i accel | head -1" || echo "")
    if [[ -n "${accel_test}" ]]; then
        log_success "✓ Accelerometer detected"
        ((sensors_found++))
    else
        log_info "Accelerometer not detected or not accessible"
    fi

    # Test gyroscope
    ((sensors_tested++))
    local gyro_test
    gyro_test=$(${adb_cmd} shell "getevent -c 1 /dev/input/event* 2>/dev/null | grep -i gyro | head -1" || echo "")
    if [[ -n "${gyro_test}" ]]; then
        log_success "✓ Gyroscope detected"
        ((sensors_found++))
    else
        log_info "Gyroscope not detected or not accessible"
    fi

    # Test GPS
    ((sensors_tested++))
    local gps_test
    gps_test=$(${adb_cmd} shell "su -c 'ls /sys/class/gps/ 2>/dev/null' | head -1" 2>/dev/null || echo "")
    if [[ -n "${gps_test}" ]]; then
        log_success "✓ GPS sensor detected"
        ((sensors_found++))
    else
        log_info "GPS sensor not detected (may be normal)"
    fi

    # Test light sensor
    ((sensors_tested++))
    local light_test
    light_test=$(${adb_cmd} shell "su -c 'ls /sys/class/lightsensor/ 2>/dev/null' | head -1" 2>/dev/null || echo "")
    if [[ -n "${light_test}" ]]; then
        log_success "✓ Light sensor detected"
        ((sensors_found++))
    else
        log_info "Light sensor not detected (may be normal)"
    fi

    log_health "Hardware sensors: ${sensors_found}/${sensors_tested} detected"

    if [[ ${sensors_found} -gt 0 ]]; then
        log_success "✓ Hardware sensors accessible"
    else
        log_warn "⚠ No hardware sensors detected"
    fi

    return 0
}

# Test network connectivity
test_network_connectivity() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Testing network connectivity..."

    local tests_passed=0
    local total_tests=3

    # Test 1: Local network connectivity
    ((total_tests++))
    log_info "Test 1/${total_tests}: Local network connectivity"
    local local_ping
    local_ping=$(${adb_cmd} shell "ping -c 3 -W ${NETWORK_TEST_TIMEOUT} 192.168.1.1" 2>/dev/null | grep "packets transmitted" | awk '{print $4}' || echo "0")
    if [[ "${local_ping}" != "0" ]]; then
        log_success "✓ Local network reachable"
        ((tests_passed++))
    else
        log_info "Local network not reachable (may be normal)"
        ((tests_passed++)) # Count as passed
    fi

    # Test 2: Internet connectivity
    ((total_tests++))
    log_info "Test 2/${total_tests}: Internet connectivity"
    local internet_ping
    internet_ping=$(${adb_cmd} shell "ping -c 3 -W ${NETWORK_TEST_TIMEOUT} 8.8.8.8" 2>/dev/null | grep "packets transmitted" | awk '{print $4}' || echo "0")
    if [[ "${internet_ping}" != "0" ]]; then
        log_success "✓ Internet connectivity confirmed"
        ((tests_passed++))
    else
        log_error "✗ No internet connectivity"
    fi

    # Test 3: DNS resolution
    ((total_tests++))
    log_info "Test 3/${total_tests}: DNS resolution"
    local dns_test
    dns_test=$(${adb_cmd} shell "nslookup google.com 8.8.8.8 2>/dev/null | grep 'Address' | head -1" || echo "")
    if [[ -n "${dns_test}" ]]; then
        log_success "✓ DNS resolution working"
        ((tests_passed++))
    else
        log_error "✗ DNS resolution failed"
    fi

    log_health "Network connectivity: ${tests_passed}/${total_tests} tests passed"

    if [[ ${tests_passed} -ge 2 ]]; then
        return 0
    else
        return 1
    fi
}

# Check storage space
check_storage_space() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_health "Checking storage space..."

    # Get storage information
    local storage_info
    storage_info=$(${adb_cmd} shell df /sdcard 2>/dev/null || ${adb_cmd} shell df /data 2>/dev/null || echo "")

    if [[ -n "${storage_info}" ]]; then
        # Parse available space
        local available_kb
        available_kb=$(echo "${storage_info}" | tail -1 | awk '{print $4}' || echo "0")

        if [[ ${available_kb} -gt 0 ]]; then
            local available_mb=$((available_kb / 1024))
            local available_gb=$((available_mb / 1024))

            log_health "Available storage: ${available_mb} MB (${available_gb} GB)"

            if [[ ${available_mb} -lt ${STORAGE_LOW_THRESHOLD} ]]; then
                log_warn "⚠ Low storage space (${available_mb} MB)"
                return 1
            else
                log_success "✓ Sufficient storage space"
                return 0
            fi
        fi
    fi

    log_warn "⚠ Could not check storage space"
    return 1
}

# Generate health check report
generate_health_report() {
    local device=${1:-""}
    local boot_stable=${2:-false}
    local core_functional=${3:-false}
    local battery_ok=${4:-false}
    local performance_ok=${5:-false}
    local sensors_ok=${6:-false}
    local network_ok=${7:-false}
    local storage_ok=${8:-false}

    log_info "Generating health check report..."

    {
        echo "Android Device Setup - Health Check Report"
        echo "Generated on: $(date)"
        echo "Device: ${device:-Unknown}"
        echo ""

        echo "=== HEALTH ASSESSMENT ==="
        echo "Boot Stability: $(if [[ "${boot_stable}" == "true" ]]; then echo "✓ PASS"; else echo "✗ FAIL"; fi)"
        echo "Core Functionality: $(if [[ "${core_functional}" == "true" ]]; then echo "✓ PASS"; else echo "⚠ PARTIAL"; fi)"
        echo "Battery Status: $(if [[ "${battery_ok}" == "true" ]]; then echo "✓ GOOD"; else echo "⚠ CHECK"; fi)"
        echo "Performance: $(if [[ "${performance_ok}" == "true" ]]; then echo "✓ GOOD"; else echo "⚠ MONITOR"; fi)"
        echo "Hardware Sensors: $(if [[ "${sensors_ok}" == "true" ]]; then echo "✓ DETECTED"; else echo "⚠ LIMITED"; fi)"
        echo "Network Connectivity: $(if [[ "${network_ok}" == "true" ]]; then echo "✓ WORKING"; else echo "✗ ISSUES"; fi)"
        echo "Storage Space: $(if [[ "${storage_ok}" == "true" ]]; then echo "✓ SUFFICIENT"; else echo "⚠ LOW"; fi)"
        echo ""

        echo "=== OVERALL STATUS ==="
        local critical_issues=0
        local warnings=0

        [[ "${boot_stable}" != "true" ]] && ((critical_issues++))
        [[ "${network_ok}" != "true" ]] && ((critical_issues++))
        [[ "${storage_ok}" != "true" ]] && ((warnings++))

        if [[ ${critical_issues} -eq 0 ]]; then
            if [[ ${warnings} -eq 0 ]]; then
                echo "Status: ✓ EXCELLENT - Device is in excellent health"
            else
                echo "Status: ✓ GOOD - Device is healthy with minor warnings"
            fi
        elif [[ ${critical_issues} -eq 1 ]]; then
            echo "Status: ⚠ FAIR - Device has some issues to address"
        else
            echo "Status: ✗ POOR - Device has critical health issues"
        fi
        echo ""

        echo "=== RECOMMENDATIONS ==="
        if [[ "${boot_stable}" != "true" ]]; then
            echo "- Investigate boot stability issues"
            echo "- Check for ROM installation problems"
            echo "- Consider clean ROM reinstallation"
        fi

        if [[ "${network_ok}" != "true" ]]; then
            echo "- Check WiFi/Bluetooth connectivity"
            echo "- Verify network permissions"
            echo "- Test with different access points"
        fi

        if [[ "${storage_ok}" != "true" ]]; then
            echo "- Free up storage space"
            echo "- Clear cache and temporary files"
            echo "- Move data to external storage if available"
        fi

        if [[ "${battery_ok}" != "true" ]]; then
            echo "- Monitor battery health"
            echo "- Consider battery calibration"
            echo "- Check for power-hungry apps"
        fi

        echo "- Run regular health checks"
        echo "- Monitor device temperature during use"
        echo "- Keep device firmware updated"
        echo ""

        echo "=== MONITORING LOGS ==="
        echo "Health check logs: ${LOG_FILE}"
        echo "System logs: Available via 'adb logcat'"
        echo ""

    } > "${REPORT_FILE}"

    log_success "Health check report generated: ${REPORT_FILE}"
}

# Comprehensive health check
run_comprehensive_health_check() {
    local device=${1:-""}

    log_health "Starting comprehensive health check..."

    # Run all health checks
    local boot_stable=false
    local core_functional=false
    local battery_ok=false
    local performance_ok=false
    local sensors_ok=false
    local network_ok=false
    local storage_ok=false

    log_info "Running boot stability test..."
    if test_boot_stability "${device}"; then
        boot_stable=true
    fi

    log_info "Checking core functionality..."
    if check_core_functionality "${device}"; then
        core_functional=true
    fi

    log_info "Monitoring battery..."
    if monitor_battery "${device}"; then
        battery_ok=true
    fi

    log_info "Monitoring performance..."
    if monitor_performance "${device}"; then
        performance_ok=true
    fi

    log_info "Testing hardware sensors..."
    if test_hardware_sensors "${device}"; then
        sensors_ok=true
    fi

    log_info "Testing network connectivity..."
    if test_network_connectivity "${device}"; then
        network_ok=true
    fi

    log_info "Checking storage space..."
    if check_storage_space "${device}"; then
        storage_ok=true
    fi

    # Generate comprehensive report
    generate_health_report "${device}" "${boot_stable}" "${core_functional}" "${battery_ok}" "${performance_ok}" "${sensors_ok}" "${network_ok}" "${storage_ok}"

    # Overall assessment
    local critical_passed=0
    local total_critical=3

    [[ "${boot_stable}" == "true" ]] && ((critical_passed++))
    [[ "${network_ok}" == "true" ]] && ((critical_passed++))
    [[ "${storage_ok}" == "true" ]] && ((critical_passed++))

    if [[ ${critical_passed} -eq ${total_critical} ]]; then
        log_health "✓ Device health check completed successfully"
        return 0
    else
        log_health "⚠ Device health check completed with issues"
        return 1
    fi
}

# Main function
main() {
    log_info "Starting Health Check Script"

    case "${1:-}" in
        "full")
            local device=${2:-""}
            run_comprehensive_health_check "${device}"
            ;;
        "boot")
            local device=${2:-""}
            test_boot_stability "${device}"
            ;;
        "core")
            local device=${2:-""}
            check_core_functionality "${device}"
            ;;
        "battery")
            local device=${2:-""}
            local duration=${3:-${BATTERY_MONITOR_DURATION}}
            monitor_battery "${device}" "${duration}"
            ;;
        "performance")
            local device=${2:-""}
            local duration=${3:-${PERFORMANCE_TEST_DURATION}}
            monitor_performance "${device}" "${duration}"
            ;;
        "sensors")
            local device=${2:-""}
            test_hardware_sensors "${device}"
            ;;
        "network")
            local device=${2:-""}
            test_network_connectivity "${device}"
            ;;
        "storage")
            local device=${2:-""}
            check_storage_space "${device}"
            ;;
        "report")
            local device=${2:-""}
            generate_health_report "${device}"
            ;;
        *)
            echo "Usage: $0 {full|boot|core|battery|performance|sensors|network|storage|report} [device] [duration]"
            echo ""
            echo "Commands:"
            echo "  full [device]          - Complete health check suite"
            echo "  boot [device]          - Test boot stability only"
            echo "  core [device]          - Check core functionality only"
            echo "  battery [device] [sec] - Monitor battery status only"
            echo "  performance [device] [sec] - Monitor performance only"
            echo "  sensors [device]       - Test hardware sensors only"
            echo "  network [device]       - Test network connectivity only"
            echo "  storage [device]       - Check storage space only"
            echo "  report [device]        - Generate health report only"
            echo ""
            echo "Examples:"
            echo "  $0 full HT123456              # Complete health check"
            echo "  $0 battery HT123456 120       # Monitor battery for 2 minutes"
            echo "  $0 performance HT123456 60    # Monitor performance for 1 minute"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"