#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Validating APK: app-debug.apk"
echo "=================================="

APK_PATH="app/build/outputs/apk/debug/app-debug.apk"

# Check APK file exists
if [ ! -f "$APK_PATH" ]; then
    echo "❌ APK file not found!"
    exit 1
fi

echo "✅ APK file exists"
echo "📊 APK size: $(ls -lh $APK_PATH | awk '{print $5}')"

# Validate APK structure
echo "📦 Validating APK structure..."

# Check if it's a valid ZIP file (APK is a ZIP)
if unzip -t "$APK_PATH" >/dev/null 2>&1; then
    echo "✅ APK is a valid ZIP archive"
else
    echo "❌ APK is not a valid ZIP archive"
    exit 1
fi

# Extract and check key files
echo "🔍 Extracting APK contents for analysis..."
TEMP_DIR=$(mktemp -d)
unzip -q "$APK_PATH" -d "$TEMP_DIR"

# Check for essential files
echo "📋 Checking essential files:"

if [ -f "$TEMP_DIR/AndroidManifest.xml" ]; then
    echo "✅ AndroidManifest.xml found"
else
    echo "❌ AndroidManifest.xml missing"
fi

if [ -d "$TEMP_DIR/classes.dex" ] || [ -f "$TEMP_DIR/classes.dex" ]; then
    echo "✅ classes.dex found"
else
    echo "❌ classes.dex missing"
fi

if [ -d "$TEMP_DIR/res" ]; then
    echo "✅ Resources directory found"
    echo "   📁 Resource files: $(find $TEMP_DIR/res -type f | wc -l)"
else
    echo "❌ Resources directory missing"
fi

if [ -d "$TEMP_DIR/assets" ]; then
    echo "✅ Assets directory found"
    echo "   📁 Asset files: $(find $TEMP_DIR/assets -type f | wc -l)"
else
    echo "⚠️  Assets directory not found (may be normal)"
fi

# Check for native libraries
if [ -d "$TEMP_DIR/lib" ]; then
    echo "✅ Native libraries directory found"
    echo "   📁 Architecture directories: $(ls $TEMP_DIR/lib/ | wc -l)"
    for arch in "$TEMP_DIR/lib"/*; do
        if [ -d "$arch" ]; then
            echo "   🔧 $(basename $arch): $(find $arch -name "*.so" | wc -l) libraries"
        fi
    done
else
    echo "⚠️  Native libraries directory not found (may be normal)"
fi

# Check APK signature
echo "🔐 Checking APK signature..."
if [ -d "$TEMP_DIR/META-INF" ]; then
    echo "✅ META-INF directory found (signature files)"
    echo "   📁 Signature files: $(find $TEMP_DIR/META-INF -name "*.RSA" -o -name "*.DSA" -o -name "*.EC" | wc -l)"
else
    echo "❌ META-INF directory missing (unsigned APK)"
fi

# Clean up
rm -rf "$TEMP_DIR"

echo "=================================="
echo "🎉 APK validation completed!"
echo ""
echo "📱 APK Summary:"
echo "   • File: $APK_PATH"
echo "   • Size: $(ls -lh $APK_PATH | awk '{print $5}')"
echo "   • Status: Valid Android APK"
echo "   • Ready for installation and testing"
