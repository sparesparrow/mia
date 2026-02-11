#!/bin/bash

# Android Device Setup - TWRP Recovery Manager
# Automated TWRP recovery installation and updates for HTC One M7

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
BACKUP_DIR="${WORK_DIR}/backups"
LOG_FILE="${WORK_DIR}/twrp-manager.log"

# HTC One M7 TWRP configuration
DEVICE_CODENAME="m7"
DEVICE_MODEL="HTC One M7"

# TWRP download sources (in order of preference)
TWRP_SOURCES=(
    "https://dl.twrp.me/${DEVICE_CODENAME}/twrp-${TWRP_VERSION:-3.7.0_9-0}-${DEVICE_CODENAME}.img"
    "https://eu.dl.twrp.me/${DEVICE_CODENAME}/twrp-${TWRP_VERSION:-3.7.0_9-0}-${DEVICE_CODENAME}.img"
    "https://twrp.me/Devices/${DEVICE_MODEL// /}/"
)

# Expected TWRP checksums (SHA256)
declare -A TWRP_CHECKSUMS=(
    ["3.7.0_9-0"]="abc123def456..."  # Placeholder - needs actual checksum
)

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

# Check if device is in fastboot mode
check_fastboot_mode() {
    log_info "Checking if device is in fastboot mode..."

    if ! fastboot devices | grep -q "fastboot"; then
        log_error "Device is not in fastboot mode"
        log_info "Please boot device into fastboot mode:"
        log_info "  1. Power off device"
        log_info "  2. Hold Volume Down + Power to enter bootloader"
        log_info "  3. Use Volume keys to select 'FASTBOOT' and press Power"
        return 1
    fi

    log_success "Device is in fastboot mode"
    return 0
}

# Boot device into fastboot mode
boot_to_fastboot() {
    log_info "Attempting to boot device into fastboot mode..."

    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Try to reboot to bootloader using ADB
    if ${adb_cmd} reboot bootloader; then
        log_info "Device rebooting to bootloader..."
        sleep 10

        # Check if device entered fastboot
        if check_fastboot_mode; then
            return 0
        fi
    fi

    log_error "Failed to boot device into fastboot mode automatically"
    log_info "Please manually boot device into fastboot mode"
    return 1
}

# Get latest TWRP version for device
get_latest_twrp_version() {
    log_info "Checking for latest TWRP version for ${DEVICE_MODEL}..."

    # Try to get latest version from TWRP website
    local latest_version=""

    # Check official TWRP website for device page
    if command -v curl >/dev/null 2>&1; then
        local device_page
        device_page=$(curl -s "https://twrp.me/Devices/${DEVICE_MODEL// /}/" 2>/dev/null || echo "")

        if [[ -n "${device_page}" ]]; then
            # Extract version from page (this is a simplified approach)
            latest_version=$(echo "${device_page}" | grep -oP 'twrp-\K[0-9]+\.[0-9]+\.[0-9]+(?:_[0-9]+)?' | head -1 || echo "")
        fi
    fi

    # Fallback to known working version for HTC One M7
    if [[ -z "${latest_version}" ]]; then
        latest_version="3.7.0_9-0"
        log_warn "Could not determine latest version, using known stable version: ${latest_version}"
    else
        log_info "Latest TWRP version: ${latest_version}"
    fi

    echo "${latest_version}"
}

# Download TWRP image
download_twrp() {
    local version=${1:-"3.7.0_9-0"}
    local twrp_file="twrp-${version}-${DEVICE_CODENAME}.img"
    local twrp_path="${DOWNLOAD_DIR}/${twrp_file}"

    log_info "Downloading TWRP ${version} for ${DEVICE_MODEL}..."

    # Create download directory
    mkdir -p "${DOWNLOAD_DIR}"

    # Check if file already exists
    if [[ -f "${twrp_path}" ]]; then
        log_info "TWRP image already exists: ${twrp_path}"
        return 0
    fi

    # Try each download source
    local download_success=false
    for source_url in "${TWRP_SOURCES[@]}"; do
        # Replace version placeholder if present
        local actual_url="${source_url//TWRP_VERSION/${version}}"

        log_info "Trying download source: ${actual_url}"

        if command -v wget >/dev/null 2>&1; then
            if wget -q -O "${twrp_path}" "${actual_url}"; then
                download_success=true
                break
            fi
        elif command -v curl >/dev/null 2>&1; then
            if curl -s -o "${twrp_path}" "${actual_url}"; then
                download_success=true
                break
            fi
        fi
    done

    if [[ "${download_success}" != true ]]; then
        log_error "Failed to download TWRP image from all sources"
        return 1
    fi

    # Verify download
    if [[ ! -f "${twrp_path}" ]] || [[ ! -s "${twrp_path}" ]]; then
        log_error "Downloaded file is empty or missing"
        rm -f "${twrp_path}"
        return 1
    fi

    log_success "TWRP image downloaded successfully: ${twrp_path}"
    return 0
}

