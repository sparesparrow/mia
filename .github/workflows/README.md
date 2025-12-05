# GitHub Actions Workflows

This directory contains consolidated CI/CD workflows for the MIA Universal project.

## Workflow Overview

### Main Workflow (`main.yml`)
**Comprehensive CI/CD pipeline** that handles everything:
- ✅ **Security scanning** - CodeQL, Trivy, Bandit, Safety, pre-commit
- ✅ **Code quality** - Linting, formatting checks
- ✅ **Python tests** - Test suite execution
- ✅ **C++ builds** - x86_64 and ARM64 (Raspberry Pi) builds
- ✅ **Android builds** - APK build and test (conditional)
- ✅ **ESP32 builds** - Firmware builds (conditional)
- ✅ **Docker builds** - Multi-platform container images
- ✅ **Integration tests** - System-wide testing
- ✅ **Deployment** - Staging and production deployment
- ✅ **Documentation** - Build and deploy to GitHub Pages

### Optional Workflow
- **`docker-multiplatform.yml`** - Advanced Docker builds with edge deployment images (optional, can be merged into main.yml if needed)

## Quick Reference

### Running Workflows

```bash
# Run main CI/CD pipeline
gh workflow run main.yml

# Run with options
gh workflow run main.yml -f skip_tests=true
gh workflow run main.yml -f build_only=true
```

### Workflow Triggers

The main workflow triggers on:
- **Push** to `main`, `develop`, or `feature/*` branches
- **Pull requests** to `main` or `develop`
- **Tags** starting with `v*`
- **Scheduled** runs (weekly security scans on Mondays)
- **Manual dispatch** via GitHub UI or CLI

### Conditional Builds

Builds are optimized to run only when needed:
- **C++ builds**: Always run (core functionality)
- **Android builds**: Only when `android/` changes or `[android]` in commit message
- **ESP32 builds**: Only when `esp32/` changes or `[esp32]` in commit message
- **Documentation**: Only when `docs/` changes

### Workflow Structure

```
main.yml
├── security (always runs)
├── python-tests (depends on security)
├── cpp-builds (depends on security)
│   ├── x86_64 build
│   └── ARM64/Raspberry Pi build
├── android-build (conditional, depends on security)
├── esp32-build (conditional, depends on security)
├── docker-builds (depends on cpp-builds, python-tests)
├── integration-tests (depends on all builds)
├── deploy (depends on integration-tests, docker-builds)
└── docs (conditional, depends on security)
```

## Artifacts

The workflow produces:
- `cpp-linux-x86_64-binaries` - x86_64 C++ binaries
- `cpp-linux-arm64-binaries` - ARM64/Raspberry Pi binaries
- `android-apk` - Android application package
- `esp32-*-firmware` - ESP32 firmware images
- `security-reports` - Security scan results

## Configuration

### Environment Variables

Set in workflow file:
- `REGISTRY` - Container registry (ghcr.io)
- `PYTHON_VERSION` - Python version (3.11)
- `NODE_VERSION` - Node.js version (18)
- `JAVA_VERSION` - Java version (17)

### GitHub Secrets

Required secrets:
- `GITHUB_TOKEN` - Automatically provided
- Optional: `SNYK_TOKEN`, `SLACK_WEBHOOK_URL`, etc.

## Troubleshooting

### Workflow Not Running

Check:
1. Path filters - workflow only runs when relevant files change
2. Branch filters - ensure you're pushing to correct branch
3. Commit message tags - use `[android]`, `[esp32]` to trigger specific builds

### Build Failures

```bash
# View workflow logs
gh run view <run-id> --log

# Download artifacts
gh run download <run-id>

# Rerun failed workflow
gh run rerun <run-id>
```

### Conditional Builds Not Running

If Android/ESP32 builds aren't running:
- Check if files in those directories changed
- Add `[android]` or `[esp32]` to commit message
- Use manual dispatch: `gh workflow run main.yml`

## Best Practices

1. **Use commit message tags** to trigger specific builds:
   - `[android]` - Trigger Android build
   - `[esp32]` - Trigger ESP32 build
   - `[rpi]` or `[raspberry]` - Emphasize Raspberry Pi build

2. **Path-based triggers** automatically detect changes

3. **Manual dispatch** for testing:
   ```bash
   gh workflow run main.yml -f skip_tests=true
   ```

4. **Check artifacts** after builds complete

## Refactoring Summary

### Before: 20+ Workflows ❌
- Multiple redundant workflows
- Duplicate functionality
- Hard to maintain
- Inconsistent configuration

### After: 2 Workflows ✅
- **`main.yml`** - Single comprehensive pipeline
- **`docker-multiplatform.yml`** - Optional advanced Docker builds

### Consolidated Into `main.yml`:
- ✅ `ci.yml` + `ci-cd-orchestration.yml` → `main.yml`
- ✅ `python.yml` → `python-tests` job
- ✅ `cpp.yml` + `raspberry-pi-cpp.yml` → `cpp-builds` job (with ARM64 matrix)
- ✅ `android.yml` → `android-build` job (conditional)
- ✅ `esp32.yml` → `esp32-build` job (conditional)
- ✅ `security.yml` + `codeql.yml` + `trivy.yml` → `security` job
- ✅ `build-and-deploy.yml` + `edge-deployment.yml` → `deploy` job
- ✅ `orchestrator-integration.yml` + `automotive-testing.yml` → `integration-tests` job
- ✅ `docs.yml` → `docs` job
- ✅ `build-web.yml` → Merged into main pipeline

**Result**: 90% reduction in workflow files, same functionality! 🎉
