# Repository Switching Guide

The AI-SERVIS bootstrap system supports easy switching between **Cloudsmith** and **GitHub Packages** for artifact downloads.

## Quick Start

### Using Cloudsmith (Default)

```bash
# No configuration needed - Cloudsmith is the default
./tools/bootstrap.sh
```

### Using GitHub Packages

```bash
# Option 1: Use the helper script
source tools/repo-config.sh github
./tools/bootstrap.sh

# Option 2: Set environment variables manually
export ARTIFACT_REPO=github
export GITHUB_OWNER=sparesparrow
export GITHUB_REPO=cpy
export GITHUB_TAG=v3.12.7
./tools/bootstrap.sh
```

### Using GitHub Packages with Authentication

For private repositories or authenticated access:

```bash
# Using helper script
source tools/repo-config.sh github --token YOUR_GITHUB_TOKEN
./tools/bootstrap.sh

# Or set environment variable
export ARTIFACT_REPO=github
export GITHUB_TOKEN=your_token_here
./tools/bootstrap.sh
```

## Environment Variables

### Cloudsmith Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTIFACT_REPO` | `cloudsmith` | Repository type: `cloudsmith` or `github` |
| `CLOUDSMITH_CPY_BASE` | `https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions` | Base URL for CPython tool downloads |
| `CLOUDSMITH_CONAN_REMOTE` | `https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/` | Conan remote URL |

### GitHub Packages Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTIFACT_REPO` | `cloudsmith` | Set to `github` to use GitHub Packages |
| `GITHUB_OWNER` | `sparesparrow` | GitHub organization or username |
| `GITHUB_REPO` | `cpy` | Repository name |
| `GITHUB_TAG` | `v3.12.7` | Release tag (e.g., `v3.12.7`, `latest`) |
| `GITHUB_TOKEN` | (none) | Personal access token for authenticated access |
| `GITHUB_USER` | `sparesparrow` | GitHub username for Conan authentication |
| `GITHUB_CONAN_REMOTE` | `https://maven.pkg.github.com/sparesparrow/conan` | Conan remote URL for GitHub Packages |

## URL Patterns

### Cloudsmith

- **CPython Tool**: `https://dl.cloudsmith.io/sparesparrow/cpy/raw/versions/{VERSION}/cpython-tool-{VERSION}-{PLATFORM}.tar.gz`
- **Conan Remote**: `https://dl.cloudsmith.io/public/sparesparrow-conan/openssl-conan/conan/`

### GitHub Packages

- **CPython Tool** (Releases): `https://github.com/{OWNER}/{REPO}/releases/download/{TAG}/cpython-tool-{VERSION}-{PLATFORM}.tar.gz`
- **Conan Remote**: `https://maven.pkg.github.com/{OWNER}/conan`

## Examples

### Switch to GitHub Packages for a session

```bash
# Set configuration
source tools/repo-config.sh github

# Run bootstrap
./tools/bootstrap.sh

# Or use complete-bootstrap.py directly
python3 complete-bootstrap.py
```

### Use GitHub Packages with custom settings

```bash
export ARTIFACT_REPO=github
export GITHUB_OWNER=myorg
export GITHUB_REPO=my-cpy-repo
export GITHUB_TAG=v3.12.7
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

python3 complete-bootstrap.py
```

### Switch back to Cloudsmith

```bash
source tools/repo-config.sh cloudsmith
# or
export ARTIFACT_REPO=cloudsmith
unset GITHUB_TOKEN GITHUB_OWNER GITHUB_REPO GITHUB_TAG
```

## Repository Helper Script

The `tools/repo-config.sh` script provides a convenient way to switch repositories:

```bash
# Use Cloudsmith (default)
source tools/repo-config.sh cloudsmith

# Use GitHub Packages (public)
source tools/repo-config.sh github

# Use GitHub Packages with authentication
source tools/repo-config.sh github --token ghp_xxxxxxxxxxxx
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Bootstrap with GitHub Packages
  env:
    ARTIFACT_REPO: github
    GITHUB_OWNER: sparesparrow
    GITHUB_REPO: cpy
    GITHUB_TAG: v3.12.7
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: python3 complete-bootstrap.py
```

### GitLab CI

```yaml
bootstrap:
  variables:
    ARTIFACT_REPO: "github"
    GITHUB_OWNER: "sparesparrow"
    GITHUB_REPO: "cpy"
    GITHUB_TAG: "v3.12.7"
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
  script:
    - python3 complete-bootstrap.py
```

## Troubleshooting

### GitHub Packages 404 Error

If you get a 404 error when using GitHub Packages:

1. Verify the release tag exists: `https://github.com/{OWNER}/{REPO}/releases/tag/{TAG}`
2. Check that the filename matches: `cpython-tool-{VERSION}-{PLATFORM}.tar.gz`
3. Ensure the repository is public or you have access with your token

### GitHub Packages Authentication

For private repositories or authenticated access:

1. Create a GitHub Personal Access Token with `read:packages` permission
2. Set `GITHUB_TOKEN` environment variable
3. For Conan, also set `GITHUB_USER` (usually your GitHub username)

### Switching Between Repositories

The bootstrap script reads environment variables at runtime, so you can switch repositories by:

1. Setting `ARTIFACT_REPO` environment variable
2. Running the bootstrap script again (it will use the new configuration)
3. No need to clean `.buildenv/` unless you want a fresh download

## Notes

- The bootstrap script uses only Python stdlib - no external dependencies
- Repository switching is done via environment variables for maximum flexibility
- Both Cloudsmith and GitHub Packages use the same CPython tool tarball format
- Conan remotes are automatically configured based on the selected repository
- GitHub Packages authentication is optional for public repositories
