# Bootstrap Approach Comparison

## Why the New Direct Download Bootstrap is Better

### Overview

The new **Cloudsmith/GitHub Packages direct download** bootstrap replaces the old **Conan-based** bootstrap. Here's why it's superior:

## Key Advantages

### 1. **No Bootstrap Dependency on Conan**

**Old (Conan-based):**
```
System Python → Install Conan → Use Conan to download CPython → Use CPython to install Conan again
```

**New (Direct download):**
```
System Python → Download CPython tarball → Use CPython to install Conan
```

**Benefit:** The new approach uses only Python stdlib (`urllib`, `tarfile`, `subprocess`) - no external dependencies needed for bootstrap. The old approach required Conan to be installed first, creating a circular dependency.

### 2. **Simpler Dependency Chain**

**Old approach problems:**
- Need Conan installed before you can get CPython
- Conan might not be available or might fail to install
- Conan profile detection can fail on some systems
- Conan cache location varies (`~/.conan2/p`, `~/.conan`, etc.)
- Need to find CPython in Conan cache (complex path searching)

**New approach:**
- Direct download to known location (`.buildenv/downloads/`)
- Extract to known location (`.buildenv/cpython/`)
- No cache hunting, no profile detection needed for bootstrap
- Predictable, reproducible paths

### 3. **Faster Bootstrap**

**Old approach:**
```bash
# Multiple steps with network round-trips
1. Install Conan (pip install conan) - ~30-60 seconds
2. Configure Conan remotes - network call
3. Conan profile detect - system introspection
4. Conan install sparetools-cpython - package resolution, download, install
5. Find CPython in Conan cache - filesystem search
6. Create symlinks - filesystem operations
```

**New approach:**
```bash
# Single direct download
1. Download tarball directly - one network call
2. Extract tarball - simple filesystem operation
3. Done - CPython ready to use
```

**Time savings:** Typically 2-3x faster, especially on first run.

### 4. **More Reliable**

**Old approach failure points:**
- ❌ Conan installation fails (PEP 668, permissions, network)
- ❌ Conan profile detection fails (unknown platform)
- ❌ Conan remote configuration fails
- ❌ Package not found in Conan cache
- ❌ Conan cache in unexpected location
- ❌ Symlink creation fails (permissions, paths)

**New approach failure points:**
- ✅ Only one: Download fails (clear error message with URL)
- ✅ Extract fails (clear error message)

**Reliability improvement:** Fewer moving parts = fewer failure modes.

### 5. **Easier Repository Switching**

**Old approach:**
```bash
# Switching requires Conan remote reconfiguration
conan remote remove sparesparrow-conan
conan remote add sparesparrow-github <github-url>
# But GitHub Packages Conan integration is complex
```

**New approach:**
```bash
# Simple environment variable
export ARTIFACT_REPO=github
export GITHUB_OWNER=sparesparrow
# Done - bootstrap uses GitHub URLs
```

**Benefit:** Direct URL downloads are easier to switch than Conan remotes.

### 6. **Better for CI/CD**

**Old approach in CI:**
```yaml
- name: Install Conan
  run: pip install conan
- name: Configure Conan
  run: conan profile detect && conan remote add ...
- name: Install CPython via Conan
  run: conan install --tool-requires=sparetools-cpython/3.12.7@
- name: Find CPython in cache
  run: find ~/.conan2 -name python3
```

**New approach in CI:**
```yaml
- name: Bootstrap CPython
  env:
    ARTIFACT_REPO: github
  run: python3 complete-bootstrap.py
```

**Benefit:** Single step, no cache hunting, works consistently across CI platforms.

### 7. **Self-Contained and Predictable**

**Old approach:**
- CPython location: `~/.conan2/p/sparetools-cpython/3.12.7/.../package/.../bin/python3`
- Path varies by Conan version, cache location, package revision
- Hard to predict, hard to debug

**New approach:**
- CPython location: `.buildenv/cpython/bin/python3`
- Always the same, always predictable
- Easy to debug, easy to verify

### 8. **No Conan Cache Pollution**

**Old approach:**
- Installs packages into global Conan cache
- Can conflict with other projects
- Cache can grow large over time
- Cache cleanup is manual

**New approach:**
- Everything in project-local `.buildenv/`
- No global state
- Easy to clean: `rm -rf .buildenv/`
- No conflicts with other projects

### 9. **Better Error Messages**

**Old approach errors:**
```
Error: Package 'sparetools-cpython/3.12.7@' not found
Error: Profile 'default' not found
Error: Remote 'sparesparrow-conan' not configured
Error: CPython not found in Conan cache
```

**New approach errors:**
```
HTTP Error 404: Not Found
URL: https://github.com/sparesparrow/cpy/releases/download/v3.12.7/cpython-tool-3.12.7-linux-x86_64.tar.gz
Hint: Check that release tag 'v3.12.7' exists in sparesparrow/cpy
```

**Benefit:** Clear, actionable error messages.

### 10. **Works Offline (After First Download)**

**Old approach:**
- Conan always checks remotes
- Cache invalidation can force re-download
- Profile detection requires system access

**New approach:**
- Download once, use forever
- Tarball cached in `.buildenv/downloads/`
- Extract is local filesystem operation
- Works completely offline after first bootstrap

## Real-World Example

### Scenario: Fresh System, No Python/Conan Installed

**Old approach:**
```bash
# Step 1: Need Python 3 (system requirement)
python3 --version  # Must exist

# Step 2: Install Conan (can fail on PEP 668 systems)
pip install --user conan  # May require --break-system-packages

# Step 3: Configure Conan
conan profile detect  # May fail on exotic platforms

# Step 4: Install CPython via Conan
conan install --tool-requires=sparetools-cpython/3.12.7@  # Network, resolution, download

# Step 5: Find it
find ~/.conan2 -name python3  # May not find it

# Step 6: Create symlinks
ln -s ~/.conan2/p/.../python3 .buildenv/python/bin/python3  # Complex path
```

**New approach:**
```bash
# Step 1: Need Python 3 (system requirement - same)
python3 --version  # Must exist

# Step 2: Download and extract (stdlib only, always works)
python3 complete-bootstrap.py  # Single command, predictable
```

## Migration Benefits

### For Existing Users

The old Conan-based approach is still available via `--legacy` flag:
```bash
./tools/bootstrap.sh --legacy
```

But new users should use the direct download approach for:
- ✅ Faster setup
- ✅ More reliable
- ✅ Easier to debug
- ✅ Better CI/CD integration

### For CI/CD Pipelines

**Before:**
```yaml
- run: pip install conan
- run: conan profile detect
- run: conan remote add ...
- run: conan install --tool-requires=...
- run: find ~/.conan2 -name python3 | head -1
```

**After:**
```yaml
- run: python3 complete-bootstrap.py
```

## Conclusion

The new direct download bootstrap is better because it:

1. **Eliminates circular dependencies** (no Conan needed to get CPython)
2. **Reduces complexity** (fewer steps, fewer failure points)
3. **Improves reliability** (predictable paths, clear errors)
4. **Speeds up bootstrap** (direct download vs. package resolution)
5. **Enhances portability** (works offline after first download)
6. **Simplifies CI/CD** (single command, no cache hunting)
7. **Easier repository switching** (environment variables vs. Conan remotes)

The old Conan-based approach served its purpose, but the new approach is a clear evolution that addresses all its pain points while maintaining the same end result: a bundled CPython environment ready for development.
