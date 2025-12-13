#!/bin/bash

# Android Device Setup - Environment Verification Script
# Automates Ubuntu 24.04 environment preparation and verification for LineageOS/Magisk installation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/environment-verification.log"
REPORT_FILE="${WORK_DIR}/environment-report.txt"

# Required packages
REQUIRED_PACKAGES=(
    "adb"
    "fastboot"
    "wget"
    "curl"
    "unzip"
    "python3"
    "python3-pip"
    "git"
    "usbutils"
    "udev"
)

# Android tools minimum versions
declare -A MIN_VERSIONS=(
    ["adb"]="1.0.41"
    ["fastboot"]="1.0.41"
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

# Version comparison function
version_compare() {
    local version1=$1
    local version2=$2

    if [[ $version1 == $version2 ]]; then
        return 0
    fi

    local IFS=.
    local i ver1=($version1) ver2=($version2)

    # Fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
        ver1[i]=0
    done

    # Fill empty fields in ver2 with zeros
    for ((i=${#ver2[@]}; i<${#ver1[@]}; i++)); do
        ver2[i]=0
    done

    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]} ]]; then
            # Fill empty fields with zero
            ver2[i]=0
        fi

        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 1
        fi

        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 2
        fi
    done

    return 0
}

# Check if running on Ubuntu
check_os() {
    log_info "Checking operating system..."

    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine OS. /etc/os-release not found."
        return 1
    fi

    local os_name=$(grep '^NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
    local os_version=$(grep '^VERSION_ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')

    if [[ "${os_name}" != "Ubuntu" ]]; then
        log_error "This script is designed for Ubuntu. Current OS: ${os_name}"
        return 1
    fi

    if [[ "${os_version}" != "24.04" ]]; then
        log_warn "This script is optimized for Ubuntu 24.04. Current version: ${os_version}"
        log_warn "Proceeding anyway, but some features may not work correctly."
    else
        log_success "Ubuntu ${os_version} detected"
    fi

    return 0
}

# Check and install required packages
check_packages() {
    log_info "Checking required packages..."

    local missing_packages=()
    local outdated_packages=()

    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! dpkg -l "${package}" >/dev/null 2>&1; then
            missing_packages+=("${package}")
        fi
    done

    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        log_warn "Missing packages: ${missing_packages[*]}"

        log_info "Installing missing packages..."
        if ! sudo apt update; then
            log_error "Failed to update package lists"
            return 1
        fi

        if ! sudo apt install -y "${missing_packages[@]}"; then
            log_error "Failed to install required packages"
            return 1
        fi

        log_success "Required packages installed successfully"
    else
        log_success "All required packages are installed"
    fi

    return 0
}

# Verify Android tools versions
verify_android_tools() {
    log_info "Verifying Android tools versions..."

    # Check ADB
    if command -v adb >/dev/null 2>&1; then
        local adb_version=$(adb version | grep -oP 'version \K[\d.]+' || echo "unknown")
        log_info "ADB version: ${adb_version}"

        if version_compare "${adb_version}" "${MIN_VERSIONS['adb']}"; then
            log_success "ADB version meets minimum requirements"
        else
            log_warn "ADB version ${adb_version} is below minimum ${MIN_VERSIONS['adb']}"
            outdated_packages+=("adb")
        fi
    else
        log_error "ADB not found in PATH"
        return 1
    fi

    # Check Fastboot
    if command -v fastboot >/dev/null 2>&1; then
        local fastboot_version=$(fastboot --version | grep -oP 'version \K[\d.]+' || echo "unknown")
        log_info "Fastboot version: ${fastboot_version}"

        if version_compare "${fastboot_version}" "${MIN_VERSIONS['fastboot']}"; then
            log_success "Fastboot version meets minimum requirements"
        else
            log_warn "Fastboot version ${fastboot_version} is below minimum ${MIN_VERSIONS['fastboot']}"
            outdated_packages+=("fastboot")
        fi
    else
        log_error "Fastboot not found in PATH"
        return 1
    fi

    if [[ ${#outdated_packages[@]} -gt 0 ]]; then
        log_warn "Some Android tools may need updating: ${outdated_packages[*]}"
        log_warn "Consider installing Android SDK Platform Tools for latest versions"
    fi

    return 0
}

# Setup udev rules for Android devices
setup_udev_rules() {
    log_info "Setting up udev rules for Android device access..."

    local udev_file="/etc/udev/rules.d/51-android.rules"

    if [[ -f "${udev_file}" ]]; then
        log_info "Android udev rules already exist"
        return 0
    fi

    log_info "Creating Android udev rules..."

    # Create udev rules content
    local udev_content="# Android devices
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0bb4\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"18d1\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"04e8\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"22b8\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0e79\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"2717\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"2a70\", MODE=\"0666\", GROUP=\"plugdev\"
# HTC One M7 (and other HTC devices)
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0bb4\", ATTR{idProduct}==\"0dff\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0bb4\", ATTR{idProduct}==\"0f87\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0bb4\", ATTR{idProduct}==\"0f91\", MODE=\"0666\", GROUP=\"plugdev\"
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0bb4\", ATTR{idProduct}==\"0f95\", MODE=\"0666\", GROUP=\"plugdev\""

    if ! echo "${udev_content}" | sudo tee "${udev_file}" >/dev/null; then
        log_error "Failed to create udev rules file"
        return 1
    fi

    # Reload udev rules
    if ! sudo udevadm control --reload-rules; then
        log_warn "Failed to reload udev rules"
    fi

    if ! sudo udevadm trigger; then
        log_warn "Failed to trigger udev rules"
    fi

    log_success "Android udev rules configured"
    return 0
}

# Create working directory structure
create_work_directory() {
    log_info "Creating working directory structure..."

    # Create main work directory
    if [[ ! -d "${WORK_DIR}" ]]; then
        if ! mkdir -p "${WORK_DIR}"; then
            log_error "Failed to create work directory: ${WORK_DIR}"
            return 1
        fi
        log_success "Created work directory: ${WORK_DIR}"
    else
        log_info "Work directory already exists: ${WORK_DIR}"
    fi

    # Create subdirectories
    local subdirs=("downloads" "backups" "logs" "temp" "reports")

    for subdir in "${subdirs[@]}"; do
        local full_path="${WORK_DIR}/${subdir}"
        if [[ ! -d "${full_path}" ]]; then
            if ! mkdir -p "${full_path}"; then
                log_error "Failed to create subdirectory: ${full_path}"
                return 1
            fi
        fi
    done

    log_success "Working directory structure created"
    return 0
}

# Check disk space
check_disk_space() {
    log_info "Checking available disk space..."

    local required_space_gb=10
    local available_space=$(df "${WORK_DIR}" | tail -1 | awk '{print int($4/1024/1024)}') # GB

    if [[ ${available_space} -lt ${required_space_gb} ]]; then
        log_error "Insufficient disk space. Required: ${required_space_gb}GB, Available: ${available_space}GB"
        return 1
    fi

    log_success "Sufficient disk space available: ${available_space}GB"
    return 0
}

# Generate environment report
generate_report() {
    log_info "Generating environment verification report..."

    {
        echo "Android Device Setup - Environment Verification Report"
        echo "Generated on: $(date)"
        echo "Host: $(hostname)"
        echo "User: $(whoami)"
        echo ""

        echo "=== SYSTEM INFORMATION ==="
        echo "OS: $(lsb_release -d | cut -f2)"
        echo "Kernel: $(uname -r)"
        echo "Architecture: $(uname -m)"
        echo ""

        echo "=== INSTALLED PACKAGES ==="
        for package in "${REQUIRED_PACKAGES[@]}"; do
            if dpkg -l "${package}" >/dev/null 2>&1; then
                local version=$(dpkg -l "${package}" | grep "^ii" | awk '{print $3}')
                echo "✓ ${package}: ${version}"
            else
                echo "✗ ${package}: NOT INSTALLED"
            fi
        done
        echo ""

        echo "=== ANDROID TOOLS ==="
        if command -v adb >/dev/null 2>&1; then
            echo "ADB: $(adb version | head -1)"
        else
            echo "ADB: NOT FOUND"
        fi

        if command -v fastboot >/dev/null 2>&1; then
            echo "Fastboot: $(fastboot --version | head -1)"
        else
            echo "Fastboot: NOT FOUND"
        fi
        echo ""

        echo "=== UDEV RULES ==="
        if [[ -f /etc/udev/rules.d/51-android.rules ]]; then
            echo "✓ Android udev rules configured"
        else
            echo "✗ Android udev rules not configured"
        fi
        echo ""

        echo "=== WORKING DIRECTORY ==="
        if [[ -d "${WORK_DIR}" ]]; then
            echo "✓ Work directory: ${WORK_DIR}"
            echo "Available space: $(df -h "${WORK_DIR}" | tail -1 | awk '{print $4}')"
        else
            echo "✗ Work directory not created"
        fi
        echo ""

        echo "=== USB DEVICES ==="
        lsusb | head -10
        echo ""

        echo "=== RECOMMENDATIONS ==="
        if ! groups | grep -q plugdev; then
            echo "- Add user to plugdev group: sudo usermod -aG plugdev \$USER"
            echo "- Log out and back in for group changes to take effect"
        fi

        echo "- Ensure USB debugging is enabled on Android device"
        echo "- Test device connection with: adb devices"
        echo ""

    } > "${REPORT_FILE}"

    log_success "Environment report generated: ${REPORT_FILE}"
    return 0
}

# Main function
main() {
    # Create workspace directory first before any logging
    mkdir -p "${WORK_DIR}"

    log_info "Starting Android Device Setup - Environment Verification"
    log_info "Working directory: ${WORK_DIR}"

    local exit_code=0

    # Run verification steps
    check_os || exit_code=1
    check_disk_space || exit_code=1
    check_packages || exit_code=1
    verify_android_tools || exit_code=1
    setup_udev_rules || exit_code=1
    create_work_directory || exit_code=1
    generate_report || exit_code=1

    if [[ ${exit_code} -eq 0 ]]; then
        log_success "Environment verification completed successfully"
        log_info "Review the report at: ${REPORT_FILE}"
        echo ""
        echo "Next steps:"
        echo "1. Add user to plugdev group if not already: sudo usermod -aG plugdev \$USER"
        echo "2. Log out and back in for group changes to take effect"
        echo "3. Connect HTC One M7 device and run device verification"
    else
        log_error "Environment verification failed. Check logs at: ${LOG_FILE}"
        exit 1
    fi
}

# Run main function
main "$@"