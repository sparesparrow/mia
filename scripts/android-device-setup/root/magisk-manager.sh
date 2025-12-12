#!/bin/bash

# Android Device Setup - Magisk Manager
# Automated Magisk root installation and management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
MAGISK_DIR="${DOWNLOAD_DIR}/magisk"
LOG_FILE="${WORK_DIR}/magisk-manager.log"

# Magisk configuration
MAGISK_REPO="topjohnwu/Magisk"
MAGISK_API_URL="https://api.github.com/repos/${MAGISK_REPO}/releases/latest"
MAGISK_DOWNLOAD_URL="https://github.com/${MAGISK_REPO}/releases/download"

# SafetyNet configuration
SAFETYNET_CHECK_ENABLED=true

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

# Get latest Magisk release information
get_latest_magisk_release() {
    log_info "Getting latest Magisk release information..."

    if ! command -v curl >/dev/null 2>&1; then
        log_error "curl command not found. Cannot fetch Magisk release info."
        return 1
    fi

    local api_response
    api_response=$(curl -s "${MAGISK_API_URL}" 2>/dev/null)

    if [[ -z "${api_response}" ]]; then
        log_error "Failed to fetch Magisk release information"
        return 1
    fi

    # Extract version tag
    local version_tag
    version_tag=$(echo "${api_response}" | grep -o '"tag_name": "[^"]*"' | cut -d'"' -f4)

    if [[ -z "${version_tag}" ]]; then
        log_error "Could not extract version tag from API response"
        return 1
    fi

    # Extract release notes
    local release_notes
    release_notes=$(echo "${api_response}" | grep -o '"body": "[^"]*"' | cut -d'"' -f4 | head -1)

    log_info "Latest Magisk version: ${version_tag}"
    if [[ -n "${release_notes}" ]]; then
        log_info "Release notes: ${release_notes:0:100}..."
    fi

    echo "${version_tag}"
}

# Download Magisk ZIP
download_magisk_zip() {
    local version=${1}

    log_info "Downloading Magisk ${version}..."

    mkdir -p "${MAGISK_DIR}"

    local zip_filename="Magisk-${version}.zip"
    local zip_path="${MAGISK_DIR}/${zip_filename}"

    # Check if file already exists
    if [[ -f "${zip_path}" ]]; then
        log_info "Magisk ZIP already exists: ${zip_path}"
        return 0
    fi

    local download_url="${MAGISK_DOWNLOAD_URL}/${version}/${zip_filename}"

    log_info "Download URL: ${download_url}"

    if command -v curl >/dev/null 2>&1; then
        if curl -L -o "${zip_path}" "${download_url}"; then
            log_success "Magisk ZIP downloaded successfully"
        else
            log_error "Failed to download Magisk ZIP"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O "${zip_path}" "${download_url}"; then
            log_success "Magisk ZIP downloaded successfully"
        else
            log_error "Failed to download Magisk ZIP"
            return 1
        fi
    else
        log_error "Neither curl nor wget available for download"
        return 1
    fi

    # Verify download
    if [[ ! -f "${zip_path}" ]] || [[ ! -s "${zip_path}" ]]; then
        log_error "Downloaded file is empty or missing"
        rm -f "${zip_path}"
        return 1
    fi

    return 0
}

# Download Magisk Manager APK
download_magisk_manager() {
    local version=${1}

    log_info "Downloading Magisk Manager APK ${version}..."

    local apk_filename="MagiskManager-${version}.apk"
    local apk_path="${MAGISK_DIR}/${apk_filename}"

    # Check if file already exists
    if [[ -f "${apk_path}" ]]; then
        log_info "Magisk Manager APK already exists: ${apk_path}"
        return 0
    fi

    local download_url="${MAGISK_DOWNLOAD_URL}/${version}/${apk_filename}"

    log_info "Download URL: ${download_url}"

    if command -v curl >/dev/null 2>&1; then
        if curl -L -o "${apk_path}" "${download_url}"; then
            log_success "Magisk Manager APK downloaded successfully"
        else
            log_error "Failed to download Magisk Manager APK"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O "${apk_path}" "${download_url}"; then
            log_success "Magisk Manager APK downloaded successfully"
        else
            log_error "Failed to download Magisk Manager APK"
            return 1
        fi
    else
        log_error "Neither curl nor wget available for download"
        return 1
    fi

    # Verify download
    if [[ ! -f "${apk_path}" ]] || [[ ! -s "${apk_path}" ]]; then
        log_error "Downloaded APK file is empty or missing"
        rm -f "${apk_path}"
        return 1
    fi

    return 0
}

