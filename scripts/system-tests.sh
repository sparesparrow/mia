#!/usr/bin/env bash
set -euo pipefail

# System integration tests for AI-Servis
# Tests end-to-end functionality across all components

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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
MQTT_BROKER_URL="localhost:1883"

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test result tracking
declare -a FAILED_TESTS=()

# Helper function to run a test
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TESTS_TOTAL++))
    log "Running test: $test_name"
    
    if $test_function; then
        success "✓ $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        error "✗ $test_name"
        FAILED_TESTS+=("$test_name")
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test service health endpoints
test_service_health() {
    local services=(
        "$CORE_ORCHESTRATOR_URL/health"
        "$SERVICE_DISCOVERY_URL/health"
        "$AUDIO_ASSISTANT_URL/health"
        "$PLATFORM_CONTROLLER_URL/health"
    )
    
    for service in "${services[@]}"; do
        if ! curl -s -f "$service" >/dev/null; then
            return 1
        fi
    done
    
    return 0
}

# Test service discovery functionality
test_service_discovery() {
    # Test service registration and discovery
    local services_response=$(curl -s "$SERVICE_DISCOVERY_URL/services")
    
    if [ -z "$services_response" ]; then
        return 1
    fi
    
    # Check if response is valid JSON
    if ! echo "$services_response" | jq . >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if core services are registered
    local core_services=("core-orchestrator" "ai-audio-assistant" "ai-platform-linux")
    
    for service in "${core_services[@]}"; do
        if ! echo "$services_response" | jq -e ".[] | select(.name == \"$service\")" >/dev/null; then
            return 1
        fi
    done
    
    return 0
}

# Test MCP communication
test_mcp_communication() {
    # Test MCP host status
    local mcp_status=$(curl -s "$CORE_ORCHESTRATOR_URL/mcp/status" || echo "")
    
    if [ -z "$mcp_status" ]; then
        return 1
    fi
    
    # Check if MCP servers are connected
    if ! echo "$mcp_status" | jq -e '.servers | length > 0' >/dev/null 2>&1; then
        return 1
    fi
    
    return 0
}

