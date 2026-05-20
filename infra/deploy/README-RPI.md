# Raspberry Pi Deployment Guide

> **Audience**: Ops engineers, deployment engineers

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
```

## Prerequisites

### On Local Machine
- `rsync` installed
- SSH access to Raspberry Pi
- SSH key configured (or password authentication)

### On Raspberry Pi
- Python 3 installed
- pip3 available
- User `mia` has access to `/dev/ttyUSB0`

## SSH Setup

```bash
# Generate SSH Key (if not exists)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy SSH Key to Raspberry Pi
ssh-copy-id mia@192.168.200.139

# Test Connection
ssh mia@192.168.200.139 "echo 'Connection successful'"
```

## Deployment Process

The deployment script will:
1. Test SSH Connection
2. Create directory structure under `/opt/mia`
3. Deploy Python modules
4. Deploy requirements and install dependencies
5. Verify deployment

## Post-Deployment

```bash
# Test Arduino Connection
ssh mia@192.168.200.139
cd /opt/mia
python3 modules/hardware-bridge/test_arduino_led.py /dev/ttyUSB0
```

## Troubleshooting

### SSH Connection Failed
```bash
ssh -v mia@192.168.200.139
ssh-add ~/.ssh/id_rsa
```

### Permission Denied on /dev/ttyUSB0
```bash
sudo chmod 666 /dev/ttyUSB0
sudo usermod -a -G dialout mia
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `RPI_USER` | `mia` | SSH username |
| `RPI_HOST` | `192.168.200.139` | Raspberry Pi IP address |
| `RPI_PORT` | `22` | SSH port |
| `RPI_PATH` | `/opt/mia` | Deployment path on Raspberry Pi |
| `SSH_KEY` | `` | Path to SSH private key (optional) |

For full deployment documentation, see [docs/PRODUCTION_DEPLOYMENT.md](../../docs/PRODUCTION_DEPLOYMENT.md).
