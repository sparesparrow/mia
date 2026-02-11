#!/usr/bin/env bash
set -euo pipefail

# Smoke tests for AI-Servis deployments
# Quick validation that deployed services are working

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

# Environment configuration
ENVIRONMENT="${1:-local}"
TIMEOUT="${TIMEOUT:-30}"

# Environment-specific URLs
case "$ENVIRONMENT" in
    "local")
        CORE_ORCHESTRATOR_URL="http://localhost:8080"
        SERVICE_DISCOVERY_URL="http://localhost:8090"
        AUDIO_ASSISTANT_URL="http://localhost:8082"
        PLATFORM_CONTROLLER_URL="http://localhost:8083"
        ;;
    "staging")
        CORE_ORCHESTRATOR_URL="https://staging-core.ai-servis.com"
        SERVICE_DISCOVERY_URL="https://staging-discovery.ai-servis.com"
        AUDIO_ASSISTANT_URL="https://staging-audio.ai-servis.com"
        PLATFORM_CONTROLLER_URL="https://staging-platform.ai-servis.com"
        ;;
    "production")
        CORE_ORCHESTRATOR_URL="https://core.ai-servis.com"
        SERVICE_DISCOVERY_URL="https://discovery.ai-servis.com"
        AUDIO_ASSISTANT_URL="https://audio.ai-servis.com"
        PLATFORM_CONTROLLER_URL="https://platform.ai-servis.com"
        ;;
    *)
        error "Unknown environment: $ENVIRONMENT"
        echo "Usage: $0 [local|staging|production]"
        exit 1
        ;;
