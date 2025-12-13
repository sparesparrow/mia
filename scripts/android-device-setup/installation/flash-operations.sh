#!/bin/bash

# Android Device Setup - Flash Operations
# Handle device wiping and ROM flashing operations

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/flash-operations.log"

# Recovery mode settings
RECOVERY_WAIT_TIMEOUT=60
FLASH_VERIFICATION_TIMEOUT=300

# Safety settings
SAFETY_CHECKS_ENABLED=true
ALLOW_DATA_WIPE=true
ALLOW_SYSTEM_WIPE=true

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

# Safety check before destructive operations
safety_check() {
    local operation=$1

    if [[ "${SAFETY_CHECKS_ENABLED}" != "true" ]]; then
        return 0
    fi

    log_warn "SAFETY CHECK: About to perform ${operation}"
    log_warn "This operation will permanently delete data on the device"
    log_warn "Make sure you have backed up important data"

    echo ""
    echo "⚠️  SAFETY CHECK ⚠️"
    echo "Operation: ${operation}"
    echo "This will wipe data from your HTC One M7"
    echo ""
    read -p "Type 'YES' to confirm: " confirmation

    if [[ "${confirmation}" != "YES" ]]; then
        log_error "Operation cancelled by user"
        return 1
    fi

    log_info "Safety check passed - proceeding with ${operation}"
    return 0
}

# Ensure device is in recovery mode
ensure_recovery_mode() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Ensuring device is in recovery mode..."

    # Check current mode
    local device_mode
    device_mode=$(${adb_cmd} get-state 2>/dev/null || echo "unknown")

    if [[ "${device_mode}" == "recovery" ]]; then
        log_success "Device is already in recovery mode"
        return 0
    fi

    # Try to boot to recovery
    log_info "Attempting to boot device to recovery mode..."
    if ${adb_cmd} reboot recovery; then
        log_info "Waiting for device to enter recovery mode..."

        local attempts=0
        while [[ ${attempts} -lt 12 ]]; do  # Wait up to 2 minutes
            sleep 10
            device_mode=$(${adb_cmd} get-state 2>/dev/null || echo "unknown")

            if [[ "${device_mode}" == "recovery" ]]; then
                log_success "Device successfully entered recovery mode"
                return 0
            fi

            ((attempts++))
        done
    fi

    log_error "Failed to enter recovery mode"
    log_info "Please manually boot device into recovery mode"
    return 1
}

# Execute recovery command
execute_recovery_command() {
    local device=${1:-""}
    local command=$2
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Executing recovery command: ${command}"

    # Send command to recovery
    echo "${command}" | ${adb_cmd} shell 2>/dev/null || true

    # Wait a moment for command to be processed
    sleep 2

    return 0
}

# Wait for recovery operation to complete
wait_for_recovery_operation() {
    local device=${1:-""}
    local timeout=${2:-60}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Waiting for recovery operation to complete (timeout: ${timeout}s)..."

    local start_time=$(date +%s)

    while true; do
        # Try to execute a simple command to test if recovery is responsive
        if ${adb_cmd} shell echo "test" >/dev/null 2>&1; then
            log_success "Recovery operation completed"
            return 0
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ ${elapsed} -ge ${timeout} ]]; then
            log_error "Timeout waiting for recovery operation to complete"
            return 1
        fi

        sleep 5
    done
}

# Wipe data partition
wipe_data() {
    local device=${1:-""}

    log_info "Wiping data partition..."

    if ! safety_check "DATA WIPE"; then
        return 1
    fi

    if [[ "${ALLOW_DATA_WIPE}" != "true" ]]; then
        log_error "Data wipe not allowed by configuration"
        return 1
    fi

    execute_recovery_command "${device}" "wipe data"

    if ! wait_for_recovery_operation "${device}" 120; then
        log_error "Data wipe operation failed"
        return 1
    fi

    log_success "Data partition wiped successfully"
    return 0
}

# Wipe cache partition
wipe_cache() {
    local device=${1:-""}

    log_info "Wiping cache partition..."

    execute_recovery_command "${device}" "wipe cache"

    if ! wait_for_recovery_operation "${device}" 60; then
        log_error "Cache wipe operation failed"
        return 1
    fi

    log_success "Cache partition wiped successfully"
    return 0
}

