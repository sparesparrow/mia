# 🚗 MIA Complete Deployment Guide

This guide provides comprehensive instructions for deploying MIA (Modular Intelligent Automotive) system from scratch on a fresh Raspberry Pi OS or Ubuntu installation.

## 📋 Prerequisites

### Hardware Requirements
- **Raspberry Pi 4 or 5** (recommended) or Ubuntu/Debian system
- **8GB RAM minimum** (16GB recommended for full functionality)
- **32GB SD card/SSD minimum** (64GB+ recommended)
- **Stable power supply** (3A+ for Raspberry Pi)
- **Ethernet or WiFi** connectivity

### Software Requirements
- **Fresh Raspberry Pi OS** (64-bit) or **Ubuntu Server 22.04+**
- **SSH access** enabled
- **sudo privileges**
- **Internet connectivity** for package installation

## 🎯 Quick Start (5 minutes)

For the fastest deployment on a fresh Raspberry Pi:

```bash
# 1. Update system and install git
sudo apt update && sudo apt upgrade -y
sudo apt install -y git

# 2. Clone MIA repository
git clone https://github.com/sparesparrow/mia.git ~/mia
cd ~/mia

# 3. Run complete deployment
sudo ./scripts/deploy-complete-system.sh

# 4. Validate deployment
sudo ./scripts/validate-mia-deployment.py
```

That's it! Your MIA system will be fully operational.

## 📖 Detailed Deployment

### Phase 1: System Preparation

The deployment script handles complete system setup:

```bash
sudo ./scripts/deploy-complete-system.sh --phase system
```

**What it does:**
- ✅ Updates system packages
- ✅ Creates dedicated `mia` user with proper permissions
- ✅ Configures SSH security (disables password auth, root login)
- ✅ Sets up real-time scheduling limits
- ✅ Configures timezone and locale
- ✅ Enables persistent systemd journaling
- ✅ Sets up log rotation

### Phase 2: Repository Setup

```bash
sudo ./scripts/deploy-complete-system.sh --phase repository
```

**What it does:**
- ✅ Clones/updates MIA repository
- ✅ Verifies repository integrity
- ✅ Sets proper file permissions
- ✅ Configures Git (if needed)

### Phase 3: Dependencies Installation

```bash
sudo ./scripts/deploy-complete-system.sh --phase dependencies
```

**What it does:**
- ✅ Installs system build tools (cmake, gcc, etc.)
- ✅ Installs Python 3 and pip
- ✅ Installs all required system packages
- ✅ Installs Python dependencies (PyZMQ, FlatBuffers, etc.)
- ✅ Installs Raspberry Pi specific packages (RPi.GPIO, gpiozero)
- ✅ Verifies critical dependency functionality

### Phase 4: Hardware Configuration

```bash
sudo ./scripts/deploy-complete-system.sh --phase hardware
```

**What it does:**
- ✅ Enables I2C, SPI, and UART interfaces
- ✅ Configures GPIO permissions and udev rules
- ✅ Sets up Bluetooth with OBD-II class configuration
- ✅ Configures PulseAudio for audio processing
- ✅ Tests hardware interface functionality

### Phase 5: MIA Services Deployment

```bash
sudo ./scripts/deploy-complete-system.sh --phase services
```

**What it does:**
- ✅ Creates installation directory structure (`/opt/mia`)
- ✅ Copies MIA Python code and modules
- ✅ Installs systemd service files
- ✅ Configures service permissions and ownership
- ✅ Enables services for automatic startup

### Phase 6: Validation & Testing

```bash
sudo ./scripts/deploy-complete-system.sh --phase validate
```

**What it does:**
- ✅ Tests Python environment and imports
- ✅ Validates MIA installation structure
- ✅ Checks systemd service file syntax
- ✅ Tests network connectivity
- ✅ Validates hardware interfaces
- ✅ Performs service startup tests

### Phase 7: Monitoring Setup

```bash
sudo ./scripts/deploy-complete-system.sh --phase monitor
```

**What it does:**
- ✅ Installs Prometheus Node Exporter
- ✅ Configures log rotation for MIA services
- ✅ Sets up system monitoring scripts
- ✅ Creates health check utilities
- ✅ Configures automated monitoring timers

## 🔧 Manual Configuration Options

### Custom Installation Paths

```bash
# Use custom repository URL
REPO_URL="https://github.com/your-org/mia.git" sudo ./scripts/deploy-complete-system.sh

# Use different branch
REPO_BRANCH="development" sudo ./scripts/deploy-complete-system.sh

# Custom MIA user
MIA_USER="automotive" sudo ./scripts/deploy-complete-system.sh
```

### Selective Deployment

```bash
# Deploy only specific components
sudo ./scripts/deploy-complete-system.sh --phase dependencies --phase hardware

# Skip validation (faster deployment)
sudo ./scripts/deploy-complete-system.sh --skip-validation

# Verbose output
sudo ./scripts/deploy-complete-system.sh --verbose
```

### Hardware-Specific Options

