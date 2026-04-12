#!/bin/bash
# =============================================================================
# AI-SERVIS Repository Configuration Helper
# =============================================================================
# Easy switching between Cloudsmith and GitHub Packages
#
# Usage:
#   source tools/repo-config.sh cloudsmith    # Use Cloudsmith (default)
#   source tools/repo-config.sh github       # Use GitHub Packages
#   source tools/repo-config.sh github --token YOUR_TOKEN  # With auth
#
# =============================================================================

is_sourced() {
    [[ "${BASH_SOURCE[0]}" != "$0" ]]
}

usage() {
    cat <<'EOF'
Usage:
  source tools/repo-config.sh cloudsmith
  source tools/repo-config.sh github
  source tools/repo-config.sh github --token YOUR_TOKEN
EOF
}

fail_config() {
    echo "$1" >&2
    return 1
}

if ! is_sourced; then
    echo "This script must be sourced so it can update the current shell environment." >&2
    usage >&2
    exit 1
fi

REPO_TYPE="${1:-cloudsmith}"

case "$REPO_TYPE" in
    -h|--help)
        usage
        return 0
        ;;
esac

if [ "$REPO_TYPE" = "github" ]; then
    if [ "$#" -gt 1 ] && { [ "${2:-}" != "--token" ] || [ -z "${3:-}" ] || [ "$#" -ne 3 ]; }; then
        usage >&2
        return 1
    fi

    export ARTIFACT_REPO=github
    export GITHUB_OWNER="${GITHUB_OWNER:-sparesparrow}"
    export GITHUB_REPO="${GITHUB_REPO:-cpy}"
    export GITHUB_TAG="${GITHUB_TAG:-v3.12.7}"
    
    # Handle token if provided
    if [ "$2" = "--token" ] && [ -n "$3" ]; then
        export GITHUB_TOKEN="$3"
        echo "✓ Configured for GitHub Packages with authentication"
    elif [ -n "$GITHUB_TOKEN" ]; then
        echo "✓ Configured for GitHub Packages (using existing GITHUB_TOKEN)"
    else
        echo "✓ Configured for GitHub Packages (public releases only)"
        echo "  Set GITHUB_TOKEN for private repos or authenticated access"
    fi
    
    echo "  Owner: $GITHUB_OWNER"
    echo "  Repo: $GITHUB_REPO"
    echo "  Tag: $GITHUB_TAG"
    
elif [ "$REPO_TYPE" = "cloudsmith" ]; then
    if [ "$#" -gt 1 ]; then
        usage >&2
        return 1
    fi

    export ARTIFACT_REPO=cloudsmith
    unset GITHUB_TOKEN
    unset GITHUB_OWNER
    unset GITHUB_REPO
    unset GITHUB_TAG
    
    echo "✓ Configured for Cloudsmith (default)"
    echo "  CPY Base: ${CLOUDSMITH_CPY_BASE:-https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions}"
    
else
    fail_config "Error: Unknown repository type '$REPO_TYPE'"
fi
