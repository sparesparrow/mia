#!/bin/bash
# ADB Connection Diagnostic Script

set -euo pipefail

status=0

echo "=== ADB Connection Diagnostics ==="
echo ""

if ! command -v adb >/dev/null 2>&1; then
    echo "adb is not installed or not available in PATH" >&2
    exit 1
fi

echo "1. Checking ADB server..."
if pgrep -x adb > /dev/null; then
    echo "   ✓ ADB server is running"
else
    echo "   ✗ ADB server is not running"
    echo "   Starting ADB server..."
    adb start-server
fi

echo ""
echo "2. Checking USB devices..."
if command -v lsusb &> /dev/null; then
    echo "   USB devices:"
    lsusb | grep -i "android\|google\|samsung\|xiaomi\|huawei\|oneplus" || echo "   No Android devices found in USB list"
else
    echo "   lsusb not available"
fi

echo ""
echo "3. Checking ADB devices..."
if device_output="$(adb devices -l 2>&1)"; then
    printf '%s\n' "$device_output"

    if ! awk 'NR > 1 && $2 == "device" { found = 1 } END { exit found ? 0 : 1 }' <<< "$device_output"; then
        status=1
        echo "   ✗ No authorized ADB devices detected"
    fi
else
    printf '%s\n' "$device_output" >&2
    status=1
fi

echo ""
echo "4. If no device is shown, try:"
echo "   - Unplug and replug USB cable"
echo "   - On your phone: Settings > Developer Options > Revoke USB debugging authorizations"
echo "   - On your phone: Settings > Developer Options > USB debugging (toggle off/on)"
echo "   - Check USB connection mode on phone (should be 'File Transfer' or 'MTP')"
echo "   - Try different USB cable/port"
echo ""
echo "5. If device shows as 'unauthorized':"
echo "   - Check your phone screen for authorization prompt"
echo "   - Tap 'Allow' or 'OK' on the prompt"
echo ""

if [ "$status" -eq 0 ]; then
    echo "ADB diagnostic complete: at least one authorized device is available."
else
    echo "ADB diagnostic complete: no authorized device is currently available." >&2
fi

exit "$status"
