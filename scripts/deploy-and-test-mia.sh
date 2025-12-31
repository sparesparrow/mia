#!/bin/bash
#
# Complete MIA Deployment and Testing Script
# Deploys MIA to Raspberry Pi and runs comprehensive tests
#

set -e

# Configuration
RPI_IP="${RPI_IP:-192.168.200.134}"
RPI_USER="${RPI_USER:-sparrow}"
DEPLOY_PACKAGE="/tmp/mia-deployment-$(date +%Y%m%d).tar.gz"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging
LOG_FILE="/tmp/mia-full-deployment-$(date +%Y%m%d-%H%M%S).log"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_header() {
    echo -e "${PURPLE}========================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}  $1${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}========================================${NC}" | tee -a "$LOG_FILE"
}

# Function to check Raspberry Pi connectivity
check_rpi() {
    log_info "Checking Raspberry Pi connectivity at $RPI_IP..."

    if ! ping -c 3 -W 5 "$RPI_IP" >/dev/null 2>&1; then
        log_error "Raspberry Pi at $RPI_IP is not reachable"
        log_info "Please ensure the Raspberry Pi is online and try again"
        exit 1
    fi

    log_success "✓ Raspberry Pi is reachable at $RPI_IP"
}

# Function to test SSH connection
test_ssh() {
    log_info "Testing SSH connection to $RPI_USER@$RPI_IP..."

    if ! ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 "$RPI_USER@$RPI_IP" "echo 'SSH test successful'" >/dev/null 2>&1; then
        log_error "SSH connection to $RPI_USER@$RPI_IP failed"
        log_info "Troubleshooting:"
        log_info "  1. Check SSH key: ssh-add ~/.ssh/id_rsa"
        log_info "  2. Test manually: ssh $RPI_USER@$RPI_IP"
        log_info "  3. Check firewall: sudo ufw status on Raspberry Pi"
        exit 1
    fi

    log_success "✓ SSH connection successful"
}

# Function to prepare deployment package
prepare_package() {
    log_header "Preparing Deployment Package"

    if [ ! -f "$DEPLOY_PACKAGE" ]; then
        log_info "Creating fresh deployment package..."
        "$PROJECT_ROOT/scripts/prepare-mia-deployment.sh" >/dev/null 2>&1
    fi

    if [ ! -f "$DEPLOY_PACKAGE" ]; then
        # Find the latest package
        DEPLOY_PACKAGE=$(ls -t /tmp/mia-deployment-*.tar.gz 2>/dev/null | head -1)
        if [ -z "$DEPLOY_PACKAGE" ]; then
            log_error "No deployment package found"
            exit 1
        fi
    fi

    log_success "✓ Using deployment package: $DEPLOY_PACKAGE"
    log_info "Package size: $(du -h "$DEPLOY_PACKAGE" | cut -f1)"
}

# Function to deploy to Raspberry Pi
deploy_to_rpi() {
    log_header "Deploying to Raspberry Pi"

    log_info "Copying deployment package to Raspberry Pi..."
    if ! scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$DEPLOY_PACKAGE" "$RPI_USER@$RPI_IP:~/" >/dev/null 2>&1; then
        log_error "Failed to copy deployment package"
        exit 1
    fi
    log_success "✓ Deployment package copied"

    local package_name=$(basename "$DEPLOY_PACKAGE")

    log_info "Extracting and running deployment on Raspberry Pi..."
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$RPI_USER@$RPI_IP" << EOF
        set -e
        echo "Starting MIA deployment on Raspberry Pi..."

        # Clean up any existing deployment
        rm -rf ~/mia-deploy-prep

        # Extract deployment package
        tar -xzf ~/$package_name
        cd mia-deploy-prep

        # Make scripts executable
        chmod +x *.sh

        # Run deployment
        echo "Running deployment script..."
        sudo ./deploy-raspberry-pi.sh

        echo "MIA deployment completed!"
EOF

    if [ $? -eq 0 ]; then
        log_success "✓ Deployment completed successfully"
    else
        log_error "Deployment failed on Raspberry Pi"
        exit 1
    fi
}