# Transfer Magisk files to device
transfer_magisk_to_device() {
    local device=${1}
    local version=${2}

    log_info "Transferring Magisk files to device..."

    local zip_file="${MAGISK_DIR}/Magisk-${version}.zip"
    local apk_file="${MAGISK_DIR}/MagiskManager-${version}.apk"

    if [[ ! -f "${zip_file}" ]]; then
        log_error "Magisk ZIP not found: ${zip_file}"
        return 1
    fi

    # Use file-transfer.sh script for reliable transfer
    local transfer_script="${SCRIPT_DIR}/../rom/file-transfer.sh"

    if [[ ! -x "${transfer_script}" ]]; then
        log_error "File transfer script not found: ${transfer_script}"
        return 1
    fi

    # Transfer Magisk ZIP
    log_info "Transferring Magisk ZIP..."
    if ! "${transfer_script}" transfer "${device}" "${zip_file}"; then
        log_error "Failed to transfer Magisk ZIP"
        return 1
    fi

    # Transfer Magisk Manager APK if it exists
    if [[ -f "${apk_file}" ]]; then
        log_info "Transferring Magisk Manager APK..."
        if ! "${transfer_script}" transfer "${device}" "${apk_file}"; then
            log_warn "Failed to transfer Magisk Manager APK (optional)"
        fi
    fi

    log_success "Magisk files transferred to device"
    return 0
}

# Install Magisk in recovery mode
install_magisk_recovery() {
    local device=${1}
    local version=${2}

    log_info "Installing Magisk ${version} in recovery mode..."

    # Ensure device is in recovery mode
    local recovery_script="${SCRIPT_DIR}/../recovery/verify-recovery.sh"
    if ! "${recovery_script}" boot "${device}" >/dev/null 2>&1; then
        log_error "Cannot ensure device is in recovery mode"
        return 1
    fi

    # Find Magisk ZIP on device
    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local magisk_path
    magisk_path=$(${adb_cmd} shell find /sdcard -name "Magisk-*.zip" 2>/dev/null | head -1)

    if [[ -z "${magisk_path}" ]]; then
        log_error "Magisk ZIP not found on device"
        return 1
    fi

    log_info "Found Magisk ZIP: ${magisk_path}"

    # Use flash-operations.sh to install ZIP
    local flash_script="${SCRIPT_DIR}/../installation/flash-operations.sh"

    if [[ ! -x "${flash_script}" ]]; then
        log_error "Flash operations script not found: ${flash_script}"
        return 1
    fi

    log_info "Installing Magisk via recovery..."
    if ! "${flash_script}" flash-zip "${device}" "${magisk_path}"; then
        log_error "Magisk installation failed"
        return 1
    fi

    log_success "Magisk installed successfully in recovery"
    return 0
}

# Install Magisk Manager APK
install_magisk_manager() {
    local device=${1}
    local version=${2}

    log_info "Installing Magisk Manager APK..."

    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local apk_path
    apk_path=$(${adb_cmd} shell find /sdcard -name "MagiskManager-*.apk" 2>/dev/null | head -1)

    if [[ -z "${apk_path}" ]]; then
        log_warn "Magisk Manager APK not found on device - skipping installation"
        return 0
    fi

    log_info "Installing Magisk Manager APK: ${apk_path}"

    # Install APK
    if ${adb_cmd} install "${apk_path}"; then
        log_success "Magisk Manager APK installed successfully"
        return 0
    else
        log_error "Failed to install Magisk Manager APK"
        return 1
    fi
}

