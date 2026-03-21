#!/usr/bin/env bash
# Example subagent task spawners for MIA Android testing

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

log() { echo "[$(date +'%H:%M:%S')] $*"; }

# Check if sessions_spawn is available
has_sessions_spawn() {
  command -v sessions_spawn >/dev/null 2>&1
}

# Task 1: Analyze logcat from test run
spawn_logcat_analyzer() {
  local logcat_file="${1:?logcat_file required}"
  local scenario="${2:-full-flow}"
  local device="${3:-unknown}"
  
  has_sessions_spawn || {
    echo "ERROR: sessions_spawn not available"
    return 1
  }
  
  log "Spawning logcat analyzer..."
  
  sessions_spawn --label "logcat-analyzer-$scenario" --task "
  Analyze MIA Android app logcat for errors and issues.
  
  Test Scenario: $scenario
  Device: $device
  Logcat Source: $logcat_file
  
  Read the logcat file and identify:
  
  1. **Crashes** (critical):
     - Pattern: AndroidRuntime: FATAL EXCEPTION
     - Extract: Exception type, stack trace
  
  2. **Permission Errors** (high):
     - Pattern: Permission denied, PermissionException, PERMISSION_DENIED
     - Extract: Which permission, when it failed
  
  3. **BLE/Bluetooth Errors** (high):
     - Pattern: BLEManager:*, BluetoothAdapter:*, Bluetooth.*Error
     - Extract: Connection failures, scan timeouts, GATT errors
  
  4. **Network/WebSocket Errors** (high):
     - Pattern: WebSocketClient:*, Retrofit:*, timeout, connection refused
     - Extract: Endpoint, timeout duration, error code
  
  5. **OBD Protocol Errors** (medium):
     - Pattern: OBDManager:*, ELM327:*, OBD.*timeout
     - Extract: Command, response, timeout details
  
  6. **Memory/ANR Warnings** (medium):
     - Pattern: Low memory, ANR, OutOfMemory
     - Extract: Available memory, process name
  
  7. **Application-level Errors** (low):
     - Pattern: cz.mia.app:*, Dashboard:*, Settings:*, ANPR:*
     - Extract: Component, error message
  
  **Output Format (JSON):**
  {
    \"scenario\": \"$scenario\",
    \"device\": \"$device\",
    \"timestamp\": \"ISO-8601\",
    \"summary\": {
      \"status\": \"pass|fail\",
      \"crash_count\": <int>,
      \"error_count\": <int>,
      \"warning_count\": <int>
    },
    \"errors\": [
      {
        \"severity\": \"critical|high|medium|low\",
        \"type\": \"crash|permission|ble|network|obd|memory|app\",
        \"component\": \"ComponentName\",
        \"message\": \"Error message\",
        \"timestamp\": \"HH:MM:SS.mmm\",
        \"stacktrace\": \"...\" (if available)
      }
    ],
    \"recommendations\": [
      \"Check <component> in code\",
      \"Verify <permission> granted\",
      \"Review BLE connection timeout settings\"
    ]
  }
  
  Be thorough and specific. Include line numbers/timestamps from logcat.
  "
}

# Task 2: Verify ADB command execution
spawn_adb_command_verifier() {
  local device="${1:?device required}"
  local command="${2:?command required}"
  
  has_sessions_spawn || {
    echo "ERROR: sessions_spawn not available"
    return 1
  }
  
  log "Spawning ADB command verifier..."
  
  sessions_spawn --label "adb-verifier-$device" --task "
  Verify ADB command execution on Android device.
  
  Device: $device
  Command: $command
  
  Execute via ADB and evaluate:
  
  1. **Connectivity**:
     - Can device be reached?
     - Is USB/Network connection stable?
     - Any disconnects?
  
  2. **Command Execution**:
     - Did command succeed?
     - Exit code (0 = success)
     - Any stderr output?
  
  3. **Performance**:
     - How long did it take?
     - Was it within expected range?
  
  4. **Side Effects**:
     - Did the device state change as expected?
     - Any unintended consequences?
  
  **Output Format (JSON):**
  {
    \"device\": \"$device\",
    \"command\": \"$command\",
    \"timestamp\": \"ISO-8601\",
    \"status\": \"success|timeout|error\",
    \"exit_code\": <int>,
    \"duration_ms\": <int>,
    \"stdout\": \"...\",
    \"stderr\": \"...\",
    \"connectivity\": {
      \"available\": true|false,
      \"disconnects\": <int>
    },
    \"recommendations\": [\"action 1\", \"action 2\"]
  }
  
  Be detailed about any errors or warnings.
  "
}

# Task 3: Compare screenshots (visual regression)
spawn_screenshot_comparator() {
  local before_dir="${1:?before_dir required}"
  local after_dir="${2:?after_dir required}"
  
  has_sessions_spawn || {
    echo "ERROR: sessions_spawn not available"
    return 1
  }
  
  log "Spawning screenshot comparator..."
  
  sessions_spawn --label "screenshot-comparator" --task "
  Compare before/after screenshots from Android test.
  
  Before: $before_dir
  After: $after_dir
  
  Analyze for visual changes:
  
  1. **UI State Changes**:
     - Did buttons appear/disappear?
     - Did text change?
     - Did layout shift?
  
  2. **Data Rendering**:
     - Are gauges displaying values?
     - Are lists populated?
     - Are errors shown?
  
  3. **Visual Issues**:
     - Any layout glitches?
     - Text truncation or overlap?
     - Rendering artifacts?
  
  4. **Consistency**:
     - Does it match expected design?
     - Are colors correct?
     - Font sizes appropriate?
  
  **Output Format (JSON):**
  {
    \"before_count\": <int>,
    \"after_count\": <int>,
    \"changes\": [
      {
        \"file\": \"screenshot_name\",
        \"type\": \"ui_change|data_update|visual_issue\",
        \"description\": \"What changed\",
        \"severity\": \"critical|high|medium|low\"
      }
    ],
    \"recommendations\": [\"action 1\", \"action 2\"]
  }
  
  Be specific about visual changes observed.
  "
}

# Task 4: Performance analysis from logcat
spawn_performance_analyzer() {
  local logcat_file="${1:?logcat_file required}"
  
  has_sessions_spawn || {
    echo "ERROR: sessions_spawn not available"
    return 1
  }
  
  log "Spawning performance analyzer..."
  
  sessions_spawn --label "performance-analyzer" --task "
  Analyze MIA Android app performance from logcat.
  
  Source: $logcat_file
  
  Look for performance metrics:
  
  1. **Startup Time**:
     - Time from app launch to first UI render
     - Look for lifecycle events (onCreate, onResume)
  
  2. **Frame Rate / Jank**:
     - Dropped frames (Choreographer: Skipped frames)
     - Slow frames (>16ms for 60fps)
  
  3. **Memory Usage**:
     - Initial memory consumption
     - Memory growth over time
     - GC events and pauses
  
  4. **CPU Usage**:
     - High CPU threads
     - Long-running operations
  
  5. **I/O Operations**:
     - File access patterns
     - Database queries
     - Network requests
  
  6. **Thread Activity**:
     - Thread creation/destruction
     - Main thread blocking
  
  **Output Format (JSON):**
  {
    \"metrics\": {
      \"startup_time_ms\": <int>,
      \"initial_memory_mb\": <float>,
      \"peak_memory_mb\": <float>,
      \"frame_drops\": <int>,
      \"gc_pauses_ms\": [<int>, ...]
    },
    \"issues\": [
      {
        \"metric\": \"startup_time\",
        \"value\": 3500,
        \"threshold\": 3000,
        \"status\": \"exceeds\",
        \"recommendation\": \"Profile startup operations\"
      }
    ],
    \"summary\": \"Performance assessment\"
  }
  
  Extract actual numbers from logcat.
  "
}

# Task 5: Full test report generator
spawn_test_report_generator() {
  local artifact_dir="${1:?artifact_dir required}"
  local device="${2:?device required}"
  local scenario="${3:?scenario required}"
  
  has_sessions_spawn || {
    echo "ERROR: sessions_spawn not available"
    return 1
  }
  
  log "Spawning test report generator..."
  
  sessions_spawn --label "test-reporter" --task "
  Generate comprehensive MIA Android test report.
  
  Artifact Directory: $artifact_dir
  Device: $device
  Scenario: $scenario
  
  Aggregate all test data:
  
  1. **Test Execution**:
     - Start/end timestamps
     - Total duration
     - Pass/fail status
  
  2. **Screenshots**:
     - Count and list
     - Any visual anomalies?
  
  3. **Logcat Analysis**:
     - Error summary
     - Performance metrics
     - Memory/CPU usage
  
  4. **Test Verdict**:
     - Overall PASS/FAIL
     - Critical issues blocking release?
     - Non-blocking warnings?
  
  5. **Recommendations**:
     - What needs fixing?
     - What's working well?
     - Next steps?
  
  **Output Format (Markdown):**
  # Test Report: $scenario
  
  ## Summary
  - Status: PASS | FAIL
  - Duration: Xm Ys
  - Device: $device
  
  ## Results
  - Screenshots: N captured
  - Errors: N found
  - Warnings: N found
  
  ## Issues
  - [If any]
  
  ## Recommendations
  - [Next steps]
  
  Make it readable and actionable.
  "
}

# Usage
main() {
  local task="${1:-help}"
  
  case "$task" in
    logcat)
      spawn_logcat_analyzer "$2" "${3:-full-flow}" "${4:-unknown}"
      ;;
    adb)
      spawn_adb_command_verifier "$2" "$3"
      ;;
    screenshots)
      spawn_screenshot_comparator "$2" "$3"
      ;;
    performance)
      spawn_performance_analyzer "$2"
      ;;
    report)
      spawn_test_report_generator "$2" "${3:--}" "${4:-full-flow}"
      ;;
    all)
      # Spawn all analyzers
      local artifact_dir="$2"
      spawn_logcat_analyzer "$artifact_dir/logs/logcat.txt" "full-flow" "device"
      spawn_performance_analyzer "$artifact_dir/logs/logcat.txt"
      spawn_test_report_generator "$artifact_dir" "device" "full-flow"
      log "All analyzers spawned (async)"
      ;;
    *)
      cat <<'EOF'
Usage: spawn-test-tasks.sh <task> [args...]

Tasks:
  logcat <logcat_file> [scenario] [device]
    Analyze logcat for errors, crashes, permissions
  
  adb <device> <command>
    Verify ADB command execution
  
  screenshots <before_dir> <after_dir>
    Compare before/after screenshots
  
  performance <logcat_file>
    Analyze performance metrics
  
  report <artifact_dir> [device] [scenario]
    Generate comprehensive test report
  
  all <artifact_dir>
    Spawn all analyzers for artifact directory

Examples:
  ./spawn-test-tasks.sh logcat apps/android/test-artifacts/.../logs/logcat.txt
  ./spawn-test-tasks.sh report apps/android/test-artifacts/20250218_084500
  ./spawn-test-tasks.sh all apps/android/test-artifacts/20250218_084500
EOF
      ;;
  esac
}

main "$@"