```bash
# Disable Bluetooth features
ENABLE_BLUETOOTH=false sudo ./scripts/deploy-complete-system.sh

# Disable GPIO features
ENABLE_GPIO=false sudo ./scripts/deploy-complete-system.sh

# Disable serial features
ENABLE_SERIAL=false sudo ./scripts/deploy-complete-system.sh
```

## 🧪 Post-Deployment Validation

After deployment, run comprehensive validation:

```bash
# Run full validation suite
sudo ./scripts/validate-mia-deployment.py

# Generate detailed report
sudo ./scripts/validate-mia-deployment.py --output validation-report.json

# Verbose validation output
sudo ./scripts/validate-mia-deployment.py --verbose
```

### Validation Tests Include:
- ✅ System information and resources
- ✅ Python environment and dependencies
- ✅ MIA installation structure
- ✅ Hardware interface functionality
- ✅ Network connectivity
- ✅ Systemd service status
- ✅ Service integration testing
- ✅ Performance benchmarks

## 🚀 Starting and Managing Services

### Automatic Startup
Services are configured to start automatically on boot. To start manually:

```bash
# Start core services
sudo systemctl start mia-broker
sudo systemctl start mia-api

# Start hardware services (if available)
sudo systemctl start mia-gpio-worker
sudo systemctl start mia-serial-bridge
sudo systemctl start mia-obd-worker

# Start Bluetooth services (if available)
sudo systemctl start mia-ble-obd
sudo systemctl start mia-ble-advertiser
```

### Service Management

```bash
# Check service status
sudo systemctl status mia-*

# View service logs
sudo journalctl -u mia-broker -f
sudo journalctl -u mia-api -f

# Restart services
sudo systemctl restart mia-broker

# Stop all MIA services
sudo systemctl stop mia-*
```

## 📊 Monitoring and Maintenance

### Built-in Monitoring

```bash
# System monitoring
sudo mia-monitor

# Health checks
sudo mia-health-check

# View recent logs
sudo tail -f /var/log/mia/*.log
```

### Prometheus Metrics
- **Node Exporter**: http://localhost:9100
- Access system metrics and MIA service status

### Log Management
- Logs are automatically rotated daily
- Located in `/var/log/mia/`
- Systemd journal provides additional logging

## 🌐 Accessing MIA Services

### API Endpoints
- **REST API**: http://localhost:8000
  - Health check: `GET /health`
  - API docs: `GET /docs`
  - Device list: `GET /devices`
  - Telemetry: `GET /status`

### WebSocket
- **Real-time telemetry**: `ws://localhost:8000/ws`

### Hardware Interfaces
- **GPIO**: Direct hardware control via API
- **Serial**: ESP32/Arduino communication
- **Bluetooth**: OBD-II adapter connectivity
- **I2C/SPI**: Sensor and peripheral communication

## 🔧 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check service status
sudo systemctl status <service-name>

# View detailed logs
sudo journalctl -u <service-name> -n 50

# Check for dependency issues
sudo systemctl list-dependencies <service-name>
```

#### Hardware Not Detected
```bash
# Check GPIO permissions
groups $USER

# Test hardware interfaces
sudo i2cdetect -y 1
sudo hciconfig hci0
```

#### Network Issues
```bash
# Check connectivity
ping 8.8.8.8

# Check service ports
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :5555
```

#### Python Import Errors
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Reinstall dependencies
sudo pip3 install -r requirements.txt
```

### Recovery Procedures

#### Complete Redeployment
```bash
# Stop all services
sudo systemctl stop mia-*

# Remove installation
sudo rm -rf /opt/mia

# Re-run deployment
sudo ./scripts/deploy-complete-system.sh
```

#### Service Reset
```bash
# Reset specific service
sudo systemctl stop mia-broker
sudo systemctl disable mia-broker
sudo systemctl enable mia-broker
sudo systemctl start mia-broker
```

## 📚 Additional Resources

### Documentation
- **API Documentation**: `/opt/mia/docs/api.md`
- **Hardware Integration**: `/opt/mia/docs/hardware/`
- **Deployment Guide**: `/opt/mia/docs/deployment/`

### Configuration Files
- **System Config**: `/opt/mia/config/mia.conf`
- **Service Configs**: `/etc/systemd/system/mia-*.service`
- **Environment**: `/etc/mia/environment`

### Log Files
- **Application Logs**: `/var/log/mia/`
- **System Logs**: `sudo journalctl -u mia-*`
- **Deployment Logs**: `~/mia/deployment-*.log`

## 🚗 Ready for Automotive Integration

After successful deployment and validation:

1. ✅ **MIA Core Services** are running
2. ✅ **Hardware Interfaces** are configured
3. ✅ **Network Connectivity** is established
4. ✅ **Monitoring** is active
5. ✅ **API Endpoints** are accessible

Your MIA system is now ready for automotive AI integration! Connect your OBD-II adapter, Arduino sensors, or other automotive peripherals and start building intelligent vehicle applications.

---

**Need Help?**
- Check the troubleshooting section above
- Review deployment logs: `tail -f ~/mia/deployment-*.log`
- Run validation: `sudo ./scripts/validate-mia-deployment.py`
- Visit the project repository for updates and community support