# Check SafetyNet status
check_safetynet() {
    local device=${1}

    if [[ "${SAFETYNET_CHECK_ENABLED}" != "true" ]]; then
        log_info "SafetyNet check disabled"
        return 0
    fi

    log_info "Checking SafetyNet status..."

    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    # Try to use SafetyNet test (requires device to have Magisk Manager)
    local safetynet_result
    safetynet_result=$(${adb_cmd} shell "su -c 'pm list packages | grep -q safetynet && echo \"SafetyNet available\" || echo \"SafetyNet not available\"'" 2>/dev/null || echo "SafetyNet check failed")

    if [[ "${safetynet_result}" == "SafetyNet available" ]]; then
        log_success "SafetyNet package found"
    elif [[ "${safetynet_result}" == "SafetyNet check failed" ]]; then
        log_warn "Could not check SafetyNet status (may require root access)"
    else
        log_info "SafetyNet status: ${safetynet_result}"
    fi

    return 0
}

# Verify Magisk installation
verify_magisk_installation() {
    local device=${1}

    log_info "Verifying Magisk installation..."

    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    local verification_passed=0
    local total_checks=4

    # Check 1: Magisk binary exists
    if ${adb_cmd} shell "which magisk" >/dev/null 2>&1; then
        log_success "✓ Magisk binary found"
        ((verification_passed++))
    else
        log_error "✗ Magisk binary not found"
    fi

    # Check 2: Magisk version
    local magisk_version
    magisk_version=$(${adb_cmd} shell "su -c 'magisk -V'" 2>/dev/null || echo "")
    if [[ -n "${magisk_version}" ]]; then
        log_success "✓ Magisk version: ${magisk_version}"
        ((verification_passed++))
    else
        log_error "✗ Could not get Magisk version"
    fi

    # Check 3: Root access
    if ${adb_cmd} shell "su -c 'echo root_test'" >/dev/null 2>&1; then
        log_success "✓ Root access available"
        ((verification_passed++))
    else
        log_error "✗ Root access not available"
    fi

    # Check 4: Magisk Manager package
    if ${adb_cmd} shell "pm list packages | grep -q magisk" >/dev/null 2>&1; then
        log_success "✓ Magisk Manager installed"
        ((verification_passed++))
    else
        log_warn "⚠ Magisk Manager not found (may not be critical)"
    fi

    log_info "Verification: ${verification_passed}/${total_checks} checks passed"

    if [[ ${verification_passed} -ge 3 ]]; then
        log_success "Magisk installation verification passed"
        return 0
    else
        log_error "Magisk installation verification failed"
        return 1
    fi
}

# Reboot device after Magisk installation
reboot_after_installation() {
    local device=${1}

    log_info "Rebooting device after Magisk installation..."

    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    if ${adb_cmd} reboot; then
        log_success "Device rebooting..."

        # Wait for device to come back online
        log_info "Waiting for device to reboot (this may take several minutes)..."
        sleep 60

        # Try to establish connection
        local attempts=0
        while [[ ${attempts} -lt 12 ]]; do
            if ${adb_cmd} shell echo "device_ready" >/dev/null 2>&1; then
                log_success "Device rebooted successfully"
                return 0
            fi
            sleep 10
            ((attempts++))
        done

        log_error "Device did not come back online after reboot"
        return 1
    else
        log_error "Failed to initiate reboot"
        return 1
    fi
}

# Get Magisk status
get_magisk_status() {
    local device=${1}

    log_info "Getting Magisk status..."

    local adb_cmd="adb"
    if [[ -n "${device}" ]]; then
        adb_cmd="${adb_cmd} -s ${device}"
    fi

    echo "=== MAGISK STATUS ==="

    # Magisk version
    local magisk_ver
    magisk_ver=$(${adb_cmd} shell "su -c 'magisk -V'" 2>/dev/null || echo "Unknown")
    echo "Magisk Version: ${magisk_ver}"

    # Root status
    if ${adb_cmd} shell "su -c 'echo root_check'" >/dev/null 2>&1; then
        echo "Root Status: ✓ Available"
    else
        echo "Root Status: ✗ Not Available"
    fi

    # Magisk Manager
    if ${adb_cmd} shell "pm list packages | grep -q magisk" >/dev/null 2>&1; then
        echo "Magisk Manager: ✓ Installed"
    else
        echo "Magisk Manager: ✗ Not Installed"
    fi

    # Magisk modules
    local module_count
    module_count=$(${adb_cmd} shell "su -c 'ls /data/adb/modules | wc -l'" 2>/dev/null || echo "0")
    echo "Magisk Modules: ${module_count}"

    echo ""
}