# Wipe system partition
wipe_system() {
    local device=${1:-""}

    log_info "Wiping system partition..."

    if ! safety_check "SYSTEM WIPE"; then
        return 1
    fi

    if [[ "${ALLOW_SYSTEM_WIPE}" != "true" ]]; then
        log_error "System wipe not allowed by configuration"
        return 1
    fi

    execute_recovery_command "${device}" "wipe system"

    if ! wait_for_recovery_operation "${device}" 60; then
        log_error "System wipe operation failed"
        return 1
    fi

    log_success "System partition wiped successfully"
    return 0
}

# Wipe dalvik cache
wipe_dalvik() {
    local device=${1:-""}

    log_info "Wiping dalvik cache..."

    execute_recovery_command "${device}" "wipe dalvik"

    if ! wait_for_recovery_operation "${device}" 60; then
        log_error "Dalvik cache wipe operation failed"
        return 1
    fi

    log_success "Dalvik cache wiped successfully"
    return 0
}

# Perform full wipe (system, data, cache, dalvik)
wipe_full() {
    local device=${1:-""}

    log_info "Performing full device wipe..."

    if ! safety_check "FULL DEVICE WIPE"; then
        return 1
    fi

    # Wipe in order: system, data, cache, dalvik
    if ! wipe_system "${device}"; then
        return 1
    fi

    if ! wipe_data "${device}"; then
        return 1
    fi

    if ! wipe_cache "${device}"; then
        return 1
    fi

    if ! wipe_dalvik "${device}"; then
        return 1
    fi

    log_success "Full device wipe completed successfully"
    return 0
}

# Flash ZIP file
flash_zip() {
    local device=${1:-""}
    local zip_path=${2}
    local description=${3:-"ZIP file"}

    if [[ ! -f "${zip_path}" ]]; then
        log_error "ZIP file not found: ${zip_path}"
        return 1
    fi

    local filename=$(basename "${zip_path}")
    log_info "Flashing ${description}: ${filename}"

    # Ensure ZIP is on device
    local device_path="/sdcard/${filename}"
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Check if file exists on device
    if ! ${adb_cmd} shell ls "${device_path}" >/dev/null 2>&1; then
        log_error "ZIP file not found on device: ${device_path}"
        log_error "Make sure to transfer files to device first"
        return 1
    fi

    # Execute flash command
    execute_recovery_command "${device}" "install ${device_path}"

    # Wait for flash to complete (this can take several minutes)
    log_info "Waiting for flash operation to complete..."
    if ! wait_for_recovery_operation "${device}" "${FLASH_VERIFICATION_TIMEOUT}"; then
        log_error "Flash operation timeout"
        return 1
    fi

    log_success "${description} flashed successfully"
    return 0
}

# Flash LineageOS ROM
flash_rom() {
    local device=${1:-""}

    log_info "Flashing LineageOS ROM..."

    # Find ROM file on device
    local rom_file
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    rom_file=$(${adb_cmd} shell find /sdcard -name "lineage*.zip" 2>/dev/null | head -1 || echo "")

    if [[ -z "${rom_file}" ]]; then
        log_error "No LineageOS ROM file found on device"
        log_error "Make sure to transfer the ROM file first"
        return 1
    fi

    if ! flash_zip "${device}" "${rom_file}" "LineageOS ROM"; then
        log_error "ROM flash failed"
        return 1
    fi

    log_success "LineageOS ROM flashed successfully"
    return 0
}

# Flash GApps
flash_gapps() {
    local device=${1:-""}

    log_info "Flashing Google Apps..."

    # Find GApps file on device
    local gapps_file
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    gapps_file=$(${adb_cmd} shell find /sdcard -name "*gapps*.zip" 2>/dev/null | head -1 || echo "")

    if [[ -z "${gapps_file}" ]]; then
        log_info "No GApps file found on device - skipping GApps installation"
        return 0
    fi

    if ! flash_zip "${device}" "${gapps_file}" "Google Apps"; then
        log_error "GApps flash failed"
        return 1
    fi

    log_success "Google Apps flashed successfully"
    return 0
}

