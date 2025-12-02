#!/bin/bash
# =============================================================================
# AI-SERVIS Zero-Copy Environment Setup
# =============================================================================
# Creates symlinks to Conan cache packages for zero-copy development.
# Reuses sparetools-cpython from Conan cache instead of downloading separately.
#
# Usage:
#   ./tools/create-zero-copy-env.sh
#
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
BUILDENV_DIR="$PROJECT_ROOT/.buildenv"
CONAN_CACHE="${HOME}/.conan2/p"

# Sparetools CPython version to use
CPYTHON_VERSION="3.12.7"
CONAN_VERSION="2.3.2"

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  AI-SERVIS Zero-Copy Environment Setup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Ensure Conan is available (use system conan or pipx installed conan)
ensure_conan() {
    echo -e "${BLUE}Checking for Conan...${NC}"
    
    if command -v conan &> /dev/null; then
        echo -e "${GREEN}  ✓ Conan found: $(conan --version)${NC}"
        return 0
    fi
    
    # Try pipx installation
    if command -v pipx &> /dev/null; then
        echo -e "${YELLOW}Installing Conan via pipx...${NC}"
        pipx install "conan==${CONAN_VERSION}"
        
        if command -v conan &> /dev/null; then
            echo -e "${GREEN}  ✓ Conan installed via pipx${NC}"
            return 0
        fi
    fi
    
    # Try system pip as last resort (may fail on PEP 668 systems)
    echo -e "${YELLOW}Attempting pip install (may require --break-system-packages on newer systems)${NC}"
    pip3 install --user "conan==${CONAN_VERSION}" 2>/dev/null || \
    pip3 install --user --break-system-packages "conan==${CONAN_VERSION}" 2>/dev/null || {
        echo -e "${RED}Failed to install Conan. Please install it manually:${NC}"
        echo -e "${YELLOW}  pipx install conan${NC}"
        echo -e "${YELLOW}  # or${NC}"
        echo -e "${YELLOW}  pip install --user conan${NC}"
        exit 1
    }
    
    # Add user bin to PATH
    export PATH="$HOME/.local/bin:$PATH"
}

# Setup Conan remotes
setup_conan_remotes() {
    echo -e "${BLUE}Setting up Conan remotes...${NC}"
    
    # Add Cloudsmith remote for sparetools packages
    conan remote add sparesparrow-conan \
        https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/ \
        --force 2>/dev/null || true
    
    echo -e "${GREEN}  ✓ Cloudsmith remote configured${NC}"
    
    # Detect default profile if not exists
    if ! conan profile path default &>/dev/null; then
        conan profile detect --force
        echo -e "${GREEN}  ✓ Default profile created${NC}"
    fi
}

# Try to install sparetools-cpython from Conan
install_cpython_from_conan() {
    echo -e "${BLUE}Installing sparetools-cpython/${CPYTHON_VERSION} from Conan...${NC}"
    
    # Try to install from Cloudsmith remote
    conan install --tool-requires="sparetools-cpython/${CPYTHON_VERSION}@" \
        --build=missing \
        -s build_type=Release 2>/dev/null && {
        echo -e "${GREEN}  ✓ sparetools-cpython installed from Cloudsmith${NC}"
        return 0
    }
    
    # Cloudsmith is the only source - no submodule fallback
    echo -e "${YELLOW}  ⚠ sparetools-cpython not available from Cloudsmith${NC}"
    echo -e "${YELLOW}  Using system Python fallback...${NC}"
    return 1
}

# Find CPython in Conan cache
find_cpython_in_cache() {
    echo -e "${BLUE}Locating CPython in Conan cache...${NC}"
    
    if [ ! -d "${CONAN_CACHE}" ]; then
        echo -e "${YELLOW}  Conan cache not found: ${CONAN_CACHE}${NC}"
        return 1
    fi
    
    # Look for sparetools-cpython package
    CPYTHON_PKG=$(find "${CONAN_CACHE}" -type d -path "*/sparetools-cpython*/package/*/bin" 2>/dev/null | head -1)
    
    if [ -n "$CPYTHON_PKG" ]; then
        CPYTHON_ROOT=$(dirname "$CPYTHON_PKG")
        echo -e "${GREEN}  ✓ Found CPython at: ${CPYTHON_ROOT}${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}  CPython not found in Conan cache${NC}"
    return 1
}

