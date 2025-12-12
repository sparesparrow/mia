#!/bin/bash

# Android Device Setup - Device Pool Manager
# Manages multiple HTC One M7 development devices for automated testing and setup

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
POOL_DIR="${WORK_DIR}/device-pool"
POOL_REGISTRY="${POOL_DIR}/devices.csv"
POOL_STATUS="${POOL_DIR}/status.log"
POOL_CONFIG="${POOL_DIR}/config.txt"

# Default device pool configuration
DEFAULT_POOL_CONFIG=(
    "MAX_DEVICES=10"
    "AUTO_ASSIGNMENT=true"
    "HEALTH_CHECK_INTERVAL=3600"
    "MAINTENANCE_MODE=false"
    "RESERVE_CRITICAL_DEVICES=true"
)

# Device states
DEVICE_STATES=(
    "available"
    "in_use"
    "maintenance"
    "offline"
    "error"
    "setup_pending"
    "setup_in_progress"
    "setup_complete"
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
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${POOL_STATUS}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${POOL_STATUS}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${POOL_STATUS}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${POOL_STATUS}"
}

log_pool() {
    echo -e "${CYAN}[POOL]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${POOL_STATUS}"
}

# Initialize device pool
init_device_pool() {
    log_pool "Initializing device pool..."

    mkdir -p "${POOL_DIR}"

    # Create registry if it doesn't exist
    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        echo "# Device Pool Registry - $(date)" > "${POOL_REGISTRY}"
        echo "# Format: serial,model,owner,status,last_seen,last_health_check,notes" >> "${POOL_REGISTRY}"
        log_pool "Created device registry: ${POOL_REGISTRY}"
    fi

    # Create config if it doesn't exist
    if [[ ! -f "${POOL_CONFIG}" ]]; then
        echo "# Device Pool Configuration" > "${POOL_CONFIG}"
        for config in "${DEFAULT_POOL_CONFIG[@]}"; do
            echo "${config}" >> "${POOL_CONFIG}"
        done
        log_pool "Created pool configuration: ${POOL_CONFIG}"
    fi

    # Load configuration
    if [[ -f "${POOL_CONFIG}" ]]; then
        source "${POOL_CONFIG}"
    fi

    log_success "✓ Device pool initialized"
}

# Load pool configuration
load_pool_config() {
    if [[ -f "${POOL_CONFIG}" ]]; then
        source "${POOL_CONFIG}"
    else
        # Use defaults
        for config in "${DEFAULT_POOL_CONFIG[@]}"; do
            local key=$(echo "${config}" | cut -d'=' -f1)
            local value=$(echo "${config}" | cut -d'=' -f2)
            declare -g "${key}=${value}"
        done
    fi
}

# Register device in pool
register_device() {
    local serial=$1
    local model=${2:-"HTC One M7"}
    local owner=${3:-"unassigned"}
    local status=${4:-"available"}
    local notes=${5:-""}

    # Check if device already exists
    if grep -q "^${serial}," "${POOL_REGISTRY}"; then
        log_warn "Device ${serial} already registered, updating..."
        # Remove existing entry
        sed -i "/^${serial},/d" "${POOL_REGISTRY}"
    fi

    # Add new entry
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${serial},${model},${owner},${status},${timestamp},${timestamp},${notes}" >> "${POOL_REGISTRY}"

    log_pool "✓ Registered device: ${serial} (${model}) - Status: ${status}"
}

# Update device status
update_device_status() {
    local serial=$1
    local status=$2
    local owner=${3:-""}
    local notes=${4:-""}

    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        log_error "Device registry not found"
        return 1
    fi

    # Check if valid status
    local valid_status=false
    for state in "${DEVICE_STATES[@]}"; do
        if [[ "${state}" == "${status}" ]]; then
            valid_status=true
            break
        fi
    done

    if [[ "${valid_status}" != true ]]; then
        log_error "Invalid status: ${status}. Valid states: ${DEVICE_STATES[*]}"
        return 1
    fi

    # Update device entry
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local temp_file=$(mktemp)

    while IFS=',' read -r reg_serial reg_model reg_owner reg_status reg_last_seen reg_health_check reg_notes; do
        if [[ "${reg_serial}" == "${serial}" ]]; then
            # Update the entry
            local new_owner=${reg_owner}
            local new_notes=${reg_notes}

            if [[ -n "${owner}" ]]; then
                new_owner=${owner}
            fi

            if [[ -n "${notes}" ]]; then
                new_notes=${notes}
            fi

            echo "${serial},${reg_model},${new_owner},${status},${timestamp},${reg_health_check},${new_notes}" >> "${temp_file}"
            log_pool "Updated device ${serial}: ${reg_status} → ${status}"
        else
            echo "${reg_serial},${reg_model},${reg_owner},${reg_status},${reg_last_seen},${reg_health_check},${reg_notes}" >> "${temp_file}"
        fi
    done < <(tail -n +3 "${POOL_REGISTRY}") # Skip header lines

    # Replace registry
    {
        head -2 "${POOL_REGISTRY}"
        cat "${temp_file}"
    } > "${POOL_REGISTRY}.tmp"
    mv "${POOL_REGISTRY}.tmp" "${POOL_REGISTRY}"
    rm -f "${temp_file}"

    log_success "✓ Updated device status: ${serial} → ${status}"
}

