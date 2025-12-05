#!/bin/bash

# 🚀 AI-SERVIS Universal Docker Orchestration
# Advanced multi-platform container management for automotive AI voice control
# Supports AMD64, ARM64, and edge deployment scenarios

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="${REGISTRY:-ghcr.io/sparesparrow/mia-universal}"
VERSION="${VERSION:-latest}"
PLATFORM="${PLATFORM:-linux/amd64,linux/arm64}"
BUILD_ARGS="${BUILD_ARGS:-}"
DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

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

# Check dependencies
check_dependencies() {
    local deps=("docker" "buildx")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "$dep is required but not installed"
            exit 1
        fi
    done
    
    # Check Docker Buildx
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx is required for multi-platform builds"
        exit 1
    fi
}

# Setup buildx builder
setup_builder() {
    local builder_name="mia-builder"
    
    if ! docker buildx ls | grep -q "$builder_name"; then
        log_info "Creating buildx builder: $builder_name"
        docker buildx create \
            --name "$builder_name" \
            --driver docker-container \
            --platform "$PLATFORM" \
            --use
        
        docker buildx inspect --bootstrap
    else
        log_info "Using existing builder: $builder_name"
        docker buildx use "$builder_name"
    fi
}

# Build component image
build_component() {
    local component="$1"
    local dockerfile="$2"
    local context="${3:-$PROJECT_ROOT}"
    local extra_args="${4:-}"
    
    log_info "Building $component for platforms: $PLATFORM"
    
    local image_name="$REGISTRY/$component:$VERSION"
    local build_cmd=(
        docker buildx build
        --platform "$PLATFORM"
        --file "$dockerfile"
        --tag "$image_name"
        --label "org.opencontainers.image.title=$component"
        --label "org.opencontainers.image.version=$VERSION"
        --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        --label "org.opencontainers.image.source=https://github.com/sparesparrow/mia-universal"
        --label "org.opencontainers.image.vendor=AI-SERVIS"
        --label "ai.servis.component=$component"
        --label "ai.servis.automotive=true"
        --cache-from "type=gha"
        --cache-to "type=gha,mode=max"
    )
    
    # Add build arguments
    if [[ -n "$BUILD_ARGS" ]]; then
        IFS=',' read -ra ARGS <<< "$BUILD_ARGS"
        for arg in "${ARGS[@]}"; do
            build_cmd+=(--build-arg "$arg")
        done
    fi
    
    # Add extra arguments
    if [[ -n "$extra_args" ]]; then
        IFS=' ' read -ra EXTRA <<< "$extra_args"
        build_cmd+=("${EXTRA[@]}")
    fi
    
    build_cmd+=("$context")
    
    log_info "Executing: ${build_cmd[*]}"
    
    if "${build_cmd[@]}"; then
        log_success "Successfully built $component"
        return 0
    else
        log_error "Failed to build $component"
        return 1
    fi
}

# Security scan image
security_scan() {
    local image="$1"
    
    log_info "Security scanning: $image"
    
    # Trivy scan
    if command -v trivy &> /dev/null; then
        trivy image --exit-code 1 --severity HIGH,CRITICAL "$image" || {
            log_warning "Security vulnerabilities found in $image"
            return 1
        }
    else
        log_warning "Trivy not available, skipping security scan"
    fi
    
    # Hadolint for Dockerfile linting
    if command -v hadolint &> /dev/null; then
        local dockerfile="${2:-Dockerfile}"
        hadolint "$dockerfile" || {
            log_warning "Dockerfile issues found in $dockerfile"
        }
    fi
    
    log_success "Security scan completed for $image"
}

