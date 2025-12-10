# CURSOR-PLAN.md Review

**Date:** 2025-12-05  
**Reviewer:** AI Assistant  
**Status:** ✅ Overall Good, ⚠️ Needs Updates  
**⚠️ IMPORTANT:** This review was initially done on `refactor/android-build-cleanup` branch, but `CURSOR-PLAN.md` is written for the **"mia" renamed version** (found on `android-todo-implementation` branch). The review has been updated accordingly.

---

## Executive Summary

The `CURSOR-PLAN.md` document provides a comprehensive set of proposed Cursor commands for the **MIA** project (recently renamed from "ai-servis"). The plan is well-structured and covers Android development, RPi deployment, Arduino integration, debugging, and workflow automation. However, several updates are needed to align with the current project state and fix inaccuracies.

**Branch Context:**
- **Current branch reviewed:** `refactor/android-build-cleanup` (still uses "ai-servis")
- **Target branch for CURSOR-PLAN.md:** `android-todo-implementation` (has "mia" rename)
- **Rename commit:** `bea45ba` (only on `android-todo-implementation` branch)

**Overall Assessment:** 7.5/10
- ✅ Excellent structure and coverage
- ✅ Practical, time-saving commands
- ⚠️ Some paths and file references need correction
- ⚠️ Missing files need to be created
- ⚠️ Docker service names don't match current setup

---

## Detailed Findings

### ✅ **Correct Elements**

1. **Package Names**: Correctly uses `cz.mia.app` (verified on `android-todo-implementation` branch - the rename target)
2. **MainActivity Path**: Correctly references `cz.aiservis.app/.MainActivity`
3. **Android Build Script**: References `android/tools/build-in-docker.sh` which exists and has correct options
4. **Docker Image**: Uses `ai-servis-android-build:latest` (matches `build-in-docker.sh`)
5. **RPi Connection**: Uses `mia@mia.local` (reasonable default)
6. **Bootstrap Script**: References `complete-bootstrap.py` which exists in root
7. **Arduino Structure**: References `arduino/sketches/` structure (though actual structure is `arduino/led_strip_controller/`)

### ⚠️ **Issues & Corrections Needed**

#### 1. **Docker Compose Service Names** (HIGH PRIORITY)

**Issue:** Commands reference services like `mia-fastapi`, `zeromq-router`, `mcp-prompts`, but actual `docker-compose.yml` (even on renamed branch) uses:
- `ai-servis-core` (not `mia-fastapi`) - **Note:** Service names in docker-compose.yml were NOT renamed in commit bea45ba
- `service-discovery` (not `zeromq-router`)
- `ai-audio-assistant` (not `mcp-prompts`)

**Location:** Commands `/run-on-rpi`, `/build-deploy-integration-test-rpi`, `/summarize-logs-and-plan-suggested-actions`

**Fix Required:**
```bash
# Current (incorrect):
ssh mia@mia.local 'docker-compose logs -f mia-fastapi'

# Should be:
ssh mia@mia.local 'docker-compose logs -f ai-servis-core'
```

**Note:** The rename commit (`bea45ba`) renamed package names, class names, and repository references, but **docker-compose.yml service names remain `ai-servis-*`**. The plan document assumes they were renamed to `mia-*`, which is incorrect.

#### 2. **Arduino Sketch Path** (MEDIUM PRIORITY)

**Issue:** Commands reference `arduino/sketches/gpio-controller/` but actual structure is:
- `arduino/led_strip_controller/led_strip_controller.ino`

**Location:** Command `/deploy-arduino`

**Fix Required:**
```bash
# Current (incorrect):
arduino-cli compile --fqbn arduino:avr:uno arduino/sketches/gpio-controller/

# Should be:
arduino-cli compile --fqbn arduino:avr:uno arduino/led_strip_controller/
```

#### 3. **Missing Integration Test File** (HIGH PRIORITY)

**Issue:** Command `/build-deploy-integration-test-rpi` references:
- `android/test/integration/test_e2e_android_rpi.py`

**Status:** File does not exist

**Action Required:** Create this test file or update command to reference existing test structure.

#### 4. **Missing Cursor Commands Directory** (MEDIUM PRIORITY)

**Issue:** All commands reference `.cursor/commands/*.md` files, but `.cursor/commands/` directory doesn't exist.

