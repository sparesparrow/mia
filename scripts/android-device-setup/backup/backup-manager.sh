#!/bin/bash

# Android Device Setup - Backup Manager
# Automated system backup creation and management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
BACKUP_DIR="${WORK_DIR}/backups"
LOG_FILE="${WORK_DIR}/backup-manager.log"
BACKUP_REGISTRY="${BACKUP_DIR}/backup-registry.txt"

# Backup settings
MAX_BACKUPS=5
BACKUP_TIMEOUT=1800  # 30 minutes
COMPRESSION_LEVEL=9

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

log_backup() {
    echo -e "${CYAN}[BACKUP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Initialize backup directory
init_backup_directory() {
    log_backup "Initializing backup directory..."

    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}/system"
    mkdir -p "${BACKUP_DIR}/data"
    mkdir -p "${BACKUP_DIR}/boot"
    mkdir -p "${BACKUP_DIR}/full"

    # Create backup registry if it doesn't exist
    if [[ ! -f "${BACKUP_REGISTRY}" ]]; then
        echo "# Backup Registry - $(date)" > "${BACKUP_REGISTRY}"
        echo "# Format: timestamp,type,name,path,size,verified" >> "${BACKUP_REGISTRY}"
    fi

    log_success "✓ Backup directory initialized"
}

# Register backup in registry
register_backup() {
    local type=$1
    local name=$2
    local path=$3
    local size=${4:-"unknown"}

    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local verified="pending"

    echo "${timestamp},${type},${name},${path},${size},${verified}" >> "${BACKUP_REGISTRY}"
    log_backup "Registered backup: ${name} (${type})"
}

# Update backup verification status
update_backup_verification() {
    local backup_name=$1
    local status=$2

    # Update registry (simplified - would need more robust implementation)
    sed -i "s/${backup_name},.*,pending/${backup_name},.*,${status}/" "${BACKUP_REGISTRY}" 2>/dev/null || true

    log_backup "Updated verification status for ${backup_name}: ${status}"
}

# Create TWRP backup
create_twrp_backup() {
    local device=${1:-""}
    local backup_type=${2:-"system"}  # system, data, boot, full
    local backup_name=${3:-"backup_$(date '+%Y%m%d_%H%M%S')"}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_backup "Creating TWRP backup: ${backup_name} (${backup_type})"

    # Ensure device is in recovery mode
    local recovery_script="${SCRIPT_DIR}/../recovery/verify-recovery.sh"
    if ! "${recovery_script}" boot "${device}" >/dev/null 2>&1; then
        log_error "Cannot ensure device is in recovery mode for backup"
        return 1
    fi

    # Determine backup partitions based on type
    local backup_partitions=""
    case "${backup_type}" in
        "system")
            backup_partitions="System"
            ;;
        "data")
            backup_partitions="Data"
            ;;
        "boot")
            backup_partitions="Boot"
            ;;
        "full")
            backup_partitions="Boot System Data"
            ;;
        *)
            log_error "Unknown backup type: ${backup_type}"
            return 1
            ;;
    esac

    # Create backup directory on device
    local device_backup_dir="/sdcard/TWRP/BACKUPS/$(get_device_codename "${device}")"
    ${adb_cmd} shell mkdir -p "${device_backup_dir}" 2>/dev/null || true

    # Start backup process
    log_backup "Starting backup of partitions: ${backup_partitions}"

    local start_time=$(date +%s)
    local backup_success=false

    # Execute backup command
    execute_recovery_command "${device}" "backup ${backup_partitions} ${backup_name}"

    # Wait for backup to complete
    local attempts=0
    local max_attempts=60  # 30 minutes max

    while [[ ${attempts} -lt ${max_attempts} ]]; do
        sleep 30
        ((attempts++))

        # Check if backup completed (simplified check)
        local backup_check
        backup_check=$(${adb_cmd} shell ls "${device_backup_dir}/${backup_name}" 2>/dev/null | wc -l || echo "0")

        if [[ "${backup_check}" != "0" ]]; then
            log_backup "Backup appears to be in progress..."
        fi

        # Check for completion indicators (simplified)
        local recovery_status
        recovery_status=$(${adb_cmd} shell getprop twrp.action_complete 2>/dev/null || echo "")

        if [[ "${recovery_status}" == "1" ]]; then
            backup_success=true
            break
        fi
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [[ "${backup_success}" != true ]]; then
        log_error "Backup did not complete successfully within timeout"
        return 1
    fi

    log_success "✓ TWRP backup completed in ${duration} seconds"

    # Calculate backup size
    local backup_size
    backup_size=$(${adb_cmd} shell du -sh "${device_backup_dir}/${backup_name}" 2>/dev/null | awk '{print $1}' || echo "unknown")

    # Register backup
    register_backup "${backup_type}" "${backup_name}" "${device_backup_dir}/${backup_name}" "${backup_size}"

    return 0
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

