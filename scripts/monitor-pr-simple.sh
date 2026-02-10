#!/bin/bash
# Simplified PR workflow monitor that works without GitHub CLI

set -e

BRANCH="${1:-feature/raspberry-pi-development}"
MAIN_BRANCH="main"
LOOP_INTERVAL=300  # 5 minutes

echo "========================================"
echo "  PR Workflow Monitor (Simple)"
echo "========================================"
echo "Branch: $BRANCH"
echo "Check interval: ${LOOP_INTERVAL}s"
echo ""

ITERATION=0

while true; do
    ITERATION=$((ITERATION + 1))
    echo ""
    echo "========================================"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Iteration $ITERATION"
    echo "========================================"
    
    # Step 1: Rebase on main
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Step 1: Rebasing on $MAIN_BRANCH..."
    git fetch origin "$MAIN_BRANCH" 2>&1 || {
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Failed to fetch main branch"
        sleep 60
        continue
    }
    
    # Check if rebase is needed
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse "origin/$MAIN_BRANCH")
    BASE=$(git merge-base HEAD "origin/$MAIN_BRANCH")
    
    if [ "$LOCAL" = "$BASE" ]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Branch is behind main, rebasing..."
        if git rebase "origin/$MAIN_BRANCH"; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ Rebase successful"
        else
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Rebase conflicts detected"
            # Try to resolve common conflicts
            if git status --short | grep -q "UU.*requirements.txt"; then
                echo "[$(date +'%Y-%m-%d %H:%M:%S')] Resolving requirements.txt conflict..."
                git checkout --ours rpi/requirements.txt 2>/dev/null || true
                git add rpi/requirements.txt 2>/dev/null || true
            fi
            if git rebase --continue 2>/dev/null; then
                echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ Conflicts resolved"
            else
                echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✗ Manual intervention needed"
                git rebase --abort 2>/dev/null || true
            fi
        fi
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Branch is up to date with main"
    fi
    
    # Step 2: Push changes
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Step 2: Pushing to origin..."
    if git push origin "$BRANCH" --force-with-lease 2>&1; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ Push successful"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Push failed (may need authentication or network)"
    fi
    
    # Step 3: Wait for workflows
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Step 3: Waiting ${LOOP_INTERVAL}s for workflows to run..."
    sleep "$LOOP_INTERVAL"
    
    # Step 4: Check for common issues and fix them
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Step 4: Checking for common issues..."
    
    # Check Python syntax
    if [ -f "rpi/services/obd_worker.py" ]; then
        if ! python3 -m py_compile rpi/services/obd_worker.py 2>/dev/null; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Syntax error in obd_worker.py"
        fi
    fi
    
    if [ -f "rpi/hardware/serial_bridge.py" ]; then
        if ! python3 -m py_compile rpi/hardware/serial_bridge.py 2>/dev/null; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Syntax error in serial_bridge.py"
        fi
    fi
    
    # Check Conan file syntax
    if [ -f "rpi/conanfile.py" ]; then
        if ! python3 -m py_compile rpi/conanfile.py 2>/dev/null; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Syntax error in conanfile.py"
        fi
    fi
    
    # Check test file syntax
    if [ -f "tests/integration/test_obd_simulator.py" ]; then
        if ! python3 -m py_compile tests/integration/test_obd_simulator.py 2>/dev/null; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Syntax error in test_obd_simulator.py"
        fi
    fi
    
    # Check if requirements.txt has all needed packages
    if [ -f "rpi/requirements.txt" ]; then
        REQUIRED_PACKAGES=("pyzmq" "pyserial" "fastapi" "pydantic")
        for pkg in "${REQUIRED_PACKAGES[@]}"; do
            if ! grep -q "$pkg" rpi/requirements.txt; then
                echo "[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ Missing package in requirements.txt: $pkg"
                echo "$pkg" >> rpi/requirements.txt
                git add rpi/requirements.txt
                git commit -m "fix: Add missing dependency $pkg" 2>/dev/null || echo "No changes"
                git push origin "$BRANCH" 2>/dev/null || echo "Push failed"
            fi
        done
    fi
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Cycle complete, next check in ${LOOP_INTERVAL}s"
done