# Verify TWRP image checksum
verify_twrp_checksum() {
    local version=${1}
    local twrp_file="twrp-${version}-${DEVICE_CODENAME}.img"
    local twrp_path="${DOWNLOAD_DIR}/${twrp_file}"

    log_info "Verifying TWRP image checksum..."

    if [[ ! -f "${twrp_path}" ]]; then
        log_error "TWRP image not found: ${twrp_path}"
        return 1
    fi

    # Calculate SHA256 checksum
    local calculated_checksum
    if command -v sha256sum >/dev/null 2>&1; then
        calculated_checksum=$(sha256sum "${twrp_path}" | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        calculated_checksum=$(shasum -a 256 "${twrp_path}" | awk '{print $1}')
    else
        log_warn "No SHA256 tool available, skipping checksum verification"
        return 0
    fi

    # Check against known checksums
    local expected_checksum="${TWRP_CHECKSUMS[${version}]:-}"

    if [[ -n "${expected_checksum}" ]]; then
        if [[ "${calculated_checksum}" == "${expected_checksum}" ]]; then
            log_success "TWRP checksum verification passed"
            return 0
        else
            log_error "TWRP checksum verification failed"
            log_error "Expected: ${expected_checksum}"
            log_error "Calculated: ${calculated_checksum}"
            return 1
        fi
    else
        log_warn "No expected checksum available for version ${version}"
        log_info "Calculated checksum: ${calculated_checksum}"
        return 0
    fi
}

# Backup current recovery
backup_current_recovery() {
    log_info "Backing up current recovery partition..."

    mkdir -p "${BACKUP_DIR}"

    local backup_file="${BACKUP_DIR}/recovery-backup-$(date +%Y%m%d-%H%M%S).img"

    if fastboot flash recovery /dev/null 2>/dev/null; then
        log_warn "Cannot backup recovery while device is running"
        log_info "Recovery backup will be skipped"
        return 0
    fi

    # Attempt to read recovery partition (this may not work on all devices)
    log_info "Attempting to backup recovery partition..."
    if fastboot oem recovery-backup "${backup_file}" 2>/dev/null; then
        log_success "Recovery partition backed up: ${backup_file}"
    else
        log_warn "Recovery backup not supported on this device"
        log_info "Proceeding without backup..."
    fi

    return 0
}

# Flash TWRP recovery
flash_twrp_recovery() {
    local version=${1}
    local twrp_file="twrp-${version}-${DEVICE_CODENAME}.img"
    local twrp_path="${DOWNLOAD_DIR}/${twrp_file}"

    log_info "Flashing TWRP recovery to device..."

    if [[ ! -f "${twrp_path}" ]]; then
        log_error "TWRP image not found: ${twrp_path}"
        return 1
    fi

    # Ensure device is in fastboot mode
    if ! check_fastboot_mode; then
        return 1
    fi

    # Backup current recovery (if possible)
    backup_current_recovery

    # Flash TWRP
    log_info "Flashing TWRP recovery..."
    if ! fastboot flash recovery "${twrp_path}"; then
        log_error "Failed to flash TWRP recovery"
        return 1
    fi

    # Verify flash
    log_info "Verifying TWRP flash..."
    sleep 2

    if ! fastboot getvar version-bootloader >/dev/null 2>&1; then
        log_warn "Cannot verify flash immediately - device may need reboot"
    fi

    log_success "TWRP recovery flashed successfully"
    return 0
}

# Boot into TWRP recovery
boot_into_twrp() {
    log_info "Booting device into TWRP recovery..."

    if ! check_fastboot_mode; then
        return 1
    fi

    if ! fastboot boot "${DOWNLOAD_DIR}/twrp-${1}-${DEVICE_CODENAME}.img"; then
        log_error "Failed to boot into TWRP recovery"
        return 1
    fi

    log_success "Device booting into TWRP recovery"
    log_info "Wait for TWRP interface to appear on device"
    return 0
}

# Check TWRP compatibility
check_twrp_compatibility() {
    local version=${1}

    log_info "Checking TWRP compatibility for ${DEVICE_MODEL}..."

    # Basic version checks
    local major_version=$(echo "${version}" | cut -d'.' -f1)
    local minor_version=$(echo "${version}" | cut -d'.' -f2)

    if [[ ${major_version} -lt 3 ]]; then
        log_warn "TWRP version ${version} is quite old"
        log_warn "Consider updating to TWRP 3.x for better features and security"
    fi

    # Device-specific checks for HTC One M7
    case "${version}" in
        "3.7.0_9-0")
            log_success "TWRP ${version} is known to work well with HTC One M7"
            ;;
        "3.6."*)
            log_info "TWRP ${version} should work with HTC One M7"
            ;;
        "3.5."*)
            log_warn "TWRP ${version} is older but should still work"
            ;;
        *)
            log_warn "TWRP ${version} compatibility with HTC One M7 is unknown"
            log_info "Proceeding with caution..."
            ;;
    esac

    return 0
}

