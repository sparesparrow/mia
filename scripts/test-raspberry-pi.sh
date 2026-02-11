#!/bin/bash
set -e

echo "========================================"
echo "  AI-SERVIS Raspberry Pi Test Suite"
echo "========================================"
echo ""

BUILD_DIR="build-raspberry-pi"
cd "$BUILD_DIR"

# Run tests
echo "Running tests..."
if [ -f tests ]; then
    ./tests
else
    echo "Tests not built. Building tests..."
    cmake --build . --target tests
    ./tests
fi

echo ""
echo "Tests complete!"
