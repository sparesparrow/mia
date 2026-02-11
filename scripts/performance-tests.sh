#!/usr/bin/env bash
set -euo pipefail

# Performance testing script for AI-Servis
# Tests system performance under various loads

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS_DIR="$PROJECT_ROOT/performance-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test configuration
CORE_ORCHESTRATOR_URL="http://localhost:8080"
SERVICE_DISCOVERY_URL="http://localhost:8090"
AUDIO_ASSISTANT_URL="http://localhost:8082"
PLATFORM_CONTROLLER_URL="http://localhost:8083"

# Performance thresholds
MAX_RESPONSE_TIME=100  # milliseconds
MAX_MEMORY_USAGE=512   # MB
MAX_CPU_USAGE=80       # percent
MIN_THROUGHPUT=100     # requests per second

# Create results directory
setup_results_dir() {
    mkdir -p "$RESULTS_DIR"
    local timestamp=$(date +'%Y%m%d_%H%M%S')
    RESULTS_DIR="$RESULTS_DIR/perf_test_$timestamp"
    mkdir -p "$RESULTS_DIR"
    log "Results will be saved to: $RESULTS_DIR"
}

# Check if required tools are available
check_dependencies() {
    local missing_tools=()
    
    for tool in curl jq ab wrk docker-compose; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        echo "Please install them and try again"
        exit 1
    fi
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    local services=(
        "$CORE_ORCHESTRATOR_URL/health"
        "$SERVICE_DISCOVERY_URL/health"
        "$AUDIO_ASSISTANT_URL/health"
        "$PLATFORM_CONTROLLER_URL/health"
    )
    
    local max_attempts=30
    local attempt=1
    
    for service in "${services[@]}"; do
        log "Checking $service..."
        
        while [ $attempt -le $max_attempts ]; do
            if curl -s -f "$service" >/dev/null 2>&1; then
                success "Service ready: $service"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                error "Service not ready after $max_attempts attempts: $service"
                return 1
            fi
            
            sleep 2
            ((attempt++))
        done
        attempt=1
    done
}

# Test response times
test_response_times() {
    log "Testing response times..."
    
    local endpoints=(
        "$CORE_ORCHESTRATOR_URL/health"
        "$CORE_ORCHESTRATOR_URL/status"
        "$SERVICE_DISCOVERY_URL/services"
        "$AUDIO_ASSISTANT_URL/capabilities"
        "$PLATFORM_CONTROLLER_URL/system/info"
    )
    
    local results_file="$RESULTS_DIR/response_times.json"
    echo "[]" > "$results_file"
    
    for endpoint in "${endpoints[@]}"; do
        log "Testing endpoint: $endpoint"
        
        local temp_file=$(mktemp)
        local start_time=$(date +%s%3N)
        
        if curl -s -w "@$SCRIPT_DIR/curl-format.txt" -o /dev/null "$endpoint" > "$temp_file"; then
            local end_time=$(date +%s%3N)
            local total_time=$(( end_time - start_time ))
            local curl_time=$(grep "time_total" "$temp_file" | cut -d: -f2 | tr -d ' ')
            
            # Convert curl time to milliseconds
            local curl_time_ms=$(echo "$curl_time * 1000" | bc -l | cut -d. -f1)
            
            # Add result to JSON file
            local result=$(jq -n \
                --arg endpoint "$endpoint" \
                --arg response_time "$curl_time_ms" \
                --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
                '{endpoint: $endpoint, response_time_ms: ($response_time | tonumber), timestamp: $timestamp}')
            
            jq ". += [$result]" "$results_file" > "$results_file.tmp" && mv "$results_file.tmp" "$results_file"
            
            if [ "$curl_time_ms" -gt $MAX_RESPONSE_TIME ]; then
                warning "Response time exceeds threshold: ${curl_time_ms}ms > ${MAX_RESPONSE_TIME}ms"
            else
                success "Response time OK: ${curl_time_ms}ms"
            fi
        else
            error "Failed to test endpoint: $endpoint"
        fi
        
        rm -f "$temp_file"
    done
}

