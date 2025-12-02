#!/bin/bash
set -e

echo "========================================"
echo "  AI-SERVIS Raspberry Pi Build"
echo "========================================"
echo ""

BUILD_DIR="build-raspberry-pi"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure CMake
echo "Configuring CMake..."
cmake ../platforms/cpp/core \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER=g++ \
    -DCMAKE_C_COMPILER=gcc

# Build
echo ""
echo "Building..."
make -j$(nproc)

echo ""
echo "Build complete!"
echo ""
echo "Binaries:"
echo "  - ai-servis-rpi: Main Raspberry Pi application"
echo "  - hardware-server: Hardware control server"
echo "  - tests: Test suite"
echo ""
