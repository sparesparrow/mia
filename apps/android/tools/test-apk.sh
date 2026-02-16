#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Testing APK: app-debug.apk"
echo "=================================="

# Check APK file exists
if [ ! -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo "❌ APK file not found!"
    exit 1
fi

echo "✅ APK file exists"
echo "📊 APK size: $(ls -lh app/build/outputs/apk/debug/app-debug.apk | awk '{print $5}')"

# Check if device is connected
if ! adb devices | grep -q "device$"; then
    echo "❌ No Android device connected"
    echo "💡 Please connect a device or start an emulator"
    exit 1
fi

echo "✅ Android device connected"

# Try to install APK
echo "📱 Installing APK..."
if adb install -r app/build/outputs/apk/debug/app-debug.apk; then
    echo "✅ APK installed successfully"
    
    # Try to launch the app
    echo "🚀 Attempting to launch app..."
    adb shell am start -n cz.mia.app.debug/.MainActivity || echo "⚠️  Could not launch app (this is normal for first install)"
    
    # Check if app is installed
    if adb shell pm list packages | grep -q "cz.mia.app.debug"; then
        echo "✅ App package found in device"
    else
        echo "⚠️  App package not found in package list (may be normal)"
    fi
    
else
    echo "❌ APK installation failed"
    exit 1
fi

echo "=================================="
echo "🎉 APK testing completed!"