# Build all components
build_all() {
    local push_flag="$1"
    local components=(
        "core-orchestrator:modules/core-orchestrator/Dockerfile"
        "ai-audio-assistant:modules/ai-audio-assistant/Dockerfile"
        "hardware-bridge:platforms/cpp/Dockerfile"
        "ai-security:modules/ai-security/Dockerfile"
        "service-discovery:modules/service-discovery/Dockerfile"
    )
    
    local failed_builds=()
    
    for component_info in "${components[@]}"; do
        IFS=':' read -r component dockerfile <<< "$component_info"
        
        if [[ -f "$PROJECT_ROOT/$dockerfile" ]]; then
            local push_arg=""
            if [[ "$push_flag" == "true" ]]; then
                push_arg="--push"
            else
                push_arg="--load"
            fi
            
            if build_component "$component" "$PROJECT_ROOT/$dockerfile" "$PROJECT_ROOT" "$push_arg"; then
                # Security scan if built locally
                if [[ "$push_flag" != "true" ]]; then
                    security_scan "$REGISTRY/$component:$VERSION" "$PROJECT_ROOT/$dockerfile"
                fi
            else
                failed_builds+=("$component")
            fi
        else
            log_warning "Dockerfile not found: $dockerfile"
            failed_builds+=("$component")
        fi
    done
    
    if [[ ${#failed_builds[@]} -eq 0 ]]; then
        log_success "All components built successfully!"
    else
        log_error "Failed to build: ${failed_builds[*]}"
        return 1
    fi
}

# Deploy stack
deploy_stack() {
    local environment="${1:-dev}"
    local compose_file="$PROJECT_ROOT/docker-compose.$environment.yml"
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Compose file not found: $compose_file"
        return 1
    fi
    
    log_info "Deploying stack for environment: $environment"
    
    # Pull latest images
    docker-compose -f "$compose_file" pull
    
    # Deploy with health checks
    docker-compose -f "$compose_file" up -d --remove-orphans
    
    # Wait for services to be healthy
    log_info "Waiting for services to become healthy..."
    local timeout=300
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        if docker-compose -f "$compose_file" ps | grep -q "unhealthy\|starting"; then
            log_info "Services still starting... ($elapsed/$timeout seconds)"
            sleep 10
            elapsed=$((elapsed + 10))
        else
            break
        fi
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log_error "Services failed to become healthy within $timeout seconds"
        docker-compose -f "$compose_file" ps
        return 1
    fi
    
    log_success "Stack deployed successfully for environment: $environment"
    docker-compose -f "$compose_file" ps
}

# Automotive-specific optimizations
optimize_for_automotive() {
    log_info "Applying automotive-specific optimizations"
    
    # Set Docker daemon options for automotive environments
    local docker_opts=(
        --storage-opt dm.basesize=10G
        --log-driver json-file
        --log-opt max-size=10m
        --log-opt max-file=3
    )
    
    # Create optimized Docker daemon configuration
    local docker_config="/etc/docker/daemon.json"
    if [[ -w "$(dirname "$docker_config")" ]]; then
        cat > "$docker_config" <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.size=10G"
  ],
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "max-concurrent-downloads": 3,
  "max-concurrent-uploads": 3
}
EOF
        log_success "Applied automotive Docker optimizations"
    else
        log_warning "Cannot write Docker daemon config, skipping optimizations"
    fi
}

# Performance monitoring
monitor_performance() {
    local duration="${1:-60}"
    
    log_info "Monitoring container performance for $duration seconds"
    
    # Create monitoring script
    local monitor_script="/tmp/docker-monitor.sh"
    cat > "$monitor_script" <<'EOF'
#!/bin/bash
echo "timestamp,container,cpu_percent,memory_usage,memory_limit,network_rx,network_tx"
while true; do
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | \
    tail -n +2 | while read -r line; do
        container=$(echo "$line" | awk '{print $1}')
        cpu=$(echo "$line" | awk '{print $2}' | sed 's/%//')
        mem_usage=$(echo "$line" | awk '{print $3}' | sed 's/MiB.*//')
        mem_limit=$(echo "$line" | awk '{print $4}' | sed 's/MiB//')
        net_rx=$(echo "$line" | awk '{print $5}' | sed 's/MB.*//')
        net_tx=$(echo "$line" | awk '{print $7}' | sed 's/MB.*//')
        echo "$(date +%s),$container,$cpu,$mem_usage,$mem_limit,$net_rx,$net_tx"
    done
    sleep 5
done
EOF
    
    chmod +x "$monitor_script"
    timeout "$duration" "$monitor_script" > "/tmp/performance-$(date +%Y%m%d-%H%M%S).csv"
    
    log_success "Performance monitoring completed, data saved to /tmp/performance-*.csv"
}

# Main function
main() {
    local action="${1:-help}"
    
    case "$action" in
        "build")
            check_dependencies
            setup_builder
            build_all "false"
            ;;
        "build-push")
            check_dependencies
            setup_builder
            build_all "true"
            ;;
        "deploy")
            local env="${2:-dev}"
            deploy_stack "$env"
            ;;
        "optimize")
            optimize_for_automotive
            ;;
        "monitor")
            local duration="${2:-60}"
            monitor_performance "$duration"
            ;;
        "scan")
            local image="${2:-$REGISTRY/core-orchestrator:$VERSION}"
            security_scan "$image"
            ;;
        "help"|*)
            cat <<EOF
🚀 AI-SERVIS Universal Docker Orchestration

Usage: $0 <action> [options]

Actions:
  build           Build all images for local use
  build-push      Build and push all images to registry
  deploy <env>    Deploy stack to environment (dev/staging/prod)
  optimize        Apply automotive-specific optimizations
  monitor <sec>   Monitor container performance (default: 60s)
  scan <image>    Security scan specific image
  help            Show this help

Environment Variables:
  REGISTRY        Container registry (default: ghcr.io/sparesparrow/mia-universal)
  VERSION         Image version tag (default: latest)
  PLATFORM        Target platforms (default: linux/amd64,linux/arm64)
  BUILD_ARGS      Additional build arguments (comma-separated)

Examples:
  $0 build                           # Build all images locally
  $0 build-push                      # Build and push to registry
  $0 deploy dev                      # Deploy to dev environment
  $0 optimize                        # Apply automotive optimizations
  $0 monitor 120                     # Monitor for 2 minutes
  
Automotive Features:
  - Multi-platform builds (AMD64/ARM64)
  - Edge deployment optimization
  - Security scanning integration
  - Performance monitoring
  - Resource constraint handling
  - Real-time voice processing support

EOF
            ;;
    esac
}

# Execute main function with all arguments
main "$@"