# Discover connected devices
discover_devices() {
    log_pool "Discovering connected devices..."

    # Get connected devices
    local connected_devices
    connected_devices=$(adb devices | grep -v "List" | grep "device$" | awk '{print $1}' || echo "")

    if [[ -z "${connected_devices}" ]]; then
        log_warn "No devices connected"
        return 0
    fi

    local device_count=0
    while read -r serial; do
        if [[ -n "${serial}" ]]; then
            # Get device model
            local model
            model=$(adb -s "${serial}" shell getprop ro.product.model 2>/dev/null | tr -d '\r' || echo "Unknown")

            # Check if already registered
            if grep -q "^${serial}," "${POOL_REGISTRY}"; then
                # Update last seen
                update_device_status "${serial}" "available" "" "Auto-discovered"
            else
                # Register new device
                register_device "${serial}" "${model}" "unassigned" "available" "Auto-discovered"
            fi

            ((device_count++))
        fi
    done <<< "${connected_devices}"

    log_success "✓ Discovered ${device_count} device(s)"
}

# Get device information
get_device_info() {
    local serial=$1

    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        log_error "Device registry not found"
        return 1
    fi

    local device_info
    device_info=$(grep "^${serial}," "${POOL_REGISTRY}" || echo "")

    if [[ -z "${device_info}" ]]; then
        log_error "Device ${serial} not found in pool"
        return 1
    fi

    # Parse device info
    IFS=',' read -r reg_serial model owner status last_seen health_check notes <<< "${device_info}"

    echo "Serial: ${reg_serial}"
    echo "Model: ${model}"
    echo "Owner: ${owner}"
    echo "Status: ${status}"
    echo "Last Seen: ${last_seen}"
    echo "Last Health Check: ${health_check}"
    echo "Notes: ${notes}"
}

# List devices in pool
list_devices() {
    local filter=${1:-""}

    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        log_error "Device registry not found"
        return 1
    fi

    echo ""
    echo "=== DEVICE POOL STATUS ==="
    echo ""
    printf "%-15s %-15s %-12s %-15s %-20s %-15s\n" "SERIAL" "MODEL" "OWNER" "STATUS" "LAST SEEN" "HEALTH CHECK"
    echo "---------------------------------------------------------------------------------------------"

    local device_count=0
    local available_count=0
    local in_use_count=0

    while IFS=',' read -r serial model owner status last_seen health_check notes; do
        # Skip header lines
        [[ "${serial}" == "#"* ]] && continue

        # Apply filter if specified
        if [[ -n "${filter}" ]] && [[ "${status}" != "${filter}" ]] && [[ "${owner}" != "${filter}" ]]; then
            continue
        fi

        printf "%-15s %-15s %-12s %-15s %-20s %-15s\n" "${serial}" "${model}" "${owner}" "${status}" "${last_seen}" "${health_check}"
        ((device_count++))

        if [[ "${status}" == "available" ]]; then
            ((available_count++))
        elif [[ "${status}" == "in_use" ]]; then
            ((in_use_count++))
        fi
    done < "${POOL_REGISTRY}"

    echo ""
    echo "Summary: ${device_count} total, ${available_count} available, ${in_use_count} in use"
    echo ""
}

# Assign device to user/project
assign_device() {
    local serial=$1
    local owner=$2
    local project=${3:-"development"}

    log_pool "Assigning device ${serial} to ${owner} for ${project}..."

    # Check if device exists and is available
    local device_info
    device_info=$(grep "^${serial}," "${POOL_REGISTRY}" || echo "")

    if [[ -z "${device_info}" ]]; then
        log_error "Device ${serial} not found in pool"
        return 1
    fi

    # Parse current status
    local current_status
    current_status=$(echo "${device_info}" | cut -d',' -f4)

    if [[ "${current_status}" != "available" ]]; then
        log_error "Device ${serial} is not available (status: ${current_status})"
        return 1
    fi

    # Update device status
    update_device_status "${serial}" "in_use" "${owner}" "Assigned to ${project}"

    log_success "✓ Device ${serial} assigned to ${owner}"
}

