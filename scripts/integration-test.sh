#!/usr/bin/env bash
set -euo pipefail

# MIA Integration Test Orchestrator
# Tests all 3 components: Android App + RPi Backend + ESP32 Firmware
#
# Usage: integration-test.sh [--device ADB_SERIAL] [--esp32-port PORT] [--duration SEC]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
ADB_SERIAL=""
ESP32_PORT="/dev/ttyACM1"  # Espressif ESP32-S3
ESP32_BAUD="115200"
DURATION=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$PROJECT_ROOT/test-artifacts/integration/$TIMESTAMP"

log() { echo "[$(date +'%H:%M:%S')] $*"; }
err() { echo "ERROR: $*" >&2; }

usage() {
  cat <<'EOF'
Usage: integration-test.sh [options]

Options:
  --device SERIAL       ADB device serial (auto-detect if omitted)
  --esp32-port PORT     ESP32 serial port (default: /dev/ttyACM1)
  --esp32-baud BAUD     ESP32 baud rate (default: 115200)
  --duration SEC        Test duration in seconds (default: 30)
  --output DIR          Output directory
  --skip-flash          Skip ESP32 firmware flash
  --skip-rpi            Skip RPi backend test
  --skip-android        Skip Android app test
  -h, --help            Show help

Examples:
  ./scripts/integration-test.sh
  ./scripts/integration-test.sh --device HT36TW903516 --duration 60
  ./scripts/integration-test.sh --skip-flash --skip-rpi
EOF
}

SKIP_FLASH=0
SKIP_RPI=0
SKIP_ANDROID=0

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --device) ADB_SERIAL="$2"; shift 2 ;;
      --esp32-port) ESP32_PORT="$2"; shift 2 ;;
      --esp32-baud) ESP32_BAUD="$2"; shift 2 ;;
      --duration) DURATION="$2"; shift 2 ;;
      --output) OUTPUT_DIR="$2"; shift 2 ;;
      --skip-flash) SKIP_FLASH=1; shift ;;
      --skip-rpi) SKIP_RPI=1; shift ;;
      --skip-android) SKIP_ANDROID=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) err "Unknown: $1"; exit 1 ;;
    esac
  done
}

setup() {
  mkdir -p "$OUTPUT_DIR"/{esp32,rpi,android,reports}
  log "Output: $OUTPUT_DIR"
}

# ─── Phase 1: ESP32 ────────────────────────────────────────────────────

detect_esp32() {
  if [[ ! -e "$ESP32_PORT" ]]; then
    # Auto-detect Espressif device
    for dev in /dev/ttyACM* /dev/ttyUSB*; do
      [[ -e "$dev" ]] || continue
      if udevadm info -q property "$dev" 2>/dev/null | grep -q "Espressif"; then
        ESP32_PORT="$dev"
        log "Auto-detected ESP32: $ESP32_PORT"
        return 0
      fi
    done
    err "No ESP32 found"
    return 1
  fi
  log "ESP32 port: $ESP32_PORT"
}

flash_esp32() {
  [[ $SKIP_FLASH -eq 1 ]] && { log "Skipping ESP32 flash"; return 0; }
  
  log "=== Phase 1a: Flash ESP32 Firmware ==="
  cd "$PROJECT_ROOT/apps/esp32"
  
  if [[ -f platformio.ini ]]; then
    pio run --target upload --upload-port "$ESP32_PORT" \
      > "$OUTPUT_DIR/esp32/flash.log" 2>&1 && {
      log "✓ ESP32 flash successful"
    } || {
      err "ESP32 flash failed. See $OUTPUT_DIR/esp32/flash.log"
      return 1
    }
  else
    log "No platformio.ini — skipping flash"
  fi
}

