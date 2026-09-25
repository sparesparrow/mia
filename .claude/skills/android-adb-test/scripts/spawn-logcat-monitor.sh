#!/usr/bin/env bash
# Spawn readonly logcat monitor subagent
# Analyzes logcat for errors, crashes, warnings

DEVICE_SERIAL="${1:-}"
DURATION_SEC="${2:-30}"
OUTPUT_FILE="${3:-logcat-analysis.json}"

[[ -z "$DEVICE_SERIAL" ]] && {
  echo "Usage: $0 <device_serial> [duration_sec] [output_file]"
  exit 1
}

# Capture logcat
LOGCAT_TMP=$(mktemp)
timeout "$DURATION_SEC" adb -s "$DEVICE_SERIAL" logcat -v time >"$LOGCAT_TMP" 2>&1 || true

# Invoke via sessions_spawn if in OpenClaw context
if command -v sessions_spawn >/dev/null 2>&1; then
  sessions_spawn --task "
  Analyze MIA Android app logcat output for errors and issues.
  
  Device: $DEVICE_SERIAL
  Duration: ${DURATION_SEC}s
  
  Raw logcat (below):
  \`\`\`
  $(cat "$LOGCAT_TMP")
  \`\`\`
  
  Analyze for:
  1. Crashes (AndroidRuntime: FATAL EXCEPTION)
  2. Permission denials (Permission denied, PermissionException)
  3. BLE/Bluetooth errors (BLEManager, Bluetooth adapter)
  4. Network errors (WebSocket, timeout, connection refused)
  5. OBD protocol errors (ELM327, SEARCHING, invalid response)
  6. Memory warnings (Low memory, ANR)
  7. Application errors (cz.mia.app)
  
  Return JSON report with:
  {
    \"status\": \"pass|fail\",
    \"crash_count\": <int>,
    \"error_count\": <int>,
    \"warning_count\": <int>,
    \"errors\": [
      {\"type\": \"crash|permission|ble|network|obd|memory|other\",
       \"message\": \"...\",
       \"timestamp\": \"HH:MM:SS\",
       \"severity\": \"error|warning\"}
    ],
    \"recommendations\": [\"action 1\", \"action 2\"]
  }
  
  Be thorough and specific.
  "
else
  # Fallback: analyze locally if not in OpenClaw
  echo "Analyzing logcat locally..."
  
  CRASH_COUNT=$(grep -c "AndroidRuntime: FATAL" "$LOGCAT_TMP" || true)
  ERROR_COUNT=$(grep -c "^E/" "$LOGCAT_TMP" || true)
  WARN_COUNT=$(grep -c "^W/" "$LOGCAT_TMP" || true)
  
  STATUS="pass"
  [[ $CRASH_COUNT -gt 0 ]] && STATUS="fail"
  
  cat >"$OUTPUT_FILE" <<EOF
{
  "status": "$STATUS",
  "duration_sec": $DURATION_SEC,
  "crash_count": $CRASH_COUNT,
  "error_count": $ERROR_COUNT,
  "warning_count": $WARN_COUNT,
  "output_file": "$OUTPUT_FILE"
}
EOF
  
  echo "Report: $OUTPUT_FILE"
fi

rm -f "$LOGCAT_TMP"
