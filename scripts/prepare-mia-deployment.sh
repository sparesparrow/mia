#!/bin/bash
#
# MIA Deployment Preparation Script
# Prepares everything needed for Raspberry Pi deployment
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
RPI_IP="192.168.200.134"
DEPLOY_USER="sparrow"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_LOG="/tmp/mia-deployment-prep-$(date +%Y%m%d-%H%M%S).log"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOY_LOG"
}

log_header() {
    echo -e "${BLUE}========================================${NC}" | tee -a "$DEPLOY_LOG"
    echo -e "${BLUE}  $1${NC}" | tee -a "$DEPLOY_LOG"
    echo -e "${BLUE}========================================${NC}" | tee -a "$DEPLOY_LOG"
}

# Function to check if Raspberry Pi is reachable
check_rpi_connectivity() {
    log_info "Checking Raspberry Pi connectivity at $RPI_IP..."

    if ping -c 3 -W 2 "$RPI_IP" >/dev/null 2>&1; then
        log_success "✓ Raspberry Pi is reachable at $RPI_IP"
        return 0
    else
        log_warning "⚠ Raspberry Pi at $RPI_IP is not reachable"
        log_info "Will prepare deployment package for when it becomes available"
        return 1
    fi
}

# Function to prepare deployment package
prepare_deployment_package() {
    log_header "Preparing Deployment Package"

    DEPLOY_PACKAGE="/tmp/mia-deployment-$(date +%Y%m%d-%H%M%S).tar.gz"

    log_info "Creating deployment package..."

    # Create temporary directory for deployment files
    DEPLOY_DIR="/tmp/mia-deploy-prep"
    rm -rf "$DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"

    # Copy essential deployment files
    cp "$PROJECT_ROOT/scripts/deploy-raspberry-pi.sh" "$DEPLOY_DIR/"
    cp "$PROJECT_ROOT/scripts/deploy-raspberry-pi-remote.sh" "$DEPLOY_DIR/"
    cp "$PROJECT_ROOT/docker-compose.yml" "$DEPLOY_DIR/"
    cp "$PROJECT_ROOT/docker-compose.pi-simulation.yml" "$DEPLOY_DIR/"

    # Copy configuration files
    cp -r "$PROJECT_ROOT/config" "$DEPLOY_DIR/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/containers" "$DEPLOY_DIR/" 2>/dev/null || true

    # Copy volume definitions (empty directories will be created on target)
    mkdir -p "$DEPLOY_DIR/volumes"

    # Create deployment README
    cat > "$DEPLOY_DIR/README.md" << 'EOF'
# MIA Raspberry Pi Deployment Package

This package contains everything needed to deploy MIA on a Raspberry Pi.

## Quick Deployment

1. Extract this package on your Raspberry Pi
2. Run: `./deploy-raspberry-pi.sh`
3. Or for remote deployment: `./deploy-raspberry-pi-remote.sh`

## Components

- **Core Services**: Orchestrator, hardware server, MQTT broker
- **AI Features**: Voice assistant, audio processing
- **Monitoring**: Prometheus, Grafana dashboards
- **Simulation**: GPIO and hardware simulation for testing

## Services Started

After deployment, these services will be running:
- Core Orchestrator (Port 8080)
- Hardware Server (Port 8081)
- Voice Assistant (Port 8082)
- Platform Controller (Port 8083)
- MQTT Broker (Port 1883)
- PostgreSQL (Port 5432)
- Redis (Port 6379)
- Prometheus (Port 9090)
- Grafana (Port 3000)

## Testing

Run the test suite:
```bash
cd /opt/mia
./scripts/test-raspberry-pi.sh
```

## Troubleshooting

Check logs:
```bash
sudo journalctl -u mia-core -n 50
docker-compose logs
```

View status:
```bash
sudo systemctl status mia-*
docker-compose ps
```
EOF

    # Create deployment script
    cat > "$DEPLOY_DIR/deploy.sh" << EOF
#!/bin/bash
set -e

echo "🚀 Starting MIA Deployment on Raspberry Pi..."
echo "Target IP: $RPI_IP"
echo "User: $DEPLOY_USER"
echo ""

# Run remote deployment
export RPI_HOST="$RPI_IP"
export RPI_USER="$DEPLOY_USER"
./deploy-raspberry-pi-remote.sh

echo ""
echo "🎉 Deployment completed!"
echo "Visit http://$RPI_IP:3000 for Grafana dashboard"
echo "Visit http://$RPI_IP:8082 for MIA web interface"
EOF

    chmod +x "$DEPLOY_DIR/deploy.sh"

    # Create the deployment package
    cd /tmp
    tar -czf "$DEPLOY_PACKAGE" "$(basename "$DEPLOY_DIR")"

    log_success "✓ Deployment package created: $DEPLOY_PACKAGE"
    log_info "Package size: $(du -h "$DEPLOY_PACKAGE" | cut -f1)"

    # Clean up
    rm -rf "$DEPLOY_DIR"

    echo "$DEPLOY_PACKAGE"
}

