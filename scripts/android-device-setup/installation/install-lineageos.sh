#!/bin/bash

# Android Device Setup - LineageOS Installation Orchestrator
# Master script coordinating the entire LineageOS 14.1 + Magisk installation process

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
LOG_FILE="${WORK_DIR}/installation.log"
CHECKPOINT_FILE="${WORK_DIR}/installation-checkpoint.txt"
CONFIG_FILE="${WORK_DIR}/installation-config.txt"

# Installation phases
PHASES=(
    "environment_check"
    "device_validation"
    "recovery_installation"
    "recovery_verification"
    "rom_download"
    "file_transfer"
    "device_wipe"
    "rom_flash"
    "gapps_flash"
    "root_installation"
    "root_verification"
    "system_boot"
    "post_install_config"
    "final_verification"
)

# Default configuration
DEFAULT_CONFIG=(
    "DEVICE_SERIAL="
    "INSTALL_GAPPS=true"
    "GAPPS_VARIANT=nano"
    "INSTALL_MAGISK=true"
    "BACKUP_BEFORE_INSTALL=true"
    "SKIP_DEVICE_VALIDATION=false"
    "FORCE_DOWNLOADS=false"
    "INTERACTIVE_MODE=true"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Installation state
CURRENT_PHASE=""
START_TIME=""
INSTALL_SUCCESS=false

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

log_phase() {
    echo -e "${CYAN}[PHASE]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# Progress display
show_progress() {
    local current=$1
    local total=$2
    local phase_name=$3

    local percentage=$((current * 100 / total))
    local progress_bar=""
    local filled=$((percentage / 5))
    local empty=$((20 - filled))

    for ((i = 0; i < filled; i++)); do
        progress_bar="${progress_bar}█"
    done

    for ((i = 0; i < empty; i++)); do
        progress_bar="${progress_bar}░"
    done

    echo -ne "\r${CYAN}[PROGRESS]${NC} ${progress_bar} ${percentage}% - ${phase_name}"
}

# Save checkpoint
save_checkpoint() {
    local phase=$1
    local status=${2:-"completed"}

    echo "PHASE=${phase}" > "${CHECKPOINT_FILE}"
    echo "STATUS=${status}" >> "${CHECKPOINT_FILE}"
    echo "TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')" >> "${CHECKPOINT_FILE}"
    echo "DEVICE_SERIAL=${DEVICE_SERIAL:-}" >> "${CHECKPOINT_FILE}"
}

# Load checkpoint
load_checkpoint() {
    if [[ -f "${CHECKPOINT_FILE}" ]]; then
        source "${CHECKPOINT_FILE}"
        return 0
    fi
    return 1
}

# Save configuration
save_config() {
    log_info "Saving installation configuration..."

    {
        echo "# LineageOS Installation Configuration"
        echo "# Generated on $(date)"
        echo ""

        for config in "${DEFAULT_CONFIG[@]}"; do
            local key=$(echo "${config}" | cut -d'=' -f1)
            local value=${!key:-$(echo "${config}" | cut -d'=' -f2)}
            echo "${key}=${value}"
        done
    } > "${CONFIG_FILE}"

    log_success "Configuration saved to ${CONFIG_FILE}"
}

# Load configuration
load_config() {
    if [[ -f "${CONFIG_FILE}" ]]; then
        log_info "Loading installation configuration..."
        source "${CONFIG_FILE}"
        return 0
    fi

    # Use defaults
    for config in "${DEFAULT_CONFIG[@]}"; do
        local key=$(echo "${config}" | cut -d'=' -f1)
        local value=$(echo "${config}" | cut -d'=' -f2)
        declare -g "${key}=${value}"
    done

    return 1
}

# Interactive prompt
prompt_user() {
    local message=$1
    local default=${2:-""}

    if [[ "${INTERACTIVE_MODE}" != "true" ]]; then
        echo "${default}"
        return 0
    fi

    local prompt="${message}"
    if [[ -n "${default}" ]]; then
        prompt="${prompt} [${default}]: "
    else
        prompt="${prompt}: "
    fi

    read -r response
    echo "${response:-${default}}"
}

# Confirm critical operation
confirm_operation() {
    local message=$1
    local default=${2:-"n"}

    if [[ "${INTERACTIVE_MODE}" != "true" ]]; then
        return 0
    fi

    local prompt="${message} (y/N): "
    read -r response

    case "${response,,}" in
        "y"|"yes")
            return 0
            ;;
        "n"|"no"|"")
            return 1
            ;;
        *)
            log_warn "Please answer 'y' or 'n'"
            confirm_operation "${message}" "${default}"
            ;;
    esac
}

