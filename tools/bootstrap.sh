#!/bin/bash
# MIA Universal Bootstrap Script
# Enhanced bootstrap with Cloudsmith/GitHub Packages support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on supported platform
check_platform() {
    local platform=$(uname -s | tr '[:upper:]' '[:lower:]')
    local machine=$(uname -m)

    log_info "Detected platform: $platform/$machine"

    case $platform in
        linux|darwin)
            log_success "Platform supported"
            ;;
        *)
            log_error "Unsupported platform: $platform"
            exit 1
            ;;
    esac
}

# Check system dependencies
check_dependencies() {
    local missing_deps=()

    # Check for Python 3.8+
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    else
        local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
            log_success "Python $python_version found"
        else
            log_error "Python 3.8+ required, found $python_version"
            exit 1
        fi
    fi

    # Check for pip
    if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
        missing_deps+=("pip3")
    fi

    # Check for curl or wget
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        missing_deps+=("curl or wget")
    fi

    # Check for tar
    if ! command -v tar &> /dev/null; then
        missing_deps+=("tar")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies and try again"
        exit 1
    fi

    log_success "All system dependencies satisfied"
}

# Install Python packages
install_python_packages() {
    log_info "Installing Python packages..."

    local packages=(
        "websockets>=11.0.0"
        "aiohttp>=3.9.0"
        "pydantic>=2.0.0"
        "fastapi>=0.104.0"
        "uvicorn>=0.24.0"
        "jinja2>=3.1.0"
        "click>=8.1.0"
    )

    for package in "${packages[@]}"; do
        log_info "Installing $package..."
        if ! python3 -m pip install "$package"; then
            log_error "Failed to install $package"
            return 1
        fi
    done

    log_success "Python packages installed"
    return 0
}