# Reboot to system
reboot_system() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Rebooting device to system..."

    execute_recovery_command "${device}" "reboot system"

    log_success "Device rebooting to system"
    log_info "This may take several minutes for first boot"
    return 0
}

# Reboot to recovery
reboot_recovery() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Rebooting device to recovery..."

    execute_recovery_command "${device}" "reboot recovery"

    log_success "Device rebooting to recovery"
    return 0
}

# Reboot to bootloader
reboot_bootloader() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Rebooting device to bootloader..."

    execute_recovery_command "${device}" "reboot bootloader"

    log_success "Device rebooting to bootloader"
    return 0
}

# Verify flash operations
verify_flash() {
    local device=${1:-""}
    local operation=${2:-"general"}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Verifying flash operation: ${operation}"

    # Wait for device to be responsive
    local attempts=0
    while [[ ${attempts} -lt 6 ]]; do  # Wait up to 1 minute
        if ${adb_cmd} shell echo "verification_test" >/dev/null 2>&1; then
            log_success "Device is responsive after flash"
            return 0
        fi

        sleep 10
        ((attempts++))
    done

    log_error "Device not responsive after flash operation"
    return 1
}

# Get recovery menu status
get_recovery_status() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Getting recovery status..."

    # Try to get recovery version/info
    local recovery_info
    recovery_info=$(${adb_cmd} shell getprop ro.twrp.version 2>/dev/null | tr -d '\r' || echo "")

    if [[ -n "${recovery_info}" ]]; then
        log_info "Recovery version: ${recovery_info}"
    else
        log_info "Recovery status: Active"
    fi

    return 0
}

# Main function
main() {
    log_info "Starting Flash Operations"

    case "${1:-}" in
        "wipe")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && wipe_full "${device}"
            ;;
        "wipe-data")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && wipe_data "${device}"
            ;;
        "wipe-cache")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && wipe_cache "${device}"
            ;;
        "wipe-system")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && wipe_system "${device}"
            ;;
        "wipe-dalvik")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && wipe_dalvik "${device}"
            ;;
        "flash-rom")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && flash_rom "${device}"
            ;;
        "flash-gapps")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && flash_gapps "${device}"
            ;;
        "flash-zip")
            local device=${2:-""}
            local zip_path=${3}
            ensure_recovery_mode "${device}" && flash_zip "${device}" "${zip_path}"
            ;;
        "reboot-system")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && reboot_system "${device}"
            ;;
        "reboot-recovery")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && reboot_recovery "${device}"
            ;;
        "reboot-bootloader")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && reboot_bootloader "${device}"
            ;;
        "status")
            local device=${2:-""}
            ensure_recovery_mode "${device}" && get_recovery_status "${device}"
            ;;
        "verify")
            local device=${2:-""}
            local operation=${3:-"flash"}
            verify_flash "${device}" "${operation}"
            ;;
        *)
            echo "Usage: $0 {wipe|wipe-data|wipe-cache|wipe-system|wipe-dalvik|flash-rom|flash-gapps|flash-zip|reboot-system|reboot-recovery|reboot-bootloader|status|verify} [device] [additional_args]"
            echo ""
            echo "Commands:"
            echo "  wipe [device]              - Full device wipe (system, data, cache, dalvik)"
            echo "  wipe-data [device]         - Wipe data partition only"
            echo "  wipe-cache [device]        - Wipe cache partition only"
            echo "  wipe-system [device]       - Wipe system partition only"
            echo "  wipe-dalvik [device]       - Wipe dalvik cache only"
            echo "  flash-rom [device]         - Flash LineageOS ROM"
            echo "  flash-gapps [device]       - Flash Google Apps"
            echo "  flash-zip [device] [path]  - Flash custom ZIP file"
            echo "  reboot-system [device]     - Reboot to Android system"
            echo "  reboot-recovery [device]   - Reboot to recovery"
            echo "  reboot-bootloader [device] - Reboot to bootloader"
            echo "  status [device]            - Get recovery status"
            echo "  verify [device] [op]       - Verify flash operation"
            echo ""
            echo "Examples:"
            echo "  $0 wipe HT123456           # Full wipe device"
            echo "  $0 flash-rom HT123456      # Flash LineageOS ROM"
            echo "  $0 reboot-system HT123456  # Reboot to system"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"