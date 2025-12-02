# Raspberry Pi Deployment Guide

## Quick Start

### Using the Remote Deployment Script

```bash
# Option 1: Use default configuration (mia@192.168.200.139)
./scripts/deploy-raspberry-pi-remote.sh

# Option 2: Customize via environment variables
export RPI_USER="mia"
export RPI_HOST="192.168.200.139"
export RPI_PORT="22"
export SSH_KEY="~/.ssh/id_rsa"  # Optional
./scripts/deploy-raspberry-pi-remote.sh

# Option 3: Source configuration file
source deploy/rpi-config.sh
./scripts/deploy-raspberry-pi-remote.sh
```

## Prerequisites

### On Local Machine
- `rsync` installed
- SSH access to Raspberry Pi
- SSH key configured (or password authentication)

### On Raspberry Pi (192.168.200.139)
- Python 3 installed
- pip3 available
- Arduino connected to `/dev/ttyUSB0`
- User `mia` has access to `/dev/ttyUSB0`

## SSH Setup

### 1. Generate SSH Key (if not exists)
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### 2. Copy SSH Key to Raspberry Pi
```bash
ssh-copy-id mia@192.168.200.139
```

### 3. Test Connection
```bash
ssh mia@192.168.200.139 "echo 'Connection successful'"
```

## Deployment Process

The deployment script will:

1. **Test SSH Connection** - Verify connectivity to Raspberry Pi
2. **Create Directory Structure** - Set up remote directories
3. **Deploy Python Modules** - Copy Arduino LED controller modules
4. **Deploy Arduino Code** - Copy Arduino sketch and documentation
5. **Deploy Requirements** - Copy Python requirements file
6. **Install Dependencies** - Install Python packages on Raspberry Pi
7. **Verify Deployment** - Test module imports

## Post-Deployment

### Test Arduino Connection
```bash
ssh mia@192.168.200.139
cd /home/mia/ai-servis
python3 modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0
```

### Start MQTT Bridge
```bash
ssh mia@192.168.200.139
cd /home/mia/ai-servis
python3 -m modules.hardware_bridge.arduino_led_controller /dev/ttyUSB0 localhost
```

### Start MCP Server
```bash
ssh mia@192.168.200.139
cd /home/mia/ai-servis
python3 -m modules.hardware_bridge.arduino_led_mcp /dev/ttyUSB0 8084
```

## Configuration Files

- **`deploy/rpi-config.sh`** - Shell configuration with deployment variables
- **`deploy/rpi-deploy.yml`** - YAML configuration for automation tools
- **`scripts/deploy-raspberry-pi-remote.sh`** - Main deployment script

## Troubleshooting

### SSH Connection Failed
```bash
# Test SSH manually
ssh -v mia@192.168.200.139

# Check SSH key
ssh-add -l

# Add SSH key
ssh-add ~/.ssh/id_rsa
```

### Permission Denied on /dev/ttyUSB0
```bash
# On Raspberry Pi
sudo chmod 666 /dev/ttyUSB0
sudo usermod -a -G dialout mia
```

### Python Module Not Found
```bash
# On Raspberry Pi, check Python path
python3 -c "import sys; print('\n'.join(sys.path))"

# Install dependencies manually
cd /home/mia/ai-servis
python3 -m pip install --user -r modules/hardware-bridge/requirements.txt
```

## Advanced Usage

### Custom Deployment Path
```bash
export RPI_PATH="/opt/ai-servis"
./scripts/deploy-raspberry-pi-remote.sh
```

### Deploy Specific Components Only
Edit `scripts/deploy-raspberry-pi-remote.sh` and comment out sections you don't need.

### Automated Deployment with Cron
```bash
# Add to crontab for daily deployment
0 2 * * * cd /path/to/ai-servis && ./scripts/deploy-raspberry-pi-remote.sh >> /var/log/rpi-deploy.log 2>&1
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `RPI_USER` | `mia` | SSH username |
| `RPI_HOST` | `192.168.200.139` | Raspberry Pi IP address |
| `RPI_PORT` | `22` | SSH port |
| `RPI_PATH` | `/home/mia/ai-servis` | Deployment path on Raspberry Pi |
| `SSH_KEY` | `` | Path to SSH private key (optional) |
