# Production Deployment Guide

This guide covers deploying the complete AI-Servis Automotive Integration system to a production Raspberry Pi.

## Prerequisites

- Raspberry Pi 4B (recommended) or Pi 3B+
- Raspberry Pi OS (Bullseye or later)
- Internet connection for initial setup
- OBD-II adapter (connected to vehicle's OBD-II port)
- Root/sudo access

## Quick Deployment

### Automated Deployment

The fastest way to deploy everything:

```bash
# On Raspberry Pi
cd ~/ai-servis
git pull origin main
sudo ./scripts/deploy-production-rpi.sh
```

This script will:
1. Update code from repository
2. Set up BLE services
3. Deploy main services
4. Enable and start all services
5. Verify deployment

### Manual Deployment Steps

If you prefer manual control:

#### 1. Update Code

```bash
cd ~/ai-servis
git checkout main
git pull origin main
```

#### 2. Setup BLE Services

```bash
sudo ./scripts/setup-ble-service.sh
```

#### 3. Deploy Main Services

```bash
sudo ./scripts/deploy-raspberry-pi.sh
```

#### 4. Enable Services

```bash
# Core services
sudo systemctl enable zmq-broker
sudo systemctl enable mia-api
sudo systemctl enable mia-gpio-worker

# OBD services
sudo systemctl enable mia-serial-bridge
sudo systemctl enable mia-obd-worker

# BLE services
sudo systemctl enable mia-ble-obd
sudo systemctl enable mia-ble-advertiser
```

#### 5. Start Services

```bash
# Start in order (broker first)
sudo systemctl start zmq-broker
sleep 2

# Start core services
sudo systemctl start mia-api
sudo systemctl start mia-gpio-worker
sleep 2

# Start OBD services
sudo systemctl start mia-serial-bridge
sudo systemctl start mia-obd-worker
sleep 2

# Start BLE services
sudo systemctl start mia-ble-advertiser
sudo systemctl start mia-ble-obd
```

## Service Verification

### Check Service Status

```bash
# Check all services
sudo systemctl status zmq-broker
sudo systemctl status mia-api
sudo systemctl status mia-gpio-worker
sudo systemctl status mia-serial-bridge
sudo systemctl status mia-obd-worker
sudo systemctl status mia-ble-obd
sudo systemctl status mia-ble-advertiser
```

### View Service Logs

```bash
# View logs for specific service
sudo journalctl -u mia-ble-obd -f
sudo journalctl -u mia-ble-advertiser -f
sudo journalctl -u mia-obd-worker -f

# View all MIA service logs
sudo journalctl -u mia-* -f
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/status

# List devices
curl http://localhost:8000/devices

# Get telemetry
curl http://localhost:8000/telemetry
```

### Test Bluetooth

```bash
# Check Bluetooth adapter
hciconfig hci0

# Should show:
# hci0:   Type: Primary  Bus: USB
#         BD Address: XX:XX:XX:XX:XX:XX  ACL MTU: 1021:8  SCO MTU: 64:1
#         UP RUNNING PSCAN ISCAN
```

## Configuration

### Change Device Name

Edit `/opt/ai-servis/rpi/services/ble_advertiser.py`:

```python
DEVICE_NAME = "Your Custom Name"
```

Then restart:
```bash
sudo systemctl restart mia-ble-advertiser
```

### Adjust OBD Polling Rate

Edit `/opt/ai-servis/rpi/services/obd_worker.py`:

```python
self.telemetry_interval = 0.1  # 10Hz (100ms)
```

Then restart:
```bash
sudo systemctl restart mia-obd-worker
```

### Configure API Port

Edit `/opt/ai-servis/rpi/api/main.py`:

```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Update systemd service if needed:
```bash
sudo systemctl edit mia-api
# Add:
# [Service]
# Environment="API_PORT=8000"
```

## Network Configuration

### Static IP Address (Recommended)

Edit `/etc/dhcpcd.conf`:

```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Then restart:
```bash
sudo systemctl restart dhcpcd
```

### Firewall Configuration

```bash
# Allow API access
sudo ufw allow 8000/tcp

# Allow SSH (if needed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

## Monitoring

### System Resources

```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Network connections
netstat -tulpn
```

### Service Health Checks

Create a health check script:

```bash
#!/bin/bash
# /opt/ai-servis/scripts/health-check.sh

services=(
    "zmq-broker"
    "mia-api"
    "mia-gpio-worker"
    "mia-obd-worker"
    "mia-ble-obd"
    "mia-ble-advertiser"
)

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "✓ $service is running"
    else
        echo "✗ $service is not running"
        systemctl restart "$service"
    fi
done
```

Run as cron job:
```bash
# Add to crontab
*/5 * * * * /opt/ai-servis/scripts/health-check.sh >> /var/log/ai-servis/health-check.log 2>&1
```

## Troubleshooting

### Services Won't Start

1. Check logs:
   ```bash
   sudo journalctl -u <service-name> -n 50
   ```

2. Check dependencies:
   ```bash
   # Verify ZeroMQ broker is running
   sudo systemctl status zmq-broker
   
   # Verify Bluetooth is enabled
   sudo systemctl status bluetooth
   ```

3. Check permissions:
   ```bash
   # Verify user has correct groups
   groups mia
   # Should include: bluetooth dialout gpio
   ```

### Bluetooth Issues

1. Reset Bluetooth adapter:
   ```bash
   sudo hciconfig hci0 down
   sudo hciconfig hci0 up
   ```

2. Restart Bluetooth service:
   ```bash
   sudo systemctl restart bluetooth
   ```

3. Make discoverable:
   ```bash
   sudo hciconfig hci0 piscan
   ```

### OBD Connection Issues

1. Verify OBD-II adapter is connected:
   ```bash
   ls -l /dev/ttyUSB* /dev/ttyACM*
   ```

2. Check serial bridge logs:
   ```bash
   sudo journalctl -u mia-serial-bridge -f
   ```

3. Test OBD worker directly:
   ```bash
   sudo -u mia python3 /opt/ai-servis/rpi/services/obd_worker.py
   ```

## Backup and Recovery

### Backup Configuration

```bash
# Backup service files
sudo tar -czf /home/mia/backup-services-$(date +%Y%m%d).tar.gz \
    /etc/systemd/system/mia-*.service \
    /opt/ai-servis/rpi
```

### Restore from Backup

```bash
# Extract backup
sudo tar -xzf backup-services-YYYYMMDD.tar.gz -C /

# Reload systemd
sudo systemctl daemon-reload

# Restart services
sudo systemctl restart mia-*
```

## Updates

### Update System

```bash
# Pull latest code
cd ~/ai-servis
git pull origin main

# Run deployment script
sudo ./scripts/deploy-production-rpi.sh
```

### Rollback

```bash
# Checkout previous version
cd ~/ai-servis
git log --oneline
git checkout <previous-commit-hash>

# Redeploy
sudo ./scripts/deploy-production-rpi.sh
```

## Security Considerations

### Change Default Passwords

```bash
# Change user password
sudo passwd mia
```

### Enable SSH Key Authentication

```bash
# Disable password authentication
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no

sudo systemctl restart sshd
```

### Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
sudo pip3 install --upgrade -r /opt/ai-servis/rpi/requirements.txt
```

## Performance Optimization

### Reduce Log Verbosity

Edit service files to change log level:
```python
logging.basicConfig(level=logging.WARNING)  # Instead of INFO
```

### Adjust Service Priorities

Edit systemd service files:
```ini
[Service]
Nice=10  # Lower priority (higher number = lower priority)
```

## Support

For issues or questions:
- **Documentation**: See [Quick Start Guide](./AUTOMOTIVE_QUICK_START.md)
- **Issues**: [GitHub Issues](https://github.com/sparesparrow/mia/issues)
- **Email**: info@ai-servis.cz
