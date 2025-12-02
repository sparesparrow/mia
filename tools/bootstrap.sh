#!/bin/bash
# =============================================================================
# AI-SERVIS Build Environment Bootstrap (Sparetools Integration)
# =============================================================================
# Uses sparetools zero-copy bootstrap approach with sparetools-cpython Conan
# package for a consistent, portable Python/Conan development environment.
#
# This script leverages:
# - sparetools-cpython/3.12.7 from Conan (or builds locally if needed)
# - Cloudsmith remote: https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/
# - Zero-copy symlinks from Conan cache to .buildenv/
#
# Usage:
#   ./tools/bootstrap.sh              # Full setup
#   ./tools/bootstrap.sh --update     # Update existing environment
#   ./tools/bootstrap.sh --clean      # Remove and reinstall
#   ./tools/bootstrap.sh --no-conan   # Skip Conan setup (system Python only)
#
# Environment is created in: .buildenv/
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script and project root directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Environment configuration
BUILDENV_DIR="$PROJECT_ROOT/.buildenv"
PYTHON_DIR="$BUILDENV_DIR/python"
VENV_DIR="$BUILDENV_DIR/venv"
CACHE_DIR="$BUILDENV_DIR/cache"
CONAN_HOME="$BUILDENV_DIR/conan"
CONAN_CACHE="${HOME}/.conan2/p"

# Version pinning (aligned with sparetools)
CPYTHON_VERSION="3.12.7"
CONAN_VERSION="2.3.2"

# Cloudsmith remote URL for sparetools packages
CLOUDSMITH_REMOTE="https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/"

# Platform detection
detect_platform() {
    local os arch
    
    case "$(uname -s)" in
        Linux)  os="linux" ;;
        Darwin) os="macos" ;;
        *)      echo -e "${RED}Unsupported OS: $(uname -s)${NC}"; exit 1 ;;
    esac
    
    case "$(uname -m)" in
        x86_64|amd64)   arch="x86_64" ;;
        aarch64|arm64)  arch="aarch64" ;;
        armv7l|armhf)   arch="armv7" ;;
        *)              echo -e "${RED}Unsupported architecture: $(uname -m)${NC}"; exit 1 ;;
    esac
    
    echo "${os}-${arch}"
}

# Ensure bootstrap Conan is available (before we have our venv)
ensure_bootstrap_conan() {
    echo -e "${CYAN}Checking for Conan (for bootstrap)...${NC}"
    
    if command -v conan &> /dev/null; then
        if conan --version | grep -q "Conan version 2"; then
            echo -e "${GREEN}  ✓ Conan 2.x found: $(conan --version | head -1)${NC}"
            return 0
        fi
    fi
    
    # Try pipx installation (preferred for isolated tools)
    if command -v pipx &> /dev/null; then
        echo -e "${YELLOW}Installing Conan via pipx...${NC}"
        pipx install "conan==${CONAN_VERSION}" 2>/dev/null || \
        pipx upgrade conan 2>/dev/null || true
        
        if command -v conan &> /dev/null && conan --version | grep -q "Conan version 2"; then
            echo -e "${GREEN}  ✓ Conan installed via pipx${NC}"
            return 0
        fi
    fi
    
    # Try user pip installation
    echo -e "${YELLOW}Installing Conan via pip (user)...${NC}"
    pip3 install --user "conan==${CONAN_VERSION}" 2>/dev/null || \
    pip3 install --user --break-system-packages "conan==${CONAN_VERSION}" 2>/dev/null || {
        echo -e "${YELLOW}  pip install failed, will use system Python${NC}"
        return 1
    }
    
    # Add user bin to PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    if command -v conan &> /dev/null; then
        echo -e "${GREEN}  ✓ Conan installed via pip${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}  ⚠ Conan not available, will use fallback Python setup${NC}"
    return 1
}

# Setup Conan remotes for sparetools packages
setup_conan_remotes() {
    echo -e "${CYAN}Configuring Conan remotes...${NC}"
    
    if ! command -v conan &> /dev/null; then
        echo -e "${YELLOW}  Conan not available, skipping remote setup${NC}"
        return 1
    fi
    
    # Add Cloudsmith remote for sparetools packages
    conan remote add sparesparrow-conan "$CLOUDSMITH_REMOTE" --force 2>/dev/null || true
    
    # Detect default profile if it doesn't exist
    if ! conan profile path default &>/dev/null; then
        conan profile detect --force
    fi
    
    echo -e "${GREEN}  ✓ Cloudsmith remote configured${NC}"
}

