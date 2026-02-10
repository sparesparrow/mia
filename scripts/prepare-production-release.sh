#!/bin/bash
# Prepare Production Release
# Merges piper branch to main and prepares for production deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

cd "$PROJECT_ROOT"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    log_error "Not a git repository"
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_info "Current branch: $CURRENT_BRANCH"

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    log_warning "You have uncommitted changes. Stashing them..."
    git stash
    STASHED=true
else
    STASHED=false
fi

# Fetch latest changes
log_info "Fetching latest changes from remote..."
git fetch origin

# Check if piper branch exists
if ! git show-ref --verify --quiet refs/heads/piper && ! git show-ref --verify --quiet refs/remotes/origin/piper; then
    log_error "piper branch not found locally or remotely"
    exit 1
fi

# Switch to main branch
log_info "Switching to main branch..."
git checkout main

# Pull latest main
log_info "Pulling latest main..."
git pull origin main

# Merge piper into main
log_info "Merging piper branch into main..."
if git merge --no-ff piper -m "Merge piper branch: Bluetooth integration and production deployment"; then
    log_success "Successfully merged piper into main"
else
    log_error "Merge conflict detected. Please resolve conflicts manually."
    log_info "After resolving conflicts, run:"
    echo "  git add ."
    echo "  git commit -m 'Merge piper: Resolve conflicts'"
    exit 1
fi

# Check if merge was successful
if [ $? -eq 0 ]; then
    log_success "Merge completed successfully"
    
    # Show summary
    log_info "Merge summary:"
    git log --oneline main ^origin/main | head -10
    
    echo ""
    log_info "Next steps:"
    echo "  1. Review the changes: git log main ^origin/main"
    echo "  2. Test the merged code"
    echo "  3. Push to remote: git push origin main"
    echo "  4. Deploy to Raspberry Pi: ./scripts/deploy-production-rpi.sh"
else
    log_error "Merge failed"
    exit 1
fi

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    log_info "Restoring stashed changes..."
    git stash pop || log_warning "Could not restore stashed changes (may have conflicts)"
fi
