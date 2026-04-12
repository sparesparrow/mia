# AI-Servis CI/CD & Development Environment

This document describes the comprehensive CI/CD pipeline and development environment setup for the AI-Servis project.

## 🚀 Quick Start

### Development Environment

```bash
# Start development environment
./scripts/dev-environment.sh up dev

# Start with monitoring
./scripts/dev-environment.sh up full

# Check status
./scripts/dev-environment.sh status dev

# View logs
./scripts/dev-environment.sh logs dev --follow
```

### VS Code Development Container

1. Install the "Dev Containers" extension
2. Open the project in VS Code
3. Press `Ctrl+Shift+P` and select "Dev Containers: Reopen in Container"
4. Wait for the container to build and start

## 🏗️ CI/CD Pipeline

### GitHub Actions Workflows

#### Main CI/CD Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`
- Path-scoped: only runs when Python, C++, ESP32, schema, or CI-owned files change

**Jobs:**
1. **Detect Changes** - Path-based change detection so the workflow only runs relevant platform jobs
2. **Schema Validation** - FlatBuffers compilation checks for `schemas/`, `protos/`, and `webgrab.fbs`
3. **Lint** - Python formatting and lint checks for maintained Python surfaces
4. **Python Tests** - `pytest tests/ -m "not hardware"` under the bundled CPython/Conan flow
5. **Build C++** - Native build validation for the C++ surfaces when native paths change
6. **Build ESP32** - PlatformIO build validation when `apps/esp32` changes

#### Dedicated Workflows

- **Android Tests** (`.github/workflows/android-test.yml`) - Gradle build plus emulator scenario matrix with artifact-backed pass/fail reporting
- **Publish Web Pages** (`.github/workflows/publish-pages.yml`) - Builds MkDocs plus static web assets and publishes them to the repo’s legacy `gh-pages` branch
- **Security** (`.github/workflows/security.yml`) - Fast PR/push checks (Trivy config, pip-audit, Bandit) with heavier CodeQL and deep Trivy scans reserved for non-PR and scheduled runs
- **Deploy** (`.github/workflows/deploy.yml`) - Deployment asset validation, compose smoke build, and tagged releases
- **Resolve Issue with Claude** (`.github/workflows/main.yml`) - Manually triggered issue-to-PR automation with dry-run support, path validation, and duplicate-PR protection

### Security Scanning

The pipeline includes multiple security scanning tools:

- **CodeQL** - Static analysis for Python, C++, JavaScript
- **Trivy** - Fast config scans on PRs and pushes, plus weekly deep filesystem/config scans
- **pip-audit** - Python dependency manifest vulnerability checks
- **Bandit** - Python security linting

### Multi-Platform Support

#### Container Images

All services are built for multiple architectures:
- `linux/amd64` - Standard x86_64 systems
- `linux/arm64` - ARM64 systems (Raspberry Pi 4, Apple Silicon)

#### C++ Builds

Cross-platform C++ builds using Conan:
- **Linux** - GCC 13, Ninja build system
- **Linux ARM64** - GCC 11 for Raspberry Pi
- **macOS** - Clang 14, native builds
- **Windows** - MSVC 2022, Visual Studio generator

## 🔧 Development Environments

### Available Environments

| Environment | Description | Docker Compose File |
|-------------|-------------|---------------------|
| `dev` | Development with hot reloading | `infra/docker/docker-compose.dev.yml` |
| `prod` | Production-like environment | `infra/docker/docker-compose.yml` |
| `pi-sim` | Raspberry Pi simulation | `docker-compose.pi-simulation.yml` |
| `monitoring` | Observability stack | `infra/docker/docker-compose.monitoring.yml` |
| `full` | All services combined | All compose files |

The `pi-sim` stack keeps the real MQTT and Redis services enabled by default. The legacy simulator containers are opt-in via `--profile legacy-sim` because several of those images are no longer part of the default repo runtime.

### Development Environment Features

- **Hot Reloading** - Code changes reflected immediately
- **Debug Ports** - Remote debugging for all services
- **Volume Mounts** - Source code mounted for live editing
- **Service Dependencies** - Automatic dependency management

### VS Code Dev Container

The development container includes:

- **Python 3.11** with all project dependencies
- **C++ Tools** - CMake, Ninja, Clang tools
- **Docker-in-Docker** - Container management from within container
- **Pre-commit Hooks** - Automatic code quality checks
- **Extensions** - Python, C++, Docker, YAML support

## 🔍 Monitoring & Observability

### Monitoring Stack

- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visualization and dashboards
- **AlertManager** - Alert routing and notification
- **Loki** - Log aggregation
- **Promtail** - Log collection
- **Jaeger** - Distributed tracing
- **Uptime Kuma** - Service uptime monitoring

### Key Metrics

- **Service Health** - Endpoint availability and response times
- **Resource Usage** - CPU, memory, disk utilization
- **Container Metrics** - Docker container performance
- **Custom Metrics** - AI-Servis specific metrics (MQTT, MCP, ESP32)

### Alerting

Alerts are configured for:
- Service downtime
- High resource usage
- Security incidents
- Performance degradation
- Hardware failures

## 🧪 Testing Strategy