# Install sparetools-cpython from Conan
install_cpython_conan() {
    echo -e "${CYAN}Installing sparetools-cpython/${CPYTHON_VERSION} from Conan...${NC}"
    
    if ! command -v conan &> /dev/null; then
        return 1
    fi
    
    # Try to install from remote
    conan install --tool-requires="sparetools-cpython/${CPYTHON_VERSION}@" \
        --build=missing \
        -s build_type=Release 2>/dev/null && {
        echo -e "${GREEN}  ✓ sparetools-cpython installed from Cloudsmith${NC}"
        return 0
    }
    
    # Try to build from sparetools submodule if available
    local sparetools_cpython="$PROJECT_ROOT/external/sparetools/packages/sparetools-cpython"
    
    if [ -d "$sparetools_cpython" ]; then
        echo -e "${YELLOW}  Building sparetools-cpython from submodule...${NC}"
        cd "$sparetools_cpython"
        conan create . --version="${CPYTHON_VERSION}" --build=missing && {
            cd "$PROJECT_ROOT"
            echo -e "${GREEN}  ✓ sparetools-cpython built locally${NC}"
            return 0
        }
        cd "$PROJECT_ROOT"
    fi
    
    echo -e "${YELLOW}  ⚠ Could not install sparetools-cpython${NC}"
    return 1
}