# Test throughput with Apache Bench
test_throughput_ab() {
    log "Testing throughput with Apache Bench..."
    
    local endpoint="$CORE_ORCHESTRATOR_URL/health"
    local requests=1000
    local concurrency=10
    local results_file="$RESULTS_DIR/throughput_ab.txt"
    
    log "Running $requests requests with concurrency $concurrency..."
    
    if ab -n $requests -c $concurrency -g "$RESULTS_DIR/ab_gnuplot.dat" "$endpoint" > "$results_file" 2>&1; then
        # Parse results
        local rps=$(grep "Requests per second" "$results_file" | awk '{print $4}')
        local mean_time=$(grep "Time per request.*mean" "$results_file" | head -1 | awk '{print $4}')
        
        log "Throughput: $rps requests/sec"
        log "Mean response time: ${mean_time}ms"
        
        if (( $(echo "$rps > $MIN_THROUGHPUT" | bc -l) )); then
            success "Throughput OK: $rps > $MIN_THROUGHPUT"
        else
            warning "Throughput below threshold: $rps < $MIN_THROUGHPUT"
        fi
    else
        error "Apache Bench test failed"
    fi
}

# Test throughput with wrk
test_throughput_wrk() {
    log "Testing throughput with wrk..."
    
    local endpoint="$CORE_ORCHESTRATOR_URL/health"
    local duration="30s"
    local threads=4
    local connections=10
    local results_file="$RESULTS_DIR/throughput_wrk.txt"
    
    log "Running wrk for $duration with $threads threads and $connections connections..."
    
    if wrk -t$threads -c$connections -d$duration --latency "$endpoint" > "$results_file" 2>&1; then
        # Parse results
        local rps=$(grep "Requests/sec:" "$results_file" | awk '{print $2}')
        local latency_avg=$(grep "Latency.*avg" "$results_file" | awk '{print $2}')
        
        log "Throughput: $rps requests/sec"
        log "Average latency: $latency_avg"
        
        success "wrk test completed successfully"
    else
        error "wrk test failed"
    fi
}

# Monitor resource usage during tests
monitor_resources() {
    log "Monitoring resource usage..."
    
    local duration=60  # Monitor for 60 seconds
    local interval=2   # Sample every 2 seconds
    local results_file="$RESULTS_DIR/resource_usage.csv"
    
    echo "timestamp,cpu_percent,memory_mb,containers" > "$results_file"
    
    for ((i=1; i<=duration/interval; i++)); do
        local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        
        # Get container stats
        local stats=$(docker-compose ps -q | xargs docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "")
        
        if [ -n "$stats" ]; then
            # Parse CPU and memory usage
            local total_cpu=0
            local total_memory=0
            local container_count=0
            
            while IFS=$'\t' read -r cpu_percent mem_usage; do
                if [[ "$cpu_percent" =~ ^[0-9.]+% ]]; then
                    cpu_value=$(echo "$cpu_percent" | sed 's/%//')
                    total_cpu=$(echo "$total_cpu + $cpu_value" | bc -l)
                    
                    # Extract memory in MB
                    mem_mb=$(echo "$mem_usage" | awk '{print $1}' | sed 's/MiB//' | sed 's/GiB/*1024/' | bc -l 2>/dev/null || echo "0")
                    total_memory=$(echo "$total_memory + $mem_mb" | bc -l)
                    
                    ((container_count++))
                fi
            done <<< "$stats"
            
            if [ $container_count -gt 0 ]; then
                local avg_cpu=$(echo "scale=2; $total_cpu / $container_count" | bc -l)
                echo "$timestamp,$avg_cpu,$total_memory,$container_count" >> "$results_file"
                
                # Check thresholds
                if (( $(echo "$avg_cpu > $MAX_CPU_USAGE" | bc -l) )); then
                    warning "High CPU usage: ${avg_cpu}%"
                fi
                
                if (( $(echo "$total_memory > $MAX_MEMORY_USAGE" | bc -l) )); then
                    warning "High memory usage: ${total_memory}MB"
                fi
            fi
        fi
        
        sleep $interval
    done &
    
    local monitor_pid=$!
    echo $monitor_pid > "$RESULTS_DIR/monitor.pid"
    log "Resource monitoring started (PID: $monitor_pid)"
}

