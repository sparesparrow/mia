#!/bin/bash
# =============================================================================
# AI-SERVIS Raspberry Pi System Dependencies Installer
# =============================================================================
# Installs required system packages for building C++ components on Raspberry Pi.
# Run with sudo if needed for system package installation.
#
# Usage:
#   ./tools/install-deps-rpi.sh           # Install all dependencies
#   ./tools/install-deps-rpi.sh --minimal # Minimal build dependencies only
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

MINIMAL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --minimal)
            MINIMAL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--minimal]"
            echo ""
            echo "Options:"
            echo "  --minimal    Install only essential build tools"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Raspberry Pi Dependencies Installer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on Debian/Ubuntu-based system
if ! command -v apt-get &> /dev/null; then
    echo -e "${RED}This script is designed for Debian/Ubuntu-based systems.${NC}"
    echo -e "${YELLOW}Please install the following packages manually:${NC}"
    echo "  - cmake"
    echo "  - ninja-build or make"
    echo "  - g++ (version 11+)"
    echo "  - libgpiod-dev"
    echo "  - libmosquitto-dev"
    echo "  - libcurl4-openssl-dev"
    echo "  - libssl-dev"
    echo "  - libjsoncpp-dev"
    exit 1
fi

# Determine if we need sudo
SUDO=""
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
    echo -e "${YELLOW}Note: Some commands will use sudo${NC}"
fi

echo -e "${CYAN}Updating package lists...${NC}"
$SUDO apt-get update

# Essential build tools
ESSENTIAL_PKGS=(
    build-essential
    cmake
    ninja-build
    pkg-config
    git
)

# Python packages for venv (needed if standalone CPython fails)
PYTHON_PKGS=(
    python3
    python3-venv
    python3-pip
    python3-dev
)

# C++ development libraries
CPP_DEV_PKGS=(
    libgpiod-dev
    libmosquitto-dev
    libcurl4-openssl-dev
    libssl-dev
    zlib1g-dev
    libjsoncpp-dev
    libflatbuffers-dev
    flatbuffers-compiler
)

# Optional but useful packages
OPTIONAL_PKGS=(
    ccache
    gdb
    valgrind
    clang-format
    clang-tidy
)

# Runtime packages (libgpiod3 for Debian Trixie, libgpiod2 for older)
RUNTIME_PKGS=(
    mosquitto
    mosquitto-clients
)

echo -e "${CYAN}Installing essential build tools...${NC}"
$SUDO apt-get install -y "${ESSENTIAL_PKGS[@]}"

echo -e "${CYAN}Installing Python packages...${NC}"
$SUDO apt-get install -y "${PYTHON_PKGS[@]}"

echo -e "${CYAN}Installing C++ development libraries...${NC}"
$SUDO apt-get install -y "${CPP_DEV_PKGS[@]}"

if [ "$MINIMAL" = false ]; then
    echo -e "${CYAN}Installing optional development tools...${NC}"
    $SUDO apt-get install -y "${OPTIONAL_PKGS[@]}" 2>/dev/null || {
        echo -e "${YELLOW}Some optional packages not available, skipping...${NC}"
    }

    echo -e "${CYAN}Installing runtime packages...${NC}"
    $SUDO apt-get install -y "${RUNTIME_PKGS[@]}"
fi

# Check compiler version
echo ""
echo -e "${CYAN}Checking compiler version...${NC}"
GCC_VERSION=$(gcc -dumpversion 2>/dev/null || echo "0")
echo -e "${BLUE}GCC version: ${GCC_VERSION}${NC}"

if [ "$(printf '%s\n' "11" "$GCC_VERSION" | sort -V | head -n1)" != "11" ]; then
    echo -e "${YELLOW}Warning: GCC version is older than 11.${NC}"
    echo -e "${YELLOW}Consider installing a newer compiler for C++20 support:${NC}"
    echo -e "${YELLOW}  sudo apt-get install g++-11${NC}"
fi

# Check CMake version
CMAKE_VERSION=$(cmake --version 2>/dev/null | head -1 | awk '{print $3}' || echo "0")
echo -e "${BLUE}CMake version: ${CMAKE_VERSION}${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Dependencies Installed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Run the bootstrap script to set up Python/Conan:"
echo -e "     ${YELLOW}./tools/bootstrap.sh${NC}"
echo ""
echo -e "  2. Activate the build environment:"
echo -e "     ${YELLOW}source tools/env.sh${NC}"
echo ""
echo -e "  3. Build the project:"
echo -e "     ${YELLOW}./tools/build.sh${NC}"
echo ""
