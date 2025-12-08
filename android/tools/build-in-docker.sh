#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=ai-servis-android-build:latest
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
ANDROID_DIR="$PROJECT_ROOT"
SDK_VOL=mia_android_sdk

# Optional args
BUILD_TASK="assembleDebug"
COVERAGE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      BUILD_TASK="$2"; shift 2 ;;
    --version-code)
      export VERSION_CODE="$2"; shift 2 ;;
    --version-name)
      export VERSION_NAME="$2"; shift 2 ;;
    --coverage)
      COVERAGE="createDebugCoverageReport"; shift ;;
    --test)
      BUILD_TASK="test"; shift ;;
    --lint)
      BUILD_TASK="lint"; shift ;;
    --connected-test)
      BUILD_TASK="connectedAndroidTest"; shift ;;
    --all)
      BUILD_TASK="assembleDebug test lint"; shift ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --task TASK         Run specific Gradle task (default: assembleDebug)"
      echo "  --test              Run unit tests"
      echo "  --lint              Run lint checks"
      echo "  --connected-test    Run instrumented tests (requires device/emulator)"
      echo "  --coverage          Generate test coverage report"
      echo "  --all               Run assembleDebug, test, and lint"
      echo "  --version-code N    Set version code"
      echo "  --version-name V    Set version name"
      exit 1 ;;
  esac
done

# Append coverage task if requested
if [[ -n "$COVERAGE" ]]; then
  BUILD_TASK="$BUILD_TASK $COVERAGE"
fi

echo "=== AI-SERVIS Android Build ==="
echo "Task: $BUILD_TASK"
echo "Directory: $ANDROID_DIR"
echo ""


# Build image (use android/ as build context)
cd "$ANDROID_DIR"
docker build -t "$IMAGE_NAME" .

# Bootstrap SDK into the named volume: accept licenses and install packages into /sdk
docker run --rm \
  -v $SDK_VOL:/sdk \
  -e ANDROID_HOME=/sdk \
  -e ANDROID_SDK_ROOT=/sdk \
  "$IMAGE_NAME" bash -lc "set -e; \
    sdkmanager --version >/dev/null; \
    yes | sdkmanager --sdk_root=/sdk --licenses >/dev/null; \
    sdkmanager --sdk_root=/sdk 'platform-tools' 'platforms;android-34' 'build-tools;34.0.0' >/dev/null"

# Run build with mounted project and persistent SDK + Gradle caches
exec docker run --rm --init \
  -u $(id -u):$(id -g) \
  -v "$ANDROID_DIR":/workspace \
  -v $SDK_VOL:/opt/android-sdk \
  -e ANDROID_HOME=/opt/android-sdk \
  -e ANDROID_SDK_ROOT=/opt/android-sdk \
  -e GRADLE_USER_HOME=/workspace/.gradle \
  -e VERSION_CODE="${VERSION_CODE:-1}" \
  -e VERSION_NAME="${VERSION_NAME:-1.0.0}" \
  -w /workspace \
  "$IMAGE_NAME" gradle --no-daemon ${BUILD_TASK}