# Stop resource monitoring
stop_monitoring() {
    if [ -f "$RESULTS_DIR/monitor.pid" ]; then
        local monitor_pid=$(cat "$RESULTS_DIR/monitor.pid")
        if kill -0 "$monitor_pid" 2>/dev/null; then
            kill "$monitor_pid"
            log "Resource monitoring stopped"
        fi
        rm -f "$RESULTS_DIR/monitor.pid"
    fi
}

# Generate performance report
generate_report() {
    log "Generating performance report..."
    
    local report_file="$RESULTS_DIR/performance_report.md"
    
    cat > "$report_file" << EOF
# AI-Servis Performance Test Report

**Test Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Test Duration:** $(date -d "@$(($(date +%s) - test_start_time))" -u +%H:%M:%S)

## Summary

This report contains performance test results for the AI-Servis system.

## Test Configuration

- **Max Response Time:** ${MAX_RESPONSE_TIME}ms
- **Max Memory Usage:** ${MAX_MEMORY_USAGE}MB
- **Max CPU Usage:** ${MAX_CPU_USAGE}%
- **Min Throughput:** ${MIN_THROUGHPUT} req/sec

## Response Time Tests

EOF

    if [ -f "$RESULTS_DIR/response_times.json" ]; then
        echo "### Response Times by Endpoint" >> "$report_file"
        echo "" >> "$report_file"
        
        jq -r '.[] | "- **\(.endpoint)**: \(.response_time_ms)ms"' "$RESULTS_DIR/response_times.json" >> "$report_file"
        echo "" >> "$report_file"
    fi

    if [ -f "$RESULTS_DIR/throughput_ab.txt" ]; then
        echo "## Apache Bench Results" >> "$report_file"
        echo "" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(Requests per second|Time per request|Transfer rate)" "$RESULTS_DIR/throughput_ab.txt" >> "$report_file"
        echo '```' >> "$report_file"
        echo "" >> "$report_file"
    fi

    if [ -f "$RESULTS_DIR/throughput_wrk.txt" ]; then
        echo "## wrk Results" >> "$report_file"
        echo "" >> "$report_file"
        echo '```' >> "$report_file"
        grep -E "(Requests/sec|Latency|Transfer/sec)" "$RESULTS_DIR/throughput_wrk.txt" >> "$report_file"
        echo '```' >> "$report_file"
        echo "" >> "$report_file"
    fi

    echo "## Files Generated" >> "$report_file"
    echo "" >> "$report_file"
    find "$RESULTS_DIR" -type f -name "*.txt" -o -name "*.json" -o -name "*.csv" -o -name "*.dat" | \
        sed "s|$RESULTS_DIR/|- |" >> "$report_file"

    success "Performance report generated: $report_file"
}

# Create curl format file for response time testing
create_curl_format() {
    cat > "$SCRIPT_DIR/curl-format.txt" << 'EOF'
     time_namelookup:  %{time_namelookup}s\n
        time_connect:  %{time_connect}s\n
     time_appconnect:  %{time_appconnect}s\n
    time_pretransfer:  %{time_pretransfer}s\n
       time_redirect:  %{time_redirect}s\n
  time_starttransfer:  %{time_starttransfer}s\n
                     ----------\n
          time_total:  %{time_total}s\n
EOF
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    stop_monitoring
    rm -f "$SCRIPT_DIR/curl-format.txt"
}

# Main execution
main() {
    local test_start_time=$(date +%s)
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    log "Starting AI-Servis performance tests..."
    
    check_dependencies
    setup_results_dir
    create_curl_format
    wait_for_services
    
    # Start resource monitoring
    monitor_resources
    
    # Run performance tests
    test_response_times
    test_throughput_ab
    test_throughput_wrk
    
    # Stop monitoring and generate report
    stop_monitoring
    generate_report
    
    success "Performance tests completed!"
    log "Results saved to: $RESULTS_DIR"
}

# Run main function
main "$@"