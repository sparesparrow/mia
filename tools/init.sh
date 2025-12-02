#!/bin/bash
# =============================================================================
# AI-SERVIS Development Environment Initialization
# =============================================================================
# Simple entry point that sets up the AI-SERVIS build environment.
# Uses Cloudsmith Conan remote for sparetools-cpython packages.
#
# Usage:
#   ./tools/init.sh              # Full setup
#   ./tools/init.sh --update     # Update existing environment
#   ./tools/init.sh --clean      # Remove and reinstall
#   source tools/init.sh --shell # Initialize for interactive use
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

# Display banner
show_banner() {
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════════════════════════════╗"
    echo "  ║         AI-SERVIS Development Environment                      ║"
    echo "  ║         Zero-Copy Bootstrap via Cloudsmith                     ║"
    echo "  ╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Setup Conan remote for sparetools packages
setup_conan_remotes() {
    echo -e "${CYAN}Setting up Conan remotes...${NC}"
    
    # Check if Conan is available
    if ! command -v conan &> /dev/null; then
        echo -e "${YELLOW}Conan not found. Will be installed during bootstrap.${NC}"
        return 0
    fi
    
    # Add Cloudsmith remote for sparetools packages
    conan remote add sparesparrow-conan \
        https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/ \
        --force 2>/dev/null || true
    
    # Verify remote was added
    if conan remote list | grep -q "sparesparrow-conan"; then
        echo -e "${GREEN}  ✓ Cloudsmith remote configured${NC}"
    fi
}

# Create AI-SERVIS specific zero-copy environment
create_ai_servis_env() {
    echo -e "${CYAN}Creating AI-SERVIS build environment...${NC}"
    
    # Run the create-zero-copy-env.sh script
    if [ -x "$SCRIPT_DIR/create-zero-copy-env.sh" ]; then
        bash "$SCRIPT_DIR/create-zero-copy-env.sh"
    else
        echo -e "${YELLOW}create-zero-copy-env.sh not found or not executable${NC}"
        echo -e "${YELLOW}Running full bootstrap instead...${NC}"
        bash "$SCRIPT_DIR/bootstrap.sh"
    fi
}

# Install AI-SERVIS specific Conan dependencies
install_ai_servis_deps() {
    echo -e "${CYAN}Installing AI-SERVIS Conan dependencies...${NC}"
    
    # Activate environment if available
    if [ -f "$BUILDENV_DIR/activate.sh" ]; then
        source "$BUILDENV_DIR/activate.sh"
    elif [ -f "${HOME}/.openssl-devenv/activate.sh" ]; then
        source "${HOME}/.openssl-devenv/activate.sh"
    fi
    
    # Check Conan
    if ! command -v conan &> /dev/null; then
        echo -e "${RED}Conan not available after bootstrap. Something went wrong.${NC}"
        exit 1
    fi
    
    # Install project dependencies using conanfile.py
    cd "$PROJECT_ROOT"
    
    echo -e "${BLUE}Installing dependencies from conanfile.py...${NC}"
    conan install . --build=missing --output-folder="$BUILDENV_DIR/conan" || {
        echo -e "${YELLOW}Conan install with options failed, trying basic install...${NC}"
        conan install . --build=missing
    }
    
    echo -e "${GREEN}  ✓ AI-SERVIS dependencies installed${NC}"
}

# Generate environment activation script
generate_activation_script() {
    echo -e "${CYAN}Generating AI-SERVIS activation script...${NC}"
    
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

# Activate sparetools environment if available
SPARETOOLS_ACTIVATE="${HOME}/.openssl-devenv/activate.sh"
if [ -f "$SPARETOOLS_ACTIVATE" ]; then
    source "$SPARETOOLS_ACTIVATE"
fi

# Fallback to local venv if sparetools not available
if [ -d "$AI_SERVIS_BUILDENV/venv" ]; then
    source "$AI_SERVIS_BUILDENV/venv/bin/activate"
fi

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
    echo "AI-SERVIS Build Environment"
    echo "  Project Root: $AI_SERVIS_ROOT"
    echo "  Build Env:    $AI_SERVIS_BUILDENV"
    echo "  Python:       $(which python3 2>/dev/null || which python 2>/dev/null || echo 'not found')"
    echo "  Conan:        $(which conan 2>/dev/null || echo 'not found')"
    echo "  Conan Home:   $CONAN_HOME"
    echo ""
    echo "Available commands:"
    echo "  ai-servis-build [target]  - Build components"
    echo "  ai-servis-clean           - Clean build directories"
    echo "  ai-servis-info            - Show this info"
}

export -f ai-servis-build ai-servis-clean ai-servis-info

echo "AI-SERVIS build environment activated."
echo "Run 'ai-servis-info' for help."
ENVSCRIPT

    chmod +x "$BUILDENV_DIR/activate.sh"
    
    # Also create tools/env.sh as an alias
    cat > "$SCRIPT_DIR/env.sh" << 'ENVSCRIPT'
#!/bin/bash
# AI-SERVIS environment activation wrapper
# Source this from project root: source tools/env.sh

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"

if [ -f "$_PROJECT_ROOT/.buildenv/activate.sh" ]; then
    source "$_PROJECT_ROOT/.buildenv/activate.sh"
else
    echo "Build environment not set up. Run: ./tools/init.sh"
    return 1
fi
ENVSCRIPT

    chmod +x "$SCRIPT_DIR/env.sh"
    
    echo -e "${GREEN}  ✓ Activation scripts created${NC}"
}

# Main function
main() {
    local mode="setup"
    local shell_mode=false
    
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
            --shell)
                shell_mode=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --update    Update existing environment"
                echo "  --clean     Remove and reinstall everything"
                echo "  --shell     Just activate for interactive shell"
                echo "  -h, --help  Show this help"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Shell mode - just activate existing environment
    if [ "$shell_mode" = true ]; then
        if [ -f "$BUILDENV_DIR/activate.sh" ]; then
            source "$BUILDENV_DIR/activate.sh"
            return 0
        else
            echo "Environment not set up. Run: ./tools/init.sh"
            return 1
        fi
    fi
    
    show_banner
    
    # Clean mode
    if [ "$mode" = "clean" ]; then
        echo -e "${YELLOW}Removing existing environment...${NC}"
        rm -rf "$BUILDENV_DIR"
        rm -rf "${HOME}/.openssl-devenv"
        mode="setup"
    fi
    
    # Update mode
    if [ "$mode" = "update" ] && [ -f "$BUILDENV_DIR/activate.sh" ]; then
        echo -e "${CYAN}Updating existing environment...${NC}"
        source "$BUILDENV_DIR/activate.sh"
        
        if command -v pip &> /dev/null; then
            pip install --upgrade pip conan
        fi
        
        install_ai_servis_deps
        echo -e "${GREEN}Update complete!${NC}"
        exit 0
    fi
    
    # Full setup
    echo -e "${BLUE}Starting AI-SERVIS environment setup...${NC}"
    echo ""
    
    setup_conan_remotes
    create_ai_servis_env
    generate_activation_script
    install_ai_servis_deps
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}To activate the build environment:${NC}"
    echo -e "  ${YELLOW}source tools/env.sh${NC}"
    echo ""
    echo -e "${CYAN}Or use the full activation script:${NC}"
    echo -e "  ${YELLOW}source .buildenv/activate.sh${NC}"
    echo ""
    echo -e "${CYAN}To build all C++ components:${NC}"
    echo -e "  ${YELLOW}./tools/build.sh${NC}"
    echo ""
}

main "$@"