monitor_esp32() {
  log "=== Phase 1b: Monitor ESP32 Serial ($DURATION sec) ==="
  
  local logfile="$OUTPUT_DIR/esp32/serial.log"
  
  # Configure port
  stty -F "$ESP32_PORT" "$ESP32_BAUD" cs8 -cstopb -parenb raw -echo 2>/dev/null || true
  
  # Capture serial output in background
  timeout "$DURATION" stdbuf -oL cat "$ESP32_PORT" 2>/dev/null | while IFS= read -r line; do
    echo "[$(date +'%H:%M:%S.%3N')] $line"
  done > "$logfile" 2>&1 &
  ESP32_MONITOR_PID=$!
  
  log "ESP32 monitor started (PID: $ESP32_MONITOR_PID)"
}

stop_esp32_monitor() {
  [[ -z "${ESP32_MONITOR_PID:-}" ]] && return
  kill "$ESP32_MONITOR_PID" 2>/dev/null || true
  wait "$ESP32_MONITOR_PID" 2>/dev/null || true
  
  local logfile="$OUTPUT_DIR/esp32/serial.log"
  local lines=$(wc -l < "$logfile" 2>/dev/null || echo 0)
  log "ESP32 serial: $lines lines captured"
}

analyze_esp32() {
  local logfile="$OUTPUT_DIR/esp32/serial.log"
  local report="$OUTPUT_DIR/esp32/analysis.json"
  
  [[ ! -f "$logfile" ]] && { echo '{"status":"skipped"}' > "$report"; return; }
  
  local boot_ok=$(grep -c "wifi.*GOT_IP\|Setup complete\|Ready" "$logfile" 2>/dev/null || echo 0)
  local crashes=$(grep -c "Guru Meditation\|panic\|abort\|task_wdt" "$logfile" 2>/dev/null || echo 0)
  local wifi_err=$(grep -c "STA_DISCONNECTED\|wifi.*fail" "$logfile" 2>/dev/null || echo 0)
  local errors=$(grep -c "^.*E (" "$logfile" 2>/dev/null || echo 0)
  
  local status="pass"
  [[ $crashes -gt 0 ]] && status="fail"
  [[ $boot_ok -eq 0 && $(wc -l < "$logfile") -gt 5 ]] && status="warning"
  
  cat > "$report" <<EOF
{
  "component": "esp32",
  "status": "$status",
  "port": "$ESP32_PORT",
  "lines_captured": $(wc -l < "$logfile"),
  "boot_success": $([[ $boot_ok -gt 0 ]] && echo true || echo false),
  "crash_count": $crashes,
  "wifi_errors": $wifi_err,
  "error_count": $errors
}
EOF
  log "ESP32 analysis: $status (crashes=$crashes, errors=$errors)"
}

# ─── Phase 2: RPi Backend ──────────────────────────────────────────────

test_rpi_backend() {
  [[ $SKIP_RPI -eq 1 ]] && { log "Skipping RPi backend"; return 0; }
  
  log "=== Phase 2: Test RPi Backend ==="
  
  local rpi_dir="$PROJECT_ROOT/apps/rpi-backend/py-api"
  local report="$OUTPUT_DIR/rpi/analysis.json"
  
  if [[ ! -d "$rpi_dir" ]]; then
    log "RPi backend not found at $rpi_dir — skipping"
    echo '{"status":"skipped","reason":"directory not found"}' > "$report"
    return 0
  fi
  
  # Check if backend is already running
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    log "RPi backend already running"
    local health=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{}')
    echo "{\"status\":\"pass\",\"running\":true,\"health\":$health}" > "$report"
    return 0
  fi
  
  # Try starting it
  cd "$rpi_dir"
  if [[ -f "requirements.txt" ]]; then
    log "Checking RPi backend dependencies..."
    python3 -c "import fastapi" 2>/dev/null || {
      log "FastAPI not installed — skipping RPi backend test"
      echo '{"status":"skipped","reason":"dependencies not installed"}' > "$report"
      return 0
    }
  fi
  
  # Start backend temporarily
  log "Starting RPi backend..."
  python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 \
    > "$OUTPUT_DIR/rpi/backend.log" 2>&1 &
  RPI_PID=$!
  
  sleep 5  # Wait for startup
  
  if kill -0 "$RPI_PID" 2>/dev/null; then
    local health=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{"error":"no health endpoint"}')
    log "✓ RPi backend started (PID: $RPI_PID)"
    echo "{\"status\":\"pass\",\"running\":true,\"pid\":$RPI_PID,\"health\":$health}" > "$report"
  else
    err "RPi backend failed to start"
    echo '{"status":"fail","reason":"startup failed"}' > "$report"
  fi
}

