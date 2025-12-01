# GitHub Actions Workflows

This directory contains all CI/CD workflows for the AI-SERVIS Universal project.

## Workflow Overview

### Core CI/CD
- **`ci-cd-orchestration.yml`** - Main comprehensive CI/CD pipeline (security, builds, tests, deployment)
- **`raspberry-pi-cpp.yml`** - Dedicated Raspberry Pi C++ build and cross-compilation

### Platform-Specific Builds
- **`cpp.yml`** - Multi-platform C++ builds (x86_64, ARM64) using Conan
- **`android.yml`** - Android app build, test, and deployment
- **`esp32.yml`** - ESP32 firmware builds for all variants

### Security & Quality
- **`security.yml`** - Security scanning (Trivy, Bandit, Safety)
- **`codeql.yml`** - CodeQL static analysis
- **`trivy.yml`** - Container vulnerability scanning

### Testing & Validation
- **`python.yml`** - Python linting and testing
- **`automotive-testing.yml`** - Automotive-specific tests
- **`orchestrator-integration.yml`** - Build orchestrator integration tests
- **`performance-optimization.yml`** - Performance benchmarking

### Deployment
- **`docker-multiplatform.yml`** - Multi-architecture Docker image builds
- **`edge-deployment.yml`** - Edge device deployment
- **`build-and-deploy.yml`** - Build and deployment pipeline
- **`deploy-pages.yml`** - GitHub Pages deployment

### Documentation & Monitoring
- **`docs.yml`** - Documentation build and deployment
- **`monitoring.yml`** - Monitoring and observability checks
- **`build-web.yml`** - Web interface builds

## Quick Reference

### Running Workflows Manually

```bash
# Run Raspberry Pi build
gh workflow run raspberry-pi-cpp.yml

# Run full CI/CD pipeline
gh workflow run ci-cd-orchestration.yml

# Run security scan
gh workflow run security.yml
```

### Workflow Triggers

Most workflows trigger on:
- **Push** to `main` or `develop` branches
- **Pull requests** to `main` or `develop`
- **Manual dispatch** via GitHub UI or CLI
- **Scheduled** runs (security scans, performance tests)

### Raspberry Pi Build

The `raspberry-pi-cpp.yml` workflow:
- Builds C++ code for Raspberry Pi (ARM64)
- Runs test suite
- Cross-compiles for ARM architecture
- Uploads binaries as artifacts

Triggered by:
- Changes to `platforms/cpp/**`
- Changes to build scripts
- Manual dispatch
- Commit messages containing `[rpi]` or `[raspberry]`

### Viewing Workflow Status

```bash
# List recent workflow runs
gh run list

# View specific workflow run
gh run view <run-id>

# Watch workflow in real-time
gh run watch <run-id>
```

## Workflow Dependencies

```
ci-cd-orchestration.yml (Main)
├── security-scan
├── code-quality
├── cpp-builds
├── raspberry-pi-build (NEW)
├── android-build
├── esp32-build
├── docker-builds
└── integration-tests
```

## Artifacts

Workflows produce the following artifacts:
- `raspberry-pi-binaries` - Raspberry Pi executables
- `cpp-*-binaries` - Multi-platform C++ binaries
- `android-apk` - Android application packages
- `esp32-*-firmware` - ESP32 firmware images
- `docker-images` - Container images

## Troubleshooting

### Workflow Failures

1. Check workflow logs: `gh run view <run-id> --log`
2. Review artifact uploads
3. Check dependency versions
4. Verify secrets are configured

### Raspberry Pi Build Issues

- Ensure all dependencies are listed in workflow
- Check CMake configuration
- Verify cross-compilation toolchain
- Review test output (tests may fail on non-Pi runners)

## Best Practices

1. **Use path filters** to avoid unnecessary runs
2. **Cache dependencies** to speed up builds
3. **Run tests in parallel** where possible
4. **Upload artifacts** for debugging
5. **Use matrix builds** for multiple platforms

## Adding New Workflows

When adding a new workflow:
1. Follow naming convention: `kebab-case.yml`
2. Add path filters for efficiency
3. Include proper error handling
4. Document in this README
5. Add to workflow dependencies if needed