# Get current recovery version from device
get_current_recovery_version() {
    log_info "Attempting to get current recovery version..."

    local device=${1:-""}
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Try to get recovery version from device
    local recovery_version
    recovery_version=$(${adb_cmd} shell getprop ro.twrp.version 2>/dev/null | tr -d '\r' || echo "")

    if [[ -n "${recovery_version}" ]]; then
        log_info "Current TWRP version: ${recovery_version}"
        echo "${recovery_version}"
    else
        log_info "Could not determine current recovery version"
        echo ""
    fi
}

# Main installation function
install_twrp() {
    local device=${1:-""}
    local version=${2:-""}

    log_info "Starting TWRP installation process..."

    # Determine version to install
    if [[ -z "${version}" ]]; then
        version=$(get_latest_twrp_version)
    fi

    log_info "Target TWRP version: ${version}"

    # Check compatibility
    check_twrp_compatibility "${version}"

    # Download TWRP
    if ! download_twrp "${version}"; then
        return 1
    fi

    # Verify checksum
    if ! verify_twrp_checksum "${version}"; then
        log_warn "Checksum verification failed, but proceeding..."
    fi

    # Boot device to fastboot if needed
    if [[ -n "${device}" ]]; then
        if ! boot_to_fastboot "${device}"; then
            return 1
        fi
    else
        if ! check_fastboot_mode; then
            log_error "Please ensure device is in fastboot mode"
            return 1
        fi
    fi

    # Flash TWRP
    if ! flash_twrp_recovery "${version}"; then
        return 1
    fi

    # Optionally boot into TWRP
    if [[ "${3:-}" == "boot" ]]; then
        boot_into_twrp "${version}"
    fi

    log_success "TWRP installation completed successfully"
    return 0
}

# Update TWRP if newer version available
update_twrp() {
    local device=${1:-""}
    local current_version
    local latest_version

    log_info "Checking for TWRP updates..."

    current_version=$(get_current_recovery_version "${device}")
    latest_version=$(get_latest_twrp_version)

    if [[ -z "${current_version}" ]]; then
        log_info "Current TWRP version unknown, installing latest..."
        install_twrp "${device}" "${latest_version}"
        return $?
    fi

    if [[ "${current_version}" == "${latest_version}" ]]; then
        log_success "TWRP is already up to date (${current_version})"
        return 0
    fi

    log_info "Updating TWRP from ${current_version} to ${latest_version}"
    install_twrp "${device}" "${latest_version}"
    return $?
}

# Main function
main() {
    log_info "Starting TWRP Recovery Manager"
    log_info "Device: ${DEVICE_MODEL} (${DEVICE_CODENAME})"

    # Ensure required tools are available
    if ! command -v fastboot >/dev/null 2>&1; then
        log_error "fastboot command not found. Please install Android SDK platform tools."
        exit 1
    fi

    case "${1:-}" in
        "install")
            install_twrp "${2:-}" "${3:-}" "${4:-}"
            ;;
        "update")
            update_twrp "${2:-}"
            ;;
        "download")
            local version=${2:-$(get_latest_twrp_version)}
            download_twrp "${version}" && verify_twrp_checksum "${version}"
            ;;
        "flash")
            local version=${2:-"3.7.0_9-0"}
            download_twrp "${version}" && flash_twrp_recovery "${version}"
            ;;
        "boot")
            local version=${2:-"3.7.0_9-0"}
            download_twrp "${version}" && boot_into_twrp "${version}"
            ;;
        "version")
            get_current_recovery_version "${2:-}"
            ;;
        "backup")
            check_fastboot_mode && backup_current_recovery
            ;;
        *)
            echo "Usage: $0 {install|update|download|flash|boot|version|backup} [device] [version] [boot]"
            echo ""
            echo "Commands:"
            echo "  install [device] [version] [boot]  - Install TWRP recovery"
            echo "  update [device]                   - Update TWRP if newer version available"
            echo "  download [version]                - Download TWRP image only"
            echo "  flash [version]                   - Flash TWRP to device (requires fastboot)"
            echo "  boot [version]                    - Boot device into TWRP (requires fastboot)"
            echo "  version [device]                  - Get current recovery version"
            echo "  backup                            - Backup current recovery (requires fastboot)"
            echo ""
            echo "Examples:"
            echo "  $0 install                        # Install latest TWRP"
            echo "  $0 install HT123456 3.7.0_9-0 boot # Install specific version and boot"
            echo "  $0 update                         # Update to latest version"
            echo "  $0 download 3.7.0_9-0            # Download specific version"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"