# Execute script with error handling
execute_script() {
    local script_path=$1
    shift
    local args=("$@")

    log_info "Executing: ${script_path} ${args[*]}"

    if [[ ! -x "${script_path}" ]]; then
        log_error "Script not found or not executable: ${script_path}"
        return 1
    fi

    if "${script_path}" "${args[@]}"; then
        log_success "Script executed successfully"
        return 0
    else
        log_error "Script execution failed"
        return 1
    fi
}

# Phase 1: Environment Check
phase_environment_check() {
    log_phase "Phase 1: Environment Check"
    save_checkpoint "environment_check" "in_progress"

    local script="${SCRIPT_DIR}/../environment/verify-environment.sh"

    if ! execute_script "${script}"; then
        log_error "Environment verification failed"
        return 1
    fi

    save_checkpoint "environment_check" "completed"
    return 0
}

# Phase 2: Device Validation
phase_device_validation() {
    log_phase "Phase 2: Device Validation"
    save_checkpoint "device_validation" "in_progress"

    # Detect device
    log_info "Detecting connected device..."
    DEVICE_SERIAL=$(adb devices | grep -v "List" | grep "device$" | head -1 | awk '{print $1}' || echo "")

    if [[ -z "${DEVICE_SERIAL}" ]]; then
        log_error "No device detected. Please connect HTC One M7 and ensure USB debugging is enabled."
        return 1
    fi

    log_info "Detected device: ${DEVICE_SERIAL}"

    local script="${SCRIPT_DIR}/../environment/device-manager.sh"

    if ! execute_script "${script}" validate "${DEVICE_SERIAL}"; then
        log_error "Device validation failed"
        return 1
    fi

    save_checkpoint "device_validation" "completed"
    return 0
}

# Phase 3: Recovery Installation
phase_recovery_installation() {
    log_phase "Phase 3: Recovery Installation"
    save_checkpoint "recovery_installation" "in_progress"

    local script="${SCRIPT_DIR}/../recovery/twrp-manager.sh"

    if ! execute_script "${script}" install "${DEVICE_SERIAL}"; then
        log_error "Recovery installation failed"
        return 1
    fi

    save_checkpoint "recovery_installation" "completed"
    return 0
}

# Phase 4: Recovery Verification
phase_recovery_verification() {
    log_phase "Phase 4: Recovery Verification"
    save_checkpoint "recovery_verification" "in_progress"

    local script="${SCRIPT_DIR}/../recovery/verify-recovery.sh"

    if ! execute_script "${script}" verify "${DEVICE_SERIAL}"; then
        log_error "Recovery verification failed"
        return 1
    fi

    save_checkpoint "recovery_verification" "completed"
    return 0
}

# Phase 5: ROM Download
phase_rom_download() {
    log_phase "Phase 5: ROM Download"
    save_checkpoint "rom_download" "in_progress"

    local script="${SCRIPT_DIR}/../rom/rom-manager.sh"

    # Download LineageOS
    if ! execute_script "${script}" download-rom; then
        log_error "ROM download failed"
        return 1
    fi

    # Download GApps if requested
    if [[ "${INSTALL_GAPPS}" == "true" ]]; then
        if ! execute_script "${script}" download-gapps "${GAPPS_VARIANT}"; then
            log_error "GApps download failed"
            return 1
        fi
    fi

    save_checkpoint "rom_download" "completed"
    return 0
}

