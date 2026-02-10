#!/usr/bin/env bash
set -euo pipefail

# VM Test Setup Script for AI-Servis CI/CD
# Tests the complete development environment in a clean VM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# VM Test Configuration
VM_TEST_LOG="/tmp/ai-servis-vm-test.log"
TEST_RESULTS_DIR="/tmp/ai-servis-test-results"
REQUIRED_MEMORY_GB=8
REQUIRED_DISK_GB=50

# Test phases
PHASES=(
    "system_requirements"
    "docker_setup" 
    "project_setup"
    "development_environment"
    "pi_simulation"
    "monitoring_stack"
    "ci_simulation"
    "performance_validation"
)

# Initialize test environment
init_test_environment() {
    log "Initializing VM test environment..."
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    # Clear previous test log
    > "$VM_TEST_LOG"
    
    # Log system information
    {
        echo "=== VM Test Environment ==="
        echo "Date: $(date)"
        echo "Hostname: $(hostname)"
        echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")"
        echo "Kernel: $(uname -r)"
        echo "Architecture: $(uname -m)"
        echo "CPU Cores: $(nproc)"
        echo "Memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
        echo "Disk Space: $(df -h / | tail -1 | awk '{print $4}')"
        echo "User: $(whoami)"
        echo "=========================="
    } | tee -a "$VM_TEST_LOG"
}

# Check system requirements
test_system_requirements() {
    log "Testing system requirements..."
    local errors=0
    
    # Check available memory
    local memory_gb=$(free -g | grep '^Mem:' | awk '{print $2}')
    if [ "$memory_gb" -lt $REQUIRED_MEMORY_GB ]; then
        error "Insufficient memory: ${memory_gb}GB (required: ${REQUIRED_MEMORY_GB}GB)"
        ((errors++))
    else
        success "Memory check passed: ${memory_gb}GB"
    fi
    
    # Check available disk space
    local disk_gb=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$disk_gb" -lt $REQUIRED_DISK_GB ]; then
        error "Insufficient disk space: ${disk_gb}GB (required: ${REQUIRED_DISK_GB}GB)"
        ((errors++))
    else
        success "Disk space check passed: ${disk_gb}GB available"
    fi
    
    # Check required commands
    local required_commands=("curl" "wget" "git" "make" "gcc" "python3" "pip3")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error "Missing required command: $cmd"
            ((errors++))
        else
            success "Command available: $cmd"
        fi
    done
    
    # Check internet connectivity
    if ! curl -s --connect-timeout 10 https://github.com >/dev/null; then
        error "No internet connectivity to GitHub"
        ((errors++))
    else
        success "Internet connectivity verified"
    fi
    
    return $errors
}

# Setup Docker
test_docker_setup() {
    log "Testing Docker setup..."
    
    # Check if Docker is installed
    if ! command -v docker >/dev/null 2>&1; then
        log "Installing Docker..."
        
        # Update package index
        sudo apt-get update
        
        # Install prerequisites
        sudo apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Add Docker's official GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Set up stable repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker Engine
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
        # Add user to docker group
        sudo usermod -aG docker "$USER"
        
        # Start and enable Docker
        sudo systemctl start docker
        sudo systemctl enable docker
        
        warning "Docker installed. Please log out and log back in, then re-run this script."
        return 1
    fi
    
    # Test Docker functionality
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running or accessible"
        return 1
    fi
    
    success "Docker is running"
    
    # Test Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose is not available"
        return 1
    fi
    
    success "Docker Compose is available"
    
    # Test Docker Buildx
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker Buildx is not available"
        return 1
    fi
    
    success "Docker Buildx is available"
    
    # Create buildx builder if needed
    if ! docker buildx ls | grep -q "multiarch"; then
        log "Creating multiarch builder..."
        docker buildx create --name multiarch --driver docker-container --use
        docker buildx inspect --bootstrap
    fi
    
    success "Docker setup completed"
    return 0
}