stop_rpi_backend() {
  [[ -z "${RPI_PID:-}" ]] && return
  kill "$RPI_PID" 2>/dev/null || true
  log "RPi backend stopped"
}

# ─── Phase 3: Android App ──────────────────────────────────────────────

detect_android() {
  [[ $SKIP_ANDROID -eq 1 ]] && return 1
  
  if [[ -z "$ADB_SERIAL" ]]; then
    ADB_SERIAL=$(adb devices | awk '/\tdevice$/{print $1}' | head -1)
  fi
  
  [[ -z "$ADB_SERIAL" ]] && {
    log "No Android device found — skipping"
    return 1
  }
  
  log "Android device: $ADB_SERIAL"
}

test_android() {
  [[ $SKIP_ANDROID -eq 1 ]] && { log "Skipping Android test"; return 0; }
  detect_android || {
    echo '{"status":"skipped","reason":"no device"}' > "$OUTPUT_DIR/android/analysis.json"
    return 0
  }
  
  log "=== Phase 3: Test Android App ==="
  
  local apk="$PROJECT_ROOT/apps/android/app/build/outputs/apk/debug/app-debug.apk"
  local report="$OUTPUT_DIR/android/analysis.json"
  
  if [[ ! -f "$apk" ]]; then
    log "No APK found — skipping Android test"
    echo '{"status":"skipped","reason":"no APK"}' > "$report"
    return 0
  fi
  
  # Deploy
  log "Installing APK..."
  adb -s "$ADB_SERIAL" install -r "$apk" > "$OUTPUT_DIR/android/install.log" 2>&1 || {
    err "APK install failed"
    echo '{"status":"fail","reason":"install failed"}' > "$report"
    return 1
  }
  
  # Launch
  log "Launching app..."
  adb -s "$ADB_SERIAL" shell am start -n cz.mia.app/.MainActivity 2>&1 || true
  sleep 3
  
  # Screenshot (use shell method for older devices where exec-out fails)
  adb -s "$ADB_SERIAL" shell screencap -p /sdcard/mia-test.png 2>/dev/null || true
  adb -s "$ADB_SERIAL" pull /sdcard/mia-test.png "$OUTPUT_DIR/android/launch.png" 2>/dev/null || true
  
  # Capture logcat
  local pid=$(adb -s "$ADB_SERIAL" shell pidof -s cz.mia.app 2>/dev/null || echo "")
  if [[ -n "$pid" ]]; then
    log "App running (PID: $pid)"
    timeout "$DURATION" adb -s "$ADB_SERIAL" logcat --pid="$pid" -v time \
      > "$OUTPUT_DIR/android/logcat.txt" 2>&1 &
    LOGCAT_PID=$!
  else
    log "App not running — capturing all logcat"
    timeout "$DURATION" adb -s "$ADB_SERIAL" logcat -v time \
      > "$OUTPUT_DIR/android/logcat.txt" 2>&1 &
    LOGCAT_PID=$!
  fi
  
  # Wait for test duration
  sleep "$DURATION"
  
  # Final screenshot
  adb -s "$ADB_SERIAL" shell screencap -p /sdcard/mia-test-final.png 2>/dev/null || true
  adb -s "$ADB_SERIAL" pull /sdcard/mia-test-final.png "$OUTPUT_DIR/android/final.png" 2>/dev/null || true
  
  # Stop logcat
  kill "$LOGCAT_PID" 2>/dev/null || true
  
  # Analyze
  local logfile="$OUTPUT_DIR/android/logcat.txt"
  local crashes=$(grep -c "AndroidRuntime: FATAL" "$logfile" 2>/dev/null || echo 0)
  local errors=$(grep -c "^E/" "$logfile" 2>/dev/null || echo 0)
  local ble_ok=$(grep -c "BLEManager.*started\|BLEManager.*connected" "$logfile" 2>/dev/null || echo 0)
  local ws_ok=$(grep -c "WebSocket.*connect" "$logfile" 2>/dev/null || echo 0)
  
  local status="pass"
  [[ $crashes -gt 0 ]] && status="fail"
  [[ -z "$pid" ]] && status="fail"
  
  cat > "$report" <<EOF
{
  "component": "android",
  "status": "$status",
  "device": "$ADB_SERIAL",
  "app_pid": "${pid:-null}",
  "crash_count": $crashes,
  "error_count": $errors,
  "ble_activity": $ble_ok,
  "websocket_activity": $ws_ok,
  "screenshots": ["launch.png", "final.png"],
  "logcat_lines": $(wc -l < "$logfile" 2>/dev/null || echo 0)
}
EOF
  log "Android analysis: $status (crashes=$crashes, errors=$errors)"
}

