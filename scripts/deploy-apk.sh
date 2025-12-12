#!/usr/bin/env bash
set -euo pipefail

# AI-SERVIS Android APK Deployment Script
# Builds, validates, and deploys APK to connected Android device

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANDROID_DIR="$PROJECT_ROOT/android"
APK_PATH="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE_NAME="cz.mia.app.debug"
MAIN_ACTIVITY="cz.mia.app.MainActivity"

# Options
BUILD_ONLY=false
VALIDATE_ONLY=false
DEPLOY_ONLY=false
NO_LAUNCH=false
CLEAN_BUILD=false
TARGET_DEVICE=""
VERSION_CODE=""
VERSION_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --deploy-only)
            DEPLOY_ONLY=true
            shift
            ;;
        --no-launch)
            NO_LAUNCH=true
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --device)
            TARGET_DEVICE="$2"
            shift 2
            ;;
        --version-code)
            VERSION_CODE="$2"
            shift 2
            ;;
        --version-name)
            VERSION_NAME="$2"
            shift 2
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [options]

Android APK Build, Validation, and Deployment

Options:
  --build-only          Build APK without deployment
  --validate-only       Validate existing APK without building
  --deploy-only         Deploy existing APK without building
  --no-launch           Deploy APK without launching the app
  --clean               Clean build cache before building
  --device SERIAL       Target specific device (ADB device serial)
  --version-code N      Override version code for build
  --version-name V      Override version name for build
  --help, -h            Show this help message

Examples:
  $0                    # Full build, validate, and deploy
  $0 --build-only       # Build APK only
  $0 --deploy-only      # Deploy existing APK
  $0 --device emulator-5554  # Deploy to specific device
EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check ADB (only if deploying)
    if [[ "$BUILD_ONLY" == false && "$VALIDATE_ONLY" == false ]]; then
        if ! command -v adb &> /dev/null; then
            log_error "ADB is not installed or not in PATH"
            log_info "Install Android SDK Platform Tools to get ADB"
            exit 1
        fi
    fi
    
    log_success "Prerequisites satisfied"
}

# Check ADB device connection
check_adb_device() {
    log_info "Checking ADB device connection..."
    
    local adb_cmd="adb"
    if [[ -n "$TARGET_DEVICE" ]]; then
        adb_cmd="adb -s $TARGET_DEVICE"
    fi
    
    # Check if device is connected
    local devices_output
    devices_output=$($adb_cmd devices 2>&1)
    
    if echo "$devices_output" | grep -q "device$"; then
        local device_count
        device_count=$(echo "$devices_output" | grep -c "device$" || echo "0")
        log_success "Found $device_count connected device(s)"
        
        if [[ -n "$TARGET_DEVICE" ]]; then
            if echo "$devices_output" | grep -q "$TARGET_DEVICE.*device$"; then
                log_success "Target device $TARGET_DEVICE is connected"
            else
                log_error "Target device $TARGET_DEVICE is not connected or not authorized"
                exit 1
            fi
        fi
    else
        log_error "No Android device connected or authorized"
        log_info "Please connect a device or start an emulator"
        log_info "Make sure USB debugging is enabled on physical devices"
        exit 1
    fi
}

# Build APK
build_apk() {
    log_step "📦 Building APK..."
    
    cd "$ANDROID_DIR"
    
    # Clean build if requested
    if [[ "$CLEAN_BUILD" == true ]]; then
        log_info "Cleaning build cache..."
        rm -rf app/build .gradle
    fi
    
    # Build arguments
    local build_args=()
    if [[ -n "$VERSION_CODE" ]]; then
        build_args+=(--version-code "$VERSION_CODE")
    fi
    if [[ -n "$VERSION_NAME" ]]; then
        build_args+=(--version-name "$VERSION_NAME")
    fi
    
    # Run build
    if ./tools/build-in-docker.sh "${build_args[@]}"; then
        if [[ -f "$APK_PATH" ]]; then
            local apk_size
            apk_size=$(ls -lh "$APK_PATH" | awk '{print $5}')
            log_success "APK built successfully: app-debug.apk ($apk_size)"
        else
            log_error "APK file not found after build"
            exit 1
        fi
    else
        log_error "APK build failed"
        exit 1
    fi
}

