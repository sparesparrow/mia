#!/bin/bash

# Android Device Setup - File Transfer Manager
# Reliable file transfer to device storage with progress monitoring and verification

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
LOG_FILE="${WORK_DIR}/file-transfer.log"
TRANSFER_LOG="${WORK_DIR}/transfer-history.log"

# Transfer settings
MAX_RETRIES=3
TRANSFER_TIMEOUT=300  # 5 minutes
CHUNK_SIZE="4M"      # For progress monitoring

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

# Check device connection and mode
check_device_status() {
    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Checking device connection status..."

    # Check if device is connected
    if ! ${adb_cmd} devices | grep -q "device$\|recovery$"; then
        log_error "No device connected or device not authorized"
        return 1
    fi

    # Determine device mode
    local device_mode
    device_mode=$(${adb_cmd} get-state 2>/dev/null || echo "unknown")

    case "${device_mode}" in
        "device")
            log_info "Device is in normal Android mode"
            DEVICE_MODE="normal"
            ;;
        "recovery")
            log_info "Device is in recovery mode"
            DEVICE_MODE="recovery"
            ;;
        "sideload")
            log_info "Device is in sideload mode"
            DEVICE_MODE="sideload"
            ;;
        *)
            log_info "Device mode: ${device_mode}"
            DEVICE_MODE="${device_mode}"
            ;;
    esac

    return 0
}

# Check available storage space on device
check_device_storage() {
    local device=${1:-""}
    local required_space=${2:-0}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Checking device storage space..."

    # Get storage information
    local storage_info
    case "${DEVICE_MODE}" in
        "normal")
            storage_info=$(${adb_cmd} shell df /sdcard 2>/dev/null || ${adb_cmd} shell df /data 2>/dev/null || echo "")
            ;;
        "recovery")
            # In recovery, try to get storage info from /sdcard or /data
            storage_info=$(${adb_cmd} shell df /sdcard 2>/dev/null || ${adb_cmd} shell df /data 2>/dev/null || echo "")
            ;;
        *)
            log_warn "Cannot determine storage in ${DEVICE_MODE} mode"
            return 0
            ;;
    esac

    if [[ -n "${storage_info}" ]]; then
        # Parse available space (simplified)
        local available_kb
        available_kb=$(echo "${storage_info}" | tail -1 | awk '{print $4}' || echo "0")

        if [[ ${available_kb} -gt 0 ]]; then
            local available_mb=$((available_kb / 1024))
            log_info "Available storage: ${available_mb} MB"

            if [[ ${required_space} -gt 0 ]]; then
                local required_mb=$((required_space / 1024 / 1024))
                if [[ ${available_mb} -lt ${required_mb} ]]; then
                    log_error "Insufficient storage space. Required: ${required_mb} MB, Available: ${available_mb} MB"
                    return 1
                fi
            fi
        else
            log_warn "Could not determine available storage space"
        fi
    else
        log_warn "Could not get storage information from device"
    fi

    return 0
}

# Determine target directory on device
get_target_directory() {
    local file_type=${1:-"generic"}

    case "${DEVICE_MODE}" in
        "recovery")
            case "${file_type}" in
                "rom")
                    echo "/sdcard/lineageos"
                    ;;
                "gapps")
                    echo "/sdcard/gapps"
                    ;;
                "magisk")
                    echo "/sdcard/magisk"
                    ;;
                *)
                    echo "/sdcard"
                    ;;
            esac
            ;;
        "normal")
            case "${file_type}" in
                "rom")
                    echo "/sdcard/Download/lineageos"
                    ;;
                "gapps")
                    echo "/sdcard/Download/gapps"
                    ;;
                "magisk")
                    echo "/sdcard/Download/magisk"
                    ;;
                *)
                    echo "/sdcard/Download"
                    ;;
            esac
            ;;
        *)
            echo "/sdcard"
            ;;
    esac
}

# Create target directory on device
create_target_directory() {
    local device=${1:-""}
    local target_dir=${2}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Creating target directory: ${target_dir}"

    if ${adb_cmd} shell mkdir -p "${target_dir}" 2>/dev/null; then
        log_success "Target directory created successfully"
        return 0
    else
        log_warn "Could not create target directory (may already exist)"
        return 0
    fi
}

# Transfer file using ADB push with progress monitoring
transfer_file_adb() {
    local device=${1:-""}
    local local_file=${2}
    local remote_path=${3}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local filename=$(basename "${local_file}")
    local file_size
    file_size=$(stat -c%s "${local_file}" 2>/dev/null || stat -f%z "${local_file}" 2>/dev/null || echo "0")

    log_info "Transferring ${filename} (${file_size} bytes) to ${remote_path}"

    # ADB push with basic progress indication
    local start_time=$(date +%s)

    if ${adb_cmd} push "${local_file}" "${remote_path}" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log_success "File transferred successfully in ${duration} seconds"
        return 0
    else
        log_error "ADB push failed"
        return 1
    fi
}

