#!/bin/bash
# =============================================================================
# AI-SERVIS Hardware Server Build Script
# =============================================================================
# Builds the hardware control server using Conan for dependencies.
# Will automatically use the bundled build environment if available.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILDENV_DIR="$PROJECT_ROOT/.buildenv"

echo -e "${GREEN}Building Hardware Control Server with Conan${NC}"

# Check for bundled environment first
if [ -d "$BUILDENV_DIR/venv" ] && [ -f "$BUILDENV_DIR/venv/bin/activate" ]; then
    echo -e "${BLUE}Using bundled build environment${NC}"
    source "$BUILDENV_DIR/venv/bin/activate"
    export CONAN_HOME="$BUILDENV_DIR/conan"
elif [ -f "$PROJECT_ROOT/tools/env.sh" ]; then
    echo -e "${YELLOW}Activating build environment...${NC}"
    source "$PROJECT_ROOT/tools/env.sh"
fi

# Check if Conan is installed
if ! command -v conan &> /dev/null; then
    echo -e "${YELLOW}Conan is not installed in current environment.${NC}"
    
    # Try to bootstrap if not already done
    if [ -f "$PROJECT_ROOT/tools/bootstrap.sh" ]; then
        echo -e "${CYAN}Running bootstrap to set up build environment...${NC}"
        "$PROJECT_ROOT/tools/bootstrap.sh"
        source "$BUILDENV_DIR/venv/bin/activate"
        export CONAN_HOME="$BUILDENV_DIR/conan"
    else
        echo -e "${RED}Please run: ./tools/bootstrap.sh${NC}"
        exit 1
    fi
fi

# Create build directory
BUILD_DIR="platforms/cpp/build"
mkdir -p "$BUILD_DIR"

# Install dependencies with Conan
echo -e "${YELLOW}Installing dependencies with Conan...${NC}"
cd "$BUILD_DIR"

# Determine the correct path for conan install based on where we are
# If running from project root, use .; if from scripts/, use ../..
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "$PROJECT_ROOT/conanfile.py" ]; then
    CONAN_INSTALL_PATH="$PROJECT_ROOT"
else
    # Fallback: try to find conanfile.py
    CONAN_INSTALL_PATH=$(find . -name "conanfile.py" -type f | head -1 | xargs dirname 2>/dev/null || echo "../..")
fi

# Find profile
if [ -f "$PROJECT_ROOT/profiles/linux-release" ]; then
    PROFILE_PATH="$PROJECT_ROOT/profiles/linux-release"
elif [ -f "../../profiles/linux-release" ]; then
    PROFILE_PATH="../../profiles/linux-release"
else
    echo -e "${YELLOW}Warning: Profile not found, using default${NC}"
    PROFILE_PATH=""
fi

if [ -n "$PROFILE_PATH" ]; then
    conan install "$CONAN_INSTALL_PATH" --profile "$PROFILE_PATH" --build missing
else
    conan install "$CONAN_INSTALL_PATH" --build missing
fi

# Find the toolchain file - Conan generates it relative to where conan install was run
# Conan creates a 'conan' directory in the install location
# First, check in the current build directory
if [ -f "conan/conan_toolchain.cmake" ]; then
    TOOLCHAIN_PATH="$(pwd)/conan/conan_toolchain.cmake"
# Check in the project root's build-release directory (common Conan layout)
elif [ -f "$PROJECT_ROOT/build-release/conan/conan_toolchain.cmake" ]; then
    TOOLCHAIN_PATH="$PROJECT_ROOT/build-release/conan/conan_toolchain.cmake"
# Check relative to where conan install was run
elif [ -f "$CONAN_INSTALL_PATH/build-release/conan/conan_toolchain.cmake" ]; then
    TOOLCHAIN_PATH="$CONAN_INSTALL_PATH/build-release/conan/conan_toolchain.cmake"
# Try to find it anywhere in the project
else
    TOOLCHAIN_PATH=$(find "$PROJECT_ROOT" -name "conan_toolchain.cmake" -type f 2>/dev/null | head -1)
    if [ -z "$TOOLCHAIN_PATH" ]; then
        echo -e "${YELLOW}Warning: Could not find conan_toolchain.cmake${NC}"
        echo -e "${YELLOW}Conan may have generated it in a different location${NC}"
        echo -e "${YELLOW}Will try to build without Conan toolchain...${NC}"
        TOOLCHAIN_PATH=""
    fi
fi

# Configure with CMake
echo -e "${YELLOW}Configuring with CMake...${NC}"
if [ -n "$TOOLCHAIN_PATH" ]; then
    echo -e "${GREEN}Using toolchain: $TOOLCHAIN_PATH${NC}"
    cmake -S ../ -B . -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN_PATH" -DCMAKE_BUILD_TYPE=Release
else
    echo -e "${YELLOW}Building without Conan toolchain (using system packages)${NC}"
    cmake -S ../ -B . -DCMAKE_BUILD_TYPE=Release
fi

# Build
echo -e "${YELLOW}Building...${NC}"
cmake --build . --parallel "$(nproc)"

echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}Hardware server executable: ${BUILD_DIR}/hardware-server${NC}"
echo -e "${GREEN}MCP server executable: ${BUILD_DIR}/mcp-server${NC}"