# Workflow Failures - Complete Fix Strategy

**Date:** 2025-12-31
**Issue:** 24 failing, 2 neutral, 7 cancelled checks
**Root Causes:** Multiple configuration issues across workflows

---

## 🔍 Identified Issues

### 1. pytest.ini Requires pytest-cov (CRITICAL) ✅ FIXED
**Problem:** pytest.ini addopts included --cov-report flags
**Impact:** All pytest runs fail if pytest-cov not installed
**Fix:** Commented out coverage flags in pytest.ini

### 2. Hardware Tests Not Marked (HIGH)
**Problem:** No @pytest.mark.hardware decorators on hardware tests
**Impact:** CI tries to run tests requiring physical hardware
**Files:** tests/integration/test_obd_simulator.py

### 3. Workflows Don't Use requirements-dev.txt (HIGH)
**Problem:** Workflows install requirements.txt only
**Impact:** Missing pytest, pytest-asyncio, etc.
**Files:** All .github/workflows/*.yml

### 4. Missing Dependency Handling (MEDIUM)
**Problem:** Workflows fail hard on optional dependencies
**Impact:** ELM327-emulator, RPi.GPIO failures block entire workflow
**Solution:** Use continue-on-error for optional deps

### 5. CodeQL Config File Missing (MEDIUM)
**Problem:** main.yml references .github/codeql/codeql-config.yml
**Impact:** CodeQL init fails
**File:** .github/codeql/codeql-config.yml (missing)

### 6. pre-commit Config Missing (LOW)
**Problem:** Workflows run pre-commit but no .pre-commit-config.yaml
**Impact:** pre-commit fails
**File:** .pre-commit-config.yaml (missing)

---

## 🔧 Fixes to Apply

### Fix 1: Update pytest.ini ✅ DONE
```ini
# Commented out coverage requirements
addopts =
    -ra
    --strict-markers
    --tb=short
    # --cov-report=term-missing  # Commented
```

### Fix 2: Mark Hardware Tests
```python
# tests/integration/test_obd_simulator.py
import pytest

@pytest.mark.hardware
class TestSerialBridge:
    ...

@pytest.mark.hardware
class TestOBDWorker:
    ...
```

### Fix 3: Update Python Workflow
```yaml
# .github/workflows/python.yml
- name: Install dependencies
  run: |
    pip install -r requirements-dev.txt || pip install -r requirements.txt

- name: Run tests
  run: pytest tests/ -v -m "not hardware"
```

### Fix 4: Update Main Workflow
```yaml
# .github/workflows/main.yml
- name: Install Python dependencies
  run: |
    pip install -r requirements-dev.txt || {
      pip install -r requirements.txt
      pip install pytest pytest-asyncio pytest-cov
    }
```

### Fix 5: Create CodeQL Config
```yaml
# .github/codeql/codeql-config.yml
name: "CodeQL Config"
disable-default-queries: false
queries:
  - uses: security-and-quality
paths-ignore:
  - "tests/"
  - "**/*.test.py"
```

### Fix 6: Create pre-commit Config
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

---

## 📋 Workflow-by-Workflow Analysis

### ✅ Should Pass (with fixes):
1. python.yml - Install requirements-dev, skip hardware
2. main.yml - Update dependency installation
3. security.yml - Handle optional C++ deps
4. codeql.yml - Create config file

### ⚠️ May Need Skipping:
5. android.yml - Requires Android SDK
6. android-ci.yml - Requires Android SDK
7. android-build.yml - Requires Android SDK
8. cpp.yml - Requires C++ build environment
9. esp32.yml - Requires ESP32 toolchain

### 🔧 Need Configuration:
10. automotive-testing.yml - Skip if no hardware
11. rpi-python-services.yml - Skip if not ARM
12. edge-deployment.yml - Skip for feature branches

---

## 🎯 Immediate Action Plan

1. ✅ Fix pytest.ini (DONE)
2. Mark hardware tests with decorators
3. Create CodeQL config file
4. Create pre-commit config file
5. Update all workflows to use requirements-dev.txt
6. Add workflow conditions to skip platform-specific builds
7. Test locally before committing

---

**Status:** Analysis complete, fixes in progress
