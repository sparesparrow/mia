#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

APK_PATH="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE_NAME="cz.mia.app.debug"
MAIN_ACTIVITY=".MainActivity"
OUTPUT_DIR="$ANDROID_DIR/debug-output"
DELAY_MS=1000
TIMEOUT_SEC=60
SCENARIO="install"
DEVICE_SERIAL=""
DO_BUILD=0
DO_LOGS=0
DO_SCREENSHOTS=0
DO_RECORD=0
NO_LAUNCH=0
DO_CLEANUP=0

LOGCAT_PID=""
RECORD_PID=""
RECORD_REMOTE=""

usage() {
  cat <<'EOF'
Usage: debug-with-adb-user-input-simulation.sh [options] [scenario]

Scenarios:
  install       Install (and launch) only
  dashboard     Dashboard smoke flow
  ble-scan      BLE scan flow
  obd-pairing   OBD pairing flow
  settings      Settings navigation
  anpr          ANPR navigation
  full-flow     Chained dashboard + BLE + OBD flow
  interactive   Interactive shell for manual input

Options:
  --device SERIAL     Target device serial (auto-detect if omitted)
  --apk PATH          APK path (default: android/app/build/outputs/apk/debug/app-debug.apk)
  --build             Build APK with android/tools/build-in-docker.sh
  --no-launch         Do not launch the app after install
  --screenshots       Capture screenshots during scripted steps
  --logs              Capture logcat to output directory
  --delay MS          Delay between scripted actions (default: 1000)
  --timeout SEC       Timeout for long-running actions (default: 60)
  --output DIR        Output directory for artifacts (default: debug-output)
  --record            Screen-record the run (saved to output/recordings)
  --cleanup           Uninstall app after run
  -h, --help          Show this help
EOF
}

ms_sleep() {
  local ms="$1"
  python3 - <<PY
import time
time.sleep(${ms}/1000)
PY
}

log() {
  echo "[$(date +'%H:%M:%S')] $*"
}

err() {
  echo "ERROR: $*" >&2
}

ensure_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    err "adb not found in PATH"
    exit 1
  fi
}

pick_device() {
  if [[ -n "$DEVICE_SERIAL" ]]; then
    return
  fi
  local devices
  devices=$(adb devices | awk '/\tdevice$/{print $1}')
  if [[ -z "$devices" ]]; then
    err "No connected devices/emulators detected"
    exit 1
  fi
  DEVICE_SERIAL="$(echo "$devices" | head -n1)"
  log "Using device: $DEVICE_SERIAL"
}

ensure_output_dirs() {
  mkdir -p "$OUTPUT_DIR" \
    "$OUTPUT_DIR/logs" \
    "$OUTPUT_DIR/screenshots" \
    "$OUTPUT_DIR/recordings"
}

start_logcat() {
  [[ $DO_LOGS -eq 1 ]] || return
  local log_file="$OUTPUT_DIR/logs/logcat.txt"
  local pid=""
  pid=$(adb -s "$DEVICE_SERIAL" shell pidof -s "$PACKAGE_NAME" 2>/dev/null || true)
  log "Starting logcat capture -> $log_file"
  if [[ -n "$pid" ]]; then
    adb -s "$DEVICE_SERIAL" logcat -v time --pid="$pid" >"$log_file" 2>&1 &
  else
    adb -s "$DEVICE_SERIAL" logcat -v time >"$log_file" 2>&1 &
  fi
  LOGCAT_PID=$!
}

stop_logcat() {
  if [[ -n "${LOGCAT_PID:-}" ]]; then
    kill "$LOGCAT_PID" >/dev/null 2>&1 || true
  fi
}

start_screenrecord() {
  [[ $DO_RECORD -eq 1 ]] || return
  RECORD_REMOTE="/sdcard/debug-sim.mp4"
  log "Starting screenrecord..."
  adb -s "$DEVICE_SERIAL" shell screenrecord --time-limit "$TIMEOUT_SEC" "$RECORD_REMOTE" >/dev/null 2>&1 &
  RECORD_PID=$!
}

stop_screenrecord() {
  [[ -n "${RECORD_REMOTE:-}" ]] || return
  if [[ -n "${RECORD_PID:-}" ]]; then
    kill "$RECORD_PID" >/dev/null 2>&1 || true
    wait "$RECORD_PID" 2>/dev/null || true
  fi
  local dest="$OUTPUT_DIR/recordings/screenrecord.mp4"
  adb -s "$DEVICE_SERIAL" pull "$RECORD_REMOTE" "$dest" >/dev/null 2>&1 || true
  adb -s "$DEVICE_SERIAL" shell rm "$RECORD_REMOTE" >/dev/null 2>&1 || true
  log "Screenrecord saved to $dest"
}

take_screenshot() {
  [[ $DO_SCREENSHOTS -eq 1 ]] || return
  local name="$1"
  local dest="$OUTPUT_DIR/screenshots/${name}.png"
  adb -s "$DEVICE_SERIAL" exec-out screencap -p >"$dest"
  log "Screenshot saved: $dest"
}

adb_tap() {
  adb -s "$DEVICE_SERIAL" shell input tap "$@"
  ms_sleep "$DELAY_MS"
}

adb_swipe() {
  adb -s "$DEVICE_SERIAL" shell input swipe "$@"
  ms_sleep "$DELAY_MS"
}

adb_text() {
  adb -s "$DEVICE_SERIAL" shell input text "$1"
  ms_sleep "$DELAY_MS"
}

