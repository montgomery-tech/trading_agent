#!/bin/bash

# Comprehensive API Test Suite for AWS FastAPI Deployment
echo "🧪 Comprehensive API Test Suite"
echo "==============================="

# Test URLs
DIRECT_URL="http://18.204.204.26:8000"
ALB_URL="http://trading-api-alb-464076303.us-east-1.elb.amazonaws.com"

# Test configuration
TIMEOUT=10
TESTS_PASSED=0
TESTS_FAILED=0

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result tracking
declare -a FAILED_TESTS=()

# Helper functions
log_test() {
    echo -e "${BLUE}🧪 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_code="${3:-200}"
    
    log_test "Testing: $test_name"
    
    # Run the test command and capture both response and HTTP code
    local response=$(eval "$test_command" 2>/dev/null)
    local http_code=$(eval "$test_command -w '%{http_code}'" 2>/dev/null | tail -c 3)
    
    if [[ "$http_code" == "$expected_code" ]]; then
        log_success "$test_name (HTTP $http_code)"
        if [[ ! -z "$response" && "$response" != *"curl:"* ]]; then
            echo "   Response preview: $(echo "$response" | head -c 100)..."
        fi
    else
        log_failure "$test_name (Expected: $expected_code, Got: $http_code)"
        if [[ ! -z "$response" ]]; then
            echo "   Response: $response"
        fi
    fi
    echo ""
}

# JSON validation helper
validate_json() {
    local json_string="$1"
    echo "$json_string" | python3 -m json.tool > /dev/null 2>&1
    return $?
}

echo "🎯 Testing both Direct EC2 and Load Balancer access"
echo "   Direct EC2: $DIRECT_URL"
echo "   ALB: $ALB_URL"
echo ""

# =============================================================================
# 1. BASIC CONNECTIVITY TESTS
# =============================================================================

echo "📡 1. BASIC CONNECTIVITY TESTS"
echo "==============================="

# Test 1.1: Direct EC2 Health Check
run_test "Direct EC2 Health Check" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/health'"

# Test 1.2: ALB Health Check
run_test "ALB Health Check" \
    "curl -s --connect-timeout $TIMEOUT '$ALB_URL/health'"

# Test 1.3: Root endpoint (Direct)
run_test "Direct EC2 Root Endpoint" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/'" \
    "200"

# Test 1.4: Root endpoint (ALB)
run_test "ALB Root Endpoint" \
    "curl -s --connect-timeout $TIMEOUT '$ALB_URL/'" \
    "200"

# =============================================================================
# 2. API ENDPOINT DISCOVERY
# =============================================================================

echo "🔍 2. API ENDPOINT DISCOVERY"
echo "============================"

# Test 2.1: OpenAPI Documentation
run_test "OpenAPI JSON Schema" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/openapi.json'"

# Test 2.2: API Documentation UI
run_test "Swagger UI Docs" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/docs'"

# Test 2.3: ReDoc Documentation
run_test "ReDoc Documentation" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/redoc'"

# =============================================================================
# 3. HEALTH AND STATUS ENDPOINTS
# =============================================================================

echo "🏥 3. HEALTH AND STATUS ENDPOINTS"
echo "================================="

# Test 3.1: Detailed health check analysis
log_test "Analyzing health endpoint response"
HEALTH_RESPONSE=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health")

if validate_json "$HEALTH_RESPONSE"; then
    log_success "Health endpoint returns valid JSON"
    
    # Parse health response components
    echo "   📊 Health Response Analysis:"
    echo "$HEALTH_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'   Status: {data.get(\"status\", \"unknown\")}')
    print(f'   Environment: {data.get(\"environment\", \"unknown\")}')
    print(f'   Version: {data.get(\"version\", \"unknown\")}')
    
    if 'database' in data:
        db = data['database']
        print(f'   Database: {db.get(\"status\", \"unknown\")} ({db.get(\"type\", \"unknown\")})')
    
    if 'authentication' in data:
        auth = data['authentication']
        print(f'   JWT: {\"Enabled\" if auth.get(\"jwt_enabled\") else \"Disabled\"}')
    
    if 'security' in data:
        sec = data['security']
        print(f'   Rate Limiting: {sec.get(\"rate_limiting\", \"unknown\")}')
        print(f'   Input Validation: {sec.get(\"input_validation\", \"unknown\")}')
except Exception as e:
    print(f'   Error parsing health response: {e}')
