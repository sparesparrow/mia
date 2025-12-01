#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Hardware Control Server with Conan${NC}"

# Check if Conan is installed
if ! command -v conan &> /dev/null; then
    echo -e "${RED}Conan is not installed. Please install it with: pip install conan${NC}"
    exit 1
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