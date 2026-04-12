#!/usr/bin/env bash
# selftest.sh — MIA boot-time self-test
# Runs before ZMQ broker and API; exits non-zero on critical failures.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; WARN=0; FAIL=0

check() {
    local name="$1" result="$2"
    if [[ "$result" == "ok" ]]; then
        echo -e "${GREEN}[PASS]${NC} $name"
        PASS=$((PASS + 1))
    elif [[ "$result" == "warn" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $name"
        WARN=$((WARN + 1))
    else
        echo -e "${RED}[FAIL]${NC} $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "══════════════════════════════════════"
echo "  MIA Boot Self-Test"
echo "══════════════════════════════════════"

# 1. SD card health — check for read errors
if [[ -f /sys/block/mmcblk0/stat ]]; then
    read_errors=$(awk '{print $10}' /sys/block/mmcblk0/stat 2>/dev/null || echo "0")
    if [[ "$read_errors" -eq 0 ]]; then
        check "SD card I/O errors" "ok"
    else
        check "SD card I/O errors ($read_errors)" "warn"
    fi
else
    check "SD card stat (not mmcblk0)" "warn"
fi

# 2. Free disk space
free_mb=$(df /opt/mia 2>/dev/null | awk 'NR==2{print int($4/1024)}' || echo "0")
if [[ "$free_mb" -ge 100 ]]; then
    check "Free space: ${free_mb}MB (>100MB)" "ok"
elif [[ "$free_mb" -ge 50 ]]; then
    check "Free space: ${free_mb}MB (low)" "warn"
else
    check "Free space: ${free_mb}MB (<50MB)" "fail"
fi

# 3. Thermal sensor
if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
    temp_mc=$(cat /sys/class/thermal/thermal_zone0/temp)
    temp_c=$((temp_mc / 1000))
    if [[ "$temp_c" -lt 70 ]]; then
        check "SoC temperature: ${temp_c}C" "ok"
    elif [[ "$temp_c" -lt 80 ]]; then
        check "SoC temperature: ${temp_c}C (warm)" "warn"
    else
        check "SoC temperature: ${temp_c}C (HOT)" "fail"
    fi
else
    check "Thermal sensor" "warn"
fi

# 4. Network interface
if ip link show wlan0 &>/dev/null || ip link show eth0 &>/dev/null; then
    check "Network interface present" "ok"
else
    check "No network interface (wlan0/eth0)" "warn"
fi

# 5. Python venv
if [[ -x /opt/mia/venv/bin/python3 ]]; then
    check "Python venv executable" "ok"
else
    check "Python venv missing" "fail"
fi

# 6. ZMQ broker script
if [[ -f /opt/mia/apps/rpi-backend/py-api/core/messaging/broker.py ]]; then
    check "ZMQ broker script present" "ok"
else
    check "ZMQ broker script missing" "fail"
fi

# 7. API main.py
if [[ -f /opt/mia/apps/rpi-backend/py-api/api/main.py ]]; then
    check "FastAPI main.py present" "ok"
else
    check "FastAPI main.py missing" "fail"
fi

echo "──────────────────────────────────────"
echo "Results: $PASS passed, $WARN warnings, $FAIL failures"
echo "──────────────────────────────────────"

if [[ "$FAIL" -gt 0 ]]; then
    echo "CRITICAL: $FAIL self-test(s) failed — services may not start correctly"
    exit 1
fi

exit 0
