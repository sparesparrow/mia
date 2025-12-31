# MIA Universal Repository Switching Guide

This guide explains how to switch between different package repositories for MIA Universal, including Cloudsmith, GitHub Packages, and local repositories.

## Repository Overview

### Supported Repositories

1. **Cloudsmith** (Primary)
   - URL: `https://cloudsmith.io/~sparetools/repos/sparetools/packages/`
   - Best for: Production, fast downloads, reliability
   - Authentication: Required (username + API key)

2. **GitHub Packages** (Fallback)
   - URL: `https://maven.pkg.github.com/sparetools`
   - Best for: Development, integration with GitHub
   - Authentication: Required (username + personal access token)

3. **Conan Center** (Public)
   - URL: `https://center.conan.io`
   - Best for: Standard C++ libraries
   - Authentication: None required

4. **Local Artifactory** (Development)
   - URL: `http://localhost:8081/artifactory/api/conan/conan-local`
   - Best for: Local development, testing
   - Authentication: Optional

## Quick Repository Switching

### Using the Repository Helper Script

The easiest way to manage repositories is using the provided helper script:

```bash
# List current repositories
./tools/repo-config.sh list

# Setup Cloudsmith
./tools/repo-config.sh cloudsmith --username youruser --password yourkey

# Setup GitHub Packages
./tools/repo-config.sh github --username youruser --password yourtoken

# Setup Conan Center
./tools/repo-config.sh conancenter

# Test repository connectivity
./tools/repo-config.sh test sparetools
```

### Interactive Setup

For guided setup:

```bash
./tools/repo-config.sh setup
```

This will prompt you to choose repositories and enter credentials.

## Manual Repository Management

### Adding Repositories

```bash
# Cloudsmith
conan remote add sparetools https://cloudsmith.io/~sparetools/repos/sparetools/packages/

# GitHub Packages
conan remote add github-sparetools https://maven.pkg.github.com/sparetools

# Conan Center
conan remote add conancenter https://center.conan.io

# Local Artifactory
conan remote add artifactory-local http://localhost:8081/artifactory/api/conan/conan-local
```

### Authentication Setup

#### Cloudsmith Authentication
```bash
# Method 1: Environment variables
export CLOUDSMITH_USERNAME="your_username"
export CLOUDSMITH_API_KEY="your_api_key"
echo $CLOUDSMITH_API_KEY | conan remote login sparetools $CLOUDSMITH_USERNAME

# Method 2: Direct login
conan remote login sparetools your_username
# Enter API key when prompted
```

#### GitHub Packages Authentication
```bash
# Method 1: Environment variables
export GITHUB_USERNAME="your_username"
export GITHUB_TOKEN="your_token"
echo $GITHUB_TOKEN | conan remote login github-sparetools $GITHUB_USERNAME

# Method 2: Direct login
conan remote login github-sparetools your_username
# Enter token when prompted
```

### Repository Priority Management

Repositories are prioritized to control package resolution order:

```bash
# View current priorities
conan remote list

# Update priorities (lower number = higher priority)
conan remote update-index sparetools 0      # Highest priority
conan remote update-index github-sparetools 1  # Fallback
conan remote update-index conancenter 2     # Lowest priority
```

## Switching Between Repositories

### Scenario 1: Primary Repository Down

If Cloudsmith is unavailable:

```bash
# Disable Cloudsmith temporarily
conan remote disable sparetools

# Enable GitHub Packages as primary
conan remote enable github-sparetools
conan remote update-index github-sparetools 0

# Install packages
conan install . --build=missing
```

### Scenario 2: Local Development

For local development with Artifactory:

```bash
# Add local repository
./tools/repo-config.sh artifactory

# Set as highest priority for local packages
conan remote update-index artifactory-local 0

# Upload local packages
conan upload "*" -r artifactory-local --confirm
```

### Scenario 3: Offline Development

For air-gapped environments:

```bash
# Export packages from online environment
conan download "*/latest@" -r sparetools

# Transfer to offline environment
# Copy conan cache directory

# Configure offline environment
conan remote add local "file://path/to/cache"
conan remote disable sparetools
conan remote disable github-sparetools
```

## Environment-Specific Configurations

### Development Environment

```bash
# Use GitHub Packages for faster development iteration
./tools/repo-config.sh github

# Enable development snapshots
conan remote add github-snapshots https://maven.pkg.github.com/sparetools
conan remote update-index github-snapshots 0
```

