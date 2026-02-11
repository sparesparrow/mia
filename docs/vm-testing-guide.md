# 🖥️ AI-Servis VM Testing Guide

This guide provides comprehensive instructions for testing the AI-Servis CI/CD infrastructure in virtual machine environments.

## 🎯 Overview

The VM testing suite validates the complete AI-Servis development and deployment infrastructure in a clean, isolated environment. This ensures that the setup works correctly across different systems and configurations.

## 📋 VM Requirements

### Minimum System Requirements

| Component | Requirement | Recommended |
|-----------|-------------|-------------|
| **RAM** | 8GB | 16GB |
| **Disk Space** | 50GB free | 100GB free |
| **CPU Cores** | 4 cores | 8 cores |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **Network** | Internet access | Broadband connection |

### Supported VM Platforms

- **VMware Workstation/Player** - Recommended for development
- **VirtualBox** - Free alternative, good performance
- **Hyper-V** - Windows native virtualization
- **KVM/QEMU** - Linux native virtualization
- **Parallels Desktop** - macOS virtualization
- **Cloud VMs** - AWS EC2, Google Cloud, Azure

## 🚀 Quick Start

### 1. Download VM Test Script

```bash
# In your VM, download the test script
curl -O https://raw.githubusercontent.com/ai-servis/ai-servis/main/scripts/vm-test-setup.sh
chmod +x vm-test-setup.sh

# Or if you have the repository
git clone https://github.com/ai-servis/ai-servis.git
cd mia
./scripts/vm-test-setup.sh
```

### 2. Run Complete Test Suite

```bash
# Run all tests (takes ~20-30 minutes)
./scripts/vm-test-setup.sh

# Run quick tests only (takes ~10-15 minutes)
./scripts/vm-test-setup.sh --quick

# Clean up after testing
./scripts/vm-test-setup.sh --cleanup
```

### 3. View Test Results

```bash
# Test results are saved to:
cat /tmp/ai-servis-test-results/vm-test-report.md

# View detailed logs:
cat /tmp/ai-servis-vm-test.log
```

## 🧪 Test Phases

The VM test suite runs through 8 comprehensive test phases:

### Phase 1: System Requirements ✅
**Duration**: ~2 minutes

- **Memory Check** - Validates sufficient RAM (8GB+)
- **Disk Space Check** - Validates free space (50GB+)
- **Command Availability** - Checks for required tools
- **Network Connectivity** - Tests internet access

```bash
# Manual validation:
free -h                    # Check memory
df -h                     # Check disk space
curl -s https://github.com # Test connectivity
```

### Phase 2: Docker Setup ✅
**Duration**: ~5 minutes

- **Docker Installation** - Installs Docker if missing
- **Docker Daemon** - Validates Docker is running
- **Docker Compose** - Tests compose functionality
- **Docker Buildx** - Tests multi-platform builds

```bash
# Manual validation:
docker --version
docker compose version
docker buildx version
docker info
```

### Phase 3: Project Setup ✅
**Duration**: ~3 minutes

- **Repository Clone** - Downloads/copies project
- **Dependencies** - Installs Python requirements
- **Pre-commit Hooks** - Sets up code quality tools
- **Script Permissions** - Makes scripts executable

```bash
# Manual validation:
ls -la scripts/           # Check script permissions
pip3 list | grep pytest   # Check Python deps
pre-commit --version      # Check pre-commit
```

### Phase 4: Development Environment ✅
**Duration**: ~8 minutes

- **Environment Startup** - Starts dev docker-compose
- **Service Health** - Tests all service endpoints
- **Database Connectivity** - PostgreSQL and Redis
- **MQTT Broker** - Message broker functionality

```bash
# Manual validation:
./scripts/dev-environment.sh status dev
curl http://localhost:8080/health
curl http://localhost:8090/health
```

### Phase 5: Pi Simulation ✅
**Duration**: ~6 minutes

- **Simulation Startup** - Pi simulation environment
- **GPIO Simulator** - Hardware simulation web UI
- **ESP32 Simulators** - Device emulation
- **Hardware Monitor** - Performance monitoring

```bash
# Manual validation:
./scripts/dev-environment.sh status pi-sim
curl http://localhost:8084  # Pi Gateway
curl http://localhost:9000  # GPIO Simulator
```

### Phase 6: Monitoring Stack ✅
**Duration**: ~8 minutes

- **Prometheus** - Metrics collection service
- **Grafana** - Visualization dashboard
- **AlertManager** - Alert routing system
- **Jaeger** - Distributed tracing
- **Uptime Kuma** - Service monitoring

```bash
# Manual validation:
./scripts/dev-environment.sh status monitoring
open http://localhost:3000   # Grafana
open http://localhost:9090   # Prometheus
```

### Phase 7: CI Simulation ✅
**Duration**: ~5 minutes

- **Code Linting** - Python code quality checks
- **Docker Builds** - Container build testing
- **Multi-platform** - Cross-platform build tools
- **Security Scanning** - Basic vulnerability checks