# Create symlinks for zero-copy environment
create_symlinks() {
    echo -e "${BLUE}Creating zero-copy symlinks...${NC}"
    
    # Clean existing
    rm -rf "${BUILDENV_DIR}/python"
    mkdir -p "${BUILDENV_DIR}"/{python/bin,python/lib,venv}
    
    if [ -n "$CPYTHON_ROOT" ] && [ -d "$CPYTHON_ROOT" ]; then
        # Symlink CPython binaries
        for bin_file in "${CPYTHON_ROOT}"/bin/*; do
            if [ -f "$bin_file" ] || [ -x "$bin_file" ]; then
                ln -sf "$bin_file" "${BUILDENV_DIR}/python/bin/$(basename "$bin_file")"
            fi
        done
        
        # Symlink CPython libraries
        if [ -d "${CPYTHON_ROOT}/lib" ]; then
            for lib_item in "${CPYTHON_ROOT}"/lib/*; do
                ln -sf "$lib_item" "${BUILDENV_DIR}/python/lib/$(basename "$lib_item")"
            done
        fi
        
        # Create venv using symlinked Python
        PYTHON_BIN="${BUILDENV_DIR}/python/bin/python3"
        if [ -x "$PYTHON_BIN" ]; then
            echo -e "${BLUE}Creating virtual environment...${NC}"
            "$PYTHON_BIN" -m venv "${BUILDENV_DIR}/venv" --system-site-packages
            echo -e "${GREEN}  ✓ Virtual environment created${NC}"
        fi
        
        SYMLINK_COUNT=$(find "${BUILDENV_DIR}/python" -type l 2>/dev/null | wc -l)
        echo -e "${GREEN}  ✓ Created ${SYMLINK_COUNT} symlinks (zero-copy)${NC}"
    else
        echo -e "${YELLOW}  Using system Python for venv...${NC}"
        use_system_python
    fi
}

# Fallback to system Python
use_system_python() {
    echo -e "${BLUE}Setting up with system Python...${NC}"
    
    local python_cmd
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &> /dev/null; then
            python_cmd="$cmd"
            break
        fi
    done
    
    if [ -z "$python_cmd" ]; then
        echo -e "${RED}No suitable Python found. Please install Python 3.10+${NC}"
        exit 1
    fi
    
    local version=$("$python_cmd" --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}  Using: ${python_cmd} (${version})${NC}"
    
    # Create venv
    "$python_cmd" -m venv "${BUILDENV_DIR}/venv" || {
        echo -e "${RED}Failed to create venv. Try: sudo apt install python3-venv${NC}"
        exit 1
    }
    
    echo -e "${GREEN}  ✓ Virtual environment created${NC}"
}

# Install tools in the virtual environment
install_tools() {
    echo -e "${BLUE}Installing build tools in venv...${NC}"
    
    source "${BUILDENV_DIR}/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install Conan in venv (for project-local use)
    pip install "conan==${CONAN_VERSION}"
    
    # Install other build tools
    pip install ninja cmake meson
    
    deactivate
    
    echo -e "${GREEN}  ✓ Build tools installed${NC}"
}

# Configure Conan for AI-SERVIS
configure_conan() {
    echo -e "${BLUE}Configuring Conan for AI-SERVIS...${NC}"
    
    source "${BUILDENV_DIR}/venv/bin/activate"
    
    # Set Conan home to project-local directory
    export CONAN_HOME="${BUILDENV_DIR}/conan"
    mkdir -p "$CONAN_HOME"
    
    # Detect profile
    conan profile detect --force
    
    # Copy project profiles if available
    if [ -d "$PROJECT_ROOT/profiles" ]; then
        mkdir -p "$CONAN_HOME/profiles"
        for profile in "$PROJECT_ROOT/profiles"/*; do
            if [ -f "$profile" ]; then
                local profile_name=$(basename "$profile")
                cp "$profile" "$CONAN_HOME/profiles/$profile_name"
                echo -e "${GREEN}    Installed profile: ${profile_name}${NC}"
            fi
        done
    fi
    
    # Add remotes to local Conan home
    conan remote add sparesparrow-conan \
        https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/ \
        --force 2>/dev/null || true
    
    deactivate
    
    echo -e "${GREEN}  ✓ Conan configured${NC}"
}

# Verify the setup
verify_setup() {
    echo -e "${BLUE}Verifying setup...${NC}"
    
    source "${BUILDENV_DIR}/venv/bin/activate"
    
    # Check Python
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        echo -e "${GREEN}  ✓ Python: $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}  ✗ Python not found${NC}"
    fi
    
    # Check Conan
    if command -v conan &> /dev/null; then
        CONAN_VERSION=$(conan --version 2>&1)
        echo -e "${GREEN}  ✓ Conan: $CONAN_VERSION${NC}"
    else
        echo -e "${RED}  ✗ Conan not found${NC}"
    fi
    
    # Check CMake
    if command -v cmake &> /dev/null; then
        CMAKE_VERSION=$(cmake --version | head -1)
        echo -e "${GREEN}  ✓ CMake: $CMAKE_VERSION${NC}"
    else
        echo -e "${YELLOW}  ⚠ CMake not found (will use system cmake if available)${NC}"
    fi
    
    # Report zero-copy status
    SYMLINK_COUNT=$(find "${BUILDENV_DIR}" -type l 2>/dev/null | wc -l)
    FILE_COUNT=$(find "${BUILDENV_DIR}" -type f 2>/dev/null | wc -l)
    
    if [ "$SYMLINK_COUNT" -gt 0 ]; then
        echo -e "${GREEN}  ✓ Zero-copy: ${SYMLINK_COUNT} symlinks, ${FILE_COUNT} files${NC}"
    else
        echo -e "${YELLOW}  ⚠ Standard venv (no zero-copy symlinks)${NC}"
    fi
    
    deactivate
}

# Main execution
main() {
    ensure_conan
    setup_conan_remotes
    
    # Try to get CPython from Conan
    if install_cpython_from_conan; then
        find_cpython_in_cache
    fi
    
    create_symlinks
    install_tools
    configure_conan
    verify_setup
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Zero-Copy Environment Ready!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  To activate:"
    echo -e "    ${YELLOW}source ${BUILDENV_DIR}/activate.sh${NC}"
    echo ""
    echo -e "  Or from project root:"
    echo -e "    ${YELLOW}source tools/env.sh${NC}"
    echo ""
    echo -e "  Environment location: ${BUILDENV_DIR}"
}

main "$@"
