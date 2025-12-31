# Repository Switching Quick Reference

## Overview

The `repo-config.sh` script helps you manage Conan package repositories for MIA Universal. It supports Cloudsmith, GitHub Packages, Conan Center, and local repositories.

## Quick Commands

### Setup Repositories

```bash
# Interactive setup (recommended)
./tools/repo-config.sh setup

# Cloudsmith (primary)
export CLOUDSMITH_USERNAME="youruser"
export CLOUDSMITH_API_KEY="yourkey"
./tools/repo-config.sh cloudsmith

# GitHub Packages (fallback)
export GITHUB_USERNAME="youruser"
export GITHUB_TOKEN="yourtoken"
./tools/repo-config.sh github

# Conan Center (public)
./tools/repo-config.sh conancenter
```

### Manage Repositories

```bash
# List configured remotes
./tools/repo-config.sh list

# Test repository connectivity
./tools/repo-config.sh test sparetools

# Update priorities
./tools/repo-config.sh priority
```

### Authentication

```bash
# Login interactively
./tools/repo-config.sh login sparetools

# Login with credentials
./tools/repo-config.sh cloudsmith --username user --password key
```

## Repository Priority

Repositories are prioritized automatically:

1. **sparetools** (Cloudsmith) - Highest priority
2. **github-sparetools** (GitHub) - Fallback
3. **conancenter** (Public) - Lowest priority

## Troubleshooting

### Connection Issues
```bash
# Test connectivity
./tools/repo-config.sh test remotename

# Check network
curl -I https://cloudsmith.io
```

### Authentication Issues
```bash
# Clear credentials and re-login
conan remote logout remotename
./tools/repo-config.sh login remotename
```

### Package Issues
```bash
# Clear cache and retry
conan remove "*" -f
conan cache clean
conan install . --build=missing
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLOUDSMITH_USERNAME` | Cloudsmith username |
| `CLOUDSMITH_API_KEY` | Cloudsmith API key |
| `GITHUB_USERNAME` | GitHub username |
| `GITHUB_TOKEN` | GitHub personal access token |

## Advanced Usage

### Custom Repository
```bash
./tools/repo-config.sh add myrepo https://myrepo.example.com
./tools/repo-config.sh login myrepo
```

### Remove Repository
```bash
./tools/repo-config.sh remove remotename
```

See `docs/REPOSITORY_SWITCHING.md` for detailed documentation.