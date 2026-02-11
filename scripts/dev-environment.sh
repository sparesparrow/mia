#!/usr/bin/env bash
set -euo pipefail

# AI-Servis Development Environment Manager
# Comprehensive script to manage the development environment

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

# Environment configurations
ENVIRONMENTS=(
    "dev:docker-compose.dev.yml:Development environment with hot reloading"
    "prod:docker-compose.yml:Production-like environment"
    "pi-sim:docker-compose.pi-simulation.yml:Raspberry Pi simulation environment"
    "monitoring:docker-compose.monitoring.yml:Monitoring and observability stack"
    "full:all:Complete environment with all services"
)

# Show usage
show_usage() {
    echo "AI-Servis Development Environment Manager"
    echo ""
    echo "Usage: $0 <command> [environment] [options]"
    echo ""
    echo "Commands:"
    echo "  up       Start the environment"
    echo "  down     Stop the environment"
    echo "  restart  Restart the environment"
    echo "  status   Show environment status"
    echo "  logs     Show logs for services"
    echo "  build    Build/rebuild containers"
    echo "  clean    Clean up containers, volumes, and images"
    echo "  health   Check health of all services"
    echo "  shell    Open shell in a service container"
    echo "  test     Run tests in the environment"
    echo "  backup   Backup environment data"
    echo "  restore  Restore environment data"
    echo ""
    echo "Environments:"
    for env_info in "${ENVIRONMENTS[@]}"; do
        IFS=':' read -r name file description <<< "$env_info"
        printf "  %-12s %s\n" "$name" "$description"
    done
    echo ""
    echo "Options:"
    echo "  --build        Force rebuild containers"
    echo "  --pull         Pull latest images"
    echo "  --no-deps      Don't start dependent services"
    echo "  --detach       Run in background (default)"
    echo "  --follow       Follow logs output"
    echo ""
    echo "Examples:"
    echo "  $0 up dev                    # Start development environment"
    echo "  $0 up full --build          # Start all services with rebuild"
    echo "  $0 logs dev core-orchestrator # Show logs for specific service"
    echo "  $0 shell dev ai-servis-core  # Open shell in core service"
    echo "  $0 test dev                  # Run tests in dev environment"
}

# Get compose files for environment
get_compose_files() {
    local env="$1"
    local files=()
    
    case "$env" in
        "dev")
            files=("-f" "docker-compose.dev.yml")
            ;;
        "prod")
            files=("-f" "docker-compose.yml")
            ;;
        "pi-sim")
            files=("-f" "docker-compose.pi-simulation.yml")
            ;;
        "monitoring")
            files=("-f" "docker-compose.monitoring.yml")
            ;;
        "full")
            files=("-f" "docker-compose.dev.yml" "-f" "docker-compose.pi-simulation.yml" "-f" "docker-compose.monitoring.yml")
            ;;
        *)
            error "Unknown environment: $env"
            return 1
            ;;
    esac
    
    echo "${files[@]}"
}

# Check prerequisites
check_prerequisites() {
    local missing_tools=()
    
    for tool in docker docker-compose jq curl; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        echo "Please install them and try again"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running"
        return 1
    fi
    
    return 0
}

# Create necessary directories
setup_directories() {
    log "Setting up directories..."
    
    local dirs=(
        "logs"
        "volumes/core-config"
        "volumes/core-data"
        "volumes/discovery-data"
        "volumes/audio-config"
        "volumes/platform-config"
        "volumes/mqtt-data"
        "volumes/mqtt-logs"
        "volumes/postgres-data-dev"
        "volumes/redis-data-dev"
        "volumes/prometheus-data"
        "volumes/grafana-data"
        "volumes/pi-sim-config"
        "volumes/pi-sim-data"
        "volumes/gpio-sim-state"
        "volumes/hw-monitor-data"
        "volumes/mqtt-pi-data"
        "volumes/mqtt-pi-logs"
        "volumes/redis-sim-data"
        "volumes/sim-control-config"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$PROJECT_ROOT/$dir"
    done
    
    # Set appropriate permissions
    if [ "$(id -u)" = "0" ]; then
        chown -R 1000:1000 "$PROJECT_ROOT/volumes" "$PROJECT_ROOT/logs"
    fi
}

# Start environment
start_environment() {
    local env="$1"
    shift
    local options=("$@")
    
    log "Starting $env environment..."
    
    setup_directories
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    # Parse options
    local build_flag=""
    local pull_flag=""
    local no_deps_flag=""
    local detach_flag="-d"
    
    for option in "${options[@]}"; do
        case "$option" in
            "--build")
                build_flag="--build"
                ;;
            "--pull")
                pull_flag="--pull"
                ;;
            "--no-deps")
                no_deps_flag="--no-deps"
                ;;
            "--no-detach")
                detach_flag=""
                ;;
        esac
    done
    
    # Execute docker-compose up
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(up $detach_flag $build_flag $pull_flag $no_deps_flag)
    
    log "Executing: ${cmd[*]}"
    
    if "${cmd[@]}"; then
        success "$env environment started successfully"
        
        # Wait a bit for services to start
        if [ -n "$detach_flag" ]; then
            log "Waiting for services to start..."
            sleep 10
            show_environment_info "$env"
        fi
        
        return 0
    else
        error "Failed to start $env environment"
        return 1
    fi
}

# Stop environment
stop_environment() {
    local env="$1"
    
    log "Stopping $env environment..."
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(down)
    
    if "${cmd[@]}"; then
        success "$env environment stopped successfully"
        return 0
    else
        error "Failed to stop $env environment"
        return 1
    fi
}

