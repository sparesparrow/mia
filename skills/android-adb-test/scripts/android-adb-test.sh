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
UI_DUMP_PATH="/sdcard/window_dump.xml"
DEVICE_SERIAL=""
SCENARIO="install"
DO_BUILD=0
DO_SCREENSHOTS=0
DO_LOGS=0
DO_INTERACTIVE=0
OUTPUT_BASE="$ANDROID_DIR/test-artifacts"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$OUTPUT_BASE/$TIMESTAMP"
DEFAULT_DELAY_MS=800

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

ensure_python3() {
  if ! command -v python3 >/dev/null 2>&1; then
    err "python3 not found. Install Python 3 to parse the Android UI hierarchy."
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

sleep_ms() {
  local delay_ms="${1:-${DELAY_MS:-$DEFAULT_DELAY_MS}}"
  local seconds
  printf -v seconds '%d.%03d' "$((delay_ms / 1000))" "$((delay_ms % 1000))"
  sleep "$seconds"
}

collapse_status_bar() {
  adb -s "$DEVICE_SERIAL" shell cmd statusbar collapse >/dev/null 2>&1 || true
}

wake_device() {
  adb -s "$DEVICE_SERIAL" shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || true
  adb -s "$DEVICE_SERIAL" shell wm dismiss-keyguard >/dev/null 2>&1 || true
}

bring_app_to_foreground() {
  wake_device
  adb -s "$DEVICE_SERIAL" shell am start -W -n "$PACKAGE_NAME/$MAIN_ACTIVITY" >/dev/null 2>&1
  sleep_ms 1200
  collapse_status_bar
}

grant_runtime_permissions() {
  local api_level
  local permissions=(
    android.permission.ACCESS_FINE_LOCATION
    android.permission.CAMERA
  )

  api_level=$(adb -s "$DEVICE_SERIAL" shell getprop ro.build.version.sdk 2>/dev/null | tr -d '\r')

  if [[ "${api_level:-0}" -ge 31 ]]; then
    permissions+=(
      android.permission.BLUETOOTH_SCAN
      android.permission.BLUETOOTH_CONNECT
    )
  fi

  if [[ "${api_level:-0}" -ge 33 ]]; then
    permissions+=(android.permission.POST_NOTIFICATIONS)
  fi

  for permission in "${permissions[@]}"; do
    adb -s "$DEVICE_SERIAL" shell pm grant "$PACKAGE_NAME" "$permission" >/dev/null 2>&1 || true
  done
}

dump_ui_xml() {
  adb -s "$DEVICE_SERIAL" shell uiautomator dump "$UI_DUMP_PATH" >/dev/null 2>&1 || return 1
  adb -s "$DEVICE_SERIAL" shell cat "$UI_DUMP_PATH" | tr -d '\r'
}

find_ui_center() {
  local needle="$1"
  local match_mode="${2:-contains}"
  local placement="${3:-first}"

  dump_ui_xml | python3 -c '
import re
import sys
import xml.etree.ElementTree as ET

needle = sys.argv[1].strip().lower()
match_mode = sys.argv[2]
placement = sys.argv[3]
xml_text = sys.stdin.read().strip()

if not xml_text:
    sys.exit(1)

root = ET.fromstring(xml_text)
candidates = []

for node in root.iter("node"):
    text = (node.attrib.get("text") or "").strip()
    desc = (node.attrib.get("content-desc") or "").strip()
    haystack = " ".join(part for part in (text, desc) if part).strip()
    if not haystack:
        continue

    haystack_lower = haystack.lower()
    matched = haystack_lower == needle if match_mode == "exact" else needle in haystack_lower
    if not matched:
        continue

    bounds = [int(value) for value in re.findall(r"\d+", node.attrib.get("bounds", ""))]
    if len(bounds) != 4:
        continue

    x = (bounds[0] + bounds[2]) // 2
    y = (bounds[1] + bounds[3]) // 2
    candidates.append((y, x))

if not candidates:
    sys.exit(1)

candidates.sort()
chosen = candidates[-1] if placement == "bottom-most" else candidates[0]
print(f"{chosen[1]} {chosen[0]}")
' "$needle" "$match_mode" "$placement"
}

ui_has_text() {
  find_ui_center "$1" "${2:-contains}" "${3:-first}" >/dev/null 2>&1
}

tap_ui_text() {
  local needle="$1"
  local match_mode="${2:-contains}"
  local placement="${3:-first}"
  local coords
  local x
  local y

  coords=$(find_ui_center "$needle" "$match_mode" "$placement") || {
    err "UI text not found: $needle"
    return 1
  }

  read -r x y <<<"$coords"
  adb -s "$DEVICE_SERIAL" shell input tap "$x" "$y"
  sleep_ms
}

wait_for_ui_text() {
  local needle="$1"
  local attempts="${2:-10}"
  local match_mode="${3:-contains}"
  local placement="${4:-first}"
  local attempt

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if ui_has_text "$needle" "$match_mode" "$placement"; then
      return 0
    fi
    sleep_ms 500
  done

  return 1
}

open_nav_tab() {
  local label="$1"
  local marker="$2"
  local marker_mode="${3:-contains}"

  bring_app_to_foreground
  wait_for_ui_text "$label" 12 exact bottom-most || {
    err "Navigation label '$label' is not visible"
    return 1
  }
  tap_ui_text "$label" exact bottom-most || return 1

  if [[ -n "$marker" ]]; then
    wait_for_ui_text "$marker" 12 "$marker_mode" || {
      err "Did not reach expected screen marker '$marker' after tapping '$label'"
      return 1
    }
  fi
}

tap_first_device_entry() {
  local match
  local x
  local y
  local label

  match=$(dump_ui_xml | python3 -c '
import re
import sys
import xml.etree.ElementTree as ET

xml_text = sys.stdin.read().strip()
if not xml_text:
    sys.exit(1)

root = ET.fromstring(xml_text)
static_texts = {
    "OBD-II Connection",
    "Disconnected",
    "Connected",
    "Connecting...",
    "Scanning...",
    "Find OBD Adapters",
    "Scan for ELM327/OBD-II devices",
    "Scan",
    "Available Devices",
    "No devices found. Start scanning.",
    "Disconnect",
    "Dashboard",
    "Alerts",
    "Camera",
    "OBD",
    "LED",
    "Settings",
}
patterns = [
    re.compile(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", re.I),
    re.compile(r"elm|obd|obdii|obd2|vgate|v-link|car scanner", re.I),
    re.compile(r"unknown device", re.I),
]
candidates = []

for node in root.iter("node"):
    text = (node.attrib.get("text") or "").strip()
    desc = (node.attrib.get("content-desc") or "").strip()
    haystack = text or desc
    if not haystack or haystack in static_texts:
        continue

    bounds = [int(value) for value in re.findall(r"\d+", node.attrib.get("bounds", ""))]
    if len(bounds) != 4:
        continue

    x = (bounds[0] + bounds[2]) // 2
    y = (bounds[1] + bounds[3]) // 2
    if not (850 <= y <= 1550):
        continue

    if any(pattern.search(haystack) for pattern in patterns):
        candidates.append((y, x, haystack))

if not candidates:
    sys.exit(1)

candidates.sort()
chosen = candidates[0]
print(f"{chosen[1]} {chosen[0]} {chosen[2]}")
' 
  ) || return 1

  read -r x y label <<<"$match"
  log "Selecting device entry: $label"
  adb -s "$DEVICE_SERIAL" shell input tap "$x" "$y"
  sleep_ms 1500
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

    log "Granting runtime permissions..."
    grant_runtime_permissions
    
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
  collapse_status_bar

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
  sleep_ms
}

adb_swipe() {
  local x1="$1" y1="$2" x2="$3" y2="$4"
  adb -s "$DEVICE_SERIAL" shell input swipe "$x1" "$y1" "$x2" "$y2"
  sleep_ms
}

start_logcat() {
  [[ "$DO_LOGS" == "0" ]] && return
  
  LOGCAT_FILE="$OUTPUT_DIR/logs/logcat.txt"
  adb -s "$DEVICE_SERIAL" logcat -c >/dev/null 2>&1 || true
  log "Logcat buffer cleared"
}

stop_logcat() {
  [[ "$DO_LOGS" == "0" ]] && return

  local pid
  pid=$(adb -s "$DEVICE_SERIAL" shell pidof -s "$PACKAGE_NAME" 2>/dev/null | tr -d '\r')

  if [[ -n "$pid" ]]; then
    adb -s "$DEVICE_SERIAL" logcat -d -v time --pid="$pid" >"$LOGCAT_FILE" 2>&1 || true
  else
    adb -s "$DEVICE_SERIAL" logcat -d -v time >"$LOGCAT_FILE" 2>&1 || true
  fi

  log "Logcat captured: $LOGCAT_FILE"
}

scenario_dashboard() {
  log "Scenario: dashboard"
  open_nav_tab "Dashboard" "Start Service" exact || return 1
  take_screenshot "dashboard_initial"
  sleep 2
  take_screenshot "dashboard_telemetry"
}

scenario_ble_scan() {
  log "Scenario: BLE scan"
  open_nav_tab "OBD" "OBD-II Connection" exact || return 1
  if ui_has_text "Scan" exact; then
    tap_ui_text "Scan" exact || return 1
    wait_for_ui_text "Scanning..." 10 exact || sleep_ms 3000
  else
    log "Scan button not visible; capturing current OBD screen"
  fi
  take_screenshot "ble_scan_screen"
}

scenario_obd_pairing() {
  log "Scenario: OBD pairing"
  open_nav_tab "OBD" "OBD-II Connection" exact || return 1
  if ui_has_text "Scan" exact; then
    tap_ui_text "Scan" exact || return 1
    sleep_ms 4000
  fi
  if ! tap_first_device_entry; then
    log "No discoverable OBD device found; skipping pairing tap"
  else
    wait_for_ui_text "Connected" 20 exact || sleep_ms 5000
  fi
  take_screenshot "obd_pairing"
}

scenario_settings() {
  log "Scenario: settings"
  open_nav_tab "Settings" "Save VIN" exact || return 1
  take_screenshot "settings"
}

scenario_anpr() {
  log "Scenario: ANPR"
  open_nav_tab "Camera" "" || return 1
  sleep_ms 2500
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
  grant_runtime_permissions

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
  ensure_python3
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
