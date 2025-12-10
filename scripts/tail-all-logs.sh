#!/usr/bin/env bash
set -euo pipefail

# AI-SERVIS Multi-Source Log Aggregation and Monitoring
# Aggregates logs from Docker, systemd, Android, Raspberry Pi, and local files

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
ORANGE='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RPI_HOST="${RPI_HOST:-mia@mia.local}"
RPI_SSH_KEY="${RPI_SSH_KEY:-}"

# Options
SOURCES="all"
FILTER_PATTERN=""
EXCLUDE_PATTERN=""
SINCE=""
FOLLOW=true
LINES=50
OUTPUT_FILE=""
NO_COLOR=false
JSON_OUTPUT=false

# Docker containers to monitor
DOCKER_CONTAINERS=(
    "core-orchestrator"
    "ai-audio-assistant"
    "service-discovery"
    "ai-platform-linux"
    "mqtt-broker"
    "postgres"
    "redis"
)

# Systemd services to monitor
SYSTEMD_SERVICES=(
    "mia-api"
    "mia-gpio-worker"
    "mia-serial-bridge"
    "mia-obd-worker"
    "mia-led-monitor"
    "ai-servis"
)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --sources)
            SOURCES="$2"
            shift 2
            ;;
        --filter)
            FILTER_PATTERN="$2"
            shift 2
            ;;
        --exclude)
            EXCLUDE_PATTERN="$2"
            shift 2
            ;;
        --since)
            SINCE="$2"
            shift 2
            ;;
        --follow)
            FOLLOW=true
            shift
            ;;
        --no-follow)
            FOLLOW=false
            shift
            ;;
        --lines)
            LINES="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --no-color)
            NO_COLOR=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [options]

Multi-source log aggregation and monitoring for AI-Servis components.

Options:
  --sources LIST       Comma-separated sources (docker,systemd,android,rpi,files,all)
  --filter PATTERN    Filter logs by regex pattern
  --exclude PATTERN   Exclude logs matching regex pattern
  --since TIME        Show logs since (e.g., "1h", "30m", "2024-01-01")
  --follow            Follow log output in real-time (default: true)
  --no-follow         Don't follow, just show historical logs
  --lines N           Number of historical lines (default: 50)
  --output FILE       Save output to file instead of stdout
  --no-color          Disable colored output
  --json              Output in JSON format
  --help, -h          Show this help message

Examples:
  $0                                    # Monitor all sources
  $0 --sources docker,systemd          # Monitor Docker and systemd only
  $0 --filter "ERROR|FATAL"            # Show only errors
  $0 --since 1h --lines 100            # Last hour, 100 lines
  $0 --json --output logs.json         # JSON output to file
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Color functions
color_docker() {
    if [[ "$NO_COLOR" == false ]]; then
        echo -e "${BLUE}DOCKER${NC}"
    else
        echo "DOCKER"
    fi
}

color_systemd() {
    if [[ "$NO_COLOR" == false ]]; then
        echo -e "${GREEN}SYSTEMD${NC}"
    else
        echo "SYSTEMD"
    fi
}

color_android() {
    if [[ "$NO_COLOR" == false ]]; then
        echo -e "${ORANGE}ANDROID${NC}"
    else
        echo "ANDROID"
    fi
}

color_rpi() {
    if [[ "$NO_COLOR" == false ]]; then
        echo -e "${RED}RPI${NC}"
    else
        echo "RPI"
    fi
}

color_files() {
    if [[ "$NO_COLOR" == false ]]; then
        echo -e "${PURPLE}FILES${NC}"
    else
        echo "FILES"
    fi
}

# Format timestamp
format_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Format log line
format_log_line() {
    local source_type="$1"
    local component="$2"
    local level="$3"
    local message="$4"
    local timestamp=$(format_timestamp)
    
    if [[ "$JSON_OUTPUT" == true ]]; then
        if command -v jq &> /dev/null; then
            jq -n \
                --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                --arg src "$source_type" \
                --arg comp "$component" \
                --arg lvl "$level" \
                --arg msg "$message" \
                '{timestamp: $ts, source: $src, component: $comp, level: $lvl, message: $msg}'
        else
            echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"source\":\"$source_type\",\"component\":\"$component\",\"level\":\"$level\",\"message\":\"$message\"}"
        fi
    else
        echo "[$timestamp] [$source_type:$component] $level: $message"
    fi
}