# Release device back to pool
release_device() {
    local serial=$1

    log_pool "Releasing device ${serial} back to pool..."

    # Check if device is currently assigned
    local device_info
    device_info=$(grep "^${serial}," "${POOL_REGISTRY}" || echo "")

    if [[ -z "${device_info}" ]]; then
        log_error "Device ${serial} not found in pool"
        return 1
    fi

    # Update status to available
    update_device_status "${serial}" "available" "unassigned" "Released to pool"

    log_success "✓ Device ${serial} released back to pool"
}

# Reserve device for maintenance
reserve_device() {
    local serial=$1
    local reason=${2:-"maintenance"}

    log_pool "Reserving device ${serial} for ${reason}..."

    update_device_status "${serial}" "maintenance" "system" "${reason}"

    log_success "✓ Device ${serial} reserved for ${reason}"
}

# Run health checks on all devices
run_pool_health_checks() {
    log_pool "Running health checks on all pool devices..."

    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        log_error "Device registry not found"
        return 1
    fi

    local checked_count=0
    local healthy_count=0

    while IFS=',' read -r serial model owner status last_seen health_check notes; do
        # Skip header lines and offline devices
        [[ "${serial}" == "#"* ]] && continue
        [[ "${status}" == "offline" ]] && continue

        log_info "Checking device: ${serial} (${model})"

        # Run health check
        local health_script="${SCRIPT_DIR}/../testing/health-check.sh"
        if [[ -x "${health_script}" ]]; then
            if "${health_script}" full "${serial}" >/dev/null 2>&1; then
                update_device_status "${serial}" "${status}" "" "Health check passed"
                ((healthy_count++))
            else
                update_device_status "${serial}" "error" "" "Health check failed"
                log_warn "Health check failed for device ${serial}"
            fi
        fi

        ((checked_count++))
    done < <(tail -n +3 "${POOL_REGISTRY}")

    log_success "✓ Health checks completed: ${healthy_count}/${checked_count} devices healthy"
}

# Get pool statistics
get_pool_stats() {
    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        log_error "Device registry not found"
        return 1
    fi

    local total_devices=0
    local available_devices=0
    local in_use_devices=0
    local maintenance_devices=0
    local error_devices=0

    while IFS=',' read -r serial model owner status last_seen health_check notes; do
        # Skip header lines
        [[ "${serial}" == "#"* ]] && continue

        ((total_devices++))

        case "${status}" in
            "available") ((available_devices++)) ;;
            "in_use") ((in_use_devices++)) ;;
            "maintenance") ((maintenance_devices++)) ;;
            "error") ((error_devices++)) ;;
        esac
    done < "${POOL_REGISTRY}"

    echo "=== DEVICE POOL STATISTICS ==="
    echo "Total Devices: ${total_devices}"
    echo "Available: ${available_devices}"
    echo "In Use: ${in_use_devices}"
    echo "Maintenance: ${maintenance_devices}"
    echo "Error: ${error_devices}"
    echo ""

    # Calculate utilization
    if [[ ${total_devices} -gt 0 ]]; then
        local utilization=$(( (total_devices - available_devices) * 100 / total_devices ))
        echo "Pool Utilization: ${utilization}%"
    fi

    echo ""
}

# Cleanup inactive devices
cleanup_inactive_devices() {
    local days_threshold=${1:-30}

    log_pool "Cleaning up devices inactive for ${days_threshold} days..."

    if [[ ! -f "${POOL_REGISTRY}" ]]; then
        log_error "Device registry not found"
        return 1
    fi

    local cleaned_count=0
    local temp_file=$(mktemp)

    # Calculate threshold date
    local threshold_date
    threshold_date=$(date -d "${days_threshold} days ago" '+%Y-%m-%d' 2>/dev/null || date -v-${days_threshold}d '+%Y-%m-%d' 2>/dev/null || echo "")

    if [[ -z "${threshold_date}" ]]; then
        log_error "Could not calculate threshold date"
        return 1
    fi

    {
        # Keep header
        head -2 "${POOL_REGISTRY}"

        # Process devices
        while IFS=',' read -r serial model owner status last_seen health_check notes; do
            # Skip header lines
            [[ "${serial}" == "#"* ]] && continue

            # Check if device should be cleaned up
            local last_seen_date
            last_seen_date=$(echo "${last_seen}" | cut -d' ' -f1)

            if [[ "${last_seen_date}" < "${threshold_date}" ]] && [[ "${status}" == "available" ]]; then
                log_info "Removing inactive device: ${serial} (last seen: ${last_seen})"
                ((cleaned_count++))
            else
                echo "${serial},${model},${owner},${status},${last_seen},${health_check},${notes}"
            fi
        done < <(tail -n +3 "${POOL_REGISTRY}")
    } > "${temp_file}"

    mv "${temp_file}" "${POOL_REGISTRY}"

    if [[ ${cleaned_count} -gt 0 ]]; then
        log_success "✓ Cleaned up ${cleaned_count} inactive device(s)"
    else
        log_info "No inactive devices to clean up"
    fi
}