# Install Magisk (complete process)
install_magisk() {
    local device=${1}
    local version=${2:-"latest"}

    log_info "Starting Magisk installation process..."

    # Get version
    if [[ "${version}" == "latest" ]]; then
        version=$(get_latest_magisk_release)
        if [[ -z "${version}" ]]; then
            log_error "Could not determine latest Magisk version"
            return 1
        fi
    fi

    log_info "Installing Magisk version: ${version}"

    # Download Magisk files
    if ! download_magisk_zip "${version}"; then
        return 1
    fi

    if ! download_magisk_manager "${version}"; then
        log_warn "Magisk Manager download failed, continuing without it"
    fi

    # Transfer files to device
    if ! transfer_magisk_to_device "${device}" "${version}"; then
        return 1
    fi

    # Install Magisk in recovery
    if ! install_magisk_recovery "${device}" "${version}"; then
        return 1
    fi

    # Reboot device
    if ! reboot_after_installation "${device}"; then
        return 1
    fi

    # Install Magisk Manager
    if ! install_magisk_manager "${device}" "${version}"; then
        log_warn "Magisk Manager installation failed, but Magisk may still work"
    fi

    # Verify installation
    if ! verify_magisk_installation "${device}"; then
        return 1
    fi

    # Check SafetyNet
    check_safetynet "${device}"

    log_success "Magisk installation completed successfully!"
    return 0
}

# Main function
main() {
    log_info "Starting Magisk Manager"

    case "${1:-}" in
        "install")
            local device=${2:-""}
            local version=${3:-"latest"}
            install_magisk "${device}" "${version}"
            ;;
        "download")
            local version=${2:-"latest"}
            if [[ "${version}" == "latest" ]]; then
                version=$(get_latest_magisk_release)
            fi
            download_magisk_zip "${version}" && download_magisk_manager "${version}"
            ;;
        "transfer")
            local device=${2}
            local version=${3:-"latest"}
            if [[ "${version}" == "latest" ]]; then
                version=$(get_latest_magisk_release)
            fi
            download_magisk_zip "${version}" && download_magisk_manager "${version}" && transfer_magisk_to_device "${device}" "${version}"
            ;;
        "flash")
            local device=${2}
            local version=${3:-"latest"}
            download_magisk_zip "${version}" && transfer_magisk_to_device "${device}" "${version}" && install_magisk_recovery "${device}" "${version}"
            ;;
        "verify")
            local device=${2:-""}
            verify_magisk_installation "${device}"
            ;;
        "status")
            local device=${2:-""}
            get_magisk_status "${device}"
            ;;
        "reboot")
            local device=${2:-""}
            reboot_after_installation "${device}"
            ;;
        "safetynet")
            local device=${2:-""}
            check_safetynet "${device}"
            ;;
        "version")
            get_latest_magisk_release
            ;;
        *)
            echo "Usage: $0 {install|download|transfer|flash|verify|status|reboot|safetynet|version} [device] [version]"
            echo ""
            echo "Commands:"
            echo "  install [device] [version]  - Complete Magisk installation"
            echo "  download [version]          - Download Magisk files only"
            echo "  transfer [device] [version] - Transfer Magisk files to device"
            echo "  flash [device] [version]    - Install Magisk in recovery mode"
            echo "  verify [device]             - Verify Magisk installation"
            echo "  status [device]             - Show Magisk status"
            echo "  reboot [device]             - Reboot device after installation"
            echo "  safetynet [device]          - Check SafetyNet compatibility"
            echo "  version                     - Get latest Magisk version"
            echo ""
            echo "Examples:"
            echo "  $0 install HT123456         # Install latest Magisk"
            echo "  $0 install HT123456 v25.2   # Install specific version"
            echo "  $0 status                   # Check Magisk status"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"