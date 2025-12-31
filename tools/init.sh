#!/bin/bash
# MIA Universal Initialization Script
# Initialize project environment and verify setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if environment is properly set up
check_environment() {
    log_info "Checking environment setup..."

    local issues=()

    # Check Python
    if ! python3 --version &> /dev/null; then
        issues+=("Python 3 not found")
    else
        local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        log_info "Python version: $python_version"
    fi

    # Check Conan
    if ! conan --version &> /dev/null; then
        issues+=("Conan not found in PATH")
    else
        local conan_version=$(conan --version | head -n1)
        log_info "Conan version: $conan_version"
    fi

    # Check required Python packages
    local python_packages=("websockets" "aiohttp" "pydantic" "fastapi" "uvicorn")
    for package in "${python_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            issues+=("Python package $package not installed")
        fi
    done

    # Check project structure
    local required_files=("conanfile.py" "modules/core-orchestrator/main.py")
    for file in "${required_files[@]}"; do
        if [ ! -f "$PROJECT_ROOT/$file" ]; then
            issues+=("Required file missing: $file")
        fi
    done

    if [ ${#issues[@]} -gt 0 ]; then
        log_error "Environment check failed:"
        for issue in "${issues[@]}"; do
            log_error "  - $issue"
        done
        return 1
    fi

    log_success "Environment check passed"
    return 0
}

# Install Conan dependencies
install_conan_dependencies() {
    log_info "Installing Conan dependencies..."

    cd "$PROJECT_ROOT"

    # Try Cloudsmith first
    if conan remote list | grep -q "sparetools"; then
        log_info "Using Cloudsmith repository..."
        if ! conan install . --build=missing -r sparetools; then
            log_warning "Cloudsmith installation failed, trying GitHub Packages..."
            if ! conan install . --build=missing; then
                log_error "Conan dependency installation failed"
                return 1
            fi
        fi
    else
        log_info "Installing from default remotes..."
        if ! conan install . --build=missing; then
            log_error "Conan dependency installation failed"
            return 1
        fi
    fi

    log_success "Conan dependencies installed"
    return 0
}

# Verify project can run
verify_project() {
    log_info "Verifying project setup..."

    # Try importing main modules
    if ! python3 -c "import sys; sys.path.insert(0, 'modules'); import mcp_framework; print('MCP framework imported successfully')"; then
        log_error "Failed to import MCP framework"
        return 1
    fi

    if ! python3 -c "import sys; sys.path.insert(0, 'modules'); import core_orchestrator.main; print('Core orchestrator imported successfully')"; then
        log_error "Failed to import core orchestrator"
        return 1
    fi

    log_success "Project verification passed"
    return 0
}

# Setup development environment
setup_dev_environment() {
    log_info "Setting up development environment..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install development dependencies
    if [ -f "requirements-dev.txt" ]; then
        log_info "Installing development dependencies..."
        pip install -r requirements-dev.txt
    fi

    # Create .env file template if it doesn't exist
    if [ ! -f ".env" ]; then
        log_info "Creating .env template..."
        cat > .env << 'EOF'
# MIA Universal Environment Configuration

# MCP Server Configuration
MCP_HOST=localhost
MCP_PORT=8080

# Service Ports
CORE_ORCHESTRATOR_PORT=8080
AI_AUDIO_ASSISTANT_PORT=8082
AI_PLATFORM_CONTROLLER_PORT=8083

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/mia.log

# Cloudsmith Configuration (optional)
# CLOUDSMITH_USERNAME=your_username
# CLOUDSMITH_API_KEY=your_api_key

# GitHub Configuration (optional)
# GITHUB_USERNAME=your_username
# GITHUB_TOKEN=your_token
EOF
    fi

    # Create logs directory
    mkdir -p logs

    log_success "Development environment setup complete"
}

# Print project information
print_project_info() {
    echo
    log_info "MIA Universal Project Information:"
    echo "  Project Root: $PROJECT_ROOT"
    echo "  Python: $(python3 --version 2>/dev/null || echo 'Not found')"
    echo "  Conan: $(conan --version 2>/dev/null | head -n1 || echo 'Not found')"
    echo
    log_info "Available commands:"
    echo "  Start core orchestrator: python3 modules/core-orchestrator/main.py"
    echo "  Start audio assistant: python3 modules/ai-audio-assistant/main.py"
    echo "  Install dependencies: conan install . --build=missing"
    echo "  Run tests: python3 -m pytest"
    echo
    log_info "Documentation:"
    echo "  docs/README.md - Main documentation"
    echo "  docs/BOOTSTRAP.md - Bootstrap guide"
    echo "  docs/DEPLOYMENT.md - Deployment instructions"
}

# Print usage information
print_usage() {
    cat << EOF
MIA Universal Initialization Script

Usage: $0 [OPTIONS]

Options:
    --help              Show this help message
    --no-conan          Skip Conan dependency installation
    --no-verify         Skip project verification
    --dev               Setup development environment
    --clean             Clean build artifacts and start fresh

Examples:
    $0                      # Standard initialization
    $0 --dev               # Setup development environment
    $0 --clean             # Clean and reinitialize
    $0 --no-conan         # Skip Conan installation
EOF
}

# Clean build artifacts
clean_artifacts() {
    log_info "Cleaning build artifacts..."

    # Remove Conan build directories
    rm -rf build-release/conan/
    rm -rf build/

    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

    # Remove virtual environment
    rm -rf venv/

    # Remove logs
    rm -rf logs/

    log_success "Build artifacts cleaned"
}

# Main function
main() {
    local no_conan=false
    local no_verify=false
    local dev=false
    local clean=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_usage
                exit 0
                ;;
            --no-conan)
                no_conan=true
                shift
                ;;
            --no-verify)
                no_verify=true
                shift
                ;;
            --dev)
                dev=true
                shift
                ;;
            --clean)
                clean=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    log_info "MIA Universal Initialization Starting..."

    if [ "$clean" = true ]; then
        clean_artifacts
    fi

    if ! check_environment; then
        log_error "Environment check failed. Run ./tools/bootstrap.sh first"
        exit 1
    fi

    if [ "$no_conan" = false ]; then
        if ! install_conan_dependencies; then
            log_error "Conan dependency installation failed"
            exit 1
        fi
    else
        log_info "Skipping Conan dependency installation"
    fi

    if [ "$no_verify" = false ]; then
        if ! verify_project; then
            log_error "Project verification failed"
            exit 1
        fi
    else
        log_info "Skipping project verification"
    fi

    if [ "$dev" = true ]; then
        setup_dev_environment
    fi

    log_success "Initialization completed successfully!"
    print_project_info
}

# Run main function
main "$@"