# Validate APK
validate_apk() {
    log_step "🔍 Validating APK..."
    
    if [[ ! -f "$APK_PATH" ]]; then
        log_error "APK file not found: $APK_PATH"
        exit 1
    fi
    
    cd "$ANDROID_DIR"
    
    if ./tools/validate-apk.sh; then
        log_success "APK validation passed"
    else
        log_error "APK validation failed"
        exit 1
    fi
}

# Deploy APK
deploy_apk() {
    log_step "📱 Deploying APK to device..."
    
    if [[ ! -f "$APK_PATH" ]]; then
        log_error "APK file not found: $APK_PATH"
        exit 1
    fi
    
    local adb_cmd="adb"
    if [[ -n "$TARGET_DEVICE" ]]; then
        adb_cmd="adb -s $TARGET_DEVICE"
    fi
    
    # Check if app is already installed and uninstall if signature mismatch
    log_info "Checking for existing installation..."
    if $adb_cmd shell pm list packages | grep -q "$PACKAGE_NAME"; then
        log_info "Existing installation found. Uninstalling to avoid signature mismatch..."
        if $adb_cmd uninstall "$PACKAGE_NAME" 2>/dev/null; then
            log_success "Previous installation removed"
        else
            log_warning "Could not uninstall existing app (may need manual removal)"
            # Try to install anyway with -r flag
        fi
    fi
    
    # Install APK
    log_info "Installing APK..."
    if $adb_cmd install -r "$APK_PATH"; then
        log_success "APK installed successfully"
    else
        log_error "APK installation failed"
        log_info "Trying to uninstall existing app and retry..."
        $adb_cmd uninstall "$PACKAGE_NAME" 2>/dev/null || true
        if $adb_cmd install "$APK_PATH"; then
            log_success "APK installed successfully after uninstall"
        else
            log_error "APK installation failed after retry"
            exit 1
        fi
    fi
    
    # Verify installation
    log_info "Verifying installation..."
    if $adb_cmd shell pm list packages | grep -q "$PACKAGE_NAME"; then
        log_success "Package $PACKAGE_NAME found on device"
    else
        log_warning "Package $PACKAGE_NAME not found in package list (may be normal)"
    fi
    
    # Launch app (unless --no-launch specified)
    if [[ "$NO_LAUNCH" == false ]]; then
        log_info "Launching application..."
        if $adb_cmd shell am start -n "$PACKAGE_NAME/$MAIN_ACTIVITY" 2>/dev/null; then
            log_success "App launched: $PACKAGE_NAME"
        else
            log_warning "Could not launch app (this may be normal for first install)"
        fi
    fi
}

# Main execution
main() {
    echo ""
    echo -e "${BLUE}🚀 Starting Android APK deployment...${NC}"
    echo ""
    
    check_prerequisites
    
    # Build phase
    if [[ "$DEPLOY_ONLY" == false && "$VALIDATE_ONLY" == false ]]; then
        build_apk
    fi
    
    # Validate phase
    if [[ "$BUILD_ONLY" == false && "$DEPLOY_ONLY" == false ]]; then
        validate_apk
    fi
    
    # Deploy phase
    if [[ "$BUILD_ONLY" == false && "$VALIDATE_ONLY" == false ]]; then
        check_adb_device
        deploy_apk
    fi
    
    echo ""
    log_step "🎉 Deployment completed successfully!"
    echo ""
    log_info "APK Summary:"
    echo "   • File: $APK_PATH"
    if [[ -f "$APK_PATH" ]]; then
        echo "   • Size: $(ls -lh "$APK_PATH" | awk '{print $5}')"
    fi
    echo "   • Package: $PACKAGE_NAME"
    echo "   • Activity: $MAIN_ACTIVITY"
    echo ""
}

# Run main function
main "$@"