```bash
# Manual validation:
flake8 --version
docker build --help
./scripts/docker-build-multiplatform.sh --help
```

### Phase 8: Performance Validation ✅
**Duration**: ~3 minutes

- **Performance Tests** - Load testing validation
- **Resource Usage** - CPU and memory monitoring
- **Response Times** - Service performance
- **System Health** - Overall system status

```bash
# Manual validation:
./scripts/performance-tests.sh
top                      # Check CPU usage
free -h                  # Check memory usage
```

## 🖥️ VM Setup Instructions

### Ubuntu 22.04 LTS (Recommended)

```bash
# 1. Create VM with recommended specs:
# - 16GB RAM, 100GB disk, 8 CPU cores
# - Enable virtualization features
# - Network: NAT or Bridged

# 2. Install Ubuntu 22.04 LTS
# - Use default installation
# - Install OpenSSH server for remote access
# - Create user account

# 3. Update system
sudo apt update && sudo apt upgrade -y

# 4. Install basic tools
sudo apt install -y curl wget git build-essential python3-pip

# 5. Run VM test
curl -O https://raw.githubusercontent.com/ai-servis/ai-servis/main/scripts/vm-test-setup.sh
chmod +x vm-test-setup.sh
./vm-test-setup.sh
```

### VMware Workstation Setup

```bash
# 1. Create new VM:
# - OS: Ubuntu 64-bit
# - Memory: 16GB
# - Disk: 100GB (thin provisioned)
# - Network: NAT

# 2. VM Settings:
# - Processors: 8 cores
# - Enable virtualization engine
# - USB 3.1 support
# - Sound card (optional)

# 3. Install VMware Tools:
sudo apt install open-vm-tools open-vm-tools-desktop

# 4. Enable shared folders (optional):
# VM Settings > Options > Shared Folders
```

### VirtualBox Setup

```bash
# 1. Create new VM:
# - Type: Linux, Ubuntu (64-bit)
# - Memory: 16GB (16384 MB)
# - Disk: 100GB VDI (dynamically allocated)

# 2. VM Settings:
# - System > Processor: 8 CPUs
# - System > Acceleration: Enable VT-x/AMD-V
# - Network: NAT or Bridged

# 3. Install Guest Additions:
sudo apt install virtualbox-guest-additions-iso
sudo mount /dev/cdrom /mnt
sudo /mnt/VBoxLinuxAdditions.run
```

### Cloud VM Setup (AWS EC2)

```bash
# 1. Launch EC2 instance:
# - AMI: Ubuntu Server 22.04 LTS
# - Instance type: t3.2xlarge (8 vCPU, 32GB RAM)
# - Storage: 100GB gp3
# - Security group: Allow SSH (22), HTTP (80), HTTPS (443)

# 2. Connect to instance:
ssh -i your-key.pem ubuntu@your-instance-ip

# 3. Run VM test:
curl -O https://raw.githubusercontent.com/ai-servis/ai-servis/main/scripts/vm-test-setup.sh
chmod +x vm-test-setup.sh
./vm-test-setup.sh
```

## 📊 Expected Test Results

### Successful Test Output

```
[2024-12-XX XX:XX:XX] Starting AI-Servis VM Test Suite...
[2024-12-XX XX:XX:XX] === Running test phase: system_requirements ===
[SUCCESS] Memory check passed: 16GB
[SUCCESS] Disk space check passed: 85GB available
[SUCCESS] Command available: curl
[SUCCESS] Command available: git
[SUCCESS] Internet connectivity verified
[SUCCESS] ✓ System requirements test passed

[2024-12-XX XX:XX:XX] === Running test phase: docker_setup ===
[SUCCESS] Docker is running
[SUCCESS] Docker Compose is available
[SUCCESS] Docker Buildx is available
[SUCCESS] Docker setup completed
[SUCCESS] ✓ Docker setup test passed

... (additional phases)

[2024-12-XX XX:XX:XX] === VM Test Suite Complete ===
[2024-12-XX XX:XX:XX] Total Tests: 8
[2024-12-XX XX:XX:XX] Passed: 8
[2024-12-XX XX:XX:XX] Failed: 0
[2024-12-XX XX:XX:XX] Success Rate: 100%
[SUCCESS] 🎉 All VM tests passed! AI-Servis is ready for deployment.
```

### Performance Benchmarks

| Metric | Expected Range | Good Performance |
|--------|----------------|------------------|
| **Total Test Time** | 20-30 minutes | < 25 minutes |
| **Docker Build Time** | 3-5 minutes | < 4 minutes |
| **Service Startup** | 30-60 seconds | < 45 seconds |
| **Endpoint Response** | < 1 second | < 500ms |
| **Memory Usage** | 4-8GB during tests | < 6GB |
| **CPU Usage** | 50-80% during builds | < 70% average |

## 🔧 Troubleshooting

### Common Issues

#### 1. Insufficient Resources