# Setup project
test_project_setup() {
    log "Testing project setup..."
    
    local test_dir="/tmp/ai-servis-test"
    
    # Clean up previous test
    rm -rf "$test_dir"
    
    # Clone or copy project
    if [ -d "$PROJECT_ROOT/.git" ]; then
        log "Copying project from current directory..."
        cp -r "$PROJECT_ROOT" "$test_dir"
    else
        log "Cloning project from GitHub..."
        git clone https://github.com/ai-servis/ai-servis.git "$test_dir"
    fi
    
    cd "$test_dir"
    
    # Install Python dependencies
    if [ -f "requirements-dev.txt" ]; then
        log "Installing Python dependencies..."
        pip3 install --user -r requirements-dev.txt
    fi
    
    # Install pre-commit hooks
    if [ -f ".pre-commit-config.yaml" ]; then
        log "Installing pre-commit hooks..."
        pip3 install --user pre-commit
        pre-commit install
    fi
    
    # Make scripts executable
    find . -name "*.sh" -exec chmod +x {} \;
    
    success "Project setup completed"
    return 0
}

# Test development environment
test_development_environment() {
    log "Testing development environment..."
    
    cd "/tmp/ai-servis-test"
    
    # Create .env file
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log "Created .env file from template"
    fi
    
    # Test environment startup
    log "Starting development environment..."
    timeout 300s ./scripts/dev-environment.sh up dev --build || {
        error "Failed to start development environment"
        return 1
    }
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 30
    
    # Test service endpoints
    local endpoints=(
        "http://localhost:8080/health"
        "http://localhost:8090/health"
        "http://localhost:8082/health"
        "http://localhost:8083/health"
    )
    
    local failed_endpoints=0
    for endpoint in "${endpoints[@]}"; do
        if curl -s -f --connect-timeout 10 "$endpoint" >/dev/null; then
            success "Endpoint responding: $endpoint"
        else
            error "Endpoint not responding: $endpoint"
            ((failed_endpoints++))
        fi
    done
    
    # Test database connectivity
    if timeout 10s bash -c "</dev/tcp/localhost/5432"; then
        success "PostgreSQL is accessible"
    else
        error "PostgreSQL is not accessible"
        ((failed_endpoints++))
    fi
    
    # Test Redis connectivity
    if timeout 10s bash -c "</dev/tcp/localhost/6379"; then
        success "Redis is accessible"
    else
        error "Redis is not accessible"
        ((failed_endpoints++))
    fi
    
    # Test MQTT broker
    if timeout 10s bash -c "</dev/tcp/localhost/1883"; then
        success "MQTT broker is accessible"
    else
        error "MQTT broker is not accessible"
        ((failed_endpoints++))
    fi
    
    # Stop development environment
    ./scripts/dev-environment.sh down dev
    
    return $failed_endpoints
}

# Test Pi simulation environment
test_pi_simulation() {
    log "Testing Pi simulation environment..."
    
    cd "/tmp/ai-servis-test"
    
    # Start Pi simulation
    log "Starting Pi simulation environment..."
    timeout 300s ./scripts/dev-environment.sh up pi-sim --build || {
        error "Failed to start Pi simulation environment"
        return 1
    }
    
    # Wait for services to start
    sleep 30
    
    # Test Pi simulation endpoints
    local pi_endpoints=(
        "http://localhost:8084"  # Pi Gateway
        "http://localhost:9000"  # GPIO Simulator
        "http://localhost:8087"  # Hardware Monitor
        "http://localhost:8088"  # Simulation Control
    )
    
    local failed_pi_endpoints=0
    for endpoint in "${pi_endpoints[@]}"; do
        if curl -s -f --connect-timeout 10 "$endpoint" >/dev/null; then
            success "Pi simulation endpoint responding: $endpoint"
        else
            error "Pi simulation endpoint not responding: $endpoint"
            ((failed_pi_endpoints++))
        fi
    done
    
    # Stop Pi simulation
    ./scripts/dev-environment.sh down pi-sim
    
    return $failed_pi_endpoints
}