# Restart environment
restart_environment() {
    local env="$1"
    shift
    
    stop_environment "$env"
    start_environment "$env" "$@"
}

# Show environment status
show_status() {
    local env="$1"
    
    log "Checking status of $env environment..."
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(ps)
    
    "${cmd[@]}"
}

# Show logs
show_logs() {
    local env="$1"
    local service="${2:-}"
    local follow="${3:-false}"
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(logs)
    
    if [ "$follow" = "true" ]; then
        cmd+=("-f")
    fi
    
    if [ -n "$service" ]; then
        cmd+=("$service")
    fi
    
    "${cmd[@]}"
}

# Build containers
build_containers() {
    local env="$1"
    
    log "Building containers for $env environment..."
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(build --no-cache)
    
    if "${cmd[@]}"; then
        success "Containers built successfully"
        return 0
    else
        error "Failed to build containers"
        return 1
    fi
}

# Clean up environment
clean_environment() {
    local env="$1"
    
    warning "This will remove all containers, volumes, and images for $env environment"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Cleanup cancelled"
        return 0
    fi
    
    log "Cleaning up $env environment..."
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(down -v --rmi all)
    
    if "${cmd[@]}"; then
        success "$env environment cleaned up successfully"
        return 0
    else
        error "Failed to clean up $env environment"
        return 1
    fi
}

# Health check
health_check() {
    local env="$1"
    
    log "Performing health check for $env environment..."
    
    if [ -f "$PROJECT_ROOT/scripts/health-check.sh" ]; then
        "$PROJECT_ROOT/scripts/health-check.sh"
    else
        warning "Health check script not found"
        return 1
    fi
}

# Open shell in container
open_shell() {
    local env="$1"
    local service="$2"
    
    log "Opening shell in $service..."
    
    local compose_files
    if ! compose_files=$(get_compose_files "$env"); then
        return 1
    fi
    
    local cmd=(docker-compose)
    read -ra compose_files_array <<< "$compose_files"
    cmd+=("${compose_files_array[@]}")
    cmd+=(exec "$service" bash)
    
    "${cmd[@]}"
}

# Run tests
run_tests() {
    local env="$1"
    
    log "Running tests in $env environment..."
    
    # Run different test suites based on environment
    case "$env" in
        "dev"|"full")
            if [ -f "$PROJECT_ROOT/scripts/system-tests.sh" ]; then
                "$PROJECT_ROOT/scripts/system-tests.sh"
            fi
            ;;
        "pi-sim")
            log "Running Pi simulation tests..."
            # Add Pi-specific tests here
            ;;
        "monitoring")
            log "Running monitoring tests..."
            # Add monitoring tests here
            ;;
    esac
}

# Show environment information
show_environment_info() {
    local env="$1"
    
    echo ""
    success "🎯 $env Environment Ready!"
    echo ""
    
    case "$env" in
        "dev"|"full")
            echo "📍 Service Endpoints:"
            echo "  - Core Orchestrator:    http://localhost:8080"
            echo "  - Service Discovery:    http://localhost:8090"
            echo "  - AI Audio Assistant:   http://localhost:8082"
            echo "  - Platform Controller:  http://localhost:8083"
            echo "  - Documentation:        http://localhost:8000"
            echo ""
            echo "🔌 Database Connections:"
            echo "  - PostgreSQL:  localhost:5432"
            echo "  - Redis:       localhost:6379"
            echo "  - MQTT:        localhost:1883"
            ;;
    esac
    
    if [[ "$env" == "monitoring" || "$env" == "full" ]]; then
        echo ""
        echo "📊 Monitoring:"
        echo "  - Grafana Dashboard:    http://localhost:3000"
        echo "  - Prometheus Metrics:   http://localhost:9090"
        echo "  - AlertManager:         http://localhost:9093"
        echo "  - Jaeger Tracing:       http://localhost:16686"
        echo "  - Uptime Kuma:          http://localhost:3001"
    fi
    
    if [[ "$env" == "pi-sim" || "$env" == "full" ]]; then
        echo ""
        echo "🔧 Pi Simulation:"
        echo "  - Pi Gateway:           http://localhost:8084"
        echo "  - GPIO Simulator:       http://localhost:9000"
        echo "  - Hardware Monitor:     http://localhost:8087"
        echo "  - Simulation Control:   http://localhost:8088"
    fi
    
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    local command="$1"
    shift
    
    if ! check_prerequisites; then
        exit 1
    fi
    
    case "$command" in
        "up")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            start_environment "$@"
            ;;
        "down")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            stop_environment "$1"
            ;;
        "restart")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            restart_environment "$@"
            ;;
        "status")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            show_status "$1"
            ;;
        "logs")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            local follow=false
            if [[ "${@: -1}" == "--follow" ]]; then
                follow=true
                set -- "${@:1:$(($#-1))}"  # Remove last argument
            fi
            show_logs "$1" "${2:-}" "$follow"
            ;;
        "build")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            build_containers "$1"
            ;;
        "clean")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            clean_environment "$1"
            ;;
        "health")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            health_check "$1"
            ;;
        "shell")
            if [ $# -lt 2 ]; then
                error "Environment and service required"
                show_usage
                exit 1
            fi
            open_shell "$1" "$2"
            ;;
        "test")
            if [ $# -eq 0 ]; then
                error "Environment required"
                show_usage
                exit 1
            fi
            run_tests "$1"
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"