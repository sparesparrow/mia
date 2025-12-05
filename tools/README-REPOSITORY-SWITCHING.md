# Quick Repository Switching Guide

Switch between **Cloudsmith** and **GitHub Packages** easily:

## Quick Commands

```bash
# Use Cloudsmith (default)
source tools/repo-config.sh cloudsmith
./tools/bootstrap.sh

# Use GitHub Packages
source tools/repo-config.sh github
./tools/bootstrap.sh

# Use GitHub Packages with authentication
source tools/repo-config.sh github --token YOUR_TOKEN
./tools/bootstrap.sh
```

## Environment Variables

```bash
# Cloudsmith (default)
export ARTIFACT_REPO=cloudsmith

# GitHub Packages
export ARTIFACT_REPO=github
export GITHUB_OWNER=sparesparrow
export GITHUB_REPO=cpy
export GITHUB_TAG=v3.12.7
export GITHUB_TOKEN=your_token  # Optional
```

For detailed documentation, see [docs/REPOSITORY_SWITCHING.md](../docs/REPOSITORY_SWITCHING.md).
