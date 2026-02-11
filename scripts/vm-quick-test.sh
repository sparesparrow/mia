#!/usr/bin/env bash
set -euo pipefail

# Quick VM Test Script for AI-Servis
# Minimal test suite for rapid validation

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Quick test functions
quick_system_check() {
    log "Quick system check..."
    
    # Check memory (minimum 4GB for quick test)
    local memory_gb=$(free -g | grep '^Mem:' | awk '{print $2}')
    if [ "$memory_gb" -lt 4 ]; then
        error "Insufficient memory: ${memory_gb}GB (minimum: 4GB)"
        return 1
    fi
    
    # Check disk space (minimum 20GB)
    local disk_gb=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$disk_gb" -lt 20 ]; then
        error "Insufficient disk space: ${disk_gb}GB (minimum: 20GB)"
        return 1
    fi
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker not installed"
        return 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        error "Docker not running"
        return 1
    fi
    
    success "System check passed"
    return 0
}

quick_project_test() {
    log "Quick project test..."
    
    # Check if we're in the project directory
    if [ ! -f "docker-compose.dev.yml" ]; then
        error "Not in AI-Servis project directory"
        return 1
    fi
    
    # Check essential scripts exist
    local scripts=("scripts/dev-environment.sh" "scripts/health-check.sh")
    for script in "${scripts[@]}"; do
        if [ ! -f "$script" ]; then
            error "Missing script: $script"
            return 1
        fi
    done
    
    success "Project structure validated"
    return 0
}

quick_docker_test() {
    log "Quick Docker test..."
    
    # Test basic Docker functionality
    if ! docker run --rm hello-world >/dev/null 2>&1; then
        error "Docker basic test failed"
        return 1
    fi
    
    # Test Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose not available"
        return 1
    fi
    
    success "Docker functionality verified"
    return 0
}

quick_service_test() {
    log "Quick service test..."
    
    # Start minimal services (just core)
    log "Starting core services..."
    if ! timeout 120s docker compose -f docker-compose.dev.yml up -d ai-servis-core mqtt-broker postgres redis >/dev/null 2>&1; then
        error "Failed to start core services"
        return 1
    fi
    
    # Wait for services
    sleep 15
    
    # Test core service
    if curl -s -f --connect-timeout 10 "http://localhost:8080/health" >/dev/null; then
        success "Core service responding"
    else
        warning "Core service not responding (may still be starting)"
    fi
    
    # Cleanup
    docker compose -f docker-compose.dev.yml down >/dev/null 2>&1
    
    success "Service test completed"
    return 0
}

# Main quick test
main() {
    echo "🚀 AI-Servis Quick VM Test"
    echo "=========================="
    
    local tests_passed=0
    local tests_total=4
    
    # Run quick tests
    if quick_system_check; then ((tests_passed++)); fi
    if quick_project_test; then ((tests_passed++)); fi  
    if quick_docker_test; then ((tests_passed++)); fi
    if quick_service_test; then ((tests_passed++)); fi
    
    echo ""
    echo "=========================="
    log "Quick test results: $tests_passed/$tests_total passed"
    
    if [ $tests_passed -eq $tests_total ]; then
        success "🎉 Quick VM test passed! System ready for full testing."
        echo ""
        echo "Next steps:"
        echo "  1. Run full test: ./scripts/vm-test-setup.sh"
        echo "  2. Start development: ./scripts/dev-environment.sh up dev"
        echo "  3. View documentation: http://localhost:8000"
        exit 0
    else
        error "💥 Quick VM test failed. Please fix issues before proceeding."
        echo ""
        echo "Troubleshooting:"
        echo "  1. Check system requirements (8GB RAM, 50GB disk)"
        echo "  2. Install/start Docker: sudo systemctl start docker"
        echo "  3. Run from project directory"
        echo "  4. Check internet connectivity"
        exit 1
    fi
}

# Show help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "AI-Servis Quick VM Test"
    echo ""
    echo "Usage: $0"
    echo ""
    echo "Performs a quick validation of the VM environment:"
    echo "  - System requirements check"
    echo "  - Project structure validation"
    echo "  - Docker functionality test"
    echo "  - Basic service startup test"
    echo ""
    echo "This test takes ~2-3 minutes vs 20-30 minutes for the full test suite."
    echo ""
    echo "For full testing, use: ./scripts/vm-test-setup.sh"
    exit 0
fi

# Run main function
main "$@"