#!/bin/bash

# Android Device Setup - ROM Manager
# Automated download and verification of LineageOS and GApps packages

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORK_DIR="${PROJECT_ROOT}/android-device-workspace"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
ROM_DIR="${DOWNLOAD_DIR}/roms"
GAPPS_DIR="${DOWNLOAD_DIR}/gapps"
LOG_FILE="${WORK_DIR}/rom-manager.log"

# Device and ROM configuration
DEVICE_CODENAME="m7"
LINEAGEOS_VERSION="14.1"
ANDROID_VERSION="7.1"

# Download sources (in order of preference)
LINEAGEOS_SOURCES=(
    "https://sourceforge.net/projects/lineageos-for-m7/files/lineage-${LINEAGEOS_VERSION}/nightly-${DEVICE_CODENAME}/"
    "https://mirrorbits.lineageos.org/full/${DEVICE_CODENAME}/"
    "https://download.lineageos.org/${DEVICE_CODENAME}"
)

GAPPS_SOURCES=(
    "https://sourceforge.net/projects/opengapps/files/${ANDROID_VERSION}/arm/7.1/nano/"
    "https://opengapps.org/"
    "https://downloads.codefi.re/jdcteam/javelinanddart/gapps"
)

# Expected file patterns
LINEAGEOS_PATTERN="lineage-${LINEAGEOS_VERSION}-[0-9]{8}-nightly-${DEVICE_CODENAME}-signed.zip"
GAPPS_PATTERN="open_gapps-arm-${ANDROID_VERSION}-nano-[0-9]{8}.zip"

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

# Setup directories
setup_directories() {
    log_info "Setting up ROM download directories..."

    mkdir -p "${ROM_DIR}"
    mkdir -p "${GAPPS_DIR}"

    log_success "Directories created successfully"
}

# Get latest LineageOS build information
get_latest_lineageos_info() {
    log_info "Getting latest LineageOS ${LINEAGEOS_VERSION} build information..."

    local latest_url=""
    local latest_filename=""
    local latest_date=""

    # Try each source to find the latest build
    for source in "${LINEAGEOS_SOURCES[@]}"; do
        log_info "Checking source: ${source}"

        if command -v curl >/dev/null 2>&1; then
            # Try to get directory listing or API info
            local listing
            listing=$(curl -s "${source}" 2>/dev/null || echo "")

            if [[ -n "${listing}" ]]; then
                # Parse for latest build (simplified - would need actual parsing logic)
                log_info "Found source with builds: ${source}"
                latest_url="${source}"
                break
            fi
        fi
    done

    if [[ -z "${latest_url}" ]]; then
        log_warn "Could not automatically determine latest build"
        log_info "Using fallback approach with known patterns"
        # Fallback to known working URLs for LineageOS 14.1 M7
        latest_url="https://sourceforge.net/projects/lineageos-for-m7/files/lineage-14.1/"
        latest_filename="lineage-14.1-20171029-nightly-m7-signed.zip"  # Known working build
    fi

    echo "${latest_url}|${latest_filename}"
}

# Download file with progress tracking
download_with_progress() {
    local url=$1
    local output_file=$2
    local description=${3:-"file"}

    log_info "Downloading ${description} from: ${url}"

    if [[ -f "${output_file}" ]]; then
        log_info "${description} already exists: ${output_file}"
        return 0
    fi

    # Create output directory
    mkdir -p "$(dirname "${output_file}")"

    # Try wget first (better progress display)
    if command -v wget >/dev/null 2>&1; then
        log_info "Using wget for download..."
        if wget -q --show-progress -O "${output_file}" "${url}"; then
            log_success "${description} downloaded successfully with wget"
            return 0
        fi
    fi

    # Fallback to curl
    if command -v curl >/dev/null 2>&1; then
        log_info "Using curl for download..."
        if curl -L -o "${output_file}" "${url}"; then
            log_success "${description} downloaded successfully with curl"
            return 0
        fi
    fi

    log_error "Failed to download ${description} from ${url}"
    return 1
}

