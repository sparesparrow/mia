# Core Orchestrator Build Fix Summary

## Issues Fixed

### 1. Invalid Docker Tag Format ✅
**Problem**: Tag `ghcr.io/sparesparrow/mia/core-orchestrator:-430629a` was invalid (colon followed by dash)

**Root Cause**: The metadata action was creating tags with `type=sha,prefix={{branch}}-` which resulted in invalid format when branch was empty or for PRs.

**Fix**: Changed to `type=sha,prefix=sha-,format=short` to ensure valid tag format.

### 2. Dockerfile Build Context ✅
**Problem**: Dockerfile was trying to copy from `../mcp_framework.py` which doesn't work with Docker build context.

**Root Cause**: Docker build context was `.` (root), but Dockerfile was using relative paths incorrectly.

**Fix**: Updated Dockerfile to use correct paths:
- `COPY modules/mcp_framework.py ./mcp_framework.py`
- `COPY modules/core-orchestrator/requirements.txt ./requirements.txt`
- `COPY modules/core-orchestrator/*.py .`

## Changes Made

### `.github/workflows/main.yml`
- Fixed tag metadata configuration
- Simplified tag generation to avoid invalid formats
- Added proper enable conditions for different event types

### `modules/core-orchestrator/Dockerfile`
- Fixed COPY paths to work with build context from root
- Properly copies mcp_framework.py from parent directory
- Copies all Python files from core-orchestrator directory

## Testing

The build should now:
1. ✅ Generate valid Docker tags
2. ✅ Successfully copy all required files
3. ✅ Build for both linux/amd64 and linux/arm64
4. ✅ Push to registry on main/develop branches

## Next Steps

1. Verify the build works in CI/CD
2. Check that tags are valid
3. Ensure all files are copied correctly
4. Test on both platforms
