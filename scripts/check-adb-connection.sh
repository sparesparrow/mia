#!/bin/bash
# ADB Connection Diagnostic Script

echo "=== ADB Connection Diagnostics ==="
echo ""

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
adb devices -l

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