# Verify file integrity
verify_file_integrity() {
    local file_path=$1
    local expected_checksum=${2:-""}
    local checksum_type=${3:-"sha256"}

    log_info "Verifying file integrity: ${file_path}"

    if [[ ! -f "${file_path}" ]]; then
        log_error "File does not exist: ${file_path}"
        return 1
    fi

    # Get file size
    local file_size
    file_size=$(stat -c%s "${file_path}" 2>/dev/null || stat -f%z "${file_path}" 2>/dev/null || echo "unknown")
    log_info "File size: ${file_size} bytes"

    # Verify checksum if provided
    if [[ -n "${expected_checksum}" ]]; then
        local calculated_checksum

        case "${checksum_type}" in
            "sha256")
                if command -v sha256sum >/dev/null 2>&1; then
                    calculated_checksum=$(sha256sum "${file_path}" | awk '{print $1}')
                elif command -v shasum >/dev/null 2>&1; then
                    calculated_checksum=$(shasum -a 256 "${file_path}" | awk '{print $1}')
                fi
                ;;
            "md5")
                if command -v md5sum >/dev/null 2>&1; then
                    calculated_checksum=$(md5sum "${file_path}" | awk '{print $1}')
                fi
                ;;
        esac

        if [[ -n "${calculated_checksum}" ]]; then
            if [[ "${calculated_checksum}" == "${expected_checksum}" ]]; then
                log_success "Checksum verification passed"
                return 0
            else
                log_error "Checksum verification failed"
                log_error "Expected: ${expected_checksum}"
                log_error "Calculated: ${calculated_checksum}"
                return 1
            fi
        else
            log_warn "Could not calculate checksum"
        fi
    else
        log_info "No expected checksum provided, skipping verification"
    fi

    # Basic ZIP file validation
    if [[ "${file_path}" == *.zip ]]; then
        log_info "Validating ZIP file structure..."
        if command -v unzip >/dev/null 2>&1; then
            if unzip -t "${file_path}" >/dev/null 2>&1; then
                log_success "ZIP file structure is valid"
                return 0
            else
                log_error "ZIP file structure is corrupted"
                return 1
            fi
        else
            log_warn "unzip not available for ZIP validation"
        fi
    fi

    return 0
}

# Download LineageOS ROM
download_lineageos() {
    local version=${1:-"${LINEAGEOS_VERSION}"}
    local force_download=${2:-false}

    log_info "Downloading LineageOS ${version} for ${DEVICE_CODENAME}..."

    # Get latest build info
    local build_info
    build_info=$(get_latest_lineageos_info)
    local base_url=$(echo "${build_info}" | cut -d'|' -f1)
    local filename=$(echo "${build_info}" | cut -d'|' -f2)

    if [[ -z "${filename}" ]]; then
        filename="lineage-${version}-$(date +%Y%m%d)-nightly-${DEVICE_CODENAME}-signed.zip"
    fi

    local rom_path="${ROM_DIR}/${filename}"

    # Check if file exists and is valid
    if [[ -f "${rom_path}" ]] && [[ "${force_download}" != true ]]; then
        log_info "LineageOS ROM already exists, verifying..."
        if verify_file_integrity "${rom_path}"; then
            log_success "Existing LineageOS ROM is valid"
            echo "${rom_path}"
            return 0
        else
            log_warn "Existing ROM is corrupted, re-downloading..."
            rm -f "${rom_path}"
        fi
    fi

    # Try multiple download sources
    local download_success=false
    local download_url=""

    for source in "${LINEAGEOS_SOURCES[@]}"; do
        # Construct full URL
        if [[ "${source}" == *sourceforge.net* ]]; then
            download_url="${source}${filename}/download"
        else
            download_url="${source}${filename}"
        fi

        log_info "Attempting download from: ${download_url}"

        if download_with_progress "${download_url}" "${rom_path}" "LineageOS ROM"; then
            download_success=true
            break
        fi
    done

    if [[ "${download_success}" != true ]]; then
        log_error "Failed to download LineageOS ROM from all sources"
        return 1
    fi

    # Verify downloaded file
    if ! verify_file_integrity "${rom_path}"; then
        log_error "Downloaded ROM failed integrity check"
        rm -f "${rom_path}"
        return 1
    fi

    log_success "LineageOS ROM downloaded and verified successfully"
    echo "${rom_path}"
}