# ─── Phase 4: Integration Report ───────────────────────────────────────

generate_integration_report() {
  log "=== Phase 4: Integration Report ==="
  
  local report="$OUTPUT_DIR/reports/integration-report.json"
  
  local esp32_status=$(cat "$OUTPUT_DIR/esp32/analysis.json" 2>/dev/null | grep -oP '"status"\s*:\s*"\K[^"]+' || echo "skipped")
  local rpi_status=$(cat "$OUTPUT_DIR/rpi/analysis.json" 2>/dev/null | grep -oP '"status"\s*:\s*"\K[^"]+' || echo "skipped")
  local android_status=$(cat "$OUTPUT_DIR/android/analysis.json" 2>/dev/null | grep -oP '"status"\s*:\s*"\K[^"]+' || echo "skipped")
  
  local overall="pass"
  [[ "$esp32_status" == "fail" || "$rpi_status" == "fail" || "$android_status" == "fail" ]] && overall="fail"
  
  cat > "$report" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "duration_sec": $DURATION,
  "overall_status": "$overall",
  "components": {
    "esp32": {
      "status": "$esp32_status",
      "port": "$ESP32_PORT",
      "report": "esp32/analysis.json"
    },
    "rpi_backend": {
      "status": "$rpi_status",
      "report": "rpi/analysis.json"
    },
    "android": {
      "status": "$android_status",
      "device": "${ADB_SERIAL:-none}",
      "report": "android/analysis.json"
    }
  },
  "artifacts": "$OUTPUT_DIR"
}
EOF
  
  log ""
  log "╔══════════════════════════════════════╗"
  log "║   MIA Integration Test Results       ║"
  log "╠══════════════════════════════════════╣"
  log "║ ESP32:      $esp32_status"
  log "║ RPi Backend: $rpi_status"
  log "║ Android:     $android_status"
  log "║ Overall:     $overall"
  log "╚══════════════════════════════════════╝"
  log ""
  log "Artifacts: $OUTPUT_DIR"
}

# ─── Main ───────────────────────────────────────────────────────────────

cleanup() {
  stop_esp32_monitor
  stop_rpi_backend
  [[ -n "${LOGCAT_PID:-}" ]] && kill "$LOGCAT_PID" 2>/dev/null || true
}
trap cleanup EXIT

main() {
  parse_args "$@"
  setup
  
  log "MIA Integration Test"
  log "Duration: ${DURATION}s per component"
  log ""
  
  # ESP32
  if detect_esp32; then
    flash_esp32 || true
    monitor_esp32
  else
    echo '{"status":"skipped","reason":"no device"}' > "$OUTPUT_DIR/esp32/analysis.json"
  fi
  
  # RPi Backend
  test_rpi_backend
  
  # Android
  test_android
  
  # Wait for monitors
  sleep 2
  stop_esp32_monitor
  
  # Analyze ESP32
  analyze_esp32
  
  # Report
  generate_integration_report
}

main "$@"
