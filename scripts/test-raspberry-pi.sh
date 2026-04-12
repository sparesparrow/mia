#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================"
echo "  AI-SERVIS Raspberry Pi Test Suite"
echo "========================================"
echo ""

BUILD_DIR="$PROJECT_ROOT/build-raspberry-pi"

if [ ! -d "$BUILD_DIR" ]; then
    echo "Build directory not found: $BUILD_DIR" >&2
    echo "Run ./scripts/build-raspberry-pi.sh first." >&2
    exit 1
fi

cd "$BUILD_DIR"

# Run tests
echo "Running tests..."
if [ -f "CTestTestfile.cmake" ] || [ -f "DartConfiguration.tcl" ]; then
    ctest --output-on-failure
elif [ -x tests ]; then
    ./tests
else
    echo "Tests not built. Building tests..."
    cmake --build . --target tests

    if [ -f "CTestTestfile.cmake" ] || [ -f "DartConfiguration.tcl" ]; then
        ctest --output-on-failure
    elif [ -x tests ]; then
        ./tests
    else
        echo "Tests target built, but no runnable test entrypoint was found." >&2
        exit 1
    fi
fi

echo ""
echo "Tests complete!"