# Download Open GApps
download_gapps() {
    local variant=${1:-"nano"}
    local android_version=${2:-"${ANDROID_VERSION}"}
    local force_download=${3:-false}

    log_info "Downloading Open GApps ${variant} for Android ${android_version}..."

    # Construct filename pattern
    local gapps_filename="open_gapps-arm-${android_version}-${variant}-$(date +%Y%m%d).zip"
    local gapps_path="${GAPPS_DIR}/${gapps_filename}"

    # Check if file exists
    if [[ -f "${gapps_path}" ]] && [[ "${force_download}" != true ]]; then
        log_info "GApps package already exists, verifying..."
        if verify_file_integrity "${gapps_path}"; then
            log_success "Existing GApps package is valid"
            echo "${gapps_path}"
            return 0
        else
            log_warn "Existing GApps package is corrupted, re-downloading..."
            rm -f "${gapps_path}"
        fi
    fi

    # Try to find latest GApps package
    local download_success=false
    local download_url=""

    for source in "${GAPPS_SOURCES[@]}"; do
        log_info "Checking GApps source: ${source}"

        # For SourceForge, try to find latest build
        if [[ "${source}" == *sourceforge.net* ]]; then
            # Try common date patterns for recent builds
            for i in {0..30}; do
                local check_date
                check_date=$(date -d "${i} days ago" +%Y%m%d 2>/dev/null || date -v-${i}d +%Y%m%d 2>/dev/null || echo "")
                if [[ -n "${check_date}" ]]; then
                    local test_filename="open_gapps-arm-${android_version}-${variant}-${check_date}.zip"
                    download_url="${source}${test_filename}/download"

                    log_info "Trying: ${download_url}"
                    if download_with_progress "${download_url}" "${gapps_path}" "GApps package"; then
                        download_success=true
                        break
                    fi
                fi
            done
        fi

        if [[ "${download_success}" == true ]]; then
            break
        fi
    done

    if [[ "${download_success}" != true ]]; then
        log_warn "Could not find latest GApps package, trying fallback..."

        # Fallback to a known working GApps package for Android 7.1
        local fallback_url="https://downloads.codefi.re/jdcteam/javelinanddart/gapps/open_gapps-arm-7.1-nano-20171029.zip"
        if download_with_progress "${fallback_url}" "${gapps_path}" "GApps package (fallback)"; then
            download_success=true
        fi
    fi

    if [[ "${download_success}" != true ]]; then
        log_error "Failed to download GApps package from all sources"
        return 1
    fi

    # Verify downloaded file
    if ! verify_file_integrity "${gapps_path}"; then
        log_error "Downloaded GApps package failed integrity check"
        rm -f "${gapps_path}"
        return 1
    fi

    log_success "GApps package downloaded and verified successfully"
    echo "${gapps_path}"
}

