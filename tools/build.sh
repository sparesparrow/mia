#!/bin/bash
# =============================================================================
# AI-SERVIS Build Script
# =============================================================================
# Build script for AI-SERVIS C++ components.
# Uses system libraries when available, falls back to Conan dependencies.
#
# Usage:
#   ./tools/build.sh              # Build all components
#   ./tools/build.sh --clean      # Clean and rebuild
#   ./tools/build.sh --release    # Release build (default)
#   ./tools/build.sh --debug      # Debug build
#   ./tools/build.sh --help       # Show help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default options
BUILD_TYPE="Release"
CLEAN_BUILD=false
USE_NINJA=true
BUILD_DIR="build"

get_cpu_count() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif command -v sysctl >/dev/null 2>&1; then
        sysctl -n hw.ncpu
    else
        printf '1\n'
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --release)
            BUILD_TYPE="Release"
            shift
            ;;
        --no-ninja)
            USE_NINJA=false
            shift
            ;;
        -h|--help)
            echo "AI-SERVIS Build Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --clean       Clean build directory before building"
            echo "  --debug       Build with debug symbols"
            echo "  --release     Build optimized release (default)"
            echo "  --no-ninja    Use Make instead of Ninja"
            echo "  -h, --help    Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI-SERVIS Build (${BUILD_TYPE})${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if ! command -v cmake >/dev/null 2>&1; then
    echo -e "${RED}cmake is required but was not found in PATH${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Determine generator
GENERATOR_ARGS=()
if [ "$USE_NINJA" = true ] && command -v ninja &> /dev/null; then
    GENERATOR_ARGS=(-G Ninja)
    echo -e "${CYAN}Using Ninja build system${NC}"
else
    echo -e "${CYAN}Using Make build system${NC}"
fi

# Clean if requested
if [ "$CLEAN_BUILD" = true ]; then
    echo -e "${YELLOW}Cleaning build directory...${NC}"
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Check if Conan toolchain exists (from conan install)
CONAN_TOOLCHAIN_ARGS=()
if [ -f "conan_toolchain.cmake" ]; then
    CONAN_TOOLCHAIN_ARGS=(-DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake)
    echo -e "${CYAN}Using Conan toolchain${NC}"
elif [ -f "../build-release/conan_toolchain.cmake" ]; then
    CONAN_TOOLCHAIN_ARGS=(-DCMAKE_TOOLCHAIN_FILE=../build-release/conan_toolchain.cmake)
    echo -e "${CYAN}Using Conan toolchain from build-release${NC}"
else
    echo -e "${YELLOW}No Conan toolchain found, using system libraries${NC}"
fi

# Configure
echo ""
echo -e "${CYAN}Configuring CMake...${NC}"
cmake "${GENERATOR_ARGS[@]}" \
    "-DCMAKE_BUILD_TYPE=$BUILD_TYPE" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    "${CONAN_TOOLCHAIN_ARGS[@]}" \
    ../platforms/cpp/core

# Build
echo ""
echo -e "${CYAN}Building...${NC}"
cmake --build . --parallel "$(get_cpu_count)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Build Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# List built binaries
echo -e "${CYAN}Built binaries:${NC}"
for binary in webgrab-client webgrab-server hardware-server mia-rpi; do
    if [ -f "$binary" ]; then
        echo -e "  ${GREEN}✓${NC} $binary"
    fi
done

echo ""
echo -e "${CYAN}To run tests:${NC}"
echo -e "  cd $BUILD_DIR && ctest --output-on-failure"
echo ""