# Export pool data
export_pool_data() {
    local format=${1:-"csv"}
    local output_file=${2:-"${POOL_DIR}/pool_export_$(date '+%Y%m%d_%H%M%S').${format}"}

    log_pool "Exporting pool data to ${output_file}..."

    case "${format}" in
        "csv")
            cp "${POOL_REGISTRY}" "${output_file}"
            ;;
        "json")
            # Convert CSV to JSON (simplified)
            {
                echo "{"
                echo '  "devices": ['
                local first=true
                while IFS=',' read -r serial model owner status last_seen health_check notes; do
                    [[ "${serial}" == "#"* ]] && continue
                    [[ "${first}" == true ]] && first=false || echo "    ,"
                    echo "    {"
                    echo "      \"serial\": \"${serial}\","
                    echo "      \"model\": \"${model}\","
                    echo "      \"owner\": \"${owner}\","
                    echo "      \"status\": \"${status}\","
                    echo "      \"last_seen\": \"${last_seen}\","
                    echo "      \"health_check\": \"${health_check}\","
                    echo "      \"notes\": \"${notes}\""
                    echo -n "    }"
                done < <(tail -n +3 "${POOL_REGISTRY}")
                echo ""
                echo "  ]"
                echo "}"
            } > "${output_file}"
            ;;
        *)
            log_error "Unsupported export format: ${format}"
            return 1
            ;;
    esac

    log_success "✓ Pool data exported to ${output_file}"
}

# Main function
main() {
    log_info "Starting Device Pool Manager"

    # Initialize pool
    init_device_pool
    load_pool_config

    case "${1:-}" in
        "init")
            # Already initialized above
            log_success "Device pool initialized and ready"
            ;;
        "register")
            local serial=${2}
            local model=${3:-"HTC One M7"}
            local owner=${4:-"unassigned"}
            register_device "${serial}" "${model}" "${owner}"
            ;;
        "discover")
            discover_devices
            ;;
        "list")
            local filter=${2:-""}
            list_devices "${filter}"
            ;;
        "info")
            local serial=${2}
            get_device_info "${serial}"
            ;;
        "assign")
            local serial=${2}
            local owner=${3}
            local project=${4:-"development"}
            assign_device "${serial}" "${owner}" "${project}"
            ;;
        "release")
            local serial=${2}
            release_device "${serial}"
            ;;
        "reserve")
            local serial=${2}
            local reason=${3:-"maintenance"}
            reserve_device "${serial}" "${reason}"
            ;;
        "health-check")
            run_pool_health_checks
            ;;
        "stats")
            get_pool_stats
            ;;
        "cleanup")
            local days=${2:-30}
            cleanup_inactive_devices "${days}"
            ;;
        "export")
            local format=${2:-"csv"}
            local file=${3:-""}
            export_pool_data "${format}" "${file}"
            ;;
        *)
            echo "Usage: $0 {init|register|discover|list|info|assign|release|reserve|health-check|stats|cleanup|export} [options]"
            echo ""
            echo "Commands:"
            echo "  init                    - Initialize device pool"
            echo "  register <serial> [model] [owner] - Register new device"
            echo "  discover                - Discover connected devices"
            echo "  list [filter]          - List devices (optional filter by status/owner)"
            echo "  info <serial>          - Get device information"
            echo "  assign <serial> <owner> [project] - Assign device to user"
            echo "  release <serial>       - Release device back to pool"
            echo "  reserve <serial> [reason] - Reserve device for maintenance"
            echo "  health-check           - Run health checks on all devices"
            echo "  stats                  - Show pool statistics"
            echo "  cleanup [days]         - Remove inactive devices (default: 30 days)"
            echo "  export [format] [file] - Export pool data (csv/json)"
            echo ""
            echo "Examples:"
            echo "  $0 init                          # Initialize pool"
            echo "  $0 register HT123456             # Register device"
            echo "  $0 discover                      # Find connected devices"
            echo "  $0 assign HT123456 john          # Assign to user"
            echo "  $0 list available               # List available devices"
            echo "  $0 health-check                 # Check all devices"
            echo "  $0 export json                  # Export as JSON"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"