# Get device codename for backup naming
get_device_codename() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Get device codename from ro.product.device
    local codename
    codename=$(${adb_cmd} shell getprop ro.product.device 2>/dev/null | tr -d '\r' || echo "unknown")

    echo "${codename}"
}

# Verify backup integrity
verify_backup() {
    local device=${1:-""}
    local backup_name=${2}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_backup "Verifying backup integrity: ${backup_name}"

    # Find backup on device
    local device_codename=$(get_device_codename "${device}")
    local backup_path="/sdcard/TWRP/BACKUPS/${device_codename}/${backup_name}"

    # Check if backup exists
    local backup_exists
    backup_exists=$(${adb_cmd} shell ls "${backup_path}" 2>/dev/null | wc -l || echo "0")

    if [[ "${backup_exists}" == "0" ]]; then
        log_error "Backup not found: ${backup_path}"
        update_backup_verification "${backup_name}" "failed"
        return 1
    fi

    # Check backup contents
    local backup_files
    backup_files=$(${adb_cmd} shell find "${backup_path}" -name "*.win" -o -name "*.img" 2>/dev/null | wc -l || echo "0")

    if [[ "${backup_files}" == "0" ]]; then
        log_error "No backup image files found"
        update_backup_verification "${backup_name}" "failed"
        return 1
    fi

    # Check file sizes (basic integrity check)
    local total_size
    total_size=$(${adb_cmd} shell du -sh "${backup_path}" 2>/dev/null | awk '{print $1}' || echo "0")

    if [[ "${total_size}" == "0" ]]; then
        log_error "Backup appears to be empty"
        update_backup_verification "${backup_name}" "failed"
        return 1
    fi

    log_success "✓ Backup integrity verified (${backup_files} files, ${total_size})"
    update_backup_verification "${backup_name}" "verified"

    return 0
}

# List available backups
list_backups() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_backup "Listing available backups..."

    # List backups from registry
    if [[ -f "${BACKUP_REGISTRY}" ]]; then
        echo ""
        echo "=== REGISTERED BACKUPS ==="
        tail -n +3 "${BACKUP_REGISTRY}" | while IFS=',' read -r timestamp type name path size verified; do
            echo "${timestamp} | ${type} | ${name} | ${size} | ${verified}"
        done
        echo ""
    fi

    # List backups on device
    local device_codename=$(get_device_codename "${device}")
    local device_backup_dir="/sdcard/TWRP/BACKUPS/${device_codename}"

    echo "=== DEVICE BACKUPS ==="
    local device_backups
    device_backups=$(${adb_cmd} shell ls "${device_backup_dir}" 2>/dev/null || echo "No backups found")

    if [[ "${device_backups}" != "No backups found" ]]; then
        echo "${device_backups}" | while read -r backup; do
            if [[ -n "${backup}" ]]; then
                local backup_size
                backup_size=$(${adb_cmd} shell du -sh "${device_backup_dir}/${backup}" 2>/dev/null | awk '{print $1}' || echo "unknown")
                echo "  ${backup} (${backup_size})"
            fi
        done
    else
        echo "No backups found on device"
    fi
    echo ""
}

# Clean old backups
clean_old_backups() {
    local device=${1:-""}
    local keep_count=${2:-${MAX_BACKUPS}}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_backup "Cleaning old backups (keeping ${keep_count} most recent)..."

    local device_codename=$(get_device_codename "${device}")
    local device_backup_dir="/sdcard/TWRP/BACKUPS/${device_codename}"

    # Get list of backups sorted by modification time (oldest first)
    local backup_list
    backup_list=$(${adb_cmd} shell ls -t "${device_backup_dir}" 2>/dev/null || echo "")

    if [[ -z "${backup_list}" ]]; then
        log_info "No backups to clean"
        return 0
    fi

    local backup_count
    backup_count=$(echo "${backup_list}" | wc -l)

    if [[ ${backup_count} -le ${keep_count} ]]; then
        log_info "Only ${backup_count} backups exist, no cleanup needed"
        return 0
    fi

    local backups_to_remove=$((backup_count - keep_count))
    log_info "Removing ${backups_to_remove} old backups..."

    local removed_count=0
    echo "${backup_list}" | tail -n "${backups_to_remove}" | while read -r backup; do
        if [[ -n "${backup}" ]]; then
            log_info "Removing backup: ${backup}"
            ${adb_cmd} shell rm -rf "${device_backup_dir}/${backup}" 2>/dev/null || true
            ((removed_count++))
        fi
    done

    log_success "✓ Cleaned up ${removed_count} old backups"
    return 0
}

