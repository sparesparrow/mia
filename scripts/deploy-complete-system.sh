#!/bin/bash
# =============================================================================
# 🚗 MIA Complete System Deployment Script
# =============================================================================
# Comprehensive deployment from fresh Raspberry Pi OS to fully operational MIA system
# Handles: system setup, dependencies, services, validation, and monitoring
#
# Usage:
#   sudo ./scripts/deploy-complete-system.sh          # Full deployment
#   sudo ./scripts/deploy-complete-system.sh --phase system  # System setup only
#   sudo ./scripts/deploy-complete-system.sh --phase validate # Validation only
#   sudo ./scripts/deploy-complete-system.sh --help   # Show help
#
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOYMENT_LOG="$PROJECT_ROOT/deployment-$(date +%Y%m%d-%H%M%S).log"
PHASE="${PHASE:-all}"
SKIP_VALIDATION="${SKIP_VALIDATION:-false}"
VERBOSE="${VERBOSE:-false}"

# System configuration
MIA_USER="${MIA_USER:-mia}"
MIA_HOME="/home/$MIA_USER"
INSTALL_DIR="/opt/mia"
RPI_DIR="$INSTALL_DIR/rpi"
CONFIG_DIR="$INSTALL_DIR/config"
LOG_DIR="/var/log/mia"

# Repository configuration
REPO_URL="${REPO_URL:-https://github.com/sparesparrow/mia.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"

# Hardware configuration
ENABLE_BLUETOOTH="${ENABLE_BLUETOOTH:-true}"
ENABLE_GPIO="${ENABLE_GPIO:-true}"
ENABLE_SERIAL="${ENABLE_SERIAL:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# =============================================================================
# Utility Functions
# =============================================================================

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

