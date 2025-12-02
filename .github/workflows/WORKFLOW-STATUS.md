# Workflow Status

## Current Structure

### ✅ Active Workflows (2)

1. **`main.yml`** - Main CI/CD Pipeline
   - Status: ✅ Active
   - Triggers: Push, PR, Schedule, Manual
   - Jobs: 9 (security, python-tests, cpp-builds, android-build, esp32-build, docker-builds, integration-tests, deploy, docs)

2. **`docker-multiplatform.yml`** - Advanced Docker Builds
   - Status: ⚠️ Optional (can be merged into main.yml)
   - Triggers: Push, PR, Manual
   - Purpose: Edge deployment images with ARM/v7 support

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
