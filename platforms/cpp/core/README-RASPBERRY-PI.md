# AI-SERVIS Universal - Raspberry Pi Deployment Guide

This guide will help you build, deploy, and test the AI-SERVIS Universal system on a Raspberry Pi.

## Prerequisites

### Hardware Requirements
- Raspberry Pi 3 or newer (recommended: Raspberry Pi 4)
- MicroSD card (16GB minimum, 32GB recommended)
- Internet connection
- GPIO access (for hardware control features)

### Software Requirements
- Raspberry Pi OS (Debian-based)
- Root or sudo access
- Basic development tools

## Quick Start

### 1. Clone and Prepare

```bash
cd /workspace
```

### 2. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libcurl4-openssl-dev \
    libmosquitto-dev \
    libgpiod-dev \
    libjsoncpp-dev \
    libflatbuffers-dev \
    espeak \
    mosquitto \
    mosquitto-clients
```

### 3. Build

```bash
./scripts/build-raspberry-pi.sh
```

Or manually:

```bash
mkdir -p build-raspberry-pi
cd build-raspberry-pi
cmake ../platforms/cpp/core -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### 4. Run Tests

```bash
./scripts/test-raspberry-pi.sh
```

### 5. Deploy

```bash
sudo ./scripts/deploy-raspberry-pi.sh
```

### 6. Start Service

```bash
sudo systemctl start ai-servis
sudo systemctl enable ai-servis  # Enable on boot
```

## Manual Deployment

### Build the Application

```bash
cd platforms/cpp/core
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

### Run Manually

```bash
# Run the main application
sudo ./ai-servis-rpi

# Or run hardware server separately
sudo ./hardware-server
```

## Services

The system provides several services:

1. **Core Orchestrator** (Port 8080)
   - Main command processing and routing
   - Service registration and discovery

2. **Hardware Control Server** (Port 8081)
   - GPIO control via TCP
   - MQTT integration for remote control

3. **Web UI** (Port 8082)
   - HTTP interface for web-based control
   - REST API endpoints

4. **MQTT Broker** (Port 1883)
   - Message queue for cross-process communication
   - Hardware control topics

## GPIO Access

To use GPIO features, you need proper permissions:

```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Or run with sudo
sudo ./ai-servis-rpi
```

## Testing GPIO

Test GPIO control:

```bash
# Via TCP
echo '{"pin": 18, "direction": "output", "value": 1}' | nc localhost 8081

# Via MQTT
mosquitto_pub -h localhost -t "hardware/gpio/control" -m '{"pin": 18, "direction": "output", "value": 1}'
```

## Troubleshooting

### Build Errors

If you encounter build errors:

1. Check all dependencies are installed:
   ```bash
   dpkg -l | grep -E "libcurl|libmosquitto|libgpiod|libjsoncpp|libflatbuffers"
   ```

2. Check CMake version (requires 3.10+):
   ```bash
   cmake --version
   ```

### Runtime Errors

1. **GPIO Access Denied**
   - Run with sudo or add user to gpio group
   - Check /dev/gpiochip* permissions

2. **Port Already in Use**
   - Check what's using the port: `sudo netstat -tulpn | grep <port>`
   - Stop conflicting services

3. **MQTT Connection Failed**
   - Ensure mosquitto is running: `sudo systemctl status mosquitto`
   - Check mosquitto config: `/etc/mosquitto/mosquitto.conf`

### Logs

View system logs:
```bash
# Systemd service logs
sudo journalctl -u ai-servis -f

# Application logs (if running manually)
./ai-servis-rpi 2>&1 | tee ai-servis.log
```

## Configuration

Edit configuration file:
```bash
sudo nano /opt/ai-servis/config/ai-servis.conf
```

After changes, restart the service:
```bash
sudo systemctl restart ai-servis
```

## Development

### Building Tests

```bash
cd build-raspberry-pi
cmake --build . --target tests
./tests
```

### Debug Build

```bash
cmake ../platforms/cpp/core -DCMAKE_BUILD_TYPE=Debug
make -j$(nproc)
```

## Next Steps

1. Connect hardware (LEDs, sensors) to GPIO pins
2. Configure MQTT broker for remote access
3. Set up web UI for browser-based control
4. Integrate with voice recognition (Whisper on ESP32)
5. Deploy to production

## Support

For issues and questions:
- Check logs: `sudo journalctl -u ai-servis`
- Review GPIO permissions
- Verify all services are running