# Transfer file using ADB sideload (for recovery mode)
transfer_file_sideload() {
    local device=${1:-""}
    local local_file=${2}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local filename=$(basename "${local_file}")

    log_info "Attempting sideload transfer for ${filename}"

    # Check if device supports sideload
    if ! ${adb_cmd} devices | grep -q "sideload"; then
        log_info "Device not in sideload mode, cannot use sideload transfer"
        return 1
    fi

    # ADB sideload doesn't have progress, but it's reliable for large files
    if ${adb_cmd} sideload "${local_file}" 2>&1; then
        log_success "File sideloaded successfully"
        return 0
    else
        log_error "ADB sideload failed"
        return 1
    fi
}

# Verify transferred file
verify_transfer() {
    local device=${1:-""}
    local local_file=${2}
    local remote_path=${3}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local filename=$(basename "${local_file}")

    log_info "Verifying transferred file: ${filename}"

    # Get local file checksum
    local local_checksum
    if command -v sha256sum >/dev/null 2>&1; then
        local_checksum=$(sha256sum "${local_file}" | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        local_checksum=$(shasum -a 256 "${local_file}" | awk '{print $1}')
    else
        log_warn "No checksum tool available, skipping verification"
        return 0
    fi

    # Get remote file checksum
    local remote_checksum
    remote_checksum=$(${adb_cmd} shell sha256sum "${remote_path}" 2>/dev/null | awk '{print $1}' || echo "")

    if [[ -z "${remote_checksum}" ]]; then
        # Try alternative method for checksum
        remote_checksum=$(${adb_cmd} shell "busybox sha256sum '${remote_path}'" 2>/dev/null | awk '{print $1}' || echo "")
    fi

    if [[ -n "${remote_checksum}" ]] && [[ "${local_checksum}" == "${remote_checksum}" ]]; then
        log_success "File verification passed"
        return 0
    else
        log_error "File verification failed"
        log_error "Local checksum: ${local_checksum}"
        log_error "Remote checksum: ${remote_checksum:-unknown}"
        return 1
    fi
}

# Transfer single file with retry logic
transfer_single_file() {
    local device=${1}
    local local_file=${2}
    local remote_path=${3}
    local max_retries=${4:-${MAX_RETRIES}}

    if [[ ! -f "${local_file}" ]]; then
        log_error "Local file does not exist: ${local_file}"
        return 1
    fi

    local filename=$(basename "${local_file}")
    local attempt=1

    while [[ ${attempt} -le ${max_retries} ]]; do
        log_info "Transfer attempt ${attempt}/${max_retries} for ${filename}"

        # Check if file already exists and is valid
        if verify_transfer "${device}" "${local_file}" "${remote_path}" 2>/dev/null; then
            log_success "File already exists and is valid on device"
            return 0
        fi

        # Try ADB push first
        if transfer_file_adb "${device}" "${local_file}" "${remote_path}"; then
            # Verify transfer
            if verify_transfer "${device}" "${local_file}" "${remote_path}"; then
                log_success "File transfer completed successfully"
                return 0
            else
                log_warn "Transfer verification failed, will retry"
            fi
        fi

        # If ADB push failed and we're in recovery, try sideload as fallback
        if [[ "${DEVICE_MODE}" == "recovery" ]] && [[ ${attempt} -eq ${max_retries} ]]; then
            log_info "Trying sideload as final attempt"
            if transfer_file_sideload "${device}" "${local_file}"; then
                log_success "File transferred via sideload"
                return 0
            fi
        fi

        ((attempt++))
        if [[ ${attempt} -le ${max_retries} ]]; then
            log_warn "Transfer failed, retrying in 5 seconds..."
            sleep 5
        fi
    done

    log_error "File transfer failed after ${max_retries} attempts"
    return 1
}

# Transfer multiple files
transfer_batch() {
    local device=${1}
    shift
    local files=("$@")

    local success_count=0
    local total_count=${#files[@]}

    log_info "Starting batch transfer of ${total_count} files"

    for file in "${files[@]}"; do
        if [[ -f "${file}" ]]; then
            local filename=$(basename "${file}")
            local target_dir
            local file_type="generic"

            # Determine file type and target directory
            if [[ "${filename}" == lineage*.zip ]]; then
                file_type="rom"
            elif [[ "${filename}" == *gapps*.zip ]]; then
                file_type="gapps"
            elif [[ "${filename}" == *magisk*.zip ]]; then
                file_type="magisk"
            fi

            target_dir=$(get_target_directory "${file_type}")
            create_target_directory "${device}" "${target_dir}"

            local remote_path="${target_dir}/${filename}"

            if transfer_single_file "${device}" "${file}" "${remote_path}"; then
                ((success_count++))
                # Log successful transfer
                echo "$(date '+%Y-%m-%d %H:%M:%S') SUCCESS ${filename} -> ${remote_path}" >> "${TRANSFER_LOG}"
            else
                log_error "Failed to transfer: ${filename}"
                echo "$(date '+%Y-%m-%d %H:%M:%S') FAILED ${filename} -> ${remote_path}" >> "${TRANSFER_LOG}"
            fi
        else
            log_warn "File not found: ${file}"
        fi
    done

    log_info "Batch transfer completed: ${success_count}/${total_count} files successful"

    if [[ ${success_count} -eq ${total_count} ]]; then
        return 0
    else
        return 1
    fi
}

# List files on device
list_device_files() {
    local device=${1:-""}
    local directory=${2:-"/sdcard"}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    log_info "Listing files in ${directory}"

    local file_list
    file_list=$(${adb_cmd} shell ls -la "${directory}" 2>/dev/null || echo "Could not list directory")

    echo "Files in ${directory}:"
    echo "${file_list}"
}

# Clean up transferred files
cleanup_transferred_files() {
    local device=${1:-""}
    local directory=${2:-""}
    local pattern=${3:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    if [[ -z "${directory}" ]] || [[ -z "${pattern}" ]]; then
        log_error "Directory and pattern required for cleanup"
        return 1
    fi

    log_info "Cleaning up files matching '${pattern}' in ${directory}"

    # Find and remove matching files
    local cleanup_cmd="find '${directory}' -name '${pattern}' -exec rm {} \;"
    if ${adb_cmd} shell "${cleanup_cmd}" 2>/dev/null; then
        log_success "Cleanup completed"
        return 0
    else
        log_warn "Cleanup may have failed or no matching files found"
        return 0
    fi
}

# Get transfer statistics
get_transfer_stats() {
    log_info "Getting transfer statistics..."

    if [[ -f "${TRANSFER_LOG}" ]]; then
        local total_transfers
        local successful_transfers
        local failed_transfers

        total_transfers=$(wc -l < "${TRANSFER_LOG}")
        successful_transfers=$(grep -c "SUCCESS" "${TRANSFER_LOG}" || echo "0")
        failed_transfers=$(grep -c "FAILED" "${TRANSFER_LOG}" || echo "0")

        echo "Total transfers: ${total_transfers}"
        echo "Successful: ${successful_transfers}"
        echo "Failed: ${failed_transfers}"

        if [[ ${total_transfers} -gt 0 ]]; then
            local success_rate=$((successful_transfers * 100 / total_transfers))
            echo "Success rate: ${success_rate}%"
        fi
    else
        echo "No transfer history found"
    fi
}

# Main function
main() {
    log_info "Starting File Transfer Manager"

    case "${1:-}" in
        "transfer")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: $0 transfer <device> <local_file> [remote_path]"
                exit 1
            fi

            local device=${2}
            local local_file=${3}
            local remote_path=${4:-""}

            check_device_status "${device}"

            if [[ -z "${remote_path}" ]]; then
                local filename=$(basename "${local_file}")
                local target_dir=$(get_target_directory)
                create_target_directory "${device}" "${target_dir}"
                remote_path="${target_dir}/${filename}"
            fi

            transfer_single_file "${device}" "${local_file}" "${remote_path}"
            ;;
        "batch")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: $0 batch <device> <file1> [file2] ..."
                exit 1
            fi

            local device=${2}
            shift 2
            local files=("$@")

            check_device_status "${device}"
            transfer_batch "${device}" "${files[@]}"
            ;;
        "list")
            local device=${2:-""}
            local directory=${3:-"/sdcard"}
            check_device_status "${device}"
            list_device_files "${device}" "${directory}"
            ;;
        "cleanup")
            if [[ $# -lt 4 ]]; then
                log_error "Usage: $0 cleanup <device> <directory> <pattern>"
                exit 1
            fi

            local device=${2}
            local directory=${3}
            local pattern=${4}

            check_device_status "${device}"
            cleanup_transferred_files "${device}" "${directory}" "${pattern}"
            ;;
        "stats")
            get_transfer_stats
            ;;
        "verify")
            if [[ $# -lt 4 ]]; then
                log_error "Usage: $0 verify <device> <local_file> <remote_path>"
                exit 1
            fi

            local device=${2}
            local local_file=${3}
            local remote_path=${4}

            check_device_status "${device}"
            verify_transfer "${device}" "${local_file}" "${remote_path}"
            ;;
        *)
            echo "Usage: $0 {transfer|batch|list|cleanup|stats|verify} [options]"
            echo ""
            echo "Commands:"
            echo "  transfer <device> <local_file> [remote_path] - Transfer single file"
            echo "  batch <device> <file1> [file2] ...          - Transfer multiple files"
            echo "  list [device] [directory]                   - List files on device"
            echo "  cleanup <device> <directory> <pattern>      - Clean up transferred files"
            echo "  stats                                       - Show transfer statistics"
            echo "  verify <device> <local_file> <remote_path>  - Verify transferred file"
            echo ""
            echo "Examples:"
            echo "  $0 transfer HT123456 /path/to/rom.zip        # Transfer ROM to device"
            echo "  $0 batch HT123456 rom.zip gapps.zip         # Transfer multiple files"
            echo "  $0 list HT123456 /sdcard/Download           # List device files"
            echo "  $0 cleanup HT123456 /sdcard '*.tmp'         # Clean up temp files"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"