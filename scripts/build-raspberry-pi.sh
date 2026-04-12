#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

get_cpu_count() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif command -v sysctl >/dev/null 2>&1; then
        sysctl -n hw.ncpu
    else
        printf '1\n'
    fi
}

echo "========================================"
echo "  AI-SERVIS Raspberry Pi Build"
echo "========================================"
echo ""

if ! command -v cmake >/dev/null 2>&1; then
    echo "cmake is required but was not found in PATH" >&2
    exit 1
fi

BUILD_DIR="$PROJECT_ROOT/build-raspberry-pi"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure CMake
echo "Configuring CMake..."
cmake "$PROJECT_ROOT/platforms/cpp/core" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER=g++ \
    -DCMAKE_C_COMPILER=gcc

# Build
echo ""
echo "Building..."
cmake --build . --parallel "$(get_cpu_count)"

echo ""
echo "Build complete!"
echo ""
echo "Binaries:"
echo "  - mia-rpi: Main Raspberry Pi application"
echo "  - hardware-server: Hardware control server"
echo "  - tests: Test suite"
echo ""