# Function to build Docker images locally
build_docker_images() {
    log_header "Building Docker Images"

    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found, skipping image builds"
        return 0
    fi

    log_info "Building MIA Docker images..."

    cd "$PROJECT_ROOT"

    # Build core services
    log_info "Building ai-servis-core..."
    docker build -t mia-core ./modules/core-orchestrator/ || log_warning "Failed to build core image"

    log_info "Building ai-audio-assistant..."
    docker build -t mia-audio ./modules/ai-audio-assistant/ || log_warning "Failed to build audio image"

    log_info "Building ai-platform-linux..."
    docker build -t mia-platform ./modules/ai-platform-controllers/linux/ || log_warning "Failed to build platform image"

    # Build simulation services
    log_info "Building Raspberry Pi simulation..."
    docker build -t mia-pi-sim ./containers/pi-simulation/ 2>/dev/null || log_warning "Failed to build Pi simulation"

    log_info "Building GPIO simulator..."
    docker build -t mia-gpio-sim ./containers/gpio-simulator/ 2>/dev/null || log_warning "Failed to build GPIO simulator"

    log_success "✓ Docker images built (where possible)"
}

# Function to validate Conan dependencies
validate_conan_setup() {
    log_header "Validating Conan Setup"

    if ! command -v conan &> /dev/null; then
        log_error "Conan not found. Install Conan 2.x first."
        return 1
    fi

    log_info "Conan version: $(conan --version)"

    # Check if SpareTools remote is configured
    if ! conan remote list | grep -q sparesparrow-conan; then
        log_warning "SpareSparrow Conan remote not configured"
        log_info "Adding remote: conan remote add sparesparrow-conan https://cloudsmith.io/~sparesparrow-conan/repos/sparetools/"
        conan remote add sparesparrow-conan https://cloudsmith.io/~sparesparrow-conan/repos/sparetools/
    fi

    log_success "✓ Conan setup validated"
}

# Function to create deployment summary
create_deployment_summary() {
    local deploy_package="$1"

    log_header "Deployment Summary"

    cat << EOF | tee -a "$DEPLOY_LOG"

🎯 MIA Deployment Preparation Complete!

📦 Deployment Package: $deploy_package

🎯 Target Raspberry Pi: $RPI_IP

📋 Deployment Checklist:
  ✅ Conan dependencies validated
  ✅ Docker images built (where possible)
  ✅ Deployment scripts prepared
  ✅ Configuration files included
  ✅ Documentation created

🚀 Next Steps:

1. Ensure Raspberry Pi is online at $RPI_IP
2. Copy deployment package to Raspberry Pi:
   scp $deploy_package $DEPLOY_USER@$RPI_IP:~/

3. SSH to Raspberry Pi and deploy:
   ssh $DEPLOY_USER@$RPI_IP
   tar -xzf $(basename "$deploy_package")
   cd mia-deploy-prep
   ./deploy.sh

4. Or run deployment directly:
   cd /path/to/mia/project
   export RPI_HOST=$RPI_IP
   ./scripts/deploy-raspberry-pi-remote.sh

🔍 After Deployment - Verify Services:

# Check system services
sudo systemctl status mia-*

# Check Docker containers
docker-compose ps

# Test core functionality
curl http://localhost:8080/api/status
curl http://localhost:8082/api/voice/status

# Access web interfaces
# - MIA Core: http://$RPI_IP:8080
# - Voice Assistant: http://$RPI_IP:8082
# - Grafana: http://$RPI_IP:3000 (admin/admin)
# - Prometheus: http://$RPI_IP:9090

📊 Monitoring:
- Hardware metrics: http://$RPI_IP:8087
- System monitoring: http://$RPI_IP:3000/dashboards

🔧 Troubleshooting:
- View logs: sudo journalctl -u mia-core -f
- Container logs: docker-compose logs -f
- Hardware test: ./scripts/test-hardware-server.sh

📝 Deployment Log: $DEPLOY_LOG

EOF

    log_success "✓ Deployment preparation complete!"
    log_info "Deployment package ready for Raspberry Pi at $RPI_IP"
}

# Main execution
main() {
    log_header "MIA Deployment Preparation"
    log_info "Target: Raspberry Pi at $RPI_IP"
    log_info "Project: $PROJECT_ROOT"
    echo ""

    # Check connectivity
    if check_rpi_connectivity; then
        log_info "Raspberry Pi is online - ready for direct deployment"
    else
        log_info "Raspberry Pi offline - preparing deployment package"
    fi
    echo ""

    # Validate Conan setup
    validate_conan_setup
    echo ""

    # Build Docker images
    build_docker_images
    echo ""

    # Prepare deployment package
    DEPLOY_PACKAGE=$(prepare_deployment_package)
    echo ""

    # Create deployment summary
    create_deployment_summary "$DEPLOY_PACKAGE"
}

# Run main function
main "$@"

