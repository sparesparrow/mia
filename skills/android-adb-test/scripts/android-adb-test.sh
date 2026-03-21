#!/usr/bin/env bash
set -euo pipefail

# Android ADB Test Orchestrator for MIA
# Builds APK, deploys to device, runs test scenarios with ADB UI automation

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$SKILL_DIR/../.." && pwd)"
ANDROID_DIR="$PROJECT_ROOT/apps/android"

# Defaults
APK_PATH="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE_NAME="cz.mia.app"
MAIN_ACTIVITY=".MainActivity"
DEVICE_SERIAL=""
SCENARIO="install"
DO_BUILD=0
DO_SCREENSHOTS=0
DO_LOGS=0
DO_INTERACTIVE=0
OUTPUT_BASE="$ANDROID_DIR/test-artifacts"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$OUTPUT_BASE/$TIMESTAMP"

# Helper functions
log() { echo "[$(date +'%H:%M:%S')] $*"; }
err() { echo "ERROR: $*" >&2; }

usage() {
  cat <<'EOF'
Usage: android-adb-test.sh <command> [options]

Commands:
  build                 Build APK only
  deploy                Deploy APK to device/emulator
  build-and-test        Build, deploy, run scenario
  test                  Run scenario on already-deployed app
  interactive           Launch app and enter interactive shell

Options:
  --device SERIAL       Target device serial (auto-detect if omitted)
  --apk PATH            APK path (default: apps/android/.../app-debug.apk)
  --scenario NAME       Test scenario: install|dashboard|ble-scan|obd-pairing|settings|anpr|full-flow|interactive
  --screenshots         Capture screenshots during test
  --logs                Capture logcat to output directory
  --output DIR          Output directory (default: apps/android/test-artifacts/<timestamp>)
  -h, --help            Show help

Examples:
  ./android-adb-test.sh build
  ./android-adb-test.sh deploy --device ZY32KXSJ2F
  ./android-adb-test.sh build-and-test --scenario dashboard --screenshots --logs
  ./android-adb-test.sh test --scenario full-flow --screenshots
EOF
}

ensure_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    err "adb not found. Install Android SDK Platform Tools."
    exit 1
  fi
}

pick_device() {
  [[ -n "$DEVICE_SERIAL" ]] && return
  local devices
  devices=$(adb devices | awk '/\tdevice$|emulator/{print $1}' | head -1)
  [[ -z "$devices" ]] && {
    err "No connected devices/emulators. Use --device <serial>"
    exit 1
  }
  DEVICE_SERIAL="$devices"
  log "Auto-selected device: $DEVICE_SERIAL"
}

ensure_output_dir() {
  mkdir -p "$OUTPUT_DIR/screenshots" "$OUTPUT_DIR/logs" "$OUTPUT_DIR/reports"
}

build_apk() {
  log "Building APK..."
  local build_log="$OUTPUT_DIR/build.log"
  mkdir -p "$OUTPUT_DIR"
  
  cd "$ANDROID_DIR"
  if ./gradlew assembleDebug >"$build_log" 2>&1; then
    log "✓ Build successful: $APK_PATH"
    ls -lh "$APK_PATH"
    return 0
  else
    err "Build failed. See $build_log"
    tail -50 "$build_log" >&2
    return 1
  fi
}

deploy_apk() {
  log "Deploying APK to $DEVICE_SERIAL..."
  local deploy_log="$OUTPUT_DIR/deploy.log"
  
  {
    log "Uninstalling stale package..."
    adb -s "$DEVICE_SERIAL" uninstall "$PACKAGE_NAME" 2>/dev/null || true
    
    log "Installing APK..."
    adb -s "$DEVICE_SERIAL" install -r "$APK_PATH"
    
    log "Launching app..."
    adb -s "$DEVICE_SERIAL" shell am start -n "$PACKAGE_NAME/$MAIN_ACTIVITY"
    
    log "Waiting for app to stabilize (3s)..."
    sleep 3
    
    # Verify app is running
    local pid
    pid=$(adb -s "$DEVICE_SERIAL" shell pidof -s "$PACKAGE_NAME" 2>/dev/null || echo "")
    if [[ -z "$pid" ]]; then
      echo "WARNING: App may not have started. Check logcat." >&2
    else
      echo "App PID: $pid"
    fi
  } >"$deploy_log" 2>&1
  
  log "✓ Deploy complete"
}