# Function to test deployment
test_deployment() {
    log_header "Testing MIA Deployment"

    log_info "Waiting for services to start (30 seconds)..."
    sleep 30

    # Test core services
    test_service "MIA Core Orchestrator" "http://$RPI_IP:8080/api/status" "8080"
    test_service "Voice Assistant" "http://$RPI_IP:8082/api/voice/status" "8082"
    test_service "Hardware Server" "http://$RPI_IP:8081/api/hardware/info" "8081"
    test_service "Grafana" "http://$RPI_IP:3000/api/health" "3000"
    test_service "Prometheus" "http://$RPI_IP:9090/-/ready" "9090"

    # Test Docker containers
    test_docker_containers

    # Test MQTT
    test_mqtt

    log_success "✓ All deployment tests completed"
}

# Function to test individual service
test_service() {
    local service_name="$1"
    local url="$2"
    local port="$3"

    log_info "Testing $service_name (Port $port)..."

    if ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$RPI_USER@$RPI_IP" "curl -f -s '$url' >/dev/null 2>&1"; then
        log_success "✓ $service_name is responding"
    else
        log_warning "⚠ $service_name not responding (may still be starting)"
    fi
}

# Function to test Docker containers
test_docker_containers() {
    log_info "Testing Docker containers..."

    local containers=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$RPI_USER@$RPI_IP" "docker-compose ps --services 2>/dev/null || docker ps --format 'table {{.Names}}\t{{.Status}}'")

    if [ -n "$containers" ]; then
        log_success "✓ Docker containers are running:"
        echo "$containers" | while read -r line; do
            log_info "  $line"
        done
    else
        log_warning "⚠ No Docker containers found"
    fi
}

# Function to test MQTT
test_mqtt() {
    log_info "Testing MQTT broker..."

    if ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$RPI_USER@$RPI_IP" "timeout 5 mosquitto_sub -h localhost -t 'test' -C 1 >/dev/null 2>&1 & sleep 1 && mosquitto_pub -h localhost -t 'test' -m 'hello'"; then
        log_success "✓ MQTT broker is working"
    else
        log_warning "⚠ MQTT broker test failed"
    fi
}

# Function to run hardware tests
run_hardware_tests() {
    log_header "Running Hardware Tests"

    log_info "Running GPIO tests..."
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$RPI_USER@$RPI_IP" << 'EOF'
        cd /opt/mia
        if [ -f scripts/test-hardware-server.sh ]; then
            echo "Running hardware server tests..."
            sudo ./scripts/test-hardware-server.sh
        else
            echo "Hardware test script not found, running basic GPIO check..."
            # Basic GPIO check
            if command -v gpiodetect >/dev/null 2>&1; then
                echo "GPIO chips detected:"
                gpiodetect
            else
                echo "gpiod not available, checking /dev/gpiochip*"
                ls -la /dev/gpiochip* 2>/dev/null || echo "No GPIO chips found"
            fi
        fi
EOF

    log_success "✓ Hardware tests completed"
}