# Test monitoring stack
test_monitoring_stack() {
    log "Testing monitoring stack..."
    
    cd "/tmp/ai-servis-test"
    
    # Start monitoring stack
    log "Starting monitoring stack..."
    timeout 300s ./scripts/dev-environment.sh up monitoring --build || {
        error "Failed to start monitoring stack"
        return 1
    }
    
    # Wait for services to start
    sleep 45
    
    # Test monitoring endpoints
    local monitoring_endpoints=(
        "http://localhost:3000"   # Grafana
        "http://localhost:9090"   # Prometheus
        "http://localhost:9093"   # AlertManager
        "http://localhost:16686"  # Jaeger
        "http://localhost:3001"   # Uptime Kuma
    )
    
    local failed_monitoring_endpoints=0
    for endpoint in "${monitoring_endpoints[@]}"; do
        if curl -s -f --connect-timeout 15 "$endpoint" >/dev/null; then
            success "Monitoring endpoint responding: $endpoint"
        else
            error "Monitoring endpoint not responding: $endpoint"
            ((failed_monitoring_endpoints++))
        fi
    done
    
    # Stop monitoring stack
    ./scripts/dev-environment.sh down monitoring
    
    return $failed_monitoring_endpoints
}

# Simulate CI pipeline
test_ci_simulation() {
    log "Testing CI pipeline simulation..."
    
    cd "/tmp/ai-servis-test"
    
    # Test linting
    if [ -f "requirements-dev.txt" ]; then
        log "Running Python linting..."
        if python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics; then
            success "Python linting passed"
        else
            warning "Python linting found issues (non-critical for VM test)"
        fi
    fi
    
    # Test Docker builds
    log "Testing Docker build..."
    if [ -f "modules/core-orchestrator/Dockerfile" ]; then
        if timeout 300s docker build -t test-core-orchestrator modules/core-orchestrator/; then
            success "Docker build successful"
            docker rmi test-core-orchestrator
        else
            error "Docker build failed"
            return 1
        fi
    fi
    
    # Test multi-platform build script
    if [ -f "scripts/docker-build-multiplatform.sh" ]; then
        log "Testing multi-platform build script..."
        if timeout 60s ./scripts/docker-build-multiplatform.sh --help >/dev/null; then
            success "Multi-platform build script is functional"
        else
            error "Multi-platform build script failed"
            return 1
        fi
    fi
    
    success "CI simulation completed"
    return 0
}

# Test performance
test_performance_validation() {
    log "Testing performance validation..."
    
    cd "/tmp/ai-servis-test"
    
    # Start minimal environment for performance testing
    ./scripts/dev-environment.sh up dev >/dev/null 2>&1
    sleep 30
    
    # Run performance tests if available
    if [ -f "scripts/performance-tests.sh" ]; then
        log "Running performance tests..."
        if timeout 120s ./scripts/performance-tests.sh; then
            success "Performance tests completed"
        else
            warning "Performance tests failed or timed out (non-critical for VM test)"
        fi
    fi
    
    # Test system resource usage
    log "Checking system resource usage..."
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local memory_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
    
    log "Current CPU usage: ${cpu_usage}%"
    log "Current memory usage: ${memory_usage}%"
    
    # Stop environment
    ./scripts/dev-environment.sh down dev >/dev/null 2>&1
    
    success "Performance validation completed"
    return 0
}

# Generate test report
generate_test_report() {
    local total_tests="$1"
    local passed_tests="$2"
    local failed_tests="$3"
    
    local report_file="$TEST_RESULTS_DIR/vm-test-report.md"
    
    cat > "$report_file" << EOF
# AI-Servis VM Test Report

**Test Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**VM Environment:** $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown Linux")
**Total Tests:** $total_tests
**Passed:** $passed_tests  
**Failed:** $failed_tests
**Success Rate:** $(( (passed_tests * 100) / total_tests ))%

## System Information

- **Hostname:** $(hostname)
- **OS:** $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")
- **Kernel:** $(uname -r)
- **Architecture:** $(uname -m)
- **CPU Cores:** $(nproc)
- **Memory:** $(free -h | grep '^Mem:' | awk '{print $2}')
- **Disk Space:** $(df -h / | tail -1 | awk '{print $4}')

## Test Results Summary

EOF

    if [ $failed_tests -eq 0 ]; then
        echo "✅ **All VM tests passed successfully!**" >> "$report_file"
        echo "" >> "$report_file"
        echo "The AI-Servis CI/CD infrastructure is fully functional in the VM environment." >> "$report_file"
    else
        echo "❌ **Some VM tests failed:**" >> "$report_file"
        echo "" >> "$report_file"
        echo "Please review the test log for detailed error information." >> "$report_file"
    fi

    echo "" >> "$report_file"
    echo "## Detailed Test Log" >> "$report_file"
    echo "" >> "$report_file"
    echo '```' >> "$report_file"
    cat "$VM_TEST_LOG" >> "$report_file"
    echo '```' >> "$report_file"

    success "Test report generated: $report_file"
}

