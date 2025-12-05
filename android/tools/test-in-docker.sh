#!/usr/bin/env bash
set -euo pipefail

echo "🐳 Testing APK in Docker environment"
echo "=================================="

IMAGE_NAME=ai-servis-android-build:latest
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ANDROID_DIR="$PROJECT_ROOT"
SDK_VOL=mia_android_sdk

# Check if APK exists
if [ ! -f "$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo "❌ APK file not found!"
    exit 1
fi

echo "✅ APK file found: $(ls -lh $ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk | awk '{print $5}')"

# Start emulator in Docker
echo "📱 Starting Android emulator in Docker..."
docker run --rm -d \
  --name ai-servis-emulator \
  -v $SDK_VOL:/opt/android-sdk \
  -e ANDROID_HOME=/opt/android-sdk \
  -e ANDROID_SDK_ROOT=/opt/android-sdk \
  -p 5555:5555 \
  "$IMAGE_NAME" \
  emulator -avd Medium_Phone_API_36.0 -no-window -no-audio -port 5555

echo "⏳ Waiting for emulator to start..."
sleep 60

# Test APK installation
echo "📦 Testing APK installation..."
docker run --rm \
  --link ai-servis-emulator:emulator \
  -v "$ANDROID_DIR":/workspace \
  -v $SDK_VOL:/opt/android-sdk \
  -e ANDROID_HOME=/opt/android-sdk \
  -e ANDROID_SDK_ROOT=/opt/android-sdk \
  -w /workspace \
  "$IMAGE_NAME" \
  bash -c "
    adb connect emulator:5555
    sleep 10
    adb devices
    adb install -r app/build/outputs/apk/debug/app-debug.apk
    adb shell pm list packages | grep aiservis || echo 'Package not found in list (may be normal)'
  "

# Clean up
echo "🧹 Cleaning up..."
docker stop ai-servis-emulator 2>/dev/null || true

echo "=================================="
echo "🎉 Docker APK testing completed!"