# Phase 6: File Transfer
phase_file_transfer() {
    log_phase "Phase 6: File Transfer"
    save_checkpoint "file_transfer" "in_progress"

    local script="${SCRIPT_DIR}/../rom/file-transfer.sh"
    local rom_file
    local gapps_file

    # Find downloaded files
    rom_file=$(find "${WORK_DIR}/downloads/roms" -name "lineage*.zip" | head -1 || echo "")
    if [[ "${INSTALL_GAPPS}" == "true" ]]; then
        gapps_file=$(find "${WORK_DIR}/downloads/gapps" -name "*gapps*.zip" | head -1 || echo "")
    fi

    if [[ -z "${rom_file}" ]]; then
        log_error "No ROM file found for transfer"
        return 1
    fi

    # Transfer files to device
    local files_to_transfer=("${rom_file}")
    if [[ -n "${gapps_file}" ]]; then
        files_to_transfer+=("${gapps_file}")
    fi

    if ! execute_script "${script}" batch "${DEVICE_SERIAL}" "${files_to_transfer[@]}"; then
        log_error "File transfer failed"
        return 1
    fi

    save_checkpoint "file_transfer" "completed"
    return 0
}

# Phase 7: Device Wipe
phase_device_wipe() {
    log_phase "Phase 7: Device Wipe"
    save_checkpoint "device_wipe" "in_progress"

    if [[ "${BACKUP_BEFORE_INSTALL}" == "true" ]]; then
        log_info "Creating backup before wipe..."
        # Note: Backup functionality would be implemented in backup-manager.sh
        log_warn "Backup before wipe not yet implemented - proceeding with wipe"
    fi

    local script="${SCRIPT_DIR}/flash-operations.sh"

    if ! execute_script "${script}" wipe "${DEVICE_SERIAL}"; then
        log_error "Device wipe failed"
        return 1
    fi

    save_checkpoint "device_wipe" "completed"
    return 0
}

# Phase 8: ROM Flash
phase_rom_flash() {
    log_phase "Phase 8: ROM Flash"
    save_checkpoint "rom_flash" "in_progress"

    local script="${SCRIPT_DIR}/flash-operations.sh"

    if ! execute_script "${script}" flash-rom "${DEVICE_SERIAL}"; then
        log_error "ROM flash failed"
        return 1
    fi

    save_checkpoint "rom_flash" "completed"
    return 0
}

# Phase 9: GApps Flash
phase_gapps_flash() {
    log_phase "Phase 9: GApps Flash"
    save_checkpoint "gapps_flash" "in_progress"

    if [[ "${INSTALL_GAPPS}" != "true" ]]; then
        log_info "Skipping GApps installation"
        save_checkpoint "gapps_flash" "skipped"
        return 0
    fi

    local script="${SCRIPT_DIR}/flash-operations.sh"

    if ! execute_script "${script}" flash-gapps "${DEVICE_SERIAL}"; then
        log_error "GApps flash failed"
        return 1
    fi

    save_checkpoint "gapps_flash" "completed"
    return 0
}

# Phase 10: Root Installation
phase_root_installation() {
    log_phase "Phase 10: Root Installation"
    save_checkpoint "root_installation" "in_progress"

    if [[ "${INSTALL_MAGISK}" != "true" ]]; then
        log_info "Skipping Magisk installation"
        save_checkpoint "root_installation" "skipped"
        return 0
    fi

    local script="${SCRIPT_DIR}/../root/magisk-manager.sh"

    if ! execute_script "${script}" install "${DEVICE_SERIAL}"; then
        log_error "Root installation failed"
        return 1
    fi

    save_checkpoint "root_installation" "completed"
    return 0
}

# Phase 11: Root Verification
phase_root_verification() {
    log_phase "Phase 11: Root Verification"
    save_checkpoint "root_verification" "in_progress"

    if [[ "${INSTALL_MAGISK}" != "true" ]]; then
        log_info "Skipping root verification"
        save_checkpoint "root_verification" "skipped"
        return 0
    fi

    local script="${SCRIPT_DIR}/../root/verify-root.sh"

    if ! execute_script "${script}" verify "${DEVICE_SERIAL}"; then
        log_error "Root verification failed"
        return 1
    fi

    save_checkpoint "root_verification" "completed"
    return 0
}

