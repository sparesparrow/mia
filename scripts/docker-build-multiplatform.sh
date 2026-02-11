#!/usr/bin/env bash
set -euo pipefail

# Multi-platform Docker build script for AI-Servis
# Builds all components for AMD64 and ARM64 architectures

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY="${REGISTRY:-ghcr.io/ai-servis}"
TAG="${TAG:-latest}"
PUSH="${PUSH:-false}"

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

# Components to build
COMPONENTS=(
    "core-orchestrator"
    "ai-audio-assistant"
    "ai-platform-controllers/linux"
    "service-discovery"
    "hardware-bridge"
)

# Platforms to build for
PLATFORMS="linux/amd64,linux/arm64"

# Check if Docker Buildx is available
check_buildx() {
    log "Checking Docker Buildx availability..."
    if ! docker buildx version >/dev/null 2>&1; then
        error "Docker Buildx is not available. Please install Docker Desktop or enable Buildx."
        exit 1
    fi
    
    # Create builder if it doesn't exist
    if ! docker buildx ls | grep -q multiarch; then
        log "Creating multiarch builder..."
        docker buildx create --name multiarch --driver docker-container --use
        docker buildx inspect --bootstrap
    else
        docker buildx use multiarch
    fi
}

# Build a single component
build_component() {
    local component="$1"
    local context_dir="$PROJECT_ROOT/modules/$component"
    
    if [ ! -d "$context_dir" ]; then
        error "Component directory not found: $context_dir"
        return 1
    fi
    
    if [ ! -f "$context_dir/Dockerfile" ]; then
        error "Dockerfile not found: $context_dir/Dockerfile"
        return 1
    fi
    
    log "Building $component for platforms: $PLATFORMS"
    
    local image_name="$REGISTRY/$(echo "$component" | tr '/' '-'):$TAG"
    local build_args=(
        "buildx" "build"
        "--platform" "$PLATFORMS"
        "--tag" "$image_name"
        "--file" "$context_dir/Dockerfile"
        "$context_dir"
    )
    
    if [ "$PUSH" = "true" ]; then
        build_args+=("--push")
        log "Will push to registry: $image_name"
    else
        build_args+=("--load")
        warning "Building locally only (use PUSH=true to push to registry)"
    fi
    
    # Add build metadata
    build_args+=(
        "--label" "org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        "--label" "org.opencontainers.image.source=https://github.com/ai-servis/ai-servis"
        "--label" "org.opencontainers.image.version=$TAG"
        "--label" "org.opencontainers.image.revision=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
        "--label" "org.opencontainers.image.title=AI-Servis $component"
    )
    
    if docker "${build_args[@]}"; then
        success "Built $component successfully"
        return 0
    else
        error "Failed to build $component"
        return 1
    fi
}

# Build all components
build_all() {
    local failed_components=()
    
    log "Starting multi-platform build for ${#COMPONENTS[@]} components..."
    log "Registry: $REGISTRY"
    log "Tag: $TAG"
    log "Platforms: $PLATFORMS"
    log "Push: $PUSH"
    
    for component in "${COMPONENTS[@]}"; do
        log "Building component: $component"
        if ! build_component "$component"; then
            failed_components+=("$component")
        fi
        echo # Add spacing between builds
    done
    
    # Report results
    if [ ${#failed_components[@]} -eq 0 ]; then
        success "All components built successfully!"
    else
        error "Failed to build ${#failed_components[@]} components:"
        for component in "${failed_components[@]}"; do
            echo "  - $component"
        done
        exit 1
    fi
}

# Health check for built images (local only)
health_check() {
    if [ "$PUSH" = "true" ]; then
        log "Skipping health check for pushed images"
        return
    fi
    
    log "Running basic health checks on built images..."
    
    for component in "${COMPONENTS[@]}"; do
        local image_name="$REGISTRY/$(echo "$component" | tr '/' '-'):$TAG"
        
        log "Checking image: $image_name"
        
        # Check if image exists
        if ! docker image inspect "$image_name" >/dev/null 2>&1; then
            error "Image not found: $image_name"
            continue
        fi
        
        # Check image size
        local size=$(docker image inspect "$image_name" --format='{{.Size}}' | numfmt --to=iec)
        log "Image size: $size"
        
        # Try to run the image briefly to check it starts
        if timeout 10s docker run --rm "$image_name" --help >/dev/null 2>&1 || \
           timeout 10s docker run --rm "$image_name" python --version >/dev/null 2>&1; then
            success "Image $image_name appears healthy"
        else
            warning "Could not verify health of $image_name (this may be normal)"
        fi
    done
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --push)
                PUSH=true
                shift
                ;;
            --tag)
                TAG="$2"
                shift 2
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            --platform)
                PLATFORMS="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --push              Push images to registry"
                echo "  --tag TAG           Image tag (default: latest)"
                echo "  --registry REG      Registry prefix (default: ghcr.io/ai-servis)"
                echo "  --platform PLAT     Target platforms (default: linux/amd64,linux/arm64)"
                echo "  --help, -h          Show this help"
                echo ""
                echo "Environment variables:"
                echo "  REGISTRY            Registry prefix"
                echo "  TAG                 Image tag"
                echo "  PUSH                Push to registry (true/false)"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    check_buildx
    build_all
    health_check
    
    success "Multi-platform build completed!"
}

# Run main function
main "$@"