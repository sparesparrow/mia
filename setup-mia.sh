#!/bin/bash
# =============================================================================
# 🚗 MIA Quick Setup Script
# =============================================================================
# One-command deployment for MIA Automotive AI System
# Detects environment and runs appropriate deployment steps
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sparesparrow/mia/main/setup-mia.sh | sudo bash
#   # OR
#   wget -qO- https://raw.githubusercontent.com/sparesparrow/mia/main/setup-mia.sh | sudo bash
#
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
REPO_URL="https://github.com/sparesparrow/mia.git"
REPO_DIR="${REPO_DIR:-/opt/mia-repo}"
INSTALL_DIR="/opt/mia"
DEPLOYMENT_LOG="/tmp/mia-setup-$(date +%Y%m%d-%H%M%S).log"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_header() {
    echo -e "${PURPLE}[MIA SETUP]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        echo
        echo "Usage:"
        echo "  curl -fsSL https://raw.githubusercontent.com/sparesparrow/mia/main/setup-mia.sh | sudo bash"
        exit 1
    fi
}

# Detect system type
detect_system() {
    log_info "Detecting system configuration..."

    # Check if Raspberry Pi
    if [[ -f /proc/device-tree/model ]]; then
        if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
            SYSTEM_TYPE="raspberry_pi"
            SYSTEM_NAME="Raspberry Pi $(cat /proc/device-tree/model | sed 's/Raspberry Pi //')"
            log_info "Detected: $SYSTEM_NAME"
        else
            SYSTEM_TYPE="unknown"
            SYSTEM_NAME="Unknown device"
            log_warning "Unknown device type, continuing anyway..."
        fi
    else
        # Check for Ubuntu/Debian
        if [[ -f /etc/os-release ]]; then
            . /etc/os-release
            SYSTEM_TYPE="linux"
            SYSTEM_NAME="$PRETTY_NAME"
            log_info "Detected: $SYSTEM_NAME"
        else
            SYSTEM_TYPE="unknown"
            SYSTEM_NAME="Unknown Linux system"
            log_warning "Unknown system type, continuing anyway..."
        fi
    fi

    # Check architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            ARCH_NAME="x86_64"
            ;;
        aarch64)
            ARCH_NAME="ARM64"
            ;;
        armv7l)
            ARCH_NAME="ARM32"
            ;;
        *)
            ARCH_NAME="$ARCH"
            log_warning "Unusual architecture: $ARCH"
            ;;
    esac

    log_info "Architecture: $ARCH_NAME"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."

    # Check available memory
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    if [[ $total_mem -lt 1024 ]]; then
        log_warning "Low memory detected: ${total_mem}MB (1GB+ recommended)"
    else
        log_success "Memory: ${total_mem}MB available"
    fi

    # Check available disk space
    local available_space=$(df / | awk 'NR==2{print $4}')
    if [[ $available_space -lt 2097152 ]]; then  # 2GB in KB
        log_warning "Low disk space: $(df -h / | awk 'NR==2{print $4}') available (2GB+ recommended)"
    else
        log_success "Disk space: $(df -h / | awk 'NR==2{print $4}') available"
    fi

    # Check internet connectivity
    if ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log_success "Internet connectivity: Available"
    else
        log_error "No internet connectivity detected"
        exit 1
    fi
}

# Update system
update_system() {
    log_header "Updating system packages..."

    # Update package lists
    apt-get update

    # Upgrade system (answer yes to prompts)
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

    # Install essential tools
    apt-get install -y curl wget git vim htop iotop lsof net-tools

    log_success "System updated successfully"
}

# Install MIA dependencies
install_dependencies() {
    log_header "Installing MIA dependencies..."

    # Install system dependencies
    local system_deps=(
        build-essential
        cmake
        pkg-config
        libcurl4-openssl-dev
        libmosquitto-dev
        libgpiod-dev
        libjsoncpp-dev
        libflatbuffers-dev
        espeak
        espeak-data
        libespeak-dev
        mosquitto
        mosquitto-clients
        python3
        python3-pip
        python3-dev
        python3-venv
        libzmq3-dev
        libbluetooth-dev
        bluez
        bluez-tools
        python3-dbus
        python3-gi
        libgirepository1.0-dev
        libcairo2-dev
        libgtk-3-dev
        gir1.2-gtk-3.0
        pulseaudio-utils
        alsa-utils
        i2c-tools
        spi-tools
    )

    apt-get install -y "${system_deps[@]}"

    # Install Python dependencies
    pip3 install --upgrade pip setuptools wheel

    local python_deps=(
        pyzmq
        flatbuffers
        pyserial
        bleak
        bluepy
        dbus-python
        pygatt
        psutil
        aiohttp
        fastapi
        uvicorn
        pydantic
        websockets
        python-multipart
        ELM327-emulator
    )

    pip3 install "${python_deps[@]}"

    # Raspberry Pi specific packages
    if [[ "$SYSTEM_TYPE" == "raspberry_pi" ]]; then
        pip3 install RPi.GPIO gpiozero
        log_success "Installed Raspberry Pi specific packages"
    fi

    log_success "Dependencies installed successfully"
}