install_apk() {
  if [[ ! -f "$APK_PATH" ]]; then
    err "APK not found at $APK_PATH"
    exit 1
  fi
  log "Installing APK: $APK_PATH"
  adb -s "$DEVICE_SERIAL" install -r "$APK_PATH" >/dev/null
}

launch_app() {
  [[ $NO_LAUNCH -eq 1 ]] && return
  log "Launching $PACKAGE_NAME/$MAIN_ACTIVITY"
  adb -s "$DEVICE_SERIAL" shell am start -n "$PACKAGE_NAME/$MAIN_ACTIVITY" >/dev/null
  ms_sleep "$DELAY_MS"
}

cleanup() {
  stop_logcat
  stop_screenrecord
  if [[ $DO_CLEANUP -eq 1 ]]; then
    log "Uninstalling $PACKAGE_NAME"
    adb -s "$DEVICE_SERIAL" uninstall "$PACKAGE_NAME" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

scenario_dashboard() {
  log "Scenario: dashboard"
  launch_app
  take_screenshot "dashboard_initial"
}

scenario_ble_scan() {
  log "Scenario: BLE scan"
  launch_app
  adb_swipe 500 1600 500 400
  adb_tap 540 300
  take_screenshot "ble_scan"
}

scenario_obd_pairing() {
  log "Scenario: OBD pairing"
  launch_app
  adb_tap 540 1200
  adb_tap 540 1400
  take_screenshot "obd_pairing"
}

scenario_settings() {
  log "Scenario: settings"
  launch_app
  adb_swipe 500 1600 500 400
  adb_tap 540 1700
  take_screenshot "settings"
}

scenario_anpr() {
  log "Scenario: ANPR"
  launch_app
  adb_tap 540 1000
  take_screenshot "anpr"
}

scenario_full_flow() {
  log "Scenario: full-flow"
  scenario_dashboard
  scenario_ble_scan
  scenario_obd_pairing
}

interactive_shell() {
  log "Interactive mode. Commands: tap x y | swipe x1 y1 x2 y2 | text \"str\" | screenshot [name] | logs | hierarchy | exit"
  while true; do
    read -r -p "> " line || break
    case "$line" in
      tap*) adb -s "$DEVICE_SERIAL" shell input $line ;;
      swipe*) adb -s "$DEVICE_SERIAL" shell input $line ;;
      text\ *) adb_text "${line#text }" ;;
      screenshot*)
        local name
        name=$(echo "$line" | awk '{print $2}')
        name=${name:-interactive_$(date +%s)}
        take_screenshot "$name"
        ;;
      logs)
        adb -s "$DEVICE_SERIAL" logcat -d -t 40 --pid="$(adb -s "$DEVICE_SERIAL" shell pidof -s "$PACKAGE_NAME" 2>/dev/null || true)" || true
        ;;
      hierarchy)
        adb -s "$DEVICE_SERIAL" shell uiautomator dump >/dev/null 2>&1 || true
        adb -s "$DEVICE_SERIAL" pull /sdcard/window_dump.xml "$OUTPUT_DIR/logs/window_dump.xml" >/dev/null 2>&1 || true
        log "UI hierarchy dumped to $OUTPUT_DIR/logs/window_dump.xml"
        ;;
      exit) break ;;
      *) echo "Unknown command: $line" ;;
    esac
  done
}

run_scenario() {
  case "$SCENARIO" in
    install) launch_app ;;
    dashboard) scenario_dashboard ;;
    ble-scan) scenario_ble_scan ;;
    obd-pairing) scenario_obd_pairing ;;
    settings) scenario_settings ;;
    anpr) scenario_anpr ;;
    full-flow) scenario_full_flow ;;
    interactive) launch_app; interactive_shell ;;
    *) err "Unknown scenario: $SCENARIO"; exit 1 ;;
  esac
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --device) DEVICE_SERIAL="$2"; shift 2 ;;
      --apk) APK_PATH="$2"; shift 2 ;;
      --build) DO_BUILD=1; shift ;;
      --no-launch) NO_LAUNCH=1; shift ;;
      --screenshots) DO_SCREENSHOTS=1; shift ;;
      --logs) DO_LOGS=1; shift ;;
      --delay) DELAY_MS="$2"; shift 2 ;;
      --timeout) TIMEOUT_SEC="$2"; shift 2 ;;
      --output) OUTPUT_DIR="$2"; shift 2 ;;
      --record) DO_RECORD=1; shift ;;
      --cleanup) DO_CLEANUP=1; shift ;;
      -h|--help) usage; exit 0 ;;
      install|dashboard|ble-scan|obd-pairing|settings|anpr|full-flow|interactive)
        SCENARIO="$1"; shift ;;
      *) usage; err "Unknown option $1"; exit 1 ;;
    esac
  done
}

main() {
  parse_args "$@"
  ensure_adb
  pick_device
  ensure_output_dirs
  log "Output directory: $OUTPUT_DIR"

  if [[ $DO_BUILD -eq 1 ]]; then
    log "Building APK..."
    "$SCRIPT_DIR/build-in-docker.sh" --task assembleDebug
  fi

  log "Waiting for device..."
  adb -s "$DEVICE_SERIAL" wait-for-device
  adb -s "$DEVICE_SERIAL" shell getprop ro.product.model >/dev/null || true

  install_apk
  start_logcat
  start_screenrecord
  run_scenario
  take_screenshot "final"
}

main "$@"