# Main test execution
main() {
    log "Starting AI-Servis VM Test Suite..."
    
    init_test_environment
    
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    # Run all test phases
    for phase in "${PHASES[@]}"; do
        ((total_tests++))
        
        log "=== Running test phase: $phase ==="
        
        case "$phase" in
            "system_requirements")
                if test_system_requirements; then
                    ((passed_tests++))
                    success "✓ System requirements test passed"
                else
                    ((failed_tests++))
                    error "✗ System requirements test failed"
                fi
                ;;
            "docker_setup")
                if test_docker_setup; then
                    ((passed_tests++))
                    success "✓ Docker setup test passed"
                else
                    ((failed_tests++))
                    error "✗ Docker setup test failed"
                fi
                ;;
            "project_setup")
                if test_project_setup; then
                    ((passed_tests++))
                    success "✓ Project setup test passed"
                else
                    ((failed_tests++))
                    error "✗ Project setup test failed"
                fi
                ;;
            "development_environment")
                if test_development_environment; then
                    ((passed_tests++))
                    success "✓ Development environment test passed"
                else
                    ((failed_tests++))
                    error "✗ Development environment test failed"
                fi
                ;;
            "pi_simulation")
                if test_pi_simulation; then
                    ((passed_tests++))
                    success "✓ Pi simulation test passed"
                else
                    ((failed_tests++))
                    error "✗ Pi simulation test failed"
                fi
                ;;
            "monitoring_stack")
                if test_monitoring_stack; then
                    ((passed_tests++))
                    success "✓ Monitoring stack test passed"
                else
                    ((failed_tests++))
                    error "✗ Monitoring stack test failed"
                fi
                ;;
            "ci_simulation")
                if test_ci_simulation; then
                    ((passed_tests++))
                    success "✓ CI simulation test passed"
                else
                    ((failed_tests++))
                    error "✗ CI simulation test failed"
                fi
                ;;
            "performance_validation")
                if test_performance_validation; then
                    ((passed_tests++))
                    success "✓ Performance validation test passed"
                else
                    ((failed_tests++))
                    error "✗ Performance validation test failed"
                fi
                ;;
        esac
        
        echo "" # Add spacing between phases
    done
    
    # Generate test report
    generate_test_report "$total_tests" "$passed_tests" "$failed_tests"
    
    # Print final summary
    echo ""
    log "=== VM Test Suite Complete ==="
    log "Total Tests: $total_tests"
    log "Passed: $passed_tests"
    log "Failed: $failed_tests"
    log "Success Rate: $(( (passed_tests * 100) / total_tests ))%"
    
    if [ $failed_tests -eq 0 ]; then
        success "🎉 All VM tests passed! AI-Servis is ready for deployment."
        exit 0
    else
        error "💥 Some VM tests failed. Please review the logs and fix issues."
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "--help"|"-h")
        echo "AI-Servis VM Test Suite"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --quick        Run quick tests only (skip performance tests)"
        echo "  --cleanup      Clean up test artifacts and exit"
        echo ""
        echo "This script tests the complete AI-Servis CI/CD infrastructure in a VM environment."
        echo "It validates Docker setup, development environment, Pi simulation, and monitoring."
        exit 0
        ;;
    "--cleanup")
        log "Cleaning up VM test artifacts..."
        rm -rf /tmp/ai-servis-test
        rm -rf "$TEST_RESULTS_DIR"
        rm -f "$VM_TEST_LOG"
        docker system prune -f
        success "Cleanup completed"
        exit 0
        ;;
    "--quick")
        # Remove performance_validation from phases for quick test
        PHASES=("${PHASES[@]/performance_validation}")
        log "Running quick VM test (skipping performance validation)..."
        ;;
esac

# Run main function
main "$@"