esac

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Run a single smoke test
run_smoke_test() {
    local test_name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    local timeout="${4:-$TIMEOUT}"
    
    ((TESTS_TOTAL++))
    log "Testing: $test_name"
    
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" || echo "000")
    
    if [ "$http_code" = "$expected_status" ]; then
        success "✓ $test_name (HTTP $http_code)"
        ((TESTS_PASSED++))
        return 0
    else
        error "✗ $test_name (Expected HTTP $expected_status, got $http_code)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test service availability with response validation
run_json_test() {
    local test_name="$1"
    local url="$2"
    local json_path="${3:-}"
    local timeout="${4:-$TIMEOUT}"
    
    ((TESTS_TOTAL++))
    log "Testing: $test_name"
    
    local response
    response=$(curl -s --max-time "$timeout" "$url" || echo "")
    
    if [ -z "$response" ]; then
        error "✗ $test_name (No response)"
        ((TESTS_FAILED++))
        return 1
    fi
    
    # Validate JSON
    if ! echo "$response" | jq . >/dev/null 2>&1; then
        error "✗ $test_name (Invalid JSON response)"
        ((TESTS_FAILED++))
        return 1
    fi
    
    # Validate specific JSON path if provided
    if [ -n "$json_path" ]; then
        if ! echo "$response" | jq -e "$json_path" >/dev/null 2>&1; then
            error "✗ $test_name (JSON path validation failed: $json_path)"
            ((TESTS_FAILED++))
            return 1
        fi
    fi
    
    success "✓ $test_name"
    ((TESTS_PASSED++))
    return 0
}

# Test critical service endpoints
test_critical_endpoints() {
    log "Testing critical service endpoints..."
    
    # Core Orchestrator
    run_smoke_test "Core Orchestrator Health" "$CORE_ORCHESTRATOR_URL/health"
    run_smoke_test "Core Orchestrator Status" "$CORE_ORCHESTRATOR_URL/status"
    
    # Service Discovery
    run_smoke_test "Service Discovery Health" "$SERVICE_DISCOVERY_URL/health"
    run_json_test "Service Discovery Services" "$SERVICE_DISCOVERY_URL/services" ".[] | length >= 0"
    
    # AI Audio Assistant
    run_smoke_test "Audio Assistant Health" "$AUDIO_ASSISTANT_URL/health"
    run_json_test "Audio Assistant Capabilities" "$AUDIO_ASSISTANT_URL/capabilities" ".capabilities | length > 0"
    
    # Platform Controller
    run_smoke_test "Platform Controller Health" "$PLATFORM_CONTROLLER_URL/health"
    run_json_test "Platform Controller System Info" "$PLATFORM_CONTROLLER_URL/system/info" ".platform"
}

# Test MCP functionality
test_mcp_functionality() {
    log "Testing MCP functionality..."
    
    run_json_test "MCP Status" "$CORE_ORCHESTRATOR_URL/mcp/status" ".servers"
    run_json_test "MCP Capabilities" "$CORE_ORCHESTRATOR_URL/mcp/capabilities" ".tools"
}

# Test service integration
test_service_integration() {
    log "Testing service integration..."
    
    # Test that services are properly registered in discovery
    run_json_test "Core Service Registration" "$SERVICE_DISCOVERY_URL/services" '.[] | select(.name == "core-orchestrator")'
    run_json_test "Audio Service Registration" "$SERVICE_DISCOVERY_URL/services" '.[] | select(.name == "ai-audio-assistant")'
    run_json_test "Platform Service Registration" "$SERVICE_DISCOVERY_URL/services" '.[] | select(.name == "ai-platform-linux")'
}

# Test performance (basic)
test_basic_performance() {
    log "Testing basic performance..."
    
    local start_time
    local end_time
    local duration
    
    # Test response time for health endpoint
    start_time=$(date +%s%N)
    if curl -s --max-time 5 "$CORE_ORCHESTRATOR_URL/health" >/dev/null; then
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
        
        if [ $duration -lt 1000 ]; then  # Less than 1 second
            success "✓ Response time acceptable: ${duration}ms"
            ((TESTS_PASSED++))
        else
            warning "⚠ Slow response time: ${duration}ms"
            ((TESTS_FAILED++))
        fi
        ((TESTS_TOTAL++))
    else
        error "✗ Performance test failed (no response)"
        ((TESTS_FAILED++))
        ((TESTS_TOTAL++))
    fi
}

# Test security headers (for production/staging)
test_security_headers() {
    if [ "$ENVIRONMENT" = "local" ]; then
        log "Skipping security header tests for local environment"
        return
    fi
    
    log "Testing security headers..."
    
    local headers
    headers=$(curl -s -I --max-time "$TIMEOUT" "$CORE_ORCHESTRATOR_URL/health" || echo "")
    
    ((TESTS_TOTAL++))
    if echo "$headers" | grep -qi "x-content-type-options"; then
        success "✓ X-Content-Type-Options header present"
        ((TESTS_PASSED++))
    else
        warning "⚠ X-Content-Type-Options header missing"
        ((TESTS_FAILED++))
    fi
    
    ((TESTS_TOTAL++))
    if echo "$headers" | grep -qi "x-frame-options"; then
        success "✓ X-Frame-Options header present"
        ((TESTS_PASSED++))
    else
        warning "⚠ X-Frame-Options header missing"
        ((TESTS_FAILED++))
    fi
    
    ((TESTS_TOTAL++))
    if echo "$headers" | grep -qi "strict-transport-security"; then
        success "✓ Strict-Transport-Security header present"
        ((TESTS_PASSED++))
    else
        warning "⚠ Strict-Transport-Security header missing"
        ((TESTS_FAILED++))
    fi
}

# Generate smoke test report
generate_report() {
    local report_file="$PROJECT_ROOT/smoke-test-report-$ENVIRONMENT.md"
    
    cat > "$report_file" << EOF
# AI-Servis Smoke Test Report

**Environment:** $ENVIRONMENT
**Test Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Total Tests:** $TESTS_TOTAL
**Passed:** $TESTS_PASSED
**Failed:** $TESTS_FAILED
**Success Rate:** $(( (TESTS_PASSED * 100) / TESTS_TOTAL ))%

## Summary

EOF

    if [ $TESTS_FAILED -eq 0 ]; then
        echo "✅ **All smoke tests passed!** The deployment appears to be healthy." >> "$report_file"
    else
        echo "❌ **Some smoke tests failed.** Please investigate the following issues:" >> "$report_file"
        echo "" >> "$report_file"
        echo "**Failed Tests:** $TESTS_FAILED out of $TESTS_TOTAL" >> "$report_file"
    fi

    echo "" >> "$report_file"
    echo "## Service Endpoints Tested" >> "$report_file"
    echo "" >> "$report_file"
    echo "- Core Orchestrator: $CORE_ORCHESTRATOR_URL" >> "$report_file"
    echo "- Service Discovery: $SERVICE_DISCOVERY_URL" >> "$report_file"
    echo "- AI Audio Assistant: $AUDIO_ASSISTANT_URL" >> "$report_file"
    echo "- Platform Controller: $PLATFORM_CONTROLLER_URL" >> "$report_file"
    
    echo "" >> "$report_file"
    echo "## Recommendations" >> "$report_file"
    echo "" >> "$report_file"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo "- Deployment is healthy and ready for use" >> "$report_file"
        echo "- All critical services are responding correctly" >> "$report_file"
        echo "- Service integration is working properly" >> "$report_file"
    else
        echo "- Investigate failed tests immediately" >> "$report_file"
        echo "- Check service logs for error details" >> "$report_file"
        echo "- Verify network connectivity and DNS resolution" >> "$report_file"
        echo "- Consider rolling back if critical services are failing" >> "$report_file"
    fi

    success "Smoke test report generated: $report_file"
}

# Main execution
main() {
    log "Starting smoke tests for $ENVIRONMENT environment..."
    log "Timeout: ${TIMEOUT}s"
    
    # Run all smoke tests
    test_critical_endpoints
    test_mcp_functionality
    test_service_integration
    test_basic_performance
    test_security_headers
    
    # Generate report
    generate_report
    
    # Print summary
    echo ""
    log "Smoke tests completed for $ENVIRONMENT!"
    log "Total: $TESTS_TOTAL, Passed: $TESTS_PASSED, Failed: $TESTS_FAILED"
    log "Success Rate: $(( (TESTS_PASSED * 100) / TESTS_TOTAL ))%"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        success "🎉 All smoke tests passed! Deployment is healthy."
        exit 0
    else
        error "💥 $TESTS_FAILED smoke tests failed. Please investigate."
        exit 1
    fi
}

# Show usage if no arguments provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 [local|staging|production] [timeout]"
    echo ""
    echo "Examples:"
    echo "  $0 local              # Test local development environment"
    echo "  $0 staging            # Test staging environment"
    echo "  $0 production 60      # Test production with 60s timeout"
    echo ""
    echo "Environment variables:"
    echo "  TIMEOUT               # Request timeout in seconds (default: 30)"
    exit 1
fi

# Run main function
main "$@"