**Current Structure:**
```
.cursor/
  └── rules/
      ├── android-apk-build-testing.mdc
      ├── android-docker-build.mdc
      └── ...
```

**Action Required:** Create `.cursor/commands/` directory and implement the command files, OR update documentation to reflect actual command implementation method.

#### 5. **Docker Build Command Inconsistency** (LOW PRIORITY)

**Issue:** Command `/deploy-apk` shows:
```bash
cd android && docker build -t mia-android .
```

But `build-in-docker.sh` uses:
- `IMAGE_NAME=ai-servis-android-build:latest`

**Fix Required:** Align image names or document the difference.

#### 6. **WebSocket Dependency** (LOW PRIORITY)

**Issue:** Command examples reference `TelemetryWebSocket`, but recent PR #36 decomposition removed this class.

**Status:** Need to verify if WebSocket functionality still exists or update references.

**Location:** Multiple commands (`/deploy-apk`, `/summarize-logs-and-plan-suggested-actions`, `/tail-all-logs`)

#### 7. **RPi Health Endpoints** (MEDIUM PRIORITY)

**Issue:** Commands reference endpoints like:
- `GET /status`
- `GET /devices`

**Status:** Need to verify these endpoints exist in the FastAPI application.

**Location:** Commands `/run-on-rpi`, `/build-deploy-integration-test-rpi`

#### 8. **Gradle Task Names** (LOW PRIORITY)

**Issue:** Some commands use `./gradlew assembleDebug` but should use the Docker build script for consistency.

**Fix:** Update all commands to use `android/tools/build-in-docker.sh` instead of direct Gradle calls.

---

## Recommendations

### **Priority 1: Critical Fixes**

1. **Update Docker Service Names**
   - Search and replace all service name references
   - Verify actual service names in `docker-compose.yml`
   - Update health check endpoints

2. **Create Missing Integration Test**
   - Implement `android/test/integration/test_e2e_android_rpi.py`
   - Or document alternative test approach

3. **Verify WebSocket References**
   - Check if `TelemetryWebSocket` still exists
   - Update or remove references accordingly

### **Priority 2: Structural Improvements**

4. **Create Commands Directory Structure**
   ```bash
   .cursor/
     ├── commands/
     │   ├── deploy-apk.md
     │   ├── debug-with-adb-user-input.md
     │   ├── run-on-rpi.md
     │   └── ...
     └── rules/
         └── ...
   ```

5. **Standardize Build Commands**
   - Use `android/tools/build-in-docker.sh` consistently
   - Document Docker image naming convention

6. **Fix Arduino Paths**
   - Update to `arduino/led_strip_controller/`
   - Or create `arduino/sketches/gpio-controller/` if that's the intended structure

### **Priority 3: Enhancements**

7. **Add Error Handling**
   - Commands should handle missing devices gracefully
   - Add validation steps before deployment

8. **Add Configuration File**
   - Create `.cursor/config.yml` for:
     - RPi hostname (default: `mia.local`)
     - Android device detection
     - Docker image names
     - Service names

9. **Document Dependencies**
   - List required tools (adb, arduino-cli, rsync, etc.)
   - Add installation instructions

10. **Add Validation Steps**
    - Verify adb connection before APK deployment
    - Check RPi connectivity before rsync
    - Validate Arduino port before upload

---

## Specific Command Reviews

### ✅ **Command 1: `/deploy-apk`** - GOOD
- **Accuracy:** 8/10
- **Issues:** Docker image name inconsistency, WebSocket reference
- **Recommendation:** Use `build-in-docker.sh` instead of direct Docker commands

### ✅ **Command 2: `/debug-with-adb-user-input-simulation`** - EXCELLENT
- **Accuracy:** 9/10
- **Issues:** None significant
- **Recommendation:** Add error handling for missing UI elements

### ⚠️ **Command 3: `/run-on-rpi`** - NEEDS FIXES
- **Accuracy:** 6/10
- **Issues:** Wrong service names, unverified endpoints
- **Recommendation:** Verify and update service names, test endpoints

