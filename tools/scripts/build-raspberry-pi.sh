#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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
SOURCE_DIR="$PROJECT_ROOT/apps/rpi-backend/cpp-audio"
# OFF, as in CI and CLAUDE.md. ON also builds hardware-server, which needs CMake packages for libgpiod and mosquitto
# (apt's -dev packages ship only pkg-config files; the Conan recipe is #125) and the libgpiod 1.x API (#197).
WITH_HARDWARE="${WITH_HARDWARE:-OFF}"

# Configure CMake
echo "Configuring CMake..."
cmake -S "$SOURCE_DIR" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER=g++ \
    -DCMAKE_C_COMPILER=gcc \
    -DWITH_HARDWARE="$WITH_HARDWARE"

# Build
echo ""
echo "Building..."
cmake --build "$BUILD_DIR" --parallel "$(get_cpu_count)"

echo ""
echo "Build complete!"
echo ""
echo "Binaries in $BUILD_DIR:"
echo "  - voice-server"
echo "  - webgrab-client, webgrab-server"
if [ "$WITH_HARDWARE" = "ON" ]; then
    echo "  - hardware-server: Hardware control server"
fi
echo ""