# Phase 12: System Boot
phase_system_boot() {
    log_phase "Phase 12: System Boot"
    save_checkpoint "system_boot" "in_progress"

    local script="${SCRIPT_DIR}/flash-operations.sh"

    if ! execute_script "${script}" reboot-system "${DEVICE_SERIAL}"; then
        log_error "System boot failed"
        return 1
    fi

    # Wait for system to boot
    log_info "Waiting for system to boot (this may take several minutes)..."
    sleep 120

    save_checkpoint "system_boot" "completed"
    return 0
}

# Phase 13: Post-Install Configuration
phase_post_install_config() {
    log_phase "Phase 13: Post-Install Configuration"
    save_checkpoint "post_install_config" "in_progress"

    local script="${SCRIPT_DIR}/../post-install/setup-dev-environment.sh"

    if ! execute_script "${script}" configure "${DEVICE_SERIAL}"; then
        log_error "Post-install configuration failed"
        return 1
    fi

    local mia_script="${SCRIPT_DIR}/../post-install/mia-integration.sh"

    if ! execute_script "${mia_script}" setup "${DEVICE_SERIAL}"; then
        log_error "MIA integration failed"
        return 1
    fi

    save_checkpoint "post_install_config" "completed"
    return 0
}

# Phase 14: Final Verification
phase_final_verification() {
    log_phase "Phase 14: Final Verification"
    save_checkpoint "final_verification" "in_progress"

    local script="${SCRIPT_DIR}/../testing/health-check.sh"

    if ! execute_script "${script}" full "${DEVICE_SERIAL}"; then
        log_error "Final verification failed"
        return 1
    fi

    save_checkpoint "final_verification" "completed"
    return 0
}

# Execute installation phases
execute_installation() {
    local start_phase=${1:-0}
    local total_phases=${#PHASES[@]}

    log_info "Starting LineageOS installation process"
    log_info "Total phases: ${total_phases}"

    START_TIME=$(date +%s)

    for ((i = start_phase; i < total_phases; i++)); do
        local phase=${PHASES[i]}
        local phase_num=$((i + 1))

        show_progress "$((i + 1))" "${total_phases}" "Phase ${phase_num}/${total_phases}: ${phase}"

        case "${phase}" in
            "environment_check")
                phase_environment_check || return 1
                ;;
            "device_validation")
                phase_device_validation || return 1
                ;;
            "recovery_installation")
                phase_recovery_installation || return 1
                ;;
            "recovery_verification")
                phase_recovery_verification || return 1
                ;;
            "rom_download")
                phase_rom_download || return 1
                ;;
            "file_transfer")
                phase_file_transfer || return 1
                ;;
            "device_wipe")
                if ! confirm_operation "About to wipe device data. Continue?"; then
                    log_info "Installation cancelled by user"
                    return 1
                fi
                phase_device_wipe || return 1
                ;;
            "rom_flash")
                phase_rom_flash || return 1
                ;;
            "gapps_flash")
                phase_gapps_flash || return 1
                ;;
            "root_installation")
                phase_root_installation || return 1
                ;;
            "root_verification")
                phase_root_verification || return 1
                ;;
            "system_boot")
                phase_system_boot || return 1
                ;;
            "post_install_config")
                phase_post_install_config || return 1
                ;;
            "final_verification")
                phase_final_verification || return 1
                ;;
        esac
    done

    echo "" # New line after progress bar
    return 0
}