### Test Types

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Service-to-service communication
3. **System Tests** - End-to-end workflow validation
4. **Performance Tests** - Load testing and benchmarking
5. **Smoke Tests** - Quick deployment validation

### Test Environments

- **Local Testing** - Developer workstation
- **CI Testing** - GitHub Actions runners
- **Staging Testing** - Production-like environment
- **Production Monitoring** - Continuous health checks

## 🌐 Raspberry Pi Simulation

### Simulation Components

- **Pi Gateway Simulator** - Raspberry Pi hardware simulation
- **GPIO Simulator** - GPIO pin state management
- **ESP32 Simulators** - OBD, I/O, and camera variants
- **Vehicle Data Generator** - Realistic vehicle telemetry
- **Hardware Monitor** - System performance simulation

### Simulation Features

- **Web Interface** - Control and monitoring dashboards
- **MQTT Integration** - Real-time data streaming
- **Hardware Emulation** - GPIO, I2C, SPI simulation
- **Scenario Playback** - Predefined test scenarios

## 🔐 Security

### Security Measures

- **Container Scanning** - Vulnerability detection in images
- **Dependency Scanning** - Third-party library vulnerabilities
- **Code Analysis** - Static security analysis
- **Secret Management** - GitHub Secrets for sensitive data
- **Network Security** - Service isolation and encryption

### Compliance

- **SARIF Reports** - Security findings in standardized format
- **Security Policies** - Automated policy enforcement
- **Audit Logging** - Comprehensive security event logging

## 📊 Performance

### Performance Targets

- **Response Time** - < 100ms for health endpoints
- **Throughput** - > 100 requests/second
- **Resource Usage** - < 80% CPU, < 85% memory
- **Build Time** - < 5 minutes for CI pipeline

### Performance Testing

- **Load Testing** - Apache Bench and wrk
- **Resource Monitoring** - Real-time performance tracking
- **Benchmarking** - Baseline performance measurement
- **Optimization** - Continuous performance improvement

## 🚀 Deployment

### Deployment Strategies

- **Rolling Deployment** - Zero-downtime updates
- **Blue-Green Deployment** - Environment switching
- **Canary Deployment** - Gradual rollout

### Environment Management

- **Development** - Feature development and testing
- **Staging** - Pre-production validation
- **Production** - Live system deployment

## 🛠️ Scripts and Tools

### Development Scripts

- `dev-environment.sh` - Environment management
- `docker-build-multiplatform.sh` - Multi-platform builds
- `health-check.sh` - Service health validation
- `performance-tests.sh` - Performance benchmarking
- `system-tests.sh` - Integration testing
- `smoke-tests.sh` - Deployment validation

### Build Tools

- **Docker Buildx** - Multi-platform container builds
- **Conan** - C++ dependency management
- **GitHub Actions** - CI/CD automation
- **Pre-commit** - Code quality enforcement

## 📚 Documentation

### Available Documentation

- **API Documentation** - Service API specifications
- **Architecture Diagrams** - System design documentation
- **Deployment Guides** - Environment setup instructions
- **Troubleshooting** - Common issues and solutions

### Documentation Tools

- **MkDocs** - Documentation site generation
- **OpenAPI** - API specification
- **Mermaid** - Diagram generation

## 🔧 Configuration

### Environment Variables

Key environment variables for configuration:

```bash
# Core Services
MQTT_BROKER=mqtt-broker:1883
LOG_LEVEL=INFO
PYTHONPATH=/app

# Database
POSTGRES_PASSWORD=your-password
REDIS_URL=redis://localhost:6379

# External APIs
ELEVENLABS_API_KEY=your-key
SPOTIFY_CLIENT_ID=your-id
SPOTIFY_CLIENT_SECRET=your-secret

# Monitoring
GRAFANA_PASSWORD=admin
SLACK_WEBHOOK_URL=your-webhook
```

### Configuration Files

- `.env` - Environment-specific variables
- `docker-compose.*.yml` - Service definitions
- `prometheus.yml` - Metrics configuration
- `alertmanager.yml` - Alert routing
- `.devcontainer/devcontainer.json` - VS Code container config

## 🚨 Troubleshooting

### Common Issues

1. **Container Won't Start**
   ```bash
   # Check logs
   ./scripts/dev-environment.sh logs dev service-name
   
   # Rebuild container
   ./scripts/dev-environment.sh build dev
   ```

2. **Port Conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8080
   
   # Stop conflicting services
   ./scripts/dev-environment.sh down dev
   ```

3. **Permission Issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $(id -u):$(id -g) volumes/
   ```

4. **Database Connection Issues**
   ```bash
   # Reset database
   docker-compose down -v
   ./scripts/dev-environment.sh up dev
   ```

### Getting Help

- Check the logs: `./scripts/dev-environment.sh logs dev --follow`
- Run health checks: `./scripts/dev-environment.sh health dev`
- Review documentation: `docs/troubleshooting.md`
- Open an issue on GitHub

## 🎯 Next Steps

1. **Set up your development environment**
2. **Configure VS Code with the dev container**
3. **Run the test suite to verify setup**
4. **Explore the monitoring dashboards**
5. **Start developing new features**

For detailed setup instructions, see the [Development Guide](development.md).