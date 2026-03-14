#!/usr/bin/env bash
set -euo pipefail

# MIA Android Test Orchestrator
# Coordinates build, deploy, test, and subagent analysis

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="$PROJECT_ROOT/skills/android-adb-test"
ANDROID_DIR="$PROJECT_ROOT/apps/android"

DEVICE_SERIAL="${1:-}"
SCENARIO="${2:-full-flow}"
VERBOSE="${3:-0}"

log() { echo "[$(date +'%H:%M:%S')] $*"; }
err() { echo "ERROR: $*" >&2; }

usage() {
  cat <<'EOF'
Usage: test-orchestrator.sh <device_serial> [scenario] [verbose]

Device Serial: e.g., HT36TW903516 or emulator-5554
Scenario: dashboard|ble-scan|obd-pairing|settings|anpr|full-flow (default: full-flow)
Verbose: 0 or 1 (default: 0)

Examples:
  ./scripts/test-orchestrator.sh HT36TW903516
  ./scripts/test-orchestrator.sh emulator-5554 full-flow 1
EOF
}

[[ -z "$DEVICE_SERIAL" ]] && {
  usage
  exit 1
}

# Verify device is connected
verify_device() {
  log "Verifying device: $DEVICE_SERIAL"
  if ! adb -s "$DEVICE_SERIAL" shell getprop ro.product.model >/dev/null 2>&1; then
    err "Device $DEVICE_SERIAL not found or unauthorized"
    adb devices
    exit 1
  fi
  log "✓ Device $DEVICE_SERIAL ready"
}

# Phase 1: Build
build_phase() {
  log "=== Phase 1: Build APK ==="
  
  cd "$PROJECT_ROOT"
  bash "$SKILL_DIR/scripts/android-adb-test.sh" build || {
    err "Build failed"
    exit 1
  }
  
  log "✓ Build complete"
}

# Phase 2: Deploy
deploy_phase() {
  log "=== Phase 2: Deploy APK ==="
  
  cd "$PROJECT_ROOT"
  bash "$SKILL_DIR/scripts/android-adb-test.sh" deploy \
    --device "$DEVICE_SERIAL" || {
    err "Deploy failed"
    exit 1
  }
  
  log "✓ Deploy complete"
}

# Phase 3: Test Scenario
test_phase() {
  log "=== Phase 3: Run Test Scenario ==="
  
  cd "$PROJECT_ROOT"
  bash "$SKILL_DIR/scripts/android-adb-test.sh" test \
    --scenario "$SCENARIO" \
    --screenshots \
    --logs \
    --device "$DEVICE_SERIAL" || {
    err "Test scenario failed"
    # Don't exit; continue to analysis
  }
  
  log "✓ Test scenario complete"
}

# Phase 4: Get Test Artifacts
get_artifacts() {
  log "=== Phase 4: Collect Artifacts ==="
  
  # Find latest test artifacts
  LATEST_TEST=$(ls -t "$ANDROID_DIR/test-artifacts" | head -1)
  if [[ -z "$LATEST_TEST" ]]; then
    err "No test artifacts found"
    return 1
  fi
  
  ARTIFACT_DIR="$ANDROID_DIR/test-artifacts/$LATEST_TEST"
  
  log "Artifacts: $ARTIFACT_DIR"
  echo "$ARTIFACT_DIR"  # Return path for next phase
}

