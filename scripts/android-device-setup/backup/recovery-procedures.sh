#!/bin/bash

# Android Device Setup - Recovery Procedures
# Emergency recovery and troubleshooting procedures

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/recovery-procedures.log"
DIAGNOSTIC_DIR="${WORK_DIR}/diagnostics"

# Recovery settings
BOOTLOOP_TIMEOUT=300  # 5 minutes
RECOVERY_CHECK_INTERVAL=30
MAX_RECOVERY_ATTEMPTS=3

# Emergency contacts and resources
SUPPORT_RESOURCES=(
    "https://wiki.lineageos.org/devices/m7"
    "https://twrp.me/Devices/HTCOneM7.html"
    "https://topjohnwu.github.io/Magisk/"
    "https://developer.android.com/studio/run/device"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

log_recovery() {
    echo -e "${CYAN}[RECOVERY]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

log_emergency() {
    echo -e "${RED}[EMERGENCY]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Initialize diagnostic collection
init_diagnostics() {
    log_recovery "Initializing diagnostic collection..."

    mkdir -p "${DIAGNOSTIC_DIR}"
    mkdir -p "${DIAGNOSTIC_DIR}/logs"
    mkdir -p "${DIAGNOSTIC_DIR}/system_info"
    mkdir -p "${DIAGNOSTIC_DIR}/backups"

    log_success "✓ Diagnostic directories initialized"
}

# Collect system diagnostic information
collect_system_diagnostics() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_recovery "Collecting system diagnostic information..."

    local diag_file="${DIAGNOSTIC_DIR}/system_info/diagnostics_$(date '+%Y%m%d_%H%M%S').txt"

    {
        echo "=== SYSTEM DIAGNOSTICS ==="
        echo "Collection Time: $(date)"
        echo "Device: ${device:-Unknown}"
        echo ""

        echo "=== ADB DEVICE INFO ==="
        ${adb_cmd} devices -l 2>/dev/null || echo "ADB device info unavailable"
        echo ""

        echo "=== DEVICE PROPERTIES ==="
        ${adb_cmd} shell getprop 2>/dev/null | head -50 || echo "Device properties unavailable"
        echo ""

        echo "=== SYSTEM LOGS (LAST 100 LINES) ==="
        ${adb_cmd} logcat -d -t 100 2>/dev/null || echo "System logs unavailable"
        echo ""

        echo "=== RECOVERY LOGS ==="
        ${adb_cmd} shell cat /tmp/recovery.log 2>/dev/null || echo "Recovery logs unavailable"
        echo ""

        echo "=== PARTITION INFORMATION ==="
        ${adb_cmd} shell df 2>/dev/null || echo "Partition info unavailable"
        echo ""

        echo "=== RUNNING PROCESSES ==="
        ${adb_cmd} shell ps 2>/dev/null | head -20 || echo "Process list unavailable"
        echo ""

    } > "${diag_file}"

    log_success "✓ System diagnostics collected: ${diag_file}"
    echo "${diag_file}"
}

# Bootloop recovery procedure
recover_bootloop() {
    local device=${1}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_emergency "INITIATING BOOTLOOP RECOVERY PROCEDURE"
    log_emergency "Device: ${device}"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    BOOTLOOP RECOVERY                        ║"
    echo "║                                                              ║"
    echo "║  This procedure will attempt to recover a device stuck in   ║"
    echo "║  a boot loop. Make sure the device is connected via USB.    ║"
    echo "║                                                              ║"
    echo "║  WARNING: This may result in data loss if backups exist.    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    # Step 1: Try to interrupt boot process
    log_recovery "Step 1: Attempting to interrupt boot process..."
    for i in {1..5}; do
        log_info "Boot interruption attempt ${i}/5..."
        ${adb_cmd} reboot bootloader 2>/dev/null || true
        sleep 5

        # Check if we got to fastboot
        if fastboot devices | grep -q "fastboot"; then
            log_success "✓ Successfully interrupted boot - device in fastboot mode"
            break
        fi
    done

    # Step 2: If in fastboot, try to boot to recovery
    if fastboot devices | grep -q "fastboot"; then
        log_recovery "Step 2: Attempting to boot to recovery from fastboot..."
        fastboot boot "${WORK_DIR}/downloads/magisk/twrp.img" 2>/dev/null || true
        sleep 10

        # Check if device entered recovery
        if ${adb_cmd} shell getprop ro.twrp.version >/dev/null 2>&1; then
            log_success "✓ Successfully booted to TWRP recovery"
        else
            log_warn "⚠ Could not verify TWRP boot"
        fi
    else
        # Step 3: Try recovery mode directly
        log_recovery "Step 3: Attempting direct recovery boot..."
        ${adb_cmd} reboot recovery 2>/dev/null || true
        sleep 15

        if ${adb_cmd} shell getprop ro.twrp.version >/dev/null 2>&1; then
            log_success "✓ Successfully entered recovery mode"
        else
            log_emergency "✗ CRITICAL: Cannot access recovery mode"
            log_emergency "Manual intervention required:"
            log_emergency "1. Power off device completely"
            log_emergency "2. Hold Vol- + Power to enter bootloader"
            log_emergency "3. Use Vol keys to select RECOVERY, press Power"
            return 1
        fi
    fi

    # Step 4: Attempt system repair
    log_recovery "Step 4: Attempting system repair..."

    # Try to wipe cache and dalvik first (least destructive)
    local flash_script="${SCRIPT_DIR}/../installation/flash-operations.sh"

    if [[ -x "${flash_script}" ]]; then
        log_info "Wiping cache and dalvik cache..."
        "${flash_script}" wipe-cache "${device}" 2>/dev/null || log_warn "Cache wipe failed"
        "${flash_script}" wipe-dalvik "${device}" 2>/dev/null || log_warn "Dalvik wipe failed"
    fi

    # Step 5: Check if system boots now
    log_recovery "Step 5: Testing system boot..."
    ${adb_cmd} reboot 2>/dev/null || true
    sleep 60

    if ${adb_cmd} shell echo "boot_test" >/dev/null 2>&1; then
        log_success "✓ BOOTLOOP RECOVERY SUCCESSFUL"
        log_success "Device is now booting normally"
        return 0
    else
        log_emergency "✗ Bootloop recovery unsuccessful"
        log_emergency "Device may require ROM reinstallation"
        return 1
    fi
}

# Failed installation rollback procedure
rollback_failed_installation() {
    local device=${1}
    local backup_name=${2:-""}

    log_emergency "INITIATING FAILED INSTALLATION ROLLBACK"
    log_emergency "Device: ${device}"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                INSTALLATION ROLLBACK                        ║"
    echo "║                                                              ║"
    echo "║  This procedure will attempt to restore from a backup       ║"
    echo "║  after a failed installation.                               ║"
    echo "║                                                              ║"
    echo "║  WARNING: This will restore the device to its previous      ║"
    echo "║  state and may result in data loss.                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    # Step 1: Access recovery mode
    log_recovery "Step 1: Accessing recovery mode..."
    local recovery_script="${SCRIPT_DIR}/../recovery/verify-recovery.sh"
    if ! "${recovery_script}" boot "${device}" >/dev/null 2>&1; then
        log_emergency "Cannot access recovery mode for rollback"
        return 1
    fi

    # Step 2: Find available backups
    log_recovery "Step 2: Looking for available backups..."
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local device_codename
    device_codename=$(${adb_cmd} shell getprop ro.product.device 2>/dev/null | tr -d '\r' || echo "m7")
    local backup_dir="/sdcard/TWRP/BACKUPS/${device_codename}"

    local available_backups
    available_backups=$(${adb_cmd} shell ls "${backup_dir}" 2>/dev/null || echo "")

    if [[ -z "${available_backups}" ]]; then
        log_emergency "✗ No backups found for rollback"
        log_emergency "Manual ROM reinstallation required"
        return 1
    fi

    log_info "Available backups:"
    echo "${available_backups}" | while read -r backup; do
        [[ -n "${backup}" ]] && echo "  - ${backup}"
    done

    # Step 3: Select backup for restore
    local selected_backup=""
    if [[ -n "${backup_name}" ]]; then
        # Use specified backup
        if echo "${available_backups}" | grep -q "^${backup_name}$"; then
            selected_backup="${backup_name}"
        else
            log_error "Specified backup '${backup_name}' not found"
        fi
    fi

    if [[ -z "${selected_backup}" ]]; then
        # Use most recent backup
        selected_backup=$(echo "${available_backups}" | head -1)
        log_info "Using most recent backup: ${selected_backup}"
    fi

    if [[ -z "${selected_backup}" ]]; then
        log_emergency "No suitable backup found"
        return 1
    fi

    # Step 4: Perform restore
    log_recovery "Step 4: Restoring from backup: ${selected_backup}"

    # Execute restore command in recovery
    execute_recovery_command "${device}" "restore ${selected_backup}"

    # Wait for restore to complete
    log_info "Waiting for restore operation to complete..."
    sleep 180  # Restore can take several minutes

    # Step 5: Reboot and verify
    log_recovery "Step 5: Rebooting after restore..."
    ${adb_cmd} reboot 2>/dev/null || true
    sleep 60

    if ${adb_cmd} shell echo "restore_test" >/dev/null 2>&1; then
        log_success "✓ ROLLBACK SUCCESSFUL"
        log_success "Device restored from backup: ${selected_backup}"
        return 0
    else
        log_emergency "✗ Rollback verification failed"
        log_emergency "Device may still be in recovery or unresponsive"
        return 1
    fi
}

# Device bricking recovery procedure
recover_bricked_device() {
    local device=${1}

    log_emergency "INITIATING BRICKED DEVICE RECOVERY"
    log_emergency "Device: ${device}"
    log_emergency "WARNING: This is a high-risk procedure"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                BRICKED DEVICE RECOVERY                      ║"
    echo "║                                                              ║"
    echo "║  This procedure attempts to recover a bricked device.       ║"
    echo "║  Only proceed if the device is completely unresponsive.     ║"
    echo "║                                                              ║"
    echo "║  EXTREME WARNING: This may brick the device permanently.    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    read -p "Type 'I UNDERSTAND THE RISK' to continue: " confirmation
    if [[ "${confirmation}" != "I UNDERSTAND THE RISK" ]]; then
        log_info "Bricked device recovery cancelled by user"
        return 1
    fi

    # Step 1: Try fastboot access
    log_recovery "Step 1: Attempting fastboot access..."
    if ! fastboot devices | grep -q "fastboot"; then
        log_emergency "Device not responding to fastboot"
        log_emergency "Try: Power off device, hold Vol- + Power for 10+ seconds"
        return 1
    fi

    log_success "✓ Fastboot access confirmed"

    # Step 2: Try to flash stock recovery
    log_recovery "Step 2: Attempting to flash stock recovery..."
    # This would require stock recovery image - simplified for now
    log_warn "Stock recovery flash not implemented (would require stock image)"

    # Step 3: Try TWRP recovery flash
    log_recovery "Step 3: Attempting TWRP recovery flash..."
    local twrp_path="${WORK_DIR}/downloads/magisk/twrp.img"

    if [[ -f "${twrp_path}" ]]; then
        log_info "Flashing TWRP recovery..."
        if fastboot flash recovery "${twrp_path}"; then
            log_success "✓ TWRP recovery flashed"
        else
            log_emergency "✗ TWRP recovery flash failed"
        fi
    else
        log_emergency "TWRP image not found for recovery flash"
    fi

    # Step 4: Try system image flash (if available)
    log_recovery "Step 4: Attempting system image flash..."
    # This would require system image - simplified for now
    log_warn "System image flash not implemented (would require system image)"

    log_emergency "BRICKED DEVICE RECOVERY COMPLETED"
    log_emergency "Check if device now responds. If not, hardware service may be required."
}

# Execute recovery command (helper function)
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

# Collect comprehensive logs
collect_comprehensive_logs() {
    local device=${1:-""}
    local issue_type=${2:-"general"}

    log_recovery "Collecting comprehensive logs for ${issue_type} issue..."

    local log_archive="${DIAGNOSTIC_DIR}/logs/comprehensive_logs_$(date '+%Y%m%d_%H%M%S').tar.gz"

    # Collect all available logs
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local temp_dir="${DIAGNOSTIC_DIR}/temp_logs"
    mkdir -p "${temp_dir}"

    # ADB logs
    ${adb_cmd} logcat -d > "${temp_dir}/adb_logcat.txt" 2>/dev/null || true

    # System logs
    ${adb_cmd} shell "su -c 'logcat -d'" > "${temp_dir}/system_logcat.txt" 2>/dev/null || true

    # Recovery logs
    ${adb_cmd} shell cat /tmp/recovery.log > "${temp_dir}/recovery.log" 2>/dev/null || true

    # Kernel logs
    ${adb_cmd} shell "su -c 'dmesg'" > "${temp_dir}/dmesg.txt" 2>/dev/null || true

    # Process list
    ${adb_cmd} shell ps > "${temp_dir}/processes.txt" 2>/dev/null || true

    # System properties
    ${adb_cmd} shell getprop > "${temp_dir}/properties.txt" 2>/dev/null || true

    # Create archive
    if tar -czf "${log_archive}" -C "${DIAGNOSTIC_DIR}" temp_logs 2>/dev/null; then
        log_success "✓ Comprehensive logs collected: ${log_archive}"
        rm -rf "${temp_dir}"
        echo "${log_archive}"
    else
        log_error "Failed to create log archive"
        return 1
    fi
}

# Generate recovery report
generate_recovery_report() {
    local device=${1:-""}
    local procedure=${2:-"general"}
    local success=${3:-false}
    local diagnostic_file=${4:-""}

    log_info "Generating recovery report..."

    local report_file="${DIAGNOSTIC_DIR}/recovery_report_$(date '+%Y%m%d_%H%M%S').txt"

    {
        echo "Android Device Setup - Recovery Report"
        echo "Generated on: $(date)"
        echo "Device: ${device:-Unknown}"
        echo "Procedure: ${procedure}"
        echo ""

        echo "=== RECOVERY STATUS ==="
        if [[ "${success}" == "true" ]]; then
            echo "✓ Recovery procedure completed successfully"
        else
            echo "✗ Recovery procedure failed or inconclusive"
        fi
        echo ""

        echo "=== DIAGNOSTIC INFORMATION ==="
        if [[ -n "${diagnostic_file}" ]] && [[ -f "${diagnostic_file}" ]]; then
            echo "Diagnostic file: ${diagnostic_file}"
        else
            echo "No diagnostic information collected"
        fi
        echo ""

        echo "=== RECOMMENDED NEXT STEPS ==="
        if [[ "${success}" != "true" ]]; then
            echo "- Review diagnostic logs for error details"
            echo "- Try alternative recovery procedures"
            echo "- Consider professional repair service"
            echo "- Check device warranty status"
        fi
        echo ""

        echo "=== SUPPORT RESOURCES ==="
        for resource in "${SUPPORT_RESOURCES[@]}"; do
            echo "- ${resource}"
        done
        echo ""

        echo "=== EMERGENCY CONTACTS ==="
        echo "- HTC Support: https://support.htc.com/"
        echo "- LineageOS Forums: https://forum.lineageos.org/"
        echo "- XDA Developers: https://forum.xda-developers.com/"
        echo ""

    } > "${report_file}"

    log_success "Recovery report generated: ${report_file}"
    echo "${report_file}"
}

# Quick diagnostic check
quick_diagnostic() {
    local device=${1:-""}

    log_recovery "Running quick diagnostic check..."

    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local issues_found=0

    # Check ADB connection
    if ! ${adb_cmd} devices | grep -q "device$\|recovery$"; then
        log_error "✗ No ADB connection to device"
        ((issues_found++))
    else
        log_success "✓ ADB connection established"
    fi

    # Check device responsiveness
    if ! ${adb_cmd} shell echo "diagnostic_test" >/dev/null 2>&1; then
        log_error "✗ Device not responding to ADB commands"
        ((issues_found++))
    else
        log_success "✓ Device responding to ADB commands"
    fi

    # Check battery level
    local battery_level
    battery_level=$(${adb_cmd} shell dumpsys battery | grep "level:" | awk '{print $2}' 2>/dev/null || echo "unknown")

    if [[ "${battery_level}" != "unknown" ]] && [[ ${battery_level} -lt 10 ]]; then
        log_warn "⚠ Low battery level: ${battery_level}%"
        ((issues_found++))
    elif [[ "${battery_level}" != "unknown" ]]; then
        log_success "✓ Battery level acceptable: ${battery_level}%"
    fi

    # Check storage space
    local storage_info
    storage_info=$(${adb_cmd} shell df /data | tail -1 | awk '{print $4}' 2>/dev/null || echo "unknown")

    if [[ "${storage_info}" != "unknown" ]] && [[ ${storage_info} -lt 100000 ]]; then  # Less than ~100MB
        log_warn "⚠ Low storage space: ${storage_info} KB available"
        ((issues_found++))
    elif [[ "${storage_info}" != "unknown" ]]; then
        log_success "✓ Storage space available: $((storage_info / 1024)) MB"
    fi

    log_recovery "Quick diagnostic: ${issues_found} issues found"

    if [[ ${issues_found} -eq 0 ]]; then
        log_success "✓ No critical issues detected"
        return 0
    else
        log_warn "⚠ Issues detected - recovery procedures may be needed"
        return 1
    fi
}

# Main function
main() {
    log_info "Starting Recovery Procedures"

    # Initialize diagnostics
    init_diagnostics

    case "${1:-}" in
        "bootloop")
            local device=${2}
            collect_system_diagnostics "${device}"
            if recover_bootloop "${device}"; then
                generate_recovery_report "${device}" "bootloop_recovery" "true"
            else
                generate_recovery_report "${device}" "bootloop_recovery" "false"
            fi
            ;;
        "rollback")
            local device=${2}
            local backup=${3:-""}
            collect_system_diagnostics "${device}"
            if rollback_failed_installation "${device}" "${backup}"; then
                generate_recovery_report "${device}" "installation_rollback" "true"
            else
                generate_recovery_report "${device}" "installation_rollback" "false"
            fi
            ;;
        "bricked")
            local device=${2}
            collect_system_diagnostics "${device}"
            recover_bricked_device "${device}"
            generate_recovery_report "${device}" "bricked_device_recovery" "unknown"
            ;;
        "diagnostics")
            local device=${2:-""}
            collect_system_diagnostics "${device}"
            ;;
        "logs")
            local device=${2:-""}
            local issue=${3:-"general"}
            collect_comprehensive_logs "${device}" "${issue}"
            ;;
        "quick-check")
            local device=${2:-""}
            quick_diagnostic "${device}"
            ;;
        "report")
            local device=${2:-""}
            local procedure=${3:-"general"}
            local success=${4:-"unknown"}
            generate_recovery_report "${device}" "${procedure}" "${success}"
            ;;
        *)
            echo "Usage: $0 {bootloop|rollback|bricked|diagnostics|logs|quick-check|report} [device] [options]"
            echo ""
            echo "Commands:"
            echo "  bootloop [device]        - Recover from boot loop"
            echo "  rollback [device] [backup] - Rollback failed installation"
            echo "  bricked [device]         - Recover bricked device"
            echo "  diagnostics [device]     - Collect diagnostic information"
            echo "  logs [device] [issue]    - Collect comprehensive logs"
            echo "  quick-check [device]     - Run quick diagnostic check"
            echo "  report [device] [proc] [success] - Generate recovery report"
            echo ""
            echo "Examples:"
            echo "  $0 bootloop HT123456          # Recover from boot loop"
            echo "  $0 rollback HT123456 backup1 # Rollback to specific backup"
            echo "  $0 diagnostics HT123456      # Collect diagnostics"
            echo "  $0 quick-check HT123456      # Quick health check"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"