take_screenshot() {
  local name="$1"
  [[ "$DO_SCREENSHOTS" == "0" ]] && return
  
  local dest="$OUTPUT_DIR/screenshots/${name}_$(date +%s).png"
  # Try exec-out first (fast), fallback to shell+pull (older devices)
  if adb -s "$DEVICE_SERIAL" exec-out screencap -p >"$dest" 2>/dev/null && [[ -s "$dest" && $(stat -c%s "$dest" 2>/dev/null || echo 0) -gt 1000 ]]; then
    log "📸 Screenshot: $dest"
  else
    adb -s "$DEVICE_SERIAL" shell screencap -p /sdcard/_adb_screenshot.png 2>/dev/null || true
    if adb -s "$DEVICE_SERIAL" pull /sdcard/_adb_screenshot.png "$dest" 2>/dev/null; then
      adb -s "$DEVICE_SERIAL" shell rm /sdcard/_adb_screenshot.png 2>/dev/null || true
      log "📸 Screenshot (pull): $dest"
    else
      err "Screenshot failed"
    fi
  fi
}

adb_tap() {
  local x="$1" y="$2"
  adb -s "$DEVICE_SERIAL" shell input tap "$x" "$y"
  sleep "${DELAY_MS:-1000}ms" || sleep 1
}

adb_swipe() {
  local x1="$1" y1="$2" x2="$3" y2="$4"
  adb -s "$DEVICE_SERIAL" shell input swipe "$x1" "$y1" "$x2" "$y2"
  sleep "${DELAY_MS:-1000}ms" || sleep 1
}

start_logcat() {
  [[ "$DO_LOGS" == "0" ]] && return
  
  local log_file="$OUTPUT_DIR/logs/logcat.txt"
  local pid
  pid=$(adb -s "$DEVICE_SERIAL" shell pidof -s "$PACKAGE_NAME" 2>/dev/null || echo "")
  
  if [[ -n "$pid" ]]; then
    adb -s "$DEVICE_SERIAL" logcat -v time --pid="$pid" >"$log_file" 2>&1 &
  else
    adb -s "$DEVICE_SERIAL" logcat -v time >"$log_file" 2>&1 &
  fi
  LOGCAT_PID=$!
  log "Logcat capturing (PID: $LOGCAT_PID)"
}

stop_logcat() {
  [[ -z "${LOGCAT_PID:-}" ]] && return
  kill "$LOGCAT_PID" 2>/dev/null || true
  log "Logcat stopped"
}

scenario_dashboard() {
  log "Scenario: dashboard"
  take_screenshot "dashboard_initial"
  sleep 2
  take_screenshot "dashboard_telemetry"
}

scenario_ble_scan() {
  log "Scenario: BLE scan"
  adb_swipe 500 1600 500 400  # Scroll up
  sleep 1
  adb_tap 540 300             # Tap BLE tab
  sleep 2
  take_screenshot "ble_scan_screen"
}

scenario_obd_pairing() {
  log "Scenario: OBD pairing"
  adb_swipe 500 1600 500 400
  sleep 1
  adb_tap 540 1200            # Tap OBD tab
  sleep 2
  take_screenshot "obd_pairing"
}

scenario_settings() {
  log "Scenario: settings"
  adb_swipe 500 1600 500 400
  sleep 1
  adb_tap 540 1700            # Tap settings
  sleep 2
  take_screenshot "settings"
}

scenario_anpr() {
  log "Scenario: ANPR"
  adb_tap 540 1000            # Tap camera/ANPR
  sleep 3
  take_screenshot "anpr_camera"
}