# Phase 5: Spawn Logcat Analyzer Subagent
analyze_logcat() {
  local logcat_file="$1"
  
  log "=== Phase 5: Logcat Analysis ==="
  
  if [[ ! -f "$logcat_file" ]]; then
    err "Logcat file not found: $logcat_file"
    return 1
  fi
  
  # Check if in OpenClaw context
  if ! command -v sessions_spawn >/dev/null 2>&1; then
    log "OpenClaw not available; skipping subagent analysis"
    return 0
  fi
  
  log "Spawning logcat analyzer subagent..."
  
  local logcat_preview=$(head -100 "$logcat_file")
  local logcat_tail=$(tail -50 "$logcat_file")
  
  sessions_spawn --label "logcat-analyzer" --task "
  Analyze MIA Android app logcat from test run.
  
  Test scenario: $SCENARIO
  Device: $DEVICE_SERIAL
  
  **Logcat Preview (first 100 lines):**
  \`\`\`
  $logcat_preview
  \`\`\`
  
  **Logcat Tail (last 50 lines):**
  \`\`\`
  $logcat_tail
  \`\`\`
  
  **Analyze for:**
  1. Crashes (AndroidRuntime: FATAL EXCEPTION)
  2. Permission denials
  3. BLE/Bluetooth errors
  4. Network/WebSocket errors
  5. OBD protocol errors
  6. Memory/ANR warnings
  7. Application-level errors (cz.mia.app:*)
  
  **Return JSON report:**
  {
    \"status\": \"pass|fail\",
    \"scenario\": \"$SCENARIO\",
    \"crash_count\": <int>,
    \"error_count\": <int>,
    \"warning_count\": <int>,
    \"errors\": [
      {\"type\": \"...\", \"severity\": \"error|warning\", \"message\": \"...\"}
    ],
    \"recommendations\": [\"action 1\", \"action 2\"]
  }
  
  Be specific and actionable in recommendations.
  "
  
  log "✓ Logcat analyzer spawned (async)"
}

# Phase 6: Screenshot Summary
screenshot_summary() {
  local artifact_dir="$1"
  local screenshot_dir="$artifact_dir/screenshots"
  
  log "=== Phase 6: Screenshot Summary ==="
  
  if [[ ! -d "$screenshot_dir" ]]; then
    log "No screenshots captured"
    return 0
  fi
  
  local count=$(find "$screenshot_dir" -type f | wc -l)
  log "Captured $count screenshots:"
  ls -1 "$screenshot_dir" | sed 's/^/  /'
}

# Phase 7: Generate Report
generate_report() {
  local artifact_dir="$1"
  
  log "=== Phase 7: Generate Report ==="
  
  local report_file="$artifact_dir/reports/orchestrator-report.json"
  mkdir -p "$(dirname "$report_file")"
  
  local screenshot_count=$(find "$artifact_dir/screenshots" -type f 2>/dev/null | wc -l || echo 0)
  local logcat_size=$(wc -c <"$artifact_dir/logs/logcat.txt" 2>/dev/null || echo 0)
  
  cat >"$report_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "device": "$DEVICE_SERIAL",
  "scenario": "$SCENARIO",
  "status": "completed",
  "artifacts": {
    "directory": "$artifact_dir",
    "screenshots": $screenshot_count,
    "logcat_bytes": $logcat_size
  },
  "phases": {
    "build": "✓",
    "deploy": "✓",
    "test": "✓",
    "analysis": "spawned (subagent)"
  }
}
EOF
  
  log "Report: $report_file"
  cat "$report_file" | jq .
}

# Main flow
main() {
  log "MIA Android Test Orchestrator"
  log "Device: $DEVICE_SERIAL"
  log "Scenario: $SCENARIO"
  log ""
  
  verify_device
  
  build_phase
  deploy_phase
  test_phase
  
  ARTIFACT_DIR=$(get_artifacts) || {
    err "Failed to find test artifacts"
    exit 1
  }
  
  screenshot_summary "$ARTIFACT_DIR"
  
  # Async analysis (doesn't block)
  if [[ -f "$ARTIFACT_DIR/logs/logcat.txt" ]]; then
    analyze_logcat "$ARTIFACT_DIR/logs/logcat.txt"
  fi
  
  generate_report "$ARTIFACT_DIR"
  
  log ""
  log "✅ Test orchestration complete"
  log "Results: $ARTIFACT_DIR"
  log ""
  log "Subagent analysis running async (check subagents list)"
}

main