# List available ROMs and GApps
list_available() {
    log_info "Listing available ROMs and GApps..."

    echo ""
    echo "=== AVAILABLE LINEAGEOS ROMS ==="
    if [[ -d "${ROM_DIR}" ]]; then
        ls -la "${ROM_DIR}"/*.zip 2>/dev/null || echo "No ROMs downloaded yet"
    else
        echo "ROM directory not found"
    fi

    echo ""
    echo "=== AVAILABLE GAPPS PACKAGES ==="
    if [[ -d "${GAPPS_DIR}" ]]; then
        ls -la "${GAPPS_DIR}"/*.zip 2>/dev/null || echo "No GApps downloaded yet"
    else
        echo "GApps directory not found"
    fi
    echo ""
}

# Clean old downloads
clean_old_downloads() {
    local days=${1:-30}

    log_info "Cleaning downloads older than ${days} days..."

    local cleaned_count=0

    # Clean ROMs
    if [[ -d "${ROM_DIR}" ]]; then
        while IFS= read -r -d '' file; do
            if [[ -f "${file}" ]] && [[ $(find "${file}" -mtime +${days} 2>/dev/null | wc -l) -gt 0 ]]; then
                log_info "Removing old ROM: ${file}"
                rm -f "${file}"
                ((cleaned_count++))
            fi
        done < <(find "${ROM_DIR}" -name "*.zip" -print0 2>/dev/null)
    fi

    # Clean GApps
    if [[ -d "${GAPPS_DIR}" ]]; then
        while IFS= read -r -d '' file; do
            if [[ -f "${file}" ]] && [[ $(find "${file}" -mtime +${days} 2>/dev/null | wc -l) -gt 0 ]]; then
                log_info "Removing old GApps: ${file}"
                rm -f "${file}"
                ((cleaned_count++))
            fi
        done < <(find "${GAPPS_DIR}" -name "*.zip" -print0 2>/dev/null)
    fi

    log_success "Cleaned ${cleaned_count} old files"
}

# Get download statistics
get_download_stats() {
    log_info "Getting download statistics..."

    local rom_count=0
    local gapps_count=0
    local total_size=0

    if [[ -d "${ROM_DIR}" ]]; then
        rom_count=$(find "${ROM_DIR}" -name "*.zip" 2>/dev/null | wc -l)
        rom_size=$(du -sb "${ROM_DIR}" 2>/dev/null | awk '{print $1}' || echo "0")
        total_size=$((total_size + rom_size))
    fi

    if [[ -d "${GAPPS_DIR}" ]]; then
        gapps_count=$(find "${GAPPS_DIR}" -name "*.zip" 2>/dev/null | wc -l)
        gapps_size=$(du -sb "${GAPPS_DIR}" 2>/dev/null | awk '{print $1}' || echo "0")
        total_size=$((total_size + gapps_size))
    fi

    echo "ROMs: ${rom_count} files"
    echo "GApps: ${gapps_count} files"
    echo "Total size: $((total_size / 1024 / 1024)) MB"
}

# Main function
main() {
    log_info "Starting ROM Manager"
    log_info "Device: ${DEVICE_CODENAME}, LineageOS: ${LINEAGEOS_VERSION}, Android: ${ANDROID_VERSION}"

    # Setup directories
    setup_directories

    case "${1:-}" in
        "download-rom")
            download_lineageos "${2:-}" "${3:-false}"
            ;;
        "download-gapps")
            download_gapps "${2:-nano}" "${3:-${ANDROID_VERSION}}" "${4:-false}"
            ;;
        "download-all")
            rom_path=$(download_lineageos)
            gapps_path=$(download_gapps)
            echo "ROM: ${rom_path}"
            echo "GApps: ${gapps_path}"
            ;;
        "list")
            list_available
            ;;
        "clean")
            clean_old_downloads "${2:-30}"
            ;;
        "stats")
            get_download_stats
            ;;
        "verify")
            if [[ -n "${2:-}" ]] && [[ -f "${2}" ]]; then
                verify_file_integrity "${2}" "${3:-}" "${4:-sha256}"
            else
                log_error "Please provide a valid file path to verify"
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 {download-rom|download-gapps|download-all|list|clean|stats|verify} [options]"
            echo ""
            echo "Commands:"
            echo "  download-rom [version] [force]     - Download LineageOS ROM"
            echo "  download-gapps [variant] [android] [force] - Download GApps"
            echo "  download-all                        - Download both ROM and GApps"
            echo "  list                                - List available downloads"
            echo "  clean [days]                        - Clean downloads older than N days"
            echo "  stats                               - Show download statistics"
            echo "  verify <file> [checksum] [type]     - Verify file integrity"
            echo ""
            echo "Examples:"
            echo "  $0 download-all                     # Download latest ROM and GApps"
            echo "  $0 download-rom 14.1 true          # Download specific ROM version, force re-download"
            echo "  $0 download-gapps pico 7.1         # Download Pico GApps for Android 7.1"
            echo "  $0 list                             # Show available files"
            echo "  $0 clean 7                          # Remove files older than 7 days"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"