scenario_full_flow() {
  log "Scenario: full-flow (chained)"
  scenario_dashboard
  scenario_ble_scan
  scenario_obd_pairing
}

scenario_interactive() {
  log "Interactive mode. Commands: tap X Y | swipe X1 Y1 X2 Y2 | text 'str' | screenshot [name] | exit"
  while true; do
    read -r -p "> " line || break
    case "$line" in
      tap*) adb -s "$DEVICE_SERIAL" shell input $line ;;
      swipe*) adb -s "$DEVICE_SERIAL" shell input $line ;;
      text\ *) adb -s "$DEVICE_SERIAL" shell input text "${line#text }" ;;
      screenshot*)
        local name="${line#screenshot }"
        name=${name:-interactive_$(date +%s)}
        take_screenshot "$name"
        ;;
      logcat)
        adb -s "$DEVICE_SERIAL" logcat -d -t 30 | grep -E "cz.mia.app|AndroidRuntime|BLEManager" || true
        ;;
      exit) break ;;
      *) echo "Unknown: $line" ;;
    esac
  done
}

run_scenario() {
  case "$SCENARIO" in
    install) log "Install only (app already launched)" ;;
    dashboard) scenario_dashboard ;;
    ble-scan) scenario_ble_scan ;;
    obd-pairing) scenario_obd_pairing ;;
    settings) scenario_settings ;;
    anpr) scenario_anpr ;;
    full-flow) scenario_full_flow ;;
    interactive)
      scenario_interactive
      ;;
    *) err "Unknown scenario: $SCENARIO"; return 1 ;;
  esac
}

generate_report() {
  local report_file="$OUTPUT_DIR/reports/test-report.json"
  cat >"$report_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "device": "$DEVICE_SERIAL",
  "scenario": "$SCENARIO",
  "package": "$PACKAGE_NAME",
  "apk_path": "$APK_PATH",
  "screenshots_captured": $(find "$OUTPUT_DIR/screenshots" -type f 2>/dev/null | wc -l),
  "logcat_available": $([[ -f "$OUTPUT_DIR/logs/logcat.txt" ]] && echo "true" || echo "false"),
  "output_dir": "$OUTPUT_DIR"
}
EOF
  log "Report: $report_file"
}

parse_args() {
  [[ $# -eq 0 ]] && {
    usage
    exit 0
  }
  
  COMMAND="$1"
  shift || true
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --device) DEVICE_SERIAL="$2"; shift 2 ;;
      --apk) APK_PATH="$2"; shift 2 ;;
      --scenario) SCENARIO="$2"; shift 2 ;;
      --screenshots) DO_SCREENSHOTS=1; shift ;;
      --logs) DO_LOGS=1; shift ;;
      --output) OUTPUT_DIR="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) err "Unknown: $1"; exit 1 ;;
    esac
  done
}

main() {
  parse_args "$@"
  ensure_adb
  pick_device
  ensure_output_dir
  
  case "$COMMAND" in
    build)
      build_apk
      ;;
    deploy)
      [[ ! -f "$APK_PATH" ]] && {
        err "APK not found: $APK_PATH. Run 'build' first."
        exit 1
      }
      deploy_apk
      ;;
    build-and-test)
      build_apk
      deploy_apk
      start_logcat
      run_scenario
      stop_logcat
      generate_report
      ;;
    test)
      [[ -z "$DEVICE_SERIAL" ]] && {
        err "No device selected. Use --device <serial>"
        exit 1
      }
      start_logcat
      run_scenario
      stop_logcat
      generate_report
      ;;
    interactive)
      [[ -z "$DEVICE_SERIAL" ]] && {
        err "No device. Use --device <serial>"
        exit 1
      }
      scenario_interactive
      ;;
    *)
      err "Unknown command: $COMMAND"
      usage
      exit 1
      ;;
  esac
}

main "$@"
