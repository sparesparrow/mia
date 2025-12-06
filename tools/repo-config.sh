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

REPO_TYPE="${1:-cloudsmith}"

if [ "$REPO_TYPE" = "github" ]; then
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
    export ARTIFACT_REPO=cloudsmith
    unset GITHUB_TOKEN
    unset GITHUB_OWNER
    unset GITHUB_REPO
    unset GITHUB_TAG
    
    echo "✓ Configured for Cloudsmith (default)"
    echo "  CPY Base: ${CLOUDSMITH_CPY_BASE:-https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions}"
    
else
    echo "Error: Unknown repository type '$REPO_TYPE'"
    echo "Usage: source tools/repo-config.sh [cloudsmith|github] [--token TOKEN]"
    return 1
fi