# Clone MIA repository
clone_repository() {
    log_header "Cloning MIA repository..."

    # Create repository directory
    mkdir -p "$REPO_DIR"

    # Clone repository
    if [[ -d "$REPO_DIR/.git" ]]; then
        log_info "Repository already exists, updating..."
        cd "$REPO_DIR"
        git fetch origin
        git checkout main
        git pull origin main
    else
        git clone "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
    fi

    # Verify repository
    if [[ -f "core/paths.py" ]] && [[ -f "scripts/deploy-complete-system.sh" ]]; then
        log_success "Repository cloned/updated successfully"
    else
        log_error "Repository verification failed"
        exit 1
    fi
}

# Run complete deployment
run_deployment() {
    log_header "Running complete MIA deployment..."

    cd "$REPO_DIR"

    # Make deployment script executable
    chmod +x scripts/deploy-complete-system.sh

    # Run deployment based on system type
    if [[ "$SYSTEM_TYPE" == "raspberry_pi" ]]; then
        log_info "Running full deployment for Raspberry Pi..."
        ./scripts/deploy-complete-system.sh --verbose
    else
        log_info "Running deployment for generic Linux system..."
        # Disable Pi-specific features
        ENABLE_GPIO=false ./scripts/deploy-complete-system.sh --verbose
    fi

    if [[ $? -eq 0 ]]; then
        log_success "MIA deployment completed successfully"
    else
        log_error "MIA deployment failed"
        exit 1
    fi
}

# Run validation
run_validation() {
    log_header "Running deployment validation..."

    cd "$REPO_DIR"

    # Make validation script executable
    chmod +x scripts/validate-mia-deployment.py

    # Run validation
    ./scripts/validate-mia-deployment.py --output "/tmp/mia-validation-$(date +%Y%m%d-%H%M%S).json"

    if [[ $? -eq 0 ]]; then
        log_success "Validation completed successfully"
    else
        log_warning "Validation found issues - check the detailed report"
    fi
}

# Display results
display_results() {
    log_header "🎉 MIA Setup Complete!"

    echo
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║ 🚗 MIA Automotive AI System Successfully Deployed!                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo
    echo "📋 Deployment Summary:"
    echo "  📁 Repository: $REPO_DIR"
    echo "  📦 Installation: $INSTALL_DIR"
    echo "  👤 System User: mia"
    echo "  📊 Logs: /var/log/mia/"
    echo "  📝 Deployment Log: $DEPLOYMENT_LOG"
    echo
    echo "🌐 Access Points:"
    echo "  🔗 API: http://localhost:8000"
    echo "  📡 WebSocket: ws://localhost:8000/ws"
    echo "  📈 Metrics: http://localhost:9100 (Prometheus)"
    echo
    echo "🛠️  Management Commands:"
    echo "  sudo systemctl status mia-*          # Check service status"
    echo "  sudo journalctl -u mia-broker -f     # View broker logs"
    echo "  sudo mia-monitor                     # System monitoring"
    echo "  sudo mia-health-check                # Health validation"
    echo
    echo "📚 Documentation:"
    echo "  $REPO_DIR/docs/deployment/COMPLETE_DEPLOYMENT_GUIDE.md"
    echo "  $REPO_DIR/README.md"
    echo
    echo "🚗 Ready for automotive AI integration!"
    echo
    echo "Next steps:"
    echo "1. Connect your OBD-II adapter or Arduino hardware"
    echo "2. Configure automotive peripherals as needed"
    echo "3. Start building intelligent vehicle applications"
    echo
}

# Cleanup function
cleanup() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_error "Setup failed with exit code $exit_code"
        echo
        echo "🔧 Troubleshooting:"
        echo "  📝 Check the log: $DEPLOYMENT_LOG"
        echo "  🔄 Re-run setup: curl -fsSL $REPO_URL/raw/main/setup-mia.sh | sudo bash"
        echo "  📖 See docs: $REPO_DIR/docs/deployment/COMPLETE_DEPLOYMENT_GUIDE.md"
        echo
    fi
}

# Main function
main() {
    # Set trap for cleanup
    trap cleanup EXIT

    # Initialize logging
    echo "MIA Quick Setup Log - $(date)" > "$DEPLOYMENT_LOG"
    echo "Command: $0 $*" >> "$DEPLOYMENT_LOG"
    echo "=================================================================" >> "$DEPLOYMENT_LOG"

    # Display banner
    echo
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║ 🚗 MIA Quick Setup - One-Command Automotive AI Deployment                 ║"
    echo "║ From Fresh System to Full MIA Operation in Minutes                         ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo

    log_info "Starting MIA Quick Setup..."
    log_info "Log file: $DEPLOYMENT_LOG"

    # Run setup phases
    check_root
    detect_system
    check_requirements
    update_system
    install_dependencies
    clone_repository
    run_deployment
    run_validation
    display_results

    log_success "MIA Quick Setup completed successfully!"
}

# Execute main function
main "$@"