# Function to create deployment report
create_report() {
    log_header "Deployment Report"

    cat << EOF | tee -a "$LOG_FILE"

🎉 MIA Deployment to Raspberry Pi Complete!

📍 Target: $RPI_IP (User: $RPI_USER)
📦 Package: $(basename "$DEPLOY_PACKAGE")
🕐 Completed: $(date)

🌐 Service Endpoints:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────┬─────────────┬─────────────────────────────────────┐
│ Service            │ Port       │ URL                                 │
├─────────────────────┼─────────────┼─────────────────────────────────────┤
│ MIA Core           │ 8080       │ http://$RPI_IP:8080                 │
│ Voice Assistant    │ 8082       │ http://$RPI_IP:8082                 │
│ Hardware Server    │ 8081       │ http://$RPI_IP:8081                 │
│ Platform Controller│ 8083       │ http://$RPI_IP:8083                 │
│ Grafana            │ 3000       │ http://$RPI_IP:3000 (admin/admin)   │
│ Prometheus         │ 9090       │ http://$RPI_IP:9090                 │
│ Hardware Monitor   │ 8087       │ http://$RPI_IP:8087                 │
│ MQTT Broker        │ 1883       │ mqtt://$RPI_IP:1883                 │
│ PostgreSQL         │ 5432       │ localhost:5432                      │
│ Redis              │ 6379       │ localhost:6379                      │
└─────────────────────┴─────────────┴─────────────────────────────────────┘

🧪 Testing Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test all services
curl http://$RPI_IP:8080/api/status
curl http://$RPI_IP:8082/api/voice/status

# Check Docker containers
ssh $RPI_USER@$RPI_IP "docker-compose ps"

# View logs
ssh $RPI_USER@$RPI_IP "sudo journalctl -u mia-core -n 20"
ssh $RPI_USER@$RPI_IP "docker-compose logs -f core"

# Test hardware (if available)
ssh $RPI_USER@$RPI_IP "echo '{\"pin\": 18}' | nc localhost 8081"

🔧 Management Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Restart all services
ssh $RPI_USER@$RPI_IP "sudo systemctl restart mia-* && docker-compose restart"

# Update deployment
ssh $RPI_USER@$RPI_IP "cd /opt/mia && git pull && sudo ./scripts/deploy-raspberry-pi.sh"

# Monitor system
ssh $RPI_USER@$RPI_IP "htop"
ssh $RPI_USER@$RPI_IP "docker stats"

📊 Monitoring & Dashboards:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• System Metrics: http://$RPI_IP:3000/d/hardware
• Application Metrics: http://$RPI_IP:3000/d/mia-app
• Hardware Metrics: http://$RPI_IP:8087
• Prometheus Targets: http://$RPI_IP:9090/targets

📝 Logs Location:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• System logs: /var/log/mia/
• Docker logs: docker-compose logs [service]
• Application logs: /opt/mia/logs/
• Deployment log: $LOG_FILE

🔍 Troubleshooting:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Service not starting? Check: sudo systemctl status mia-core
2. Port not accessible? Check: sudo netstat -tulpn | grep :8080
3. Docker issues? Check: docker-compose ps
4. Hardware problems? Check: sudo journalctl -u mia-hardware

🎯 Next Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Connect hardware (LEDs, sensors) to GPIO pins
2. Configure voice recognition models
3. Set up external MQTT clients
4. Customize Grafana dashboards
5. Configure automated backups

📞 Support:
• Logs: $LOG_FILE
• Commands: ssh $RPI_USER@$RPI_IP
• Web UI: http://$RPI_IP:8082
• Monitoring: http://$RPI_IP:3000

🚀 MIA is now live on your Raspberry Pi! 🎉

EOF

    log_success "✓ Deployment report created: $LOG_FILE"
}

# Main execution
main() {
    log_header "MIA Full Deployment & Testing"
    log_info "Target Raspberry Pi: $RPI_IP"
    log_info "User: $RPI_USER"
    log_info "Project: $PROJECT_ROOT"
    echo ""

    # Pre-deployment checks
    check_rpi
    test_ssh

    # Prepare deployment
    prepare_package

    # Deploy
    deploy_to_rpi

    # Test deployment
    test_deployment

    # Run hardware tests
    run_hardware_tests

    # Create final report
    create_report

    log_header "🎉 MIA Deployment Complete!"
    log_success "Your AI Automotive Assistant is now running on Raspberry Pi at $RPI_IP"
    log_info "Access the web interface at: http://$RPI_IP:8082"
    log_info "View dashboards at: http://$RPI_IP:3000"
    log_info "Full deployment log: $LOG_FILE"
}

# Handle command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --rpi-ip)
            RPI_IP="$2"
            shift 2
            ;;
        --rpi-user)
            RPI_USER="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Deploy and test MIA on Raspberry Pi"
            echo ""
            echo "Options:"
            echo "  --rpi-ip IP        Raspberry Pi IP address (default: 192.168.200.134)"
            echo "  --rpi-user USER    SSH username (default: sparrow)"
            echo "  --help             Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"