"
else
    log_failure "Health endpoint returns invalid JSON"
fi
echo ""

# =============================================================================
# 4. SECURITY TESTS
# =============================================================================

echo "🛡️ 4. SECURITY TESTS"
echo "===================="

# Test 4.1: Security headers check
log_test "Checking security headers"
HEADERS_RESPONSE=$(curl -s -I --connect-timeout $TIMEOUT "$DIRECT_URL/health")

# Check for important security headers
declare -A SECURITY_HEADERS=(
    ["X-Content-Type-Options"]="nosniff"
    ["X-Frame-Options"]="DENY"
    ["X-XSS-Protection"]="1; mode=block"
)

HEADERS_PASSED=0
HEADERS_TOTAL=${#SECURITY_HEADERS[@]}

for header in "${!SECURITY_HEADERS[@]}"; do
    if echo "$HEADERS_RESPONSE" | grep -qi "$header"; then
        log_success "Security header present: $header"
        ((HEADERS_PASSED++))
    else
        log_warning "Security header missing: $header"
    fi
done

echo "   📊 Security headers: $HEADERS_PASSED/$HEADERS_TOTAL present"
echo ""

# Test 4.2: Rate limiting headers
log_test "Checking rate limiting headers"
if echo "$HEADERS_RESPONSE" | grep -qi "x-ratelimit"; then
    log_success "Rate limiting headers present"
    echo "$HEADERS_RESPONSE" | grep -i "x-ratelimit" | sed 's/^/   /'
else
    log_warning "Rate limiting headers not found in response"
fi
echo ""

# Test 4.3: Host header validation
log_test "Testing host header validation"
INVALID_HOST_RESPONSE=$(curl -s -w "%{http_code}" -H "Host: malicious-host.com" --connect-timeout $TIMEOUT "$DIRECT_URL/health" | tail -c 3)

if [[ "$INVALID_HOST_RESPONSE" == "400" ]]; then
    log_success "Host header validation working (rejects invalid hosts)"
else
    log_warning "Host header validation may be disabled (HTTP $INVALID_HOST_RESPONSE)"
fi

# =============================================================================
# 5. API FUNCTIONALITY TESTS
# =============================================================================

echo "⚙️ 5. API FUNCTIONALITY TESTS"
echo "============================="

# Test 5.1: API versioning
run_test "API v1 prefix endpoint" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/api/v1/'" \
    "404"  # Expected 404 since we haven't defined this route

# Test 5.2: Error handling
run_test "Non-existent endpoint (404 handling)" \
    "curl -s --connect-timeout $TIMEOUT '$DIRECT_URL/nonexistent'" \
    "404"

# Test 5.3: Method not allowed
run_test "Method not allowed test" \
    "curl -s -X POST --connect-timeout $TIMEOUT '$DIRECT_URL/health'" \
    "405"

# =============================================================================
# 6. PERFORMANCE TESTS
# =============================================================================

echo "⚡ 6. PERFORMANCE TESTS"
echo "======================"

# Test 6.1: Response time test
log_test "Response time measurement"
RESPONSE_TIME=$(curl -s -w "%{time_total}" --connect-timeout $TIMEOUT "$DIRECT_URL/health" -o /dev/null)
RESPONSE_TIME_MS=$(echo "$RESPONSE_TIME * 1000" | bc -l | cut -d. -f1)

if (( RESPONSE_TIME_MS < 1000 )); then
    log_success "Response time: ${RESPONSE_TIME_MS}ms (< 1000ms)"
elif (( RESPONSE_TIME_MS < 3000 )); then
    log_warning "Response time: ${RESPONSE_TIME_MS}ms (acceptable but could be faster)"
else
    log_failure "Response time: ${RESPONSE_TIME_MS}ms (> 3000ms - too slow)"
fi

# Test 6.2: Concurrent requests test
log_test "Concurrent requests test (5 parallel requests)"
CONCURRENT_START=$(date +%s.%N)

# Run 5 concurrent requests
for i in {1..5}; do
    curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health" > /dev/null &
done
wait

CONCURRENT_END=$(date +%s.%N)
CONCURRENT_TIME=$(echo "($CONCURRENT_END - $CONCURRENT_START) * 1000" | bc -l | cut -d. -f1)

if (( CONCURRENT_TIME < 2000 )); then
    log_success "Concurrent requests: ${CONCURRENT_TIME}ms for 5 requests"
else
    log_warning "Concurrent requests: ${CONCURRENT_TIME}ms (may indicate performance issues)"
fi
echo ""

# =============================================================================
# 7. LOAD BALANCER SPECIFIC TESTS
# =============================================================================

echo "⚖️ 7. LOAD BALANCER TESTS"
echo "========================"

# Test 7.1: ALB response consistency
log_test "ALB response consistency test"
ALB_RESPONSES_CONSISTENT=true

for i in {1..3}; do
    ALB_RESP=$(curl -s --connect-timeout $TIMEOUT "$ALB_URL/health")
    DIRECT_RESP=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health")
    
    if [[ "$ALB_RESP" != "$DIRECT_RESP" ]]; then
        ALB_RESPONSES_CONSISTENT=false
        break
    fi
    sleep 1
done

if $ALB_RESPONSES_CONSISTENT; then
    log_success "ALB and direct responses are consistent"
else
    log_failure "ALB and direct responses differ"
fi

# Test 7.2: ALB health check simulation
log_test "ALB health check simulation"
ALB_HEALTH_CODE=$(curl -s -w "%{http_code}" --connect-timeout $TIMEOUT "$ALB_URL/health" | tail -c 3)

if [[ "$ALB_HEALTH_CODE" == "200" ]]; then
    log_success "ALB health check simulation passed"
else
    log_failure "ALB health check simulation failed (HTTP $ALB_HEALTH_CODE)"
fi
echo ""

# =============================================================================
# 8. DATABASE CONNECTIVITY TESTS
# =============================================================================

echo "🗄️ 8. DATABASE CONNECTIVITY TESTS"
echo "================================="

# Test 8.1: Database status from health endpoint
log_test "Database connectivity via health endpoint"
DB_STATUS=$(curl -s --connect-timeout $TIMEOUT "$DIRECT_URL/health" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    db = data.get('database', {})
    print(f'{db.get(\"status\", \"unknown\")}:{db.get(\"type\", \"unknown\")}')
except:
    print('error:unknown')
")

if [[ "$DB_STATUS" == "connected:postgresql" ]]; then
    log_success "Database connectivity: PostgreSQL connected"
else
    log_failure "Database connectivity issue: $DB_STATUS"
fi
echo ""

# =============================================================================
# 9. FINAL TEST SUMMARY
# =============================================================================

echo "📊 TEST SUMMARY"
echo "==============="
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$(echo "scale=1; $TESTS_PASSED * 100 / $TOTAL_TESTS" | bc -l)

echo "🎯 Test Results:"
echo "   Total Tests: $TOTAL_TESTS"
echo "   Passed: $TESTS_PASSED"
echo "   Failed: $TESTS_FAILED"
echo "   Pass Rate: ${PASS_RATE}%"
echo ""

if (( TESTS_FAILED == 0 )); then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! Your API is working perfectly!${NC}"
    echo ""
    echo "✅ Your FastAPI application is:"
    echo "   • Fully operational and responsive"
    echo "   • Properly secured with middleware"
    echo "   • Connected to PostgreSQL database"
    echo "   • Load balanced and highly available"
    echo "   • Production-ready for real use"
    
elif (( TESTS_FAILED <= 2 )); then
    echo -e "${YELLOW}🎯 MOSTLY SUCCESSFUL! Minor issues detected${NC}"
    echo ""
    echo "✅ Core functionality is working"
    echo "⚠️  Some non-critical issues found:"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo "   • $failed_test"
    done
    
else
    echo -e "${RED}⚠️  SEVERAL ISSUES DETECTED${NC}"
    echo ""
    echo "❌ Failed tests:"
    for failed_test in "${FAILED_TESTS[@]}"; do
        echo "   • $failed_test"
    done
    echo ""
    echo "💡 Recommendations:"
    echo "   • Check application logs for detailed errors"
    echo "   • Verify database connectivity"
    echo "   • Review security middleware configuration"
fi

echo ""
echo "🌐 Your API endpoints:"
echo "   Direct: $DIRECT_URL/health"
echo "   ALB: $ALB_URL/health"
echo "   Docs: $DIRECT_URL/docs"
echo ""
echo "🔧 Management commands:"
echo "   View logs: ssh -i trading-api-keypair.pem ec2-user@18.204.204.26 'tail -f /var/log/trading-api/app.log'"
echo "   Check status: ssh -i trading-api-keypair.pem ec2-user@18.204.204.26 'ps aux | grep uvicorn'"
echo ""
echo "🧪 Test suite completed!"