# Export backup to host
export_backup() {
    local device=${1}
    local backup_name=${2}
    local export_path=${3:-"${BACKUP_DIR}/exported"}

    log_backup "Exporting backup to host: ${backup_name}"

    mkdir -p "${export_path}"

    local device_codename=$(get_device_codename "${device}")
    local device_backup_path="/sdcard/TWRP/BACKUPS/${device_codename}/${backup_name}"
    local host_backup_path="${export_path}/${backup_name}"

    # Use file transfer script to copy backup files
    local transfer_script="${SCRIPT_DIR}/../rom/file-transfer.sh"

    if [[ ! -x "${transfer_script}" ]]; then
        log_error "File transfer script not found"
        return 1
    fi

    # Get list of files to transfer
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local backup_files
    backup_files=$(${adb_cmd} shell find "${device_backup_path}" -type f 2>/dev/null || echo "")

    if [[ -z "${backup_files}" ]]; then
        log_error "No backup files found to export"
        return 1
    fi

    log_info "Found $(echo "${backup_files}" | wc -l) files to export"

    # Create host directory
    mkdir -p "${host_backup_path}"

    # Export each file (simplified - would need proper handling of large files)
    echo "${backup_files}" | while read -r file; do
        if [[ -n "${file}" ]]; then
            local filename=$(basename "${file}")
            local relative_path=${file#"${device_backup_path}/"}
            local host_file="${host_backup_path}/${relative_path}"

            mkdir -p "$(dirname "${host_file}")"

            log_info "Exporting: ${filename}"
            ${adb_cmd} pull "${file}" "${host_file}" 2>/dev/null || log_warn "Failed to export: ${filename}"
        fi
    done

    # Compress exported backup
    local archive_name="${backup_name}_$(date '+%Y%m%d_%H%M%S').tar.gz"
    local archive_path="${export_path}/${archive_name}"

    log_info "Compressing backup to: ${archive_name}"
    if tar -czf "${archive_path}" -C "${export_path}" "${backup_name}" 2>/dev/null; then
        log_success "✓ Backup exported and compressed: ${archive_path}"
        # Clean up uncompressed version
        rm -rf "${host_backup_path}"
        return 0
    else
        log_error "Failed to compress exported backup"
        return 1
    fi
}

# Create pre-installation backup
create_pre_install_backup() {
    local device=${1}
    local backup_name=${2:-"pre_install_$(date '+%Y%m%d_%H%M%S')"}

    log_backup "Creating pre-installation backup..."

    # Create full system backup before any modifications
    if create_twrp_backup "${device}" "full" "${backup_name}"; then
        log_success "✓ Pre-installation backup completed: ${backup_name}"
        return 0
    else
        log_error "Pre-installation backup failed"
        return 1
    fi
}

# Main function
main() {
    log_info "Starting Backup Manager"

    # Initialize backup system
    init_backup_directory

    case "${1:-}" in
        "create")
            local device=${2}
            local type=${3:-"system"}
            local name=${4:-"backup_$(date '+%Y%m%d_%H%M%S')"}
            create_twrp_backup "${device}" "${type}" "${name}"
            ;;
        "verify")
            local device=${2}
            local backup_name=${3}
            verify_backup "${device}" "${backup_name}"
            ;;
        "list")
            local device=${2:-""}
            list_backups "${device}"
            ;;
        "clean")
            local device=${2:-""}
            local keep=${3:-${MAX_BACKUPS}}
            clean_old_backups "${device}" "${keep}"
            ;;
        "export")
            local device=${2}
            local backup_name=${3}
            local export_path=${4:-"${BACKUP_DIR}/exported"}
            export_backup "${device}" "${backup_name}" "${export_path}"
            ;;
        "pre-install")
            local device=${2}
            local name=${3:-"pre_install_$(date '+%Y%m%d_%H%M%S')"}
            create_pre_install_backup "${device}" "${name}"
            ;;
        "full-backup")
            local device=${2}
            local name=${3:-"full_backup_$(date '+%Y%m%d_%H%M%S')"}
            create_twrp_backup "${device}" "full" "${name}"
            ;;
        *)
            echo "Usage: $0 {create|verify|list|clean|export|pre-install|full-backup} [device] [options]"
            echo ""
            echo "Commands:"
            echo "  create <device> [type] [name]     - Create TWRP backup"
            echo "  verify <device> <backup_name>     - Verify backup integrity"
            echo "  list [device]                     - List available backups"
            echo "  clean [device] [keep_count]       - Clean old backups"
            echo "  export <device> <backup> [path]   - Export backup to host"
            echo "  pre-install <device> [name]       - Create pre-install backup"
            echo "  full-backup <device> [name]       - Create full system backup"
            echo ""
            echo "Backup Types: system, data, boot, full"
            echo ""
            echo "Examples:"
            echo "  $0 create HT123456 full           # Create full backup"
            echo "  $0 list HT123456                  # List device backups"
            echo "  $0 verify HT123456 backup_20241201 # Verify specific backup"
            echo "  $0 clean HT123456 3              # Keep only 3 most recent backups"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"