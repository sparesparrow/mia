#!/bin/bash
# Setup script for TinyMCP integration with AI-SERVIS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Setting up TinyMCP for AI-SERVIS ==="

# Activate virtual environment if it exists
if [ -f "$WORKSPACE_DIR/venv/bin/activate" ]; then
    source "$WORKSPACE_DIR/venv/bin/activate"
fi

# Ensure Conan is installed
if ! command -v conan &> /dev/null; then
    echo "Installing Conan..."
    pip install conan
fi

# Create and export TinyMCP package
echo "Building TinyMCP Conan package..."
cd "$WORKSPACE_DIR/conan-recipes/tinymcp"

# Create the package in local cache
conan create . --user=ai-servis --channel=stable \
    --build=missing \
    -o tinymcp/*:enable_logging=True \
    -o tinymcp/*:with_tests=False

# Export the recipe for reuse
conan export . ai-servis/stable

echo "TinyMCP package created successfully"

# Now build the MCP C++ Bridge with TinyMCP
echo "Building MCP C++ Bridge with TinyMCP..."
cd "$WORKSPACE_DIR/mcp-cpp-bridge"

# Create build directory
mkdir -p build
cd build

# Install dependencies including TinyMCP
conan install .. \
    --build=missing \
    --profile="$WORKSPACE_DIR/profiles/linux-release" \
    -o mcp-cpp-bridge/*:with_python=True \
    -o mcp-cpp-bridge/*:with_grpc=True \
    -o mcp-cpp-bridge/*:with_mqtt=True

# Build with CMake
cmake .. \
    -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DMCP_WITH_PYTHON=ON \
    -DMCP_WITH_GRPC=ON \
    -DMCP_WITH_MQTT=ON \
    -DMCP_ENABLE_TESTING=ON

cmake --build . --parallel $(nproc)

echo "=== Build complete ==="

# Run tests if available
if [ -f "bin/mcp-cpp-bridge-tests" ]; then
    echo "Running tests..."
    ctest --output-on-failure
fi

echo "=== Setup complete ==="
echo ""
echo "TinyMCP has been successfully integrated into the AI-SERVIS MCP C++ Bridge."
echo "The following components are now available:"
echo "  - TinyMCP base library (tinymcp/0.2.0@ai-servis/stable)"
echo "  - MCP C++ Bridge with TinyMCP integration"
echo "  - Python bindings for high-level orchestration"
echo ""
echo "To use in your project, add to your conanfile.txt or conanfile.py:"
echo "  tinymcp/0.2.0@ai-servis/stable"
echo "  mcp-cpp-bridge/1.0.0@ai-servis/stable"