log_phase() {
    echo -e "${PURPLE}[PHASE]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

# Command execution with logging
run_cmd() {
    local cmd="$1"
    local description="$2"

    log_step "$description"
    if [[ "$VERBOSE" == "true" ]]; then
        echo "  Command: $cmd" | tee -a "$DEPLOYMENT_LOG"
    fi

    if eval "$cmd" >> "$DEPLOYMENT_LOG" 2>&1; then
        log_success "$description completed"
        return 0
    else
        log_error "$description failed"
        return 1
    fi
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if running on Raspberry Pi
check_raspberry_pi() {
    if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        log_warning "This script is designed for Raspberry Pi. Continuing anyway..."
        read -p "Continue on non-Raspberry Pi system? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "Raspberry Pi detected: $(cat /proc/device-tree/model)"
    fi
}

# =============================================================================
# Banner and Help
# =============================================================================

show_banner() {
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║ 🚗 MIA Complete System Deployment                                           ║
║ From Fresh Raspberry Pi OS to Fully Operational AI Automotive System        ║
║                                                                              ║
║ Features:                                                                   ║
║  • Complete system setup from scratch                                       ║
║  • Hardware validation and configuration                                   ║
║  • Service deployment and monitoring                                       ║
║  • Security hardening and optimization                                     ║
║  • Comprehensive validation and testing                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo
}

show_help() {
    cat << EOF
MIA Complete System Deployment Script

USAGE:
    sudo $0 [OPTIONS]

OPTIONS:
    --phase PHASE       Run specific phase (see PHASES below)
    --skip-validation   Skip validation steps
    --verbose           Enable verbose output
    --help              Show this help message

PHASES:
    system              System preparation and user setup
    repository          Repository cloning and environment setup
    dependencies        System and Python dependencies installation
    hardware           Hardware configuration and validation
    services           MIA services deployment
    validate           Comprehensive system validation
    monitor            Monitoring and logging setup
    all                Complete deployment (default)

EXAMPLES:
    sudo $0                             # Full deployment
    sudo $0 --phase system              # System setup only
    sudo $0 --phase validate            # Validation only
    sudo $0 --verbose --skip-validation # Verbose deployment without validation

LOGGING:
    Deployment logs are saved to: deployment-YYYYMMDD-HHMMSS.log
    All commands and output are logged for troubleshooting

For more information, see docs/deployment/raspberry-pi.md
EOF
}

# =============================================================================
# Phase 1: System Preparation
# =============================================================================

phase_system() {
    log_phase "Phase 1: System Preparation"

    # Update system
    run_cmd "apt-get update" "Updating package lists"
    run_cmd "apt-get upgrade -y" "Upgrading system packages"

    # Install essential tools
    run_cmd "apt-get install -y curl wget git vim htop iotop lsof net-tools" "Installing essential system tools"

    # Create MIA user if it doesn't exist
    if ! id "$MIA_USER" &>/dev/null; then
        run_cmd "useradd -r -s /bin/bash -m -G dialout,bluetooth,audio,video,gpio,i2c,spi $MIA_USER" "Creating MIA system user"
        run_cmd "mkdir -p $MIA_HOME/.ssh" "Creating SSH directory for MIA user"
        run_cmd "chown -R $MIA_USER:$MIA_USER $MIA_HOME/.ssh" "Setting SSH directory permissions"
        run_cmd "chmod 700 $MIA_HOME/.ssh" "Setting SSH directory permissions"
    else
        log_info "MIA user already exists, updating groups"
        run_cmd "usermod -a -G dialout,bluetooth,audio,video,gpio,i2c,spi $MIA_USER" "Adding MIA user to required groups"
    fi

    # Configure SSH
    run_cmd "sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config" "Disabling SSH password authentication"
    run_cmd "sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config" "Disabling root SSH login"
    run_cmd "systemctl reload ssh" "Reloading SSH service"

    # Configure system limits for real-time operations
    cat > /etc/security/limits.d/mia.conf << EOF
$MIA_USER soft rtprio 50
$MIA_USER hard rtprio 50
$MIA_USER soft priority 10
$MIA_USER hard priority 10
$MIA_USER soft memlock 1024
$MIA_USER hard memlock 1024
EOF
    log_success "Configured real-time limits for MIA user"

    # Configure timezone and locale
    run_cmd "timedatectl set-timezone UTC" "Setting system timezone to UTC"
    run_cmd "localectl set-locale LANG=en_US.UTF-8" "Setting system locale"

    # Configure systemd journal for persistent logging
    run_cmd "mkdir -p /var/log/journal" "Creating journal directory"
    run_cmd "systemctl enable systemd-journald" "Enabling persistent journal"

    # Configure log rotation
    cat > /etc/logrotate.d/mia << EOF
/var/log/mia/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $MIA_USER $MIA_USER
    postrotate
        systemctl reload mia-* || true
    endscript
}
EOF
    log_success "Configured log rotation for MIA services"

    log_success "System preparation completed"
}

# =============================================================================
# Phase 2: Repository Setup
# =============================================================================

phase_repository() {
    log_phase "Phase 2: Repository Setup"

    # Install git if not present
    if ! command -v git &> /dev/null; then
        run_cmd "apt-get install -y git" "Installing Git"
    fi

    # Clone or update repository
    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        log_info "Repository already exists, updating"
        cd "$PROJECT_ROOT"
        run_cmd "git fetch origin" "Fetching latest changes"
        run_cmd "git checkout $REPO_BRANCH" "Checking out $REPO_BRANCH branch"
        run_cmd "git pull origin $REPO_BRANCH" "Pulling latest changes"
    else
        log_info "Cloning MIA repository"
        run_cmd "git clone -b $REPO_BRANCH $REPO_URL $PROJECT_ROOT" "Cloning MIA repository"
        cd "$PROJECT_ROOT"
    fi

    # Verify repository integrity against the current monorepo layout
    if [[ -f "apps/rpi-backend/py-api/api/main.py" ]] && [[ -f "infra/systemd/mia-api.service" ]] && [[ -f "config/paths.json" ]]; then
        log_success "Repository structure verified"
    else
        log_error "Repository structure incomplete for the current MIA layout"
        exit 1
    fi

    # Set repository permissions
    run_cmd "chown -R $MIA_USER:$MIA_USER $PROJECT_ROOT" "Setting repository ownership"
    run_cmd "chmod -R 755 $PROJECT_ROOT" "Setting repository permissions"

    log_success "Repository setup completed"
}

# =============================================================================
# Phase 3: Dependencies Installation
# =============================================================================

phase_dependencies() {
    log_phase "Phase 3: Dependencies Installation"

    # Install system build dependencies
    local build_deps=(
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

    run_cmd "apt-get install -y ${build_deps[*]}" "Installing system build dependencies"

    # Install Python build dependencies
    run_cmd "pip3 install --upgrade pip setuptools wheel" "Upgrading Python package managers"

    # Install Python dependencies
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        run_cmd "pip3 install -r $PROJECT_ROOT/requirements.txt" "Installing Python dependencies from requirements.txt"
    fi

    if [[ -f "$PROJECT_ROOT/rpi/requirements.txt" ]]; then
        run_cmd "pip3 install -r $PROJECT_ROOT/rpi/requirements.txt" "Installing Raspberry Pi specific Python dependencies"
    fi

    # Install MIA-specific Python packages
    local mia_packages=(
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

    run_cmd "pip3 install ${mia_packages[*]}" "Installing MIA-specific Python packages"

    # Install Raspberry Pi specific packages if on Pi
    if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        run_cmd "pip3 install RPi.GPIO gpiozero" "Installing Raspberry Pi GPIO libraries"
    fi

    # Verify critical dependencies
    local critical_deps=("python3" "pip3" "cmake" "gcc" "g++")
    for dep in "${critical_deps[@]}"; do
        if command -v "$dep" &> /dev/null; then
            log_success "$dep is available"
        else
            log_error "$dep is not available"
            exit 1
        fi
    done

    # Test Python imports
    python3 -c "
import sys
import zmq
import flatbuffers
import serial
try:
    import RPi.GPIO
    print('RPi.GPIO available')
except ImportError:
    print('RPi.GPIO not available (expected on non-Pi systems)')
print('Critical Python imports successful')
" 2>/dev/null || {
        log_error "Critical Python imports failed"
        exit 1
    }

    log_success "Dependencies installation completed"
}

# =============================================================================
# Phase 4: Hardware Configuration
# =============================================================================

phase_hardware() {
    log_phase "Phase 4: Hardware Configuration"

    # Enable I2C
    if [[ -f /boot/config.txt ]]; then
        if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
            echo "dtparam=i2c_arm=on" >> /boot/config.txt
            log_success "Enabled I2C interface"
        fi
    fi

    # Enable SPI
    if [[ -f /boot/config.txt ]]; then
        if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
            echo "dtparam=spi=on" >> /boot/config.txt
            log_success "Enabled SPI interface"
        fi
    fi

    # Enable serial console if needed
    if [[ -f /boot/config.txt ]]; then
        if ! grep -q "^enable_uart=1" /boot/config.txt; then
            echo "enable_uart=1" >> /boot/config.txt
            log_success "Enabled UART interface"
        fi
    fi

    # Configure GPIO permissions
    if [[ -f /etc/udev/rules.d/99-gpio.rules ]]; then
        log_info "GPIO udev rules already exist"
    else
        cat > /etc/udev/rules.d/99-gpio.rules << EOF
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", RUN+="/bin/sh -c 'chown root:dialout /dev/gpiochip* && chmod g+rw /dev/gpiochip*'"
SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add", RUN+="/bin/sh -c 'chown root:dialout /dev/gpio* && chmod g+rw /dev/gpio*'"
EOF
        run_cmd "udevadm control --reload-rules && udevadm trigger" "Reloading udev rules"
        log_success "Configured GPIO permissions"
    fi

    # Configure Bluetooth
    if [[ "$ENABLE_BLUETOOTH" == "true" ]]; then
        run_cmd "systemctl enable bluetooth" "Enabling Bluetooth service"
        run_cmd "systemctl start bluetooth" "Starting Bluetooth service"

        # Configure Bluetooth device class for OBD-II adapter
        cat > /etc/bluetooth/main.conf << EOF
[General]
Name = MIA OBD-II Adapter
Class = 0x002540
DiscoverableTimeout = 0
PairableTimeout = 0

[Policy]
AutoEnable=true
EOF
        run_cmd "systemctl restart bluetooth" "Restarting Bluetooth with new configuration"
        log_success "Configured Bluetooth for OBD-II operations"
    fi

    # Configure PulseAudio for audio processing
    if [[ -f /etc/pulse/default.pa ]]; then
        if ! grep -q "load-module module-null-sink" /etc/pulse/default.pa; then
            echo "load-module module-null-sink sink_name=MIA_Audio sink_properties=device.description=MIA_Audio_Processing" >> /etc/pulse/default.pa
            log_success "Configured PulseAudio for MIA audio processing"
        fi
    fi

    # Test hardware interfaces
    log_info "Testing hardware interfaces..."

    # Test GPIO (if available)
    if command -v python3 &> /dev/null; then
        python3 -c "
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT)
    GPIO.output(18, GPIO.LOW)
    GPIO.cleanup()
    print('GPIO test successful')
except ImportError:
    print('GPIO not available (expected on non-Pi systems)')
except Exception as e:
    print(f'GPIO test failed: {e}')
    exit(1)
" 2>/dev/null || log_warning "GPIO test failed"

        # Test I2C
        if command -v i2cdetect &> /dev/null; then
            i2cdetect -y 1 &>/dev/null && log_success "I2C interface available" || log_warning "I2C interface not available"
        fi

        # Test Bluetooth
        if command -v hciconfig &> /dev/null; then
            hciconfig hci0 &>/dev/null && log_success "Bluetooth interface available" || log_warning "Bluetooth interface not available"
        fi
    fi

    log_success "Hardware configuration completed"
}

# =============================================================================
# Phase 5: MIA Services Deployment
# =============================================================================

phase_services() {
    log_phase "Phase 5: MIA Services Deployment"

    local py_api_target="$INSTALL_DIR/apps/rpi-backend/py-api"
    local shared_target="$INSTALL_DIR/apps/rpi-backend/shared"
    local systemd_source_dir="$PROJECT_ROOT/infra/systemd"

    # Create installation directories
    run_cmd "mkdir -p '$INSTALL_DIR/bin' '$INSTALL_DIR/lib' '$CONFIG_DIR' '$LOG_DIR' '$INSTALL_DIR/apps/rpi-backend' '$py_api_target' '$shared_target' '$INSTALL_DIR/infra' '$INSTALL_DIR/Mia' '$INSTALL_DIR/scripts'" "Creating installation directories"
    run_cmd "chown -R $MIA_USER:$MIA_USER $INSTALL_DIR $LOG_DIR" "Setting directory ownership"

    # Copy the current Raspberry Pi runtime layout
    run_cmd "cp -r '$PROJECT_ROOT/apps/rpi-backend/py-api/.' '$py_api_target/'" "Copying Raspberry Pi API"

    if [[ -d "$PROJECT_ROOT/apps/rpi-backend/shared" ]]; then
        run_cmd "cp -r '$PROJECT_ROOT/apps/rpi-backend/shared/.' '$shared_target/'" "Copying shared runtime modules"
    fi

    if [[ -d "$PROJECT_ROOT/infra" ]]; then
        run_cmd "cp -r '$PROJECT_ROOT/infra/.' '$INSTALL_DIR/infra/'" "Copying deployment assets"
    fi

    if [[ -d "$PROJECT_ROOT/Mia" ]]; then
        run_cmd "cp -r '$PROJECT_ROOT/Mia/.' '$INSTALL_DIR/Mia/'" "Copying generated Mia bindings"
    fi

    if [[ -d "$PROJECT_ROOT/scripts" ]]; then
        run_cmd "cp -r '$PROJECT_ROOT/scripts/.' '$INSTALL_DIR/scripts/'" "Copying operational scripts"
    fi

    run_cmd "cp -r '$PROJECT_ROOT/config/.' '$INSTALL_DIR/config/'" "Copying MIA configuration"

    # Set permissions
    run_cmd "chown -R $MIA_USER:$MIA_USER $INSTALL_DIR" "Setting MIA installation ownership"
    run_cmd "chmod -R 755 $INSTALL_DIR" "Setting MIA installation permissions"

    # Create configuration files
    cat > "$CONFIG_DIR/mia.conf" << EOF
# MIA System Configuration
# Generated by deploy-complete-system.sh on $(date)

[system]
install_dir = $INSTALL_DIR
log_dir = $LOG_DIR
user = $MIA_USER

[networking]
broker_port = 5555
api_port = 8000
websocket_port = 8000

[hardware]
gpio_enabled = $ENABLE_GPIO
bluetooth_enabled = $ENABLE_BLUETOOTH
serial_enabled = $ENABLE_SERIAL

[logging]
level = INFO
max_size = 10MB
retention_days = 30
EOF
    log_success "Created MIA system configuration"

    # Copy systemd service files
    local services=(
        "zmq-broker.service"
        "mia-api.service"
        "mia-gpio-worker.service"
        "mia-serial-bridge.service"
        "mia-obd-worker.service"
        "mia-ble-obd.service"
        "mia-ble-advertiser.service"
        "mia-citroen-bridge.service"
    )

    for service in "${services[@]}"; do
        if [[ -f "$systemd_source_dir/$service" ]]; then
            run_cmd "cp '$systemd_source_dir/$service' /etc/systemd/system/" "Installing $service"
        fi
    done

    # Reload systemd
    run_cmd "systemctl daemon-reload" "Reloading systemd daemon"

    # Enable services
    local enable_services=(
        "zmq-broker.service"
        "mia-api.service"
    )

    if [[ "$ENABLE_GPIO" == "true" ]]; then
        enable_services+=("mia-gpio-worker.service")
    fi

    if [[ "$ENABLE_SERIAL" == "true" ]]; then
        enable_services+=("mia-serial-bridge.service" "mia-obd-worker.service")
    fi

    if [[ "$ENABLE_BLUETOOTH" == "true" ]]; then
        enable_services+=("mia-ble-obd.service" "mia-ble-advertiser.service")
    fi

    for service in "${enable_services[@]}"; do
        if [[ -f "/etc/systemd/system/$service" ]]; then
            run_cmd "systemctl enable $service" "Enabling $service"
        fi
    done

    log_success "MIA services deployment completed"
}

# =============================================================================
# Phase 6: Validation and Testing
# =============================================================================

phase_validate() {
    log_phase "Phase 6: Validation and Testing"

    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        log_info "Skipping validation as requested"
        return 0
    fi

    local validation_passed=true

    # Test 1: Python environment
    log_info "Testing Python environment..."
    if python3 -c "
import sys
import zmq
import flatbuffers
print('Python version:', sys.version)
print('Critical imports successful')
"; then
        log_success "Python environment validation passed"
    else
        log_error "Python environment validation failed"
        validation_passed=false
    fi

    # Test 2: MIA module imports
    log_info "Testing MIA module imports..."
    if PYTHONPATH="$INSTALL_DIR:$PYTHONPATH" python3 -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
try:
    from core.paths import PathConfig
    config = PathConfig()
    print('PathConfig loaded successfully')
    print('Project root:', config.project_root)
except Exception as e:
    print('PathConfig failed:', e)
    exit(1)
"; then
        log_success "MIA module imports validation passed"
    else
        log_error "MIA module imports validation failed"
        validation_passed=false
    fi

    # Test 3: Service file syntax
    log_info "Testing systemd service files..."
    local service_files=(
        "zmq-broker.service"
        "mia-api.service"
        "mia-gpio-worker.service"
        "mia-ble-obd.service"
    )

    for service_file in "${service_files[@]}"; do
        if [[ -f "/etc/systemd/system/$service_file" ]]; then
            if systemd-analyze verify "/etc/systemd/system/$service_file" &>/dev/null; then
                log_success "$service_file syntax is valid"
            else
                log_error "$service_file syntax is invalid"
                validation_passed=false
            fi
        fi
    done

    # Test 4: Network connectivity
    log_info "Testing network connectivity..."
    if ping -c 1 8.8.8.8 &>/dev/null; then
        log_success "Internet connectivity available"
    else
        log_warning "No internet connectivity detected"
    fi

    # Test 5: Hardware interfaces (if available)
    log_info "Testing hardware interfaces..."
    if command -v i2cdetect &>/dev/null; then
        if i2cdetect -y 1 &>/dev/null 2>&1; then
            log_success "I2C interface functional"
        else
            log_warning "I2C interface not functional"
        fi
    fi

    if command -v hciconfig &>/dev/null; then
        if hciconfig hci0 &>/dev/null 2>&1; then
            log_success "Bluetooth interface functional"
        else
            log_warning "Bluetooth interface not functional"
        fi
    fi

    # Test 6: Service startup (dry run)
    log_info "Testing service startup capability..."
    if [[ -f "/etc/systemd/system/zmq-broker.service" ]]; then
        if timeout 10s systemctl start zmq-broker 2>/dev/null; then
            log_success "Service startup test passed"
            systemctl stop zmq-broker 2>/dev/null || true
        else
            log_warning "Service startup test failed (may be expected)"
        fi
    fi

    if [[ "$validation_passed" == "true" ]]; then
        log_success "All validation tests passed"
    else
        log_warning "Some validation tests failed - check logs for details"
    fi
}

# =============================================================================
# Phase 7: Monitoring and Logging Setup
# =============================================================================

phase_monitor() {
    log_phase "Phase 7: Monitoring and Logging Setup"

    # Install monitoring tools
    run_cmd "apt-get install -y prometheus-node-exporter" "Installing Prometheus Node Exporter"

    # Configure logrotate for MIA logs
    cat > /etc/logrotate.d/mia-services << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 644 $MIA_USER $MIA_USER
    postrotate
        systemctl reload mia-* || true
    endscript
}
EOF
    log_success "Configured log rotation for MIA services"

    # Create monitoring script
    cat > /usr/local/bin/mia-monitor << EOF
#!/bin/bash
# MIA System Monitor
# Monitors service health and system resources

echo "=== MIA System Monitor ==="
echo "Timestamp: \$(date)"
echo

echo "=== Service Status ==="
services=("zmq-broker" "mia-api" "mia-gpio-worker" "mia-ble-obd")
for service in "\${services[@]}"; do
    if systemctl is-active --quiet \$service 2>/dev/null; then
        echo "✅ \$service: RUNNING"
    else
        echo "❌ \$service: STOPPED"
    fi
done
echo

echo "=== System Resources ==="
echo "CPU Usage: \$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - \$1"%"}')"
echo "Memory Usage: \$(free | grep Mem | awk '{printf "%.2f%%", \$3/\$2 * 100.0}')"
echo "Disk Usage: \$(df / | tail -1 | awk '{print \$5}')"
echo

echo "=== Network Status ==="
echo "IP Address: \$(hostname -I | awk '{print \$1}')"
if ping -c 1 8.8.8.8 &>/dev/null; then
    echo "Internet: ✅ Connected"
else
    echo "Internet: ❌ Disconnected"
fi
echo

echo "=== MIA Logs (Last 10 lines) ==="
tail -10 $LOG_DIR/*.log 2>/dev/null || echo "No logs available"
EOF

    run_cmd "chmod +x /usr/local/bin/mia-monitor" "Making MIA monitor script executable"

    # Create systemd timer for monitoring
    cat > /etc/systemd/system/mia-monitor.service << EOF
[Unit]
Description=MIA System Monitor

[Service]
Type=oneshot
ExecStart=/usr/local/bin/mia-monitor >> $LOG_DIR/monitor.log 2>&1
EOF

    cat > /etc/systemd/system/mia-monitor.timer << EOF
[Unit]
Description=Run MIA System Monitor every 5 minutes
Requires=mia-monitor.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

    run_cmd "systemctl daemon-reload" "Reloading systemd for monitoring services"
    run_cmd "systemctl enable mia-monitor.timer" "Enabling MIA monitoring timer"

    # Create health check script
    cat > /usr/local/bin/mia-health-check << EOF
#!/bin/bash
# MIA Health Check Script
# Performs comprehensive health checks and reports issues

ERRORS=0
WARNINGS=0

echo "=== MIA Health Check ==="
echo "Started at: \$(date)"
echo

# Check critical services
echo "Checking critical services..."
services=("mia-broker" "mia-api")
for service in "\${services[@]}"; do
    if ! systemctl is-active --quiet \$service 2>/dev/null; then
        echo "❌ CRITICAL: \$service is not running"
        ERRORS=\$((ERRORS + 1))
    else
        echo "✅ \$service is running"
    fi
done
echo

# Check optional services
echo "Checking optional services..."
optional_services=("mia-gpio-worker" "mia-ble-obd" "mia-serial-bridge")
for service in "\${optional_services[@]}"; do
    if systemctl is-active --quiet \$service 2>/dev/null; then
        echo "✅ \$service is running"
    else
        echo "⚠️  \$service is not running (optional)"
        WARNINGS=\$((WARNINGS + 1))
    fi
done
echo

# Check disk space
echo "Checking disk space..."
disk_usage=\$(df / | tail -1 | awk '{print \$5}' | sed 's/%//')
if [[ \$disk_usage -gt 90 ]]; then
    echo "❌ CRITICAL: Disk usage is \${disk_usage}% (above 90%)"
    ERRORS=\$((ERRORS + 1))
elif [[ \$disk_usage -gt 80 ]]; then
    echo "⚠️  WARNING: Disk usage is \${disk_usage}% (above 80%)"
    WARNINGS=\$((WARNINGS + 1))
else
    echo "✅ Disk usage is \${disk_usage}%"
fi
echo

# Check memory usage
echo "Checking memory usage..."
mem_usage=\$(free | grep Mem | awk '{printf "%.0f", \$3/\$2 * 100.0}')
if [[ \$mem_usage -gt 95 ]]; then
    echo "❌ CRITICAL: Memory usage is \${mem_usage}% (above 95%)"
    ERRORS=\$((ERRORS + 1))
elif [[ \$mem_usage -gt 85 ]]; then
    echo "⚠️  WARNING: Memory usage is \${mem_usage}% (above 85%)"
    WARNINGS=\$((WARNINGS + 1))
else
    echo "✅ Memory usage is \${mem_usage}%"
fi
echo

# Check network connectivity
echo "Checking network connectivity..."
if ping -c 1 8.8.8.8 &>/dev/null; then
    echo "✅ Internet connectivity is available"
else
    echo "❌ CRITICAL: No internet connectivity"
    ERRORS=\$((ERRORS + 1))
fi
echo

# Summary
echo "=== Health Check Summary ==="
echo "Errors: \$ERRORS"
echo "Warnings: \$WARNINGS"
echo "Completed at: \$(date)"
echo

if [[ \$ERRORS -gt 0 ]]; then
    echo "❌ Health check FAILED - immediate attention required"
    exit 1
elif [[ \$WARNINGS -gt 0 ]]; then
    echo "⚠️  Health check PASSED with warnings"
    exit 0
else
    echo "✅ Health check PASSED"
    exit 0
fi
EOF

    run_cmd "chmod +x /usr/local/bin/mia-health-check" "Making MIA health check script executable"

    log_success "Monitoring and logging setup completed"
}

# =============================================================================
# Main Function
# =============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --phase)
                PHASE="$2"
                shift 2
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Show banner
    show_banner

    # Initialize logging
    echo "MIA Complete System Deployment Log - $(date)" > "$DEPLOYMENT_LOG"
    echo "Command: $0 $*" >> "$DEPLOYMENT_LOG"
    echo "User: $(whoami)" >> "$DEPLOYMENT_LOG"
    echo "Host: $(hostname)" >> "$DEPLOYMENT_LOG"
    echo "Phase: $PHASE" >> "$DEPLOYMENT_LOG"
    echo "=================================================================" >> "$DEPLOYMENT_LOG"

    log_info "Starting MIA Complete System Deployment"
    log_info "Deployment log: $DEPLOYMENT_LOG"

    # Pre-deployment checks
    check_root
    check_raspberry_pi

    # Execute phases
    case "$PHASE" in
        "system")
            phase_system
            ;;
        "repository")
            phase_repository
            ;;
        "dependencies")
            phase_dependencies
            ;;
        "hardware")
            phase_hardware
            ;;
        "services")
            phase_services
            ;;
        "validate")
            phase_validate
            ;;
        "monitor")
            phase_monitor
            ;;
        "all")
            phase_system
            phase_repository
            phase_dependencies
            phase_hardware
            phase_services
            phase_validate
            phase_monitor
            ;;
        *)
            log_error "Unknown phase: $PHASE"
            show_help
            exit 1
            ;;
    esac

    # Post-deployment summary
    echo
    log_success "🎉 MIA Complete System Deployment Completed!"
    echo
    echo "📋 Deployment Summary:"
    echo "  📁 Installation Directory: $INSTALL_DIR"
    echo "  👤 MIA User: $MIA_USER"
    echo "  📝 Configuration: $CONFIG_DIR/mia.conf"
    echo "  📊 Logs: $LOG_DIR"
    echo "  🚨 Deployment Log: $DEPLOYMENT_LOG"
    echo
    echo "🛠️  Available Commands:"
    echo "  sudo systemctl start mia-broker        # Start message broker"
    echo "  sudo systemctl start mia-api           # Start REST API"
    echo "  sudo systemctl status mia-*            # Check all services"
    echo "  sudo mia-monitor                       # System monitoring"
    echo "  sudo mia-health-check                  # Health validation"
    echo
    echo "🌐 Access Points:"
    echo "  🔗 API: http://localhost:8000"
    echo "  📡 WebSocket: ws://localhost:8000/ws"
    echo "  📊 Monitoring: http://localhost:9100 (Node Exporter)"
    echo
    echo "📚 Documentation:"
    echo "  📖 README: $PROJECT_ROOT/README.md"
    echo "  🔧 Deployment: $PROJECT_ROOT/docs/deployment/raspberry-pi.md"
    echo "  ⚙️  Configuration: $PROJECT_ROOT/docs/WORKSPACE_ORGANIZATION.md"
    echo
    echo "🚗 Ready for automotive AI integration!"
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Trap for cleanup on exit
trap 'echo -e "\n${YELLOW}Deployment interrupted. Check log: $DEPLOYMENT_LOG${NC}"' INT TERM

# Execute main function
main "$@"