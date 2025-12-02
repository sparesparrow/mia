#!/bin/bash
# =============================================================================
# Raspberry Pi Hardware Server Build Script
# =============================================================================
# Builds just the hardware-server component for Raspberry Pi.
# Uses minimal dependencies (no FlatBuffers complexity).
#
# Usage:
#   ./scripts/build-hardware-server-rpi.sh          # Build
#   ./scripts/build-hardware-server-rpi.sh --clean  # Clean and rebuild
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BUILD_DIR="$PROJECT_ROOT/build-hardware-server"
CMAKE_FILE="$PROJECT_ROOT/platforms/cpp/core/CMakeLists-rpi-minimal.txt"
SOURCE_DIR="$PROJECT_ROOT/platforms/cpp/core"

# Parse arguments
CLEAN_BUILD=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Raspberry Pi Hardware Server Build Script"
            echo ""
            echo "Usage: $0 [--clean]"
            echo ""
            echo "Options:"
            echo "  --clean    Clean build directory before building"
            echo "  -h, --help Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Raspberry Pi Hardware Server Build${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check for minimal CMakeLists
if [ ! -f "$CMAKE_FILE" ]; then
    echo -e "${RED}Error: Minimal CMakeLists not found: $CMAKE_FILE${NC}"
    exit 1
fi

# Clean if requested
if [ "$CLEAN_BUILD" = true ]; then
    echo -e "${YELLOW}Cleaning build directory...${NC}"
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"

# Create a temporary source directory with just the files we need
TEMP_SRC="$BUILD_DIR/src"
mkdir -p "$TEMP_SRC"

# Copy only the required source files
echo -e "${CYAN}Copying source files...${NC}"
cp "$CMAKE_FILE" "$TEMP_SRC/CMakeLists.txt"
cp "$SOURCE_DIR/main_hardware_server.cpp" "$TEMP_SRC/"
cp "$SOURCE_DIR/HardwareControlServer.cpp" "$TEMP_SRC/"

# Create a simplified header without MessageQueueProcessor dependency
cat > "$TEMP_SRC/HardwareControlServer.h" << 'HEADER_EOF'
#pragma once

// Third-party includes
#include <gpiod.hpp>
#include <json/json.h>

// Standard library includes
#include <atomic>
#include <memory>
#include <netinet/in.h>
#include <string>
#include <thread>
#include <unordered_map>
#include <mutex>

struct mosquitto;  // Forward declaration

namespace WebGrab {

/**
 * @brief Hardware Control Server for GPIO operations
 *
 * Provides GPIO control capabilities for Raspberry Pi via TCP + MQTT.
 */
class HardwareControlServer {
public:
    explicit HardwareControlServer(int port = 8081,
                                   const std::string& mqtt_host = "localhost",
                                   int mqtt_port = 1883,
                                   const std::string& working_dir = "/tmp/webgrab");
    ~HardwareControlServer();

    bool Start();
    void Stop();

private:
    int port;
    int serverSocket;
    std::atomic<bool> running;
    std::thread acceptThread;

    std::string mqtt_host;
    int mqtt_port;
    struct mosquitto* mqtt_client;
    std::thread mqttThread;
    std::mutex mqttMutex;

    std::unique_ptr<gpiod::chip> chip;
    std::unordered_map<int, gpiod::line> activeLines;

    bool InitializeGPIO();
    bool SetupServerSocket();
    bool InitializeMQTT();
    void AcceptConnections();
    void HandleClient(int clientSocket);
    void MQTTLoop();

    static void on_mqtt_connect(struct mosquitto* mosq, void* obj, int rc);
    static void on_mqtt_message(struct mosquitto* mosq, void* obj,
                               const struct mosquitto_message* msg);
    void HandleMQTTMessage(const std::string& topic, const std::string& payload);

    std::string HandleGPIOControl(const std::string& jsonRequest);
    bool SetGPIOPin(int pin, bool value);
    bool GetGPIOPin(int pin, bool& value);
    bool ConfigureGPIOPin(int pin, const std::string& direction);
};

} // namespace WebGrab
HEADER_EOF

cd "$BUILD_DIR"

# Determine generator
GENERATOR=""
if command -v ninja &> /dev/null; then
    GENERATOR="-G Ninja"
    echo -e "${CYAN}Using Ninja build system${NC}"
else
    echo -e "${CYAN}Using Make build system${NC}"
fi

# Configure
echo ""
echo -e "${CYAN}Configuring CMake...${NC}"
cmake $GENERATOR \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    "$TEMP_SRC"

# Build
echo ""
echo -e "${CYAN}Building...${NC}"
cmake --build . --parallel $(nproc)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Build Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ -f "$BUILD_DIR/hardware-server" ]; then
    echo -e "${CYAN}Built binary:${NC}"
    echo -e "  ${GREEN}✓${NC} $BUILD_DIR/hardware-server"
    echo ""
    echo -e "${CYAN}To run:${NC}"
    echo -e "  sudo $BUILD_DIR/hardware-server"
    echo ""
    echo -e "${CYAN}Note: GPIO access requires root privileges${NC}"
else
    echo -e "${RED}Build failed - hardware-server binary not found${NC}"
    exit 1
fi