# Generate installation report
generate_installation_report() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local report_file="${WORK_DIR}/installation-report.txt"

    log_info "Generating installation report..."

    {
        echo "LineageOS Installation Report"
        echo "Generated on: $(date)"
        echo "Duration: ${duration} seconds"
        echo ""

        echo "=== INSTALLATION SUMMARY ==="
        if [[ "${INSTALL_SUCCESS}" == "true" ]]; then
            echo "Status: SUCCESS"
        else
            echo "Status: FAILED"
        fi
        echo ""

        echo "=== DEVICE INFORMATION ==="
        echo "Device Serial: ${DEVICE_SERIAL:-Unknown}"
        echo ""

        echo "=== CONFIGURATION ==="
        echo "Install GApps: ${INSTALL_GAPPS}"
        echo "GApps Variant: ${GAPPS_VARIANT}"
        echo "Install Magisk: ${INSTALL_MAGISK}"
        echo "Backup Before Install: ${BACKUP_BEFORE_INSTALL}"
        echo ""

        echo "=== PHASES EXECUTED ==="
        for phase in "${PHASES[@]}"; do
            local status="Unknown"
            if [[ -f "${CHECKPOINT_FILE}" ]]; then
                # Check if phase was completed
                if grep -q "PHASE=${phase}" "${CHECKPOINT_FILE}"; then
                    status=$(grep "STATUS=" "${CHECKPOINT_FILE}" | cut -d'=' -f2)
                else
                    status="Not Started"
                fi
            fi
            echo "- ${phase}: ${status}"
        done
        echo ""

        echo "=== LOG FILES ==="
        echo "Main Log: ${LOG_FILE}"
        echo "Checkpoint: ${CHECKPOINT_FILE}"
        echo ""

        if [[ "${INSTALL_SUCCESS}" == "true" ]]; then
            echo "=== NEXT STEPS ==="
            echo "1. Disconnect device from USB"
            echo "2. Complete initial Android setup"
            echo "3. Install MIA application"
            echo "4. Test device functionality"
            echo ""
        fi

    } > "${report_file}"

    log_success "Installation report generated: ${report_file}"
}

# Main function
main() {
    log_info "LineageOS Installation Orchestrator Starting"
    log_info "Working directory: ${WORK_DIR}"

    # Create work directory
    mkdir -p "${WORK_DIR}/logs"

    # Load configuration
    load_config

    # Parse command line arguments
    local resume_mode=false
    local start_phase=0

    while [[ $# -gt 0 ]]; do
        case $1 in
            --resume)
                resume_mode=true
                shift
                ;;
            --start-phase)
                start_phase=$2
                shift 2
                ;;
            --device)
                DEVICE_SERIAL=$2
                shift 2
                ;;
            --no-gapps)
                INSTALL_GAPPS=false
                shift
                ;;
            --no-root)
                INSTALL_MAGISK=false
                shift
                ;;
            --non-interactive)
                INTERACTIVE_MODE=false
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--resume] [--start-phase N] [--device SERIAL] [--no-gapps] [--no-root] [--non-interactive]"
                exit 1
                ;;
        esac
    done

    # Check for resume mode
    if [[ "${resume_mode}" == "true" ]]; then
        if load_checkpoint; then
            log_info "Resuming installation from phase: ${PHASE:-unknown}"
            # Find phase index
            for ((i = 0; i < ${#PHASES[@]}; i++)); do
                if [[ "${PHASES[i]}" == "${PHASE:-}" ]]; then
                    start_phase=$i
                    break
                fi
            done
        else
            log_warn "No checkpoint found, starting from beginning"
        fi
    fi

    # Save initial configuration
    save_config

    # Execute installation
    if execute_installation "${start_phase}"; then
        INSTALL_SUCCESS=true
        log_success "LineageOS installation completed successfully!"
    else
        INSTALL_SUCCESS=false
        log_error "LineageOS installation failed!"
    fi

    # Generate report
    generate_installation_report

    if [[ "${INSTALL_SUCCESS}" == "true" ]]; then
        echo ""
        echo "🎉 Installation completed successfully!"
        echo "📄 Check the report at: ${WORK_DIR}/installation-report.txt"
        echo ""
        echo "Next steps:"
        echo "1. Your HTC One M7 now has LineageOS 14.1 installed"
        echo "2. Magisk root access is available if selected"
        echo "3. The device is configured for MIA app development"
        echo ""
        exit 0
    else
        echo ""
        echo "❌ Installation failed!"
        echo "📄 Check the logs at: ${LOG_FILE}"
        echo "📄 Check the report at: ${WORK_DIR}/installation-report.txt"
        echo ""
        echo "You can resume the installation with: $0 --resume"
        echo ""
        exit 1
    fi
}

# Handle interrupts gracefully
trap 'echo ""; log_error "Installation interrupted by user"; generate_installation_report; exit 1' INT TERM

# Run main function
main "$@"