# Download and install Conan
install_conan() {
    local conan_version="2.0.0"
    local platform=$(uname -s | tr '[:upper:]' '[:lower:]')
    local machine=$(uname -m)

    log_info "Installing Conan $conan_version..."

    # Determine download URL
    local download_url=""
    case $platform in
        linux)
            case $machine in
                x86_64)
                    download_url="https://github.com/conan-io/conan/releases/download/$conan_version/conan-$conan_version-x86_64-linux-gnu.tar.gz"
                    ;;
                aarch64|arm64)
                    download_url="https://github.com/conan-io/conan/releases/download/$conan_version/conan-$conan_version-armv8-linux-gnu.tar.gz"
                    ;;
                *)
                    log_error "Unsupported architecture: $machine"
                    return 1
                    ;;
            esac
            ;;
        darwin)
            case $machine in
                arm64)
                    download_url="https://github.com/conan-io/conan/releases/download/$conan_version/conan-$conan_version-armv8-macos.tar.gz"
                    ;;
                x86_64)
                    download_url="https://github.com/conan-io/conan/releases/download/$conan_version/conan-$conan_version-x86_64-macos.tar.gz"
                    ;;
                *)
                    log_error "Unsupported architecture: $machine"
                    return 1
                    ;;
            esac
            ;;
        *)
            log_error "Unsupported platform: $platform"
            return 1
            ;;
    esac

    if [ -z "$download_url" ]; then
        log_error "Could not determine Conan download URL"
        return 1
    fi

    # Create temporary directory
    local temp_dir=$(mktemp -d)
    local archive_name="conan-$conan_version.tar.gz"
    local archive_path="$temp_dir/$archive_name"

    log_info "Downloading Conan from $download_url..."

    # Download archive
    if command -v curl &> /dev/null; then
        if ! curl -L -o "$archive_path" "$download_url"; then
            log_error "Failed to download Conan"
            rm -rf "$temp_dir"
            return 1
        fi
    elif command -v wget &> /dev/null; then
        if ! wget -O "$archive_path" "$download_url"; then
            log_error "Failed to download Conan"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_error "Neither curl nor wget available"
        rm -rf "$temp_dir"
        return 1
    fi

    # Extract archive
    log_info "Extracting Conan..."
    local extract_dir="$temp_dir/conan_extract"
    mkdir -p "$extract_dir"

    if ! tar -xzf "$archive_path" -C "$extract_dir"; then
        log_error "Failed to extract Conan archive"
        rm -rf "$temp_dir"
        return 1
    fi

    # Find Conan binary
    local conan_bin=""
    for dir in "$extract_dir"/*/; do
        if [ -f "$dir/conan" ]; then
            conan_bin="$dir/conan"
            break
        fi
    done

    if [ -z "$conan_bin" ]; then
        log_error "Could not find Conan binary in extracted archive"
        rm -rf "$temp_dir"
        return 1
    fi

    # Install Conan
    local install_dir="$PROJECT_ROOT/tools/conan"
    mkdir -p "$install_dir"

    log_info "Installing Conan to $install_dir..."
    cp -r "$extract_dir"/* "$install_dir/"

    # Add to PATH
    export PATH="$install_dir:$PATH"

    # Verify installation
    if ! command -v conan &> /dev/null; then
        log_error "Conan installation failed - not found in PATH"
        rm -rf "$temp_dir"
        return 1
    fi

    local installed_version=$(conan --version 2>/dev/null | head -n1 || echo "unknown")
    log_success "Conan $installed_version installed successfully"

    # Cleanup
    rm -rf "$temp_dir"
    return 0
}

# Configure Conan repositories
configure_conan_repositories() {
    log_info "Configuring Conan repositories..."

    # Add Cloudsmith repository
    if [ -n "$CLOUDSMITH_USERNAME" ] && [ -n "$CLOUDSMITH_API_KEY" ]; then
        log_info "Adding Cloudsmith repository..."

        if conan remote add sparetools "https://cloudsmith.io/~sparetools/repos/sparetools/packages/" --force; then
            log_success "Cloudsmith repository added"
        else
            log_warning "Failed to add Cloudsmith repository"
        fi

        # Login to Cloudsmith
        echo "$CLOUDSMITH_API_KEY" | conan remote login sparetools "$CLOUDSMITH_USERNAME" || log_warning "Cloudsmith login failed"
    else
        log_warning "Cloudsmith credentials not found (CLOUDSMITH_USERNAME, CLOUDSMITH_API_KEY)"
    fi

    # Add GitHub Packages as fallback
    if [ -n "$GITHUB_USERNAME" ] && [ -n "$GITHUB_TOKEN" ]; then
        log_info "Adding GitHub Packages repository..."

        if conan remote add github-sparetools "https://maven.pkg.github.com/sparetools" --force; then
            log_success "GitHub Packages repository added"
        else
            log_warning "Failed to add GitHub Packages repository"
        fi
    else
        log_warning "GitHub credentials not found (GITHUB_USERNAME, GITHUB_TOKEN)"
    fi

    # List configured remotes
    log_info "Configured Conan remotes:"
    conan remote list
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."

    local issues=()

    # Check Python
    if ! python3 --version &> /dev/null; then
        issues+=("Python 3 not found")
    fi

    # Check Conan
    if ! conan --version &> /dev/null; then
        issues+=("Conan not found in PATH")
    fi

    # Check Python packages
    local python_packages=("websockets" "aiohttp" "pydantic" "fastapi")
    for package in "${python_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            issues+=("Python package $package not installed")
        fi
    done

    if [ ${#issues[@]} -gt 0 ]; then
        log_error "Installation verification failed:"
        for issue in "${issues[@]}"; do
            log_error "  - $issue"
        done
        return 1
    fi

    log_success "Installation verified successfully"
    return 0
}

# Print usage information
print_usage() {
    cat << EOF
MIA Universal Bootstrap Script

Usage: $0 [OPTIONS]

Options:
    --help          Show this help message
    --skip-python   Skip Python package installation
    --skip-conan    Skip Conan installation
    --force         Force reinstallation of all components

Environment Variables:
    CLOUDSMITH_USERNAME    Cloudsmith username
    CLOUDSMITH_API_KEY     Cloudsmith API key
    GITHUB_USERNAME        GitHub username
    GITHUB_TOKEN           GitHub personal access token

Examples:
    $0
    $0 --force
    CLOUDSMITH_USERNAME=user CLOUDSMITH_API_KEY=key $0
EOF
}

# Main function
main() {
    local skip_python=false
    local skip_conan=false
    local force=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_usage
                exit 0
                ;;
            --skip-python)
                skip_python=true
                shift
                ;;
            --skip-conan)
                skip_conan=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    log_info "MIA Universal Bootstrap Starting..."
    log_info "Project root: $PROJECT_ROOT"

    # Run bootstrap steps
    check_platform
    check_dependencies

    if [ "$skip_python" = false ]; then
        if ! install_python_packages; then
            log_error "Python package installation failed"
            exit 1
        fi
    else
        log_info "Skipping Python package installation"
    fi

    if [ "$skip_conan" = false ]; then
        if ! install_conan; then
            log_error "Conan installation failed"
            exit 1
        fi
    else
        log_info "Skipping Conan installation"
    fi

    configure_conan_repositories

    if ! verify_installation; then
        log_error "Installation verification failed"
        exit 1
    fi

    log_success "Bootstrap completed successfully!"
    echo
    log_info "Next steps:"
    echo "  1. Run: conan install . --build=missing -r sparetools"
    echo "  2. Run: python3 modules/core-orchestrator/main.py"
    echo "  3. Check docs/ for more information"
}

# Run main function
main "$@"