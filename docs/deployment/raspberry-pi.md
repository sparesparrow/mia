# Raspberry Pi Deployment Guide

This guide covers deploying MIA on a Raspberry Pi 4B.

## Prerequisites

### Hardware
- Raspberry Pi 4B (2GB+ RAM recommended)
- MicroSD card (32GB+ recommended)
- Power supply (5V 3A USB-C)
- Network connection (Ethernet or WiFi)

### Optional Hardware
- ELM327 OBD-II adapter (USB or Bluetooth)
- Arduino/ESP32 for GPIO expansion
- WS2812 LED strip for status indicators

## Installation

### 1. Prepare the SD Card

Download and install Raspberry Pi OS Lite (64-bit recommended):

```bash
# Using Raspberry Pi Imager or:
sudo dd if=2024-03-15-raspios-bookworm-arm64-lite.img of=/dev/sdX bs=4M status=progress
```

Enable SSH before first boot:
```bash
touch /boot/ssh
```

### 2. Initial System Setup

After first boot, update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

Install required system packages:

```bash
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    libzmq3-dev \
    i2c-tools \
    screen
```

### 3. Clone the Repository

```bash
cd /home/mia
git clone https://github.com/sparesparrow/ai-servis.git
cd ai-servis
```

### 4. Install Python Dependencies

```bash
pip3 install --break-system-packages -r rpi/requirements.txt
```

Or use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r rpi/requirements.txt
```

### 5. Install systemd Services

```bash
sudo cp rpi/services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Enable services to start on boot:

```bash
# Core services
sudo systemctl enable mia-broker
sudo systemctl enable mia-api

# Hardware services (enable as needed)
sudo systemctl enable mia-gpio-worker
sudo systemctl enable mia-serial-bridge
sudo systemctl enable mia-obd-worker

# Citroën telemetry (if using OBD-II)
sudo systemctl enable mia-citroen-bridge
```

## Configuration

### Environment Variables

Create `/etc/mia/environment`:

```bash
sudo mkdir -p /etc/mia
sudo tee /etc/mia/environment << 'EOF'
# API Configuration
MIA_API_KEY=your_secure_api_key_here
# MIA_AUTH_DISABLED=1  # Uncomment to disable auth

# ZeroMQ Ports
ZMQ_BROKER_PORT=5555
ZMQ_PUB_PORT=5557

# OBD-II Configuration (if using)
ELM_SERIAL_PORT=/dev/ttyUSB0
ELM_BAUD_RATE=38400
# ELM_MOCK=1  # Uncomment for mock mode

# Device Registry
DEVICE_REGISTRY_PATH=/var/lib/mia/device_registry.json
EOF
```

Update service files to use environment file:

```bash
sudo systemctl edit mia-api --force
# Add:
# [Service]
# EnvironmentFile=/etc/mia/environment
```

### Serial Port Permissions

Add user to dialout group for serial access:

```bash
sudo usermod -a -G dialout mia
```

### GPIO Permissions

For GPIO access without root:

```bash
sudo usermod -a -G gpio mia
```

## Starting Services

### Start All Services

```bash
# Start core services
sudo systemctl start mia-broker
sleep 2
sudo systemctl start mia-api

# Start hardware services
sudo systemctl start mia-gpio-worker

# Start OBD services (if applicable)
sudo systemctl start mia-citroen-bridge
```

### Check Service Status

```bash
sudo systemctl status mia-*
```

### View Logs

```bash
# All MIA logs
journalctl -u 'mia-*' -f

# Specific service
journalctl -u mia-api -f
```

## Testing the Deployment

### Test API

```bash
# Health check
curl http://localhost:8000/

# Device list
curl http://localhost:8000/devices

# System status
curl http://localhost:8000/status
```

### Test with Authentication

```bash
# Set API key header
curl -H "X-API-Key: your_secure_api_key_here" http://localhost:8000/devices
```

### Test WebSocket

```python
import asyncio
import websockets

async def test():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        msg = await ws.recv()
        print(msg)

asyncio.run(test())
```

## OBD-II Setup (Citroën/PSA Vehicles)

### 1. Connect ELM327 Adapter

```bash
# Check if adapter is detected
ls -l /dev/ttyUSB*
```

### 2. Test in Mock Mode

```bash
ELM_MOCK=1 python3 agents/citroen_bridge.py
```

### 3. Test Real Connection

```bash
# Connect to vehicle OBD-II port
# Turn ignition ON (not necessarily engine running)
sudo systemctl start mia-citroen-bridge
journalctl -u mia-citroen-bridge -f
```

### Verify Telemetry

```bash
curl http://localhost:8000/telemetry
```

## Performance Tuning

### Memory Optimization

For 2GB RPi, add swap:

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### CPU Governor

Set performance mode:

```bash
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
journalctl -u mia-api -n 50 --no-pager

# Check dependencies
python3 -c "import zmq; print('ZMQ OK')"
python3 -c "import fastapi; print('FastAPI OK')"
```

### Port Already in Use

```bash
# Check what's using the port
sudo netstat -tulpn | grep -E "5555|8000"

# Kill conflicting process
sudo fuser -k 8000/tcp
```

### Serial Port Issues

```bash
# Check permissions
ls -la /dev/ttyUSB*

# Test serial connection
screen /dev/ttyUSB0 38400
# Type ATZ and press Enter (should see "ELM327...")
# Ctrl+A, K to exit
```

### GPIO Not Working

```bash
# Check if gpiomem is available
ls -la /dev/gpiomem

# Test GPIO
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"
```

## Security Recommendations

1. **Change default passwords**
2. **Enable firewall**:
   ```bash
   sudo apt install ufw
   sudo ufw allow ssh
   sudo ufw allow 8000/tcp  # API port
   sudo ufw enable
   ```
3. **Use HTTPS** (see TLS setup guide)
4. **Set strong API key**
5. **Regular updates**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Backup

### Backup Configuration

```bash
sudo tar -czvf mia-backup.tar.gz \
    /etc/mia/ \
    /var/lib/mia/ \
    /home/mia/ai-servis/config/
```

### Restore

```bash
sudo tar -xzvf mia-backup.tar.gz -C /
sudo systemctl restart mia-*
```

## Updates

### Update MIA

```bash
cd /home/mia/ai-servis
git pull origin main
pip3 install --break-system-packages -r rpi/requirements.txt
sudo systemctl restart mia-*
```