### ⚠️ **Command 4: `/build-deploy-integration-test-rpi`** - NEEDS CREATION
- **Accuracy:** N/A (file doesn't exist)
- **Issues:** Test file missing
- **Recommendation:** Create test file or document alternative approach

### ✅ **Command 5: `/deploy-arduino`** - GOOD
- **Accuracy:** 7/10
- **Issues:** Wrong sketch path
- **Recommendation:** Update to `arduino/led_strip_controller/`

### ✅ **Command 6: `/test-gpio-hardware`** - GOOD
- **Accuracy:** 9/10
- **Issues:** None significant
- **Recommendation:** Add GPIO pin validation

### ✅ **Command 7: `/summarize-logs-and-plan-suggested-actions`** - EXCELLENT CONCEPT
- **Accuracy:** 7/10
- **Issues:** Service name references, WebSocket references
- **Recommendation:** Update service names, verify log sources

### ✅ **Command 8: `/tail-all-logs`** - GOOD
- **Accuracy:** 8/10
- **Issues:** Service name references
- **Recommendation:** Update Docker service names

### ⚠️ **Commands 9-12: Quick Workflow Commands** - INCOMPLETE
- **Status:** Only headers provided, no implementation
- **Recommendation:** Complete implementation details

---

## Action Items

### Immediate (Before Use)
- [ ] Update all Docker service name references
- [ ] Fix Arduino sketch path
- [ ] Verify health endpoint URLs
- [ ] Check WebSocket class existence

### Short-term (This Week)
- [ ] Create `.cursor/commands/` directory structure
- [ ] Implement missing integration test
- [ ] Standardize build command usage
- [ ] Add configuration file

### Long-term (This Month)
- [ ] Complete quick workflow commands (9-12)
- [ ] Add comprehensive error handling
- [ ] Create validation scripts
- [ ] Document dependencies and setup

---

## Conclusion

The `CURSOR-PLAN.md` is a well-thought-out document that would significantly improve development workflow efficiency. The main issues have been **FIXED**:

1. ✅ **Service name mismatches** - Updated to correct Docker service names
2. ✅ **Package name** - Updated from `cz.aiservis.app` to `cz.mia.app`
3. ✅ **Arduino path** - Updated to `arduino/led_strip_controller/`
4. ⚠️ **Missing files** - Still need to be created (integration test, command files)

With these fixes, the plan is now aligned with the `android-todo-implementation` branch (which has the "mia" rename). The estimated time savings (3-30 minutes per command) are realistic and would compound significantly over time.

**Recommendation:** 
- ✅ **CURSOR-PLAN.md is now fixed and ready for use on `android-todo-implementation` branch**
- ⚠️ **Merge consideration:** See `MERGE-ANALYSIS.md` for details on merging the rename to `main`
- 📝 **Next steps:** Create missing command files and integration test

---

## Branch Context Note

**Important:** `CURSOR-PLAN.md` was written for the "mia" renamed version of the project. The rename commit (`bea45ba`) is currently only on the `android-todo-implementation` branch, not on `main` or the current branch (`refactor/android-build-cleanup`).

**On the renamed branch:**
- Package: `cz.mia.app` ✅ (matches plan)
- Conan class: `MIAConan` ✅ (matches plan)
- Conan name: `"mia"` ✅ (matches plan)
- Docker services: Still `ai-servis-*` ⚠️ (plan assumes `mia-*`)

**Recommendation:** Review and use this plan on the `android-todo-implementation` branch, or merge the rename to main first.

**Verified on `android-todo-implementation` branch:**
- ✅ Package: `cz.mia.app` (matches plan)
- ✅ Application class: `MIAApplication` (matches plan)
- ✅ Conan: `MIAConan`, `name = "mia"` (matches plan)
- ⚠️ Docker services: Still `ai-servis-*` (plan incorrectly assumes `mia-*`)

---

## Appendix: Quick Reference Fixes

### Service Name Mapping
```yaml
Plan Document     → Actual (even on mia branch)
mia-fastapi       → ai-servis-core
zeromq-router     → service-discovery
mcp-prompts       → ai-audio-assistant
```

**Note:** Docker service names were NOT renamed in the "mia" rename commit. They remain `ai-servis-*` even on the renamed branch.

### Path Corrections
```bash
# Arduino
arduino/sketches/gpio-controller/  → arduino/led_strip_controller/

# Docker
docker build -t mia-android .      → Use build-in-docker.sh
```

### Missing Files to Create
- `.cursor/commands/deploy-apk.md`
- `.cursor/commands/debug-with-adb-user-input.md`
- `.cursor/commands/run-on-rpi.md`
- `android/test/integration/test_e2e_android_rpi.py`
- `.cursor/config.yml` (optional but recommended)
