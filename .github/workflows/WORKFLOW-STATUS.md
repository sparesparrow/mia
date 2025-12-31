# Workflow Status

## Current Structure

### ✅ Active Workflows (6)

1. **`main.yml`** - Main CI/CD Pipeline
   - Status: ✅ Active
   - Triggers: Push, PR, Schedule, Manual
   - Jobs: 9 (security, python-tests, cpp-builds, android-build, esp32-build, docker-builds, integration-tests, deploy, docs)
   - Purpose: Comprehensive CI/CD pipeline

2. **`docker-multiplatform.yml`** - Advanced Docker Builds
   - Status: ✅ Active
   - Triggers: Push, PR, Manual
   - Purpose: Multi-platform Docker builds with ARM/v7 support

3. **`esp32.yml`** - ESP32 Firmware Builds
   - Status: ✅ Active
   - Triggers: Path-based (esp32/** changes)
   - Purpose: Automated ESP32 builds on firmware changes

4. **`build-web.yml`** - Web Deployment
   - Status: ✅ Active
   - Triggers: Path-based (web/** changes)
   - Purpose: Web application builds and AWS deployment

5. **`monitoring.yml`** - Observability Pipeline
   - Status: ✅ Active
   - Triggers: Push, PR, Schedule (6h), Manual
   - Purpose: Health checks and monitoring infrastructure

6. **`deploy-docker-compose.yml`** - Docker Compose Deployment
   - Status: ✅ Active
   - Triggers: Manual
   - Purpose: Docker Compose-based deployments

### 🗑️ Removed Redundant Workflows (8)

Removed during consolidation:
- `python.yml` - Functionality merged into main.yml
- `cpp.yml` - Functionality merged into main.yml
- `android.yml` - Functionality merged into main.yml
- `android-build.yml` - Functionality merged into main.yml
- `android-ci.yml` - Functionality merged into main.yml
- `security.yml` - Functionality merged into main.yml
- `trivy.yml` - Functionality merged into main.yml
- `codeql.yml` - Functionality merged into main.yml

## Workflow Performance

### Average Run Times
- Security scan: ~5 minutes
- Python tests: ~3 minutes
- C++ builds: ~8 minutes (both platforms)
- Android build: ~12 minutes
- ESP32 build: ~15 minutes (all variants)
- Docker builds: ~10 minutes
- Integration tests: ~5 minutes
- Total pipeline: ~30-40 minutes (parallel execution)

### Optimization
- Conditional builds reduce unnecessary runs
- Parallel job execution
- Caching for dependencies
- Artifact reuse

## Monitoring

Check workflow status:
```bash
# View recent runs
gh run list --workflow=main.yml

# View specific run
gh run view <run-id>

# Watch in real-time
gh run watch <run-id>
```

## Troubleshooting

### Workflow Not Running
1. Check path filters
2. Verify branch is correct
3. Check commit message for tags

### Build Failures
1. Check logs: `gh run view <run-id> --log`
2. Download artifacts: `gh run download <run-id>`
3. Review error messages in workflow output

### Conditional Builds
- Use commit tags: `[android]`, `[esp32]`, `[rpi]`
- Or modify files in relevant directories
- Or use manual dispatch
