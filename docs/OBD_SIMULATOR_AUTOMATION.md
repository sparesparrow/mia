# OBD Simulator Automation & CI/CD Integration

This document describes the automated dependency management, testing, and deployment processes for the MIA OBD Simulator components.

## Overview

The OBD Simulator has been integrated into the MIA automated build, test, and deployment pipeline using:

- **Conan** for dependency management
- **pytest** for unit and integration testing
- **GitHub Actions** for CI/CD automation
- **Systemd** for production deployment

## Architecture

### Components

1. **Serial Bridge** (`rpi/hardware/serial_bridge.py`)
   - Reads ESP32/Arduino telemetry via USB Serial
   - Publishes to ZeroMQ PUB socket (port 5556)

2. **OBD Worker** (`rpi/services/obd_worker.py`)
   - Subscribes to hardware telemetry
   - Runs ELM327 emulator with dynamic PID responses
   - Integrates with ZeroMQ broker (port 5555)

3. **Conan Recipe** (`rpi/conanfile.py`)
   - Manages Python service packaging
   - Validates component dependencies

## Dependency Management

### Conan Integration

The OBD simulator components are packaged using Conan:

```bash
# Build Conan package
cd rpi
conan create . --build=missing

# Install package
conan install rpi/conanfile.py --build=missing
```

### Python Dependencies

Python dependencies are managed via `rpi/requirements.txt`:

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pyzmq>=25.1.0
psutil>=5.9.0
pyserial>=3.5
ELM327-emulator>=1.1.1
```

### System Dependencies

Required system packages (installed via apt-get):

```bash
sudo apt-get install -y \
    libzmq3-dev \
    python3-dev \
    python3-pip
```

## Testing

### Unit Tests

Unit tests are located in `tests/integration/test_obd_simulator.py`:

```bash
# Run OBD simulator tests
python -m pytest tests/integration/test_obd_simulator.py -v
```

Test coverage includes:
- Dynamic car state management
- Serial bridge functionality
- OBD worker initialization
- ZeroMQ integration
- PID encoding/decoding

### Integration Test Script

Automated integration test script:

```bash
# Run integration tests
bash scripts/test-obd-simulator.sh
```

The script validates:
- Component file presence
- Python dependency availability
- ZeroMQ communication
- Mock mode operation

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Main CI Pipeline (`.github/workflows/main.yml`)

The main pipeline includes:
- **Python Tests**: Runs OBD simulator tests as part of Python test suite
- **System Dependencies**: Installs `libzmq3-dev` and `python3-dev`

#### 2. RPi Python Services CI (`.github/workflows/rpi-python-services.yml`)

Dedicated workflow for RPi Python services:
- **Multi-Python Testing**: Tests on Python 3.9, 3.10, 3.11
- **Conan Build**: Builds and validates Conan package
- **Deployment Validation**: Validates deployment scripts and service files

#### 3. Conan Build (`ci/github-actions/rpi-python-conan.yml`)

Conan-specific workflow:
- Builds Conan package for multiple Python versions
- Validates package contents
- Caches Conan dependencies

### Workflow Triggers

Workflows trigger on:
- Push to `main`, `develop`, or `feature/*` branches
- Changes to `rpi/**` files
- Pull requests affecting RPi components
- Manual workflow dispatch

## Deployment

### Automated Deployment Script

The deployment script (`scripts/deploy-raspberry-pi.sh`) has been updated to include:

1. **OBD Service Installation**:
   - Copies `mia-serial-bridge.service`
   - Copies `mia-obd-worker.service`
   - Installs Python dependencies from `rpi/requirements.txt`

2. **Service Management**:
   - Enables services to start on boot
   - Provides status and log commands

### Manual Deployment

```bash
# Run deployment script
sudo ./scripts/deploy-raspberry-pi.sh

# Start services
sudo systemctl start zmq-broker
sudo systemctl start mia-serial-bridge
sudo systemctl start mia-obd-worker

# Check status
sudo systemctl status mia-obd-worker
sudo journalctl -u mia-obd-worker -f
```

## Validation Checklist

### Pre-Deployment

- [ ] All tests pass in CI/CD pipeline
- [ ] Conan package builds successfully
- [ ] Python dependencies install correctly
- [ ] Service files reference correct paths
- [ ] ZeroMQ ports are available (5555, 5556)

### Post-Deployment

- [ ] Services start without errors
- [ ] Serial bridge detects hardware (or runs in mock mode)
- [ ] OBD worker connects to broker
- [ ] Telemetry flow works end-to-end
- [ ] Logs show no critical errors

## Troubleshooting

### CI/CD Failures

**Issue**: Tests fail due to missing dependencies
- **Solution**: Ensure `rpi/requirements.txt` includes all required packages
- **Check**: CI logs for specific missing package

**Issue**: Conan build fails
- **Solution**: Verify `rpi/conanfile.py` syntax
- **Check**: Conan cache is properly configured

### Deployment Issues

**Issue**: Services fail to start
- **Check**: `sudo journalctl -u mia-obd-worker -n 50`
- **Verify**: Python dependencies installed: `pip3 list | grep -E "pyzmq|pyserial|ELM327"`

**Issue**: Serial bridge can't connect
- **Check**: Serial port permissions: `ls -l /dev/ttyUSB*`
- **Solution**: Add user to dialout group: `sudo usermod -a -G dialout $USER`

## Future Enhancements

- [ ] Add Docker containerization for OBD simulator
- [ ] Implement hardware-in-the-loop CI testing
- [ ] Add performance benchmarks
- [ ] Create deployment validation tests
- [ ] Add monitoring and alerting integration

## References

- [MIA RPi README](../rpi/README.md)
- [Conan Documentation](https://docs.conan.io/)
- [ZeroMQ Documentation](https://zeromq.org/)
- [ELM327 Emulator](https://github.com/Ircama/ELM327-emulator)