```bash
# Error: "Insufficient memory: 4GB (required: 8GB)"
# Solution: Increase VM RAM allocation

# Error: "Insufficient disk space"
# Solution: Increase VM disk size or clean up space
sudo apt autoremove
docker system prune -a
```

#### 2. Docker Issues

```bash
# Error: "Docker daemon is not running"
# Solution: Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Error: "Permission denied" for Docker
# Solution: Add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in
```

#### 3. Network Issues

```bash
# Error: "No internet connectivity"
# Solution: Check VM network settings

# For NAT networking:
# VM Settings > Network > NAT

# For bridged networking:
# VM Settings > Network > Bridged Adapter

# Test connectivity:
ping -c 4 8.8.8.8
curl -I https://github.com
```

#### 4. Service Startup Issues

```bash
# Error: "Service endpoints not responding"
# Solution: Check service logs

# View container logs:
docker logs ai-servis-core-dev
docker logs ai-servis-discovery-dev

# Check resource usage:
docker stats

# Restart services:
./scripts/dev-environment.sh restart dev
```

#### 5. Port Conflicts

```bash
# Error: "Port already in use"
# Solution: Check for conflicting processes

# Check port usage:
netstat -tulpn | grep :8080
lsof -i :8080

# Kill conflicting process:
sudo kill -9 <PID>

# Or use different ports:
# Edit docker-compose.dev.yml
```

### Performance Optimization

#### VM Settings Optimization

```bash
# VMware Workstation:
# - Enable hardware acceleration
# - Allocate maximum recommended memory
# - Use NVME/SSD storage
# - Enable 3D acceleration

# VirtualBox:
# - Enable VT-x/AMD-V and Nested Paging
# - Increase video memory to 256MB
# - Enable 3D acceleration
# - Use VDI with fixed size for better performance
```

#### System Optimization

```bash
# Disable unnecessary services:
sudo systemctl disable snapd
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Optimize Docker:
# Add to /etc/docker/daemon.json:
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

sudo systemctl restart docker
```

## 📈 Test Metrics & Reporting

### Automated Reporting

The VM test suite generates comprehensive reports:

```bash
# Test report location:
/tmp/ai-servis-test-results/vm-test-report.md

# Report includes:
# - System information
# - Test results summary  
# - Performance metrics
# - Detailed test logs
# - Recommendations
```

### Manual Validation

After automated tests, manually verify key functionality:

```bash
# 1. Check all services are running:
./scripts/dev-environment.sh status full

# 2. Access web interfaces:
open http://localhost:8080  # Core Orchestrator
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9000  # GPIO Simulator

# 3. Run integration tests:
./scripts/system-tests.sh

# 4. Test performance:
./scripts/performance-tests.sh

# 5. Validate monitoring:
# Check Grafana dashboards show data
# Verify Prometheus targets are up
```

### CI/CD Validation

Test the CI/CD pipeline simulation:

```bash
# 1. Test pre-commit hooks:
pre-commit run --all-files

# 2. Test Docker builds:
./scripts/docker-build-multiplatform.sh --help

# 3. Simulate GitHub Actions:
# Check .github/workflows/ files are valid
# Verify all referenced scripts exist
# Test environment variable substitution
```

## 🎯 Success Criteria

### VM Test Completion Criteria

- ✅ **All 8 test phases pass** without errors
- ✅ **Service endpoints respond** within timeout
- ✅ **Resource usage** stays within limits
- ✅ **No critical errors** in logs
- ✅ **Performance benchmarks** meet targets

### Ready for Production Criteria

- ✅ **VM tests pass** on multiple VM platforms
- ✅ **Different OS versions** validated
- ✅ **Resource scaling** tested (4GB to 32GB RAM)
- ✅ **Network configurations** validated
- ✅ **Security scanning** shows no critical issues

## 📚 Additional Resources

### Documentation Links

- **[CI/CD Setup Guide](ci-cd-setup.md)** - Complete pipeline documentation
- **[Development Guide](development.md)** - Developer onboarding
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Performance Tuning](performance-tuning.md)** - Optimization guidelines

### VM Templates

Pre-configured VM templates are available:

- **VMware Template** - Ubuntu 22.04 with Docker pre-installed
- **VirtualBox OVA** - Ready-to-use development environment
- **Cloud Images** - AWS/GCP/Azure marketplace images
- **Vagrant Box** - Automated VM provisioning

### Support Channels

- **GitHub Issues** - Bug reports and feature requests
- **Documentation Wiki** - Comprehensive guides
- **Team Chat** - Real-time support
- **Video Tutorials** - Step-by-step walkthroughs

---

## 🎉 Conclusion

The AI-Servis VM testing suite provides comprehensive validation of the entire CI/CD infrastructure in isolated environments. This ensures reliable deployment across different systems and configurations.

**Next Steps:**
1. Run the VM test suite in your environment
2. Review the generated test report
3. Address any issues identified
4. Proceed with development or deployment

For questions or issues, please refer to the troubleshooting section or create a GitHub issue.