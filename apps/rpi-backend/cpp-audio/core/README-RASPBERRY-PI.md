# MIA C++ Audio — Raspberry Pi Deployment Guide

> **Audience**: Embedded developers, ops engineers

## Prerequisites

### Hardware Requirements
- Raspberry Pi 3 or newer (recommended: Raspberry Pi 4)
- MicroSD card (16GB minimum, 32GB recommended)
- Internet connection
- GPIO access (for hardware control features)

## Quick Start

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential cmake pkg-config \
    libcurl4-openssl-dev libmosquitto-dev libgpiod-dev \
    libjsoncpp-dev libflatbuffers-dev \
    espeak mosquitto mosquitto-clients
```

### 2. Build

```bash
./tools/scripts/build-raspberry-pi.sh
```

Or manually, from the repository root:
```bash
cmake -S apps/rpi-backend/cpp-audio -B build/cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/cpp --parallel "$(nproc)"
```

### 3. Deploy

`tools/scripts/deploy-raspberry-pi.sh` installs the Python services and their systemd units; it does not build or
install these C++ binaries, and no unit in `infra/systemd/` runs them. See
[the Pi install](../../../../docs/install/pi-gateway.md).

## Services

| Service | Port | Description |
|---------|------|-------------|
| Core Orchestrator | 8080 | Main command processing |
| Hardware Control Server | 8081 | GPIO control via TCP and MQTT |
| MQTT Broker | 1883 | Message queue |

## GPIO Access

```bash
sudo usermod -a -G gpio $USER
```

## Troubleshooting

- Build errors: `dpkg -l | grep -E "libcurl|libmosquitto|libgpiod|libjsoncpp"`
- GPIO denied: run with sudo or check `/dev/gpiochip*` permissions
- Port conflict: `sudo netstat -tulpn | grep <port>`
- Logs: `sudo journalctl -u mia-api -f`

For full C++ build documentation, see [docs/conan-setup.md](../../../../docs/conan-setup.md) and [docs/ARM64_BUILD_REQUIREMENTS.md](../../../../docs/ARM64_BUILD_REQUIREMENTS.md).