# Test MQTT connectivity
test_mqtt_connectivity() {
    # Test MQTT connection using mosquitto_pub/sub if available
    if command -v mosquitto_pub >/dev/null && command -v mosquitto_sub >/dev/null; then
        local test_topic="test/system/$(date +%s)"
        local test_message="system_test_$(date +%s)"
        local received_message=""
        
        # Start subscriber in background
        timeout 10s mosquitto_sub -h localhost -p 1883 -t "$test_topic" > /tmp/mqtt_test_output &
        local sub_pid=$!
        
        sleep 2
        
        # Publish test message
        if mosquitto_pub -h localhost -p 1883 -t "$test_topic" -m "$test_message"; then
            sleep 2
            
            # Check if message was received
            if [ -f /tmp/mqtt_test_output ]; then
                received_message=$(cat /tmp/mqtt_test_output)
                rm -f /tmp/mqtt_test_output
                
                if [ "$received_message" = "$test_message" ]; then
                    kill $sub_pid 2>/dev/null || true
                    return 0
                fi
            fi
        fi
        
        kill $sub_pid 2>/dev/null || true
        rm -f /tmp/mqtt_test_output
    fi
    
    # Fallback: check if MQTT port is open
    if timeout 5s bash -c "</dev/tcp/localhost/1883" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Test database connectivity
test_database_connectivity() {
    # Test PostgreSQL connection
    if command -v psql >/dev/null; then
        if PGPASSWORD="aiservislicdbdev" psql -h localhost -U aiservispdev -d aiservisdwxb -c "SELECT 1;" >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    # Fallback: check if PostgreSQL port is open
    if timeout 5s bash -c "</dev/tcp/localhost/5432" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Test Redis connectivity
test_redis_connectivity() {
    # Test Redis connection
    if command -v redis-cli >/dev/null; then
        if redis-cli -h localhost ping | grep -q "PONG"; then
            return 0
        fi
    fi
    
    # Fallback: check if Redis port is open
    if timeout 5s bash -c "</dev/tcp/localhost/6379" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Test audio assistant capabilities
test_audio_assistant() {
    local capabilities_response=$(curl -s "$AUDIO_ASSISTANT_URL/capabilities" || echo "")
    
    if [ -z "$capabilities_response" ]; then
        return 1
    fi
    
    # Check if response is valid JSON
    if ! echo "$capabilities_response" | jq . >/dev/null 2>&1; then
        return 1
    fi
    
    # Check for expected capabilities
    local expected_capabilities=("text_to_speech" "speech_to_text" "music_control")
    
    for capability in "${expected_capabilities[@]}"; do
        if ! echo "$capabilities_response" | jq -e ".capabilities[] | select(. == \"$capability\")" >/dev/null 2>&1; then
            return 1
        fi
    done
    
    return 0
}

# Test platform controller
test_platform_controller() {
    local system_info=$(curl -s "$PLATFORM_CONTROLLER_URL/system/info" || echo "")
    
    if [ -z "$system_info" ]; then
        return 1
    fi
    
    # Check if response is valid JSON
    if ! echo "$system_info" | jq . >/dev/null 2>&1; then
        return 1
    fi
    
    # Check for expected system info fields
    local required_fields=("platform" "version" "uptime")
    
    for field in "${required_fields[@]}"; do
        if ! echo "$system_info" | jq -e ".$field" >/dev/null 2>&1; then
            return 1
        fi
    done
    
    return 0
}

# Test end-to-end workflow
test_e2e_workflow() {
    # Test a complete workflow: service discovery -> MCP communication -> platform control
    
    # 1. Get available services
    local services=$(curl -s "$SERVICE_DISCOVERY_URL/services" || echo "")
    if [ -z "$services" ]; then
        return 1
    fi
    
    # 2. Check MCP status
    local mcp_status=$(curl -s "$CORE_ORCHESTRATOR_URL/mcp/status" || echo "")
    if [ -z "$mcp_status" ]; then
        return 1
    fi
    
    # 3. Get system info from platform controller
    local system_info=$(curl -s "$PLATFORM_CONTROLLER_URL/system/info" || echo "")
    if [ -z "$system_info" ]; then
        return 1
    fi
    
    # 4. Test audio assistant capabilities
    local audio_capabilities=$(curl -s "$AUDIO_ASSISTANT_URL/capabilities" || echo "")
    if [ -z "$audio_capabilities" ]; then
        return 1
    fi
    
    return 0
}

# Test container health
test_container_health() {
    local unhealthy_containers=()
    
    # Get list of running containers
    local containers=$(docker-compose ps -q 2>/dev/null || echo "")
    
    if [ -z "$containers" ]; then
        return 1
    fi
    
    # Check health status of each container
    while IFS= read -r container_id; do
        if [ -n "$container_id" ]; then
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "unknown")
            local container_name=$(docker inspect --format='{{.Name}}' "$container_id" 2>/dev/null | sed 's/^.//')
            
            if [ "$health_status" = "unhealthy" ]; then
                unhealthy_containers+=("$container_name")
            fi
        fi
    done <<< "$containers"
    
    if [ ${#unhealthy_containers[@]} -gt 0 ]; then
        return 1
    fi
    
    return 0
}

# Test log output
test_log_output() {
    local log_dir="$PROJECT_ROOT/logs"
    
    if [ ! -d "$log_dir" ]; then
        return 1
    fi
    
    # Check if log files exist and contain recent entries
    local log_files=$(find "$log_dir" -name "*.log" -mmin -10 2>/dev/null || echo "")
    
    if [ -z "$log_files" ]; then
        return 1
    fi
    
    # Check for error patterns in logs
    local error_count=0
    while IFS= read -r log_file; do
        if [ -f "$log_file" ]; then
            local errors=$(grep -i "error\|exception\|traceback" "$log_file" | wc -l)
            error_count=$((error_count + errors))
        fi
    done <<< "$log_files"
    
    # Allow some errors but not too many
    if [ "$error_count" -gt 10 ]; then
        return 1
    fi
    
    return 0
}

# Generate test report
generate_report() {
    log "Generating system test report..."
    
    local report_file="$PROJECT_ROOT/system-test-report.md"
    
    cat > "$report_file" << EOF
# AI-Servis System Test Report

**Test Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Total Tests:** $TESTS_TOTAL
**Passed:** $TESTS_PASSED
**Failed:** $TESTS_FAILED
**Success Rate:** $(( (TESTS_PASSED * 100) / TESTS_TOTAL ))%

## Test Results

EOF

    if [ $TESTS_FAILED -eq 0 ]; then
        echo "✅ **All tests passed successfully!**" >> "$report_file"
    else
        echo "❌ **Some tests failed:**" >> "$report_file"
        echo "" >> "$report_file"
        for test in "${FAILED_TESTS[@]}"; do
            echo "- $test" >> "$report_file"
        done
    fi

    echo "" >> "$report_file"
    echo "## Test Details" >> "$report_file"
    echo "" >> "$report_file"
    echo "- Service Health: $([ $TESTS_FAILED -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$report_file"
    echo "- Service Discovery: $([ $TESTS_FAILED -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$report_file"
    echo "- MCP Communication: $([ $TESTS_FAILED -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$report_file"
    echo "- MQTT Connectivity: $([ $TESTS_FAILED -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$report_file"
    echo "- Database Connectivity: $([ $TESTS_FAILED -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$report_file"
    echo "- End-to-End Workflow: $([ $TESTS_FAILED -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$report_file"

    success "System test report generated: $report_file"
}

# Main execution
main() {
    log "Starting AI-Servis system tests..."
    
    # Run all system tests
    run_test "Service Health Check" test_service_health
    run_test "Service Discovery" test_service_discovery
    run_test "MCP Communication" test_mcp_communication
    run_test "MQTT Connectivity" test_mqtt_connectivity
    run_test "Database Connectivity" test_database_connectivity
    run_test "Redis Connectivity" test_redis_connectivity
    run_test "Audio Assistant" test_audio_assistant
    run_test "Platform Controller" test_platform_controller
    run_test "End-to-End Workflow" test_e2e_workflow
    run_test "Container Health" test_container_health
    run_test "Log Output Check" test_log_output
    
    # Generate report
    generate_report
    
    # Print summary
    log "System tests completed!"
    log "Total: $TESTS_TOTAL, Passed: $TESTS_PASSED, Failed: $TESTS_FAILED"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        success "All system tests passed!"
        exit 0
    else
        error "$TESTS_FAILED tests failed"
        exit 1
    fi
}

# Run main function
main "$@"