# Find CPython in Conan cache and create zero-copy symlinks
create_zero_copy_python() {
    echo -e "${CYAN}Creating zero-copy Python environment...${NC}"
    
    if [ ! -d "${CONAN_CACHE}" ]; then
        echo -e "${YELLOW}  Conan cache not found${NC}"
        return 1
    fi
    
    # Find sparetools-cpython package
    local cpython_bin=$(find "${CONAN_CACHE}" -type d -path "*/sparetools-cpython*/package/*/bin" 2>/dev/null | head -1)
    
    if [ -z "$cpython_bin" ]; then
        echo -e "${YELLOW}  CPython not found in Conan cache${NC}"
        return 1
    fi
    
    local cpython_root=$(dirname "$cpython_bin")
    echo -e "${GREEN}  Found CPython at: ${cpython_root}${NC}"
    
    # Create directories
    rm -rf "${PYTHON_DIR}"
    mkdir -p "${PYTHON_DIR}"/{bin,lib}
    
    # Symlink binaries
    local symlink_count=0
    for bin_file in "${cpython_root}"/bin/*; do
        if [ -f "$bin_file" ] || [ -x "$bin_file" ]; then
            ln -sf "$bin_file" "${PYTHON_DIR}/bin/$(basename "$bin_file")"
            ((symlink_count++)) || true
        fi
    done
    
    # Symlink libraries
    if [ -d "${cpython_root}/lib" ]; then
        for lib_item in "${cpython_root}"/lib/*; do
            ln -sf "$lib_item" "${PYTHON_DIR}/lib/$(basename "$lib_item")"
            ((symlink_count++)) || true
        done
    fi
    
    echo -e "${GREEN}  ✓ Created ${symlink_count} symlinks (zero-copy)${NC}"
    
    # Create venv from symlinked Python
    local python_bin="${PYTHON_DIR}/bin/python3"
    if [ -x "$python_bin" ]; then
        echo -e "${BLUE}  Creating virtual environment from Conan CPython...${NC}"
        "$python_bin" -m venv "$VENV_DIR" --system-site-packages
        echo -e "${GREEN}  ✓ Virtual environment created${NC}"
        return 0
    fi
    
    return 1
}

# Fallback: Setup using system Python with venv
setup_system_python_venv() {
    echo -e "${YELLOW}Setting up virtual environment using system Python...${NC}"
    
    local python_cmd
    for cmd in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "$cmd" &> /dev/null; then
            python_cmd="$cmd"
            break
        fi
    done
    
    if [ -z "$python_cmd" ]; then
        echo -e "${RED}No suitable Python found. Install python3 first:${NC}"
        echo -e "${YELLOW}  sudo apt install python3 python3-venv python3-pip${NC}"
        exit 1
    fi
    
    local version=$("$python_cmd" --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}Using system Python: ${python_cmd} (${version})${NC}"
    
    # Create venv
    "$python_cmd" -m venv "$VENV_DIR" || {
        echo -e "${RED}Failed to create venv. Try: sudo apt install python3-venv${NC}"
        exit 1
    }
}

# Install build tools in the virtual environment
install_build_tools() {
    echo -e "${CYAN}Installing build tools...${NC}"
    
    # Activate venv
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install Conan
    echo -e "${BLUE}Installing Conan ${CONAN_VERSION}...${NC}"
    pip install "conan==${CONAN_VERSION}"
    
    # Install CMake (if not available system-wide)
    if ! command -v cmake &> /dev/null; then
        echo -e "${BLUE}Installing CMake...${NC}"
        pip install cmake
    fi
    
    # Install Ninja and Meson (build tools)
    pip install ninja meson
    
    deactivate
}

# Configure Conan
configure_conan() {
    echo -e "${CYAN}Configuring Conan...${NC}"
    
    source "$VENV_DIR/bin/activate"
    
    # Set Conan home
    export CONAN_HOME="$CONAN_HOME"
    mkdir -p "$CONAN_HOME"
    
    # Detect default profile
    conan profile detect --force
    
    # Add Cloudsmith remote
    conan remote add sparesparrow-conan "$CLOUDSMITH_REMOTE" --force 2>/dev/null || true
    
    # Copy project-specific profiles
    if [ -d "$PROJECT_ROOT/profiles" ]; then
        echo -e "${BLUE}Installing project Conan profiles...${NC}"
        mkdir -p "$CONAN_HOME/profiles"
        for profile in "$PROJECT_ROOT/profiles"/*; do
            if [ -f "$profile" ]; then
                local profile_name=$(basename "$profile")
                cp "$profile" "$CONAN_HOME/profiles/$profile_name"
                echo -e "${GREEN}  Installed profile: ${profile_name}${NC}"
            fi
        done
    fi
    
    deactivate
}

# Create environment activation script
create_env_script() {
    echo -e "${CYAN}Creating environment activation script...${NC}"
    
    mkdir -p "$BUILDENV_DIR"
    
    cat > "$BUILDENV_DIR/activate.sh" << 'ENVSCRIPT'
#!/bin/bash
# =============================================================================
# AI-SERVIS Build Environment Activation
# =============================================================================
# Source this script to activate the build environment:
#   source .buildenv/activate.sh
# =============================================================================

_BUILDENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AI_SERVIS_ROOT="$(cd "$_BUILDENV_DIR/.." && pwd)"
export AI_SERVIS_BUILDENV="$_BUILDENV_DIR"

# Check if bootstrap was run
if [ ! -d "$AI_SERVIS_BUILDENV/venv" ]; then
    echo "Build environment not set up. Run: ./tools/bootstrap.sh"
    return 1
fi

# Activate virtual environment
source "$AI_SERVIS_BUILDENV/venv/bin/activate"

# Set Conan home
export CONAN_HOME="$AI_SERVIS_BUILDENV/conan"

# Add project bin to PATH
export PATH="$AI_SERVIS_ROOT/bin:$PATH"

# Set build cache directory
export CCACHE_DIR="$AI_SERVIS_BUILDENV/ccache"

# Helper functions
ai-servis-build() {
    "$AI_SERVIS_ROOT/tools/build.sh" "$@"
}

ai-servis-clean() {
    echo "Cleaning build directories..."
    rm -rf "$AI_SERVIS_ROOT/build-"* 2>/dev/null
    rm -rf "$AI_SERVIS_ROOT/platforms/cpp/build" 2>/dev/null
    echo "Clean complete."
}

ai-servis-info() {
    echo "AI-SERVIS Build Environment (Sparetools)"
    echo "  Project Root: $AI_SERVIS_ROOT"
    echo "  Build Env:    $AI_SERVIS_BUILDENV"
    echo "  Python:       $(which python)"
    echo "  Conan:        $(which conan)"
    echo "  Conan Home:   $CONAN_HOME"
    echo ""
    echo "  Sparetools-based zero-copy environment"
    echo ""
    echo "Available commands:"
    echo "  ai-servis-build [target]  - Build components"
    echo "  ai-servis-clean           - Clean build directories"
    echo "  ai-servis-info            - Show this info"
    echo ""
    echo "Targets:"
    echo "  hardware-server  - Build hardware control server"
    echo "  mcp-server       - Build MCP tools server"
    echo "  all              - Build all C++ components"
}

export -f ai-servis-build ai-servis-clean ai-servis-info

echo "AI-SERVIS build environment activated (sparetools)."
echo "Run 'ai-servis-info' for help."
ENVSCRIPT

    chmod +x "$BUILDENV_DIR/activate.sh"
    
    # Create tools/env.sh wrapper
    cat > "$PROJECT_ROOT/tools/env.sh" << 'ENVSCRIPT'
#!/bin/bash
# AI-SERVIS environment activation wrapper
# Source this from project root: source tools/env.sh

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"

if [ -f "$_PROJECT_ROOT/.buildenv/activate.sh" ]; then
    source "$_PROJECT_ROOT/.buildenv/activate.sh"
else
    echo "Build environment not set up. Run: ./tools/bootstrap.sh"
    return 1
fi
ENVSCRIPT

    chmod +x "$PROJECT_ROOT/tools/env.sh"
}

# Create version file
create_version_file() {
    cat > "$PROJECT_ROOT/.tool-versions" << EOF
# AI-SERVIS Build Tool Versions (Sparetools Integration)
# Managed by tools/bootstrap.sh
python ${CPYTHON_VERSION}
conan ${CONAN_VERSION}
# Using sparetools-cpython from Conan: ${CLOUDSMITH_REMOTE}
EOF
}

# Update gitignore entries
update_gitignore() {
    local gitignore="$PROJECT_ROOT/.gitignore"
    local entries=(
        "# Build environment (generated by tools/bootstrap.sh)"
        ".buildenv/"
        "build-Debug/"
        "build-Release/"
    )
    
    for entry in "${entries[@]}"; do
        if ! grep -qF "$entry" "$gitignore" 2>/dev/null; then
            echo "$entry" >> "$gitignore"
        fi
    done
}

# Main setup function
main() {
    local mode="setup"
    local use_conan=true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --update)
                mode="update"
                shift
                ;;
            --clean)
                mode="clean"
                shift
                ;;
            --no-conan)
                use_conan=false
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --update      Update existing environment"
                echo "  --clean       Remove and reinstall everything"
                echo "  --no-conan    Skip Conan CPython, use system Python only"
                echo "  -h, --help    Show this help"
                echo ""
                echo "This script uses sparetools infrastructure for zero-copy"
                echo "Python environment setup via Conan packages."
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  AI-SERVIS Build Environment Setup (Sparetools Integration)${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ "$mode" = "clean" ]; then
        echo -e "${YELLOW}Removing existing environment...${NC}"
        rm -rf "$BUILDENV_DIR"
    fi
    
    if [ "$mode" = "update" ] && [ -d "$VENV_DIR" ]; then
        echo -e "${CYAN}Updating existing environment...${NC}"
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip
        pip install --upgrade "conan==${CONAN_VERSION}"
        deactivate
        echo -e "${GREEN}Update complete!${NC}"
        exit 0
    fi
    
    # Create directories
    mkdir -p "$BUILDENV_DIR"
    mkdir -p "$CACHE_DIR"
    mkdir -p "$CONAN_HOME"
    
    # Detect platform
    local platform=$(detect_platform)
    echo -e "${BLUE}Detected platform: ${platform}${NC}"
    
    # Try sparetools/Conan approach first
    local zero_copy_success=false
    
    if [ "$use_conan" = true ]; then
        if ensure_bootstrap_conan; then
            setup_conan_remotes
            
            if install_cpython_conan && create_zero_copy_python; then
                zero_copy_success=true
                echo -e "${GREEN}  ✓ Zero-copy Python environment ready${NC}"
            fi
        fi
    fi
    
    # Fallback to system Python if zero-copy didn't work
    if [ "$zero_copy_success" = false ]; then
        echo -e "${YELLOW}Using system Python fallback...${NC}"
        setup_system_python_venv
    fi
    
    # Install build tools
    install_build_tools
    
    # Configure Conan
    configure_conan
    
    # Create helper scripts
    create_env_script
    create_version_file
    update_gitignore
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ "$zero_copy_success" = true ]; then
        echo -e "${CYAN}Environment type: Zero-copy (sparetools-cpython)${NC}"
    else
        echo -e "${CYAN}Environment type: Standard venv (system Python)${NC}"
    fi
    echo ""
    echo -e "${CYAN}To activate the build environment:${NC}"
    echo -e "  ${YELLOW}source tools/env.sh${NC}"
    echo ""
    echo -e "${CYAN}To build all C++ components:${NC}"
    echo -e "  ${YELLOW}./tools/build.sh${NC}"
    echo ""
    echo -e "${CYAN}For help:${NC}"
    echo -e "  ${YELLOW}./tools/build.sh --help${NC}"
    echo ""
}

main "$@"