### CI/CD Environment

```bash
# Use Cloudsmith for reliable CI/CD builds
export CLOUDSMITH_USERNAME=$CI_CLOUDSMITH_USER
export CLOUDSMITH_API_KEY=$CI_CLOUDSMITH_KEY
./tools/repo-config.sh cloudsmith

# Enable caching for faster builds
conan remote add cache https://cache.example.com
conan remote update-index cache 0
```

### Production Environment

```bash
# Use Cloudsmith with strict versioning
./tools/repo-config.sh cloudsmith

# Disable development repositories
conan remote disable github-sparetools

# Enable security scanning
conan remote add security https://security.example.com
```

## Repository Health Monitoring

### Check Repository Status

```bash
# Test all repositories
for remote in $(conan remote list | awk '{print $1}' | grep -v "^Remote"); do
    echo "Testing $remote..."
    if conan search "*" -r $remote --raw >/dev/null 2>&1; then
        echo "✅ $remote is healthy"
    else
        echo "❌ $remote is unreachable"
    fi
done
```

### Monitor Package Availability

```bash
# Check if MIA packages are available
conan search "sparetools-*" -r sparetools

# Compare package versions across repositories
for remote in sparetools github-sparetools; do
    echo "Packages in $remote:"
    conan search "*" -r $remote | head -10
done
```

## Troubleshooting Repository Issues

### Authentication Problems

```bash
# Clear stored credentials
conan remote logout sparetools

# Re-login with correct credentials
./tools/repo-config.sh login sparetools

# Check credential storage
conan remote list --raw
```

### Connectivity Issues

```bash
# Test basic connectivity
curl -I https://cloudsmith.io
curl -I https://maven.pkg.github.com

# Check DNS resolution
nslookup cloudsmith.io

# Test with verbose output
conan remote login sparetools youruser --verbose
```

### Package Resolution Problems

```bash
# Clear package cache
conan remove "*" -f
conan cache clean

# Force re-download
conan install . --build=missing --update

# Check package conflicts
conan info . --graph
```

### SSL/TLS Issues

```bash
# Disable SSL verification (temporary workaround)
conan remote update sparetools --no-verify-ssl

# Update CA certificates
# Ubuntu/Debian: sudo apt-get install ca-certificates
# CentOS/RHEL: sudo yum install ca-certificates
```

## Advanced Repository Management

### Mirror Setup

Create repository mirrors for improved reliability:

```bash
# Setup mirror repository
conan remote add mirror-sparetools https://mirror.example.com/conan/
conan remote update mirror-sparetools --mirror=sparetools

# Use mirror as primary
conan remote update-index mirror-sparetools 0
```

### Custom Repository Configuration

Create custom repository configurations:

```bash
# Create custom remote with specific settings
conan remote add custom-repo https://custom.example.com/conan/ \
    --verify-ssl=true \
    --timeout=60 \
    --retries=3
```

### Repository Backup and Restore

```bash
# Backup repository configuration
conan remote list > repositories_backup.txt

# Restore from backup
while read -r line; do
    name=$(echo $line | awk '{print $1}')
    url=$(echo $line | awk '{print $2}')
    conan remote add "$name" "$url" --force
done < repositories_backup.txt
```

## Best Practices

### Repository Priority Guidelines

1. **Production**: Cloudsmith > Conan Center
2. **Development**: GitHub Packages > Cloudsmith > Conan Center
3. **CI/CD**: Cache > Cloudsmith > Conan Center
4. **Offline**: Local > Cache > Cloudsmith

### Security Considerations

- Store credentials securely (environment variables, secret managers)
- Rotate API keys regularly
- Use least-privilege access
- Monitor repository access logs
- Enable 2FA where available

### Performance Optimization

- Use closest geographic mirrors
- Enable package caching
- Pre-download frequently used packages
- Monitor download speeds and switch repositories if needed
- Use parallel downloads when available

## Support and Resources

### Getting Help

- **Repository status**: Check service status pages
- **Authentication issues**: Verify credentials and permissions
- **Package conflicts**: Review dependency resolution
- **Performance problems**: Test network connectivity

### Useful Commands

```bash
# View detailed remote information
conan remote list --raw

# Check package information
conan info package/version@

# View dependency graph
conan info . --graph --graph-binaries

# Clean old packages
conan cache clean --temp
```

This guide covers the most common repository switching scenarios. For complex enterprise setups, consult the system administrators or refer to the Conan documentation.