# Check if source should be monitored
should_monitor_source() {
    local source="$1"
    
    if [[ "$SOURCES" == "all" ]]; then
        return 0
    fi
    
    IFS=',' read -ra SOURCE_ARRAY <<< "$SOURCES"
    for s in "${SOURCE_ARRAY[@]}"; do
        if [[ "$s" == "$source" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Filter log line
filter_log() {
    local line="$1"
    
    if [[ -n "$FILTER_PATTERN" ]]; then
        if ! echo "$line" | grep -qE "$FILTER_PATTERN"; then
            return 1
        fi
    fi
    
    if [[ -n "$EXCLUDE_PATTERN" ]]; then
        if echo "$line" | grep -qE "$EXCLUDE_PATTERN"; then
            return 1
        fi
    fi
    
    return 0
}

# Docker logs
monitor_docker() {
    if ! should_monitor_source "docker"; then
        return 0
    fi
    
    if ! command -v docker &> /dev/null; then
        return 1
    fi
    
    local follow_flag=""
    if [[ "$FOLLOW" == true ]]; then
        follow_flag="-f"
    fi
    
    local since_flag=""
    if [[ -n "$SINCE" ]]; then
        since_flag="--since $SINCE"
    fi
    
    for container in "${DOCKER_CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            docker logs $follow_flag $since_flag --tail "$LINES" "$container" 2>/dev/null | while IFS= read -r line; do
                if filter_log "$line"; then
                    if [[ "$JSON_OUTPUT" == false ]]; then
                        echo "[$(format_timestamp)] [$(color_docker):$container] $line"
                    else
                        format_log_line "docker" "$container" "INFO" "$line"
                    fi
                fi
            done &
        fi
    done
}

# Systemd logs
monitor_systemd() {
    if ! should_monitor_source "systemd"; then
        return 0
    fi
    
    if ! command -v journalctl &> /dev/null; then
        return 1
    fi
    
    local follow_flag=""
    if [[ "$FOLLOW" == true ]]; then
        follow_flag="-f"
    fi
    
    local since_flag=""
    if [[ -n "$SINCE" ]]; then
        since_flag="--since $SINCE"
    fi
    
    for service in "${SYSTEMD_SERVICES[@]}"; do
        if systemctl list-units --type=service --all | grep -q "^${service}"; then
            journalctl $follow_flag $since_flag -u "$service" -n "$LINES" --no-pager 2>/dev/null | while IFS= read -r line; do
                if filter_log "$line"; then
                    if [[ "$JSON_OUTPUT" == false ]]; then
                        echo "[$(format_timestamp)] [$(color_systemd):$service] $line"
                    else
                        format_log_line "systemd" "$service" "INFO" "$line"
                    fi
                fi
            done &
        fi
    done
}

# Android logs
monitor_android() {
    if ! should_monitor_source "android"; then
        return 0
    fi
    
    if ! command -v adb &> /dev/null; then
        return 1
    fi
    
    if ! adb devices 2>/dev/null | grep -q "device$"; then
        return 1
    fi
    
    local follow_flag=""
    if [[ "$FOLLOW" == true ]]; then
        follow_flag="-f"
    fi
    
    # Monitor logcat
    if [[ "$FOLLOW" == true ]]; then
        adb logcat -v time 2>/dev/null | while IFS= read -r line; do
            if filter_log "$line"; then
                if [[ "$JSON_OUTPUT" == false ]]; then
                    echo "[$(format_timestamp)] [$(color_android):logcat] $line"
                else
                    format_log_line "android" "logcat" "INFO" "$line"
                fi
            fi
        done &
    else
        adb logcat -v time -d 2>/dev/null | tail -n "$LINES" | while IFS= read -r line; do
            if filter_log "$line"; then
                if [[ "$JSON_OUTPUT" == false ]]; then
                    echo "[$(format_timestamp)] [$(color_android):logcat] $line"
                else
                    format_log_line "android" "logcat" "INFO" "$line"
                fi
            fi
        done
    fi
    
    # Monitor app-specific logs if available
    if adb shell pm list packages 2>/dev/null | grep -q "cz.mia.app.debug"; then
        if [[ "$FOLLOW" == true ]]; then
            adb logcat -v time -s "cz.mia.app:*" 2>/dev/null | while IFS= read -r line; do
                if filter_log "$line"; then
                    if [[ "$JSON_OUTPUT" == false ]]; then
                        echo "[$(format_timestamp)] [$(color_android):app-logs] $line"
                    else
                        format_log_line "android" "app-logs" "INFO" "$line"
                    fi
                fi
            done &
        else
            adb logcat -v time -s "cz.mia.app:*" -d 2>/dev/null | tail -n "$LINES" | while IFS= read -r line; do
                if filter_log "$line"; then
                    if [[ "$JSON_OUTPUT" == false ]]; then
                        echo "[$(format_timestamp)] [$(color_android):app-logs] $line"
                    else
                        format_log_line "android" "app-logs" "INFO" "$line"
                    fi
                fi
            done
        fi
    fi
}

# Raspberry Pi logs
monitor_rpi() {
    if ! should_monitor_source "rpi"; then
        return 0
    fi
    
    local ssh_cmd="ssh"
    if [[ -n "$RPI_SSH_KEY" ]]; then
        ssh_cmd="ssh -i $RPI_SSH_KEY"
    fi
    
    # Check SSH connection
    if ! $ssh_cmd -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$RPI_HOST" "echo test" &>/dev/null; then
        return 1
    fi
    
    local follow_flag=""
    if [[ "$FOLLOW" == true ]]; then
        follow_flag="-f"
    fi
    
    local since_flag=""
    if [[ -n "$SINCE" ]]; then
        since_flag="--since $SINCE"
    fi
    
    # Monitor system journal
    $ssh_cmd -o StrictHostKeyChecking=no "$RPI_HOST" \
        "journalctl $follow_flag $since_flag -n $LINES --no-pager" 2>/dev/null | \
        while IFS= read -r line; do
            if filter_log "$line"; then
                if [[ "$JSON_OUTPUT" == false ]]; then
                    echo "[$(format_timestamp)] [$(color_rpi):journal] $line"
                else
                    format_log_line "rpi" "journal" "INFO" "$line"
                fi
            fi
        done &
    
    # Monitor systemd services
    for service in "${SYSTEMD_SERVICES[@]}"; do
        $ssh_cmd -o StrictHostKeyChecking=no "$RPI_HOST" \
            "journalctl $follow_flag $since_flag -u $service -n $LINES --no-pager" 2>/dev/null | \
            while IFS= read -r line; do
                if filter_log "$line"; then
                    if [[ "$JSON_OUTPUT" == false ]]; then
                        echo "[$(format_timestamp)] [$(color_rpi):$service] $line"
                    else
                        format_log_line "rpi" "$service" "INFO" "$line"
                    fi
                fi
            done &
    done
}

# Local file logs
monitor_files() {
    if ! should_monitor_source "files"; then
        return 0
    fi
    
    local follow_flag=""
    if [[ "$FOLLOW" == true ]]; then
        follow_flag="-F"
    fi
    
    # Find log files
    local log_files=()
    
    # Local logs directory
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        while IFS= read -r -d '' file; do
            log_files+=("$file")
        done < <(find "$PROJECT_ROOT/logs" -name "*.log" -type f -print0 2>/dev/null)
    fi
    
    # Docker volume logs
    if [[ -d "$PROJECT_ROOT/volumes" ]]; then
        while IFS= read -r -d '' file; do
            log_files+=("$file")
        done < <(find "$PROJECT_ROOT/volumes" -name "*.log" -type f -print0 2>/dev/null)
    fi
    
    for log_file in "${log_files[@]}"; do
        local component=$(basename "$log_file" .log)
        tail $follow_flag -n "$LINES" "$log_file" 2>/dev/null | while IFS= read -r line; do
            if filter_log "$line"; then
                if [[ "$JSON_OUTPUT" == false ]]; then
                    echo "[$(format_timestamp)] [$(color_files):$component] $line"
                else
                    format_log_line "files" "$component" "INFO" "$line"
                fi
            fi
        done &
    done
}

# Main execution
main() {
    # Setup output
    if [[ -n "$OUTPUT_FILE" ]]; then
        exec > "$OUTPUT_FILE"
    fi
    
    # Start monitoring
    echo "Starting log aggregation from sources: $SOURCES"
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Start all monitors
    monitor_docker
    monitor_systemd
    monitor_android
    monitor_rpi
    monitor_files
    
    # Wait for all background processes
    if [[ "$FOLLOW" == true ]]; then
        wait
    else
        sleep 2
        wait
    fi
}

# Handle cleanup
trap 'kill $(jobs -p) 2>/dev/null; exit' INT TERM

# Run main function
main "$@"
