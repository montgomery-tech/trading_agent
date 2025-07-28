#!/bin/bash
# Comprehensive API Endpoint Testing Script
# Tests all endpoints to identify working vs broken functionality

# Configuration
BASE_URL="http://localhost:8000"
API_KEY="btapi_WIzZEd7BYB1TBBIy_CTonaCJy7Id4yNfsABWNeMVW7ww7x9qj"
AUTH_HEADER="Authorization: Bearer $API_KEY"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local use_auth=$4
    local expected_status=$5
    local data=$6

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo -e "\n${BLUE}Testing:${NC} $description"
    echo -e "${BLUE}Endpoint:${NC} $method $endpoint"

    # Build curl command
    local curl_cmd="curl -s -w '%{http_code}' -X $method"

    if [ "$use_auth" = "true" ]; then
        curl_cmd="$curl_cmd -H '$AUTH_HEADER'"
    fi

    if [ "$method" = "POST" ] || [ "$method" = "PUT" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json'"
        if [ -n "$data" ]; then
            curl_cmd="$curl_cmd -d '$data'"
        fi
    fi

    curl_cmd="$curl_cmd '$BASE_URL$endpoint'"

    # Execute request
    local response
    response=$(eval $curl_cmd)

    # Extract status code (last 3 characters)
    local status_code=${response: -3}
    local response_body=${response%???}

    # Check result
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} - Status: $status_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))

        # Show response preview for successful requests
        if [ ${#response_body} -gt 100 ]; then
            echo -e "${GREEN}Response:${NC} ${response_body:0:100}..."
        else
            echo -e "${GREEN}Response:${NC} $response_body"
        fi
    else
        echo -e "${RED}❌ FAIL${NC} - Expected: $expected_status, Got: $status_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))

        # Show error response
        if [ ${#response_body} -gt 200 ]; then
            echo -e "${RED}Error:${NC} ${response_body:0:200}..."
        else
            echo -e "${RED}Error:${NC} $response_body"
        fi
    fi
}

echo "🧪 COMPREHENSIVE API ENDPOINT TESTING"
echo "====================================="
echo "Base URL: $BASE_URL"
echo "API Key: ${API_KEY:0:20}..."
echo ""

# =============================================================================
# PUBLIC ENDPOINTS (No Authentication Required)
# =============================================================================

echo -e "\n${YELLOW}📋 PUBLIC ENDPOINTS${NC}"
echo "==================="

test_endpoint "GET" "/" "Root endpoint" false "200"
test_endpoint "GET" "/health" "Health check" false "200"
test_endpoint "GET" "/docs" "API documentation" false "200"

# =============================================================================
# API KEY MANAGEMENT (Admin Only)
# =============================================================================

echo -e "\n${YELLOW}🔑 API KEY MANAGEMENT${NC}"
echo "====================="

test_endpoint "GET" "/api/v1/admin/api-keys/stats/summary" "API key statistics" true "200"
test_endpoint "GET" "/api/v1/admin/api-keys" "List API keys" true "200"
test_endpoint "POST" "/api/v1/admin/api-keys" "Create API key" true "200" '{"name":"test_key","description":"Test key","permissions_scope":"read_only","user_id":"1c6e8997-413a-4be3-ad48-90619823a833"}'

# =============================================================================
# USER MANAGEMENT
# =============================================================================

echo -e "\n${YELLOW}👥 USER MANAGEMENT${NC}"
echo "=================="

test_endpoint "GET" "/api/v1/users" "List users" true "200"
test_endpoint "GET" "/api/v1/users/garrett_admin" "Get specific user" true "200"
test_endpoint "GET" "/api/v1/users/nonexistent" "Get nonexistent user" true "404"

# =============================================================================
# BALANCE MANAGEMENT
# =============================================================================

echo -e "\n${YELLOW}💰 BALANCE MANAGEMENT${NC}"
echo "====================="

test_endpoint "GET" "/api/v1/balances/summary/garrett_admin" "Get user balance summary" true "200"
test_endpoint "GET" "/api/v1/balances/user/garrett_admin" "Get user balances" true "200"
test_endpoint "GET" "/api/v1/balances/user/nonexistent" "Get nonexistent user balances" true "404"

# =============================================================================
# TRANSACTION MANAGEMENT
# =============================================================================

echo -e "\n${YELLOW}💳 TRANSACTION MANAGEMENT${NC}"
echo "========================="

test_endpoint "GET" "/api/v1/transactions/user/garrett_admin" "Get user transactions" true "200"
test_endpoint "GET" "/api/v1/transactions/user/nonexistent" "Get nonexistent user transactions" true "404"

# =============================================================================
# CURRENCY MANAGEMENT
# =============================================================================

echo -e "\n${YELLOW}💱 CURRENCY MANAGEMENT${NC}"
echo "======================"

test_endpoint "GET" "/api/v1/currencies" "List currencies" true "200"
test_endpoint "GET" "/api/v1/currencies/USD" "Get specific currency" true "200"
test_endpoint "GET" "/api/v1/currencies/INVALID" "Get invalid currency" true "404"

# =============================================================================
# TRADING ENDPOINTS
# =============================================================================

echo -e "\n${YELLOW}📈 TRADING ENDPOINTS${NC}"
echo "===================="

test_endpoint "GET" "/api/v1/trades/status" "Trading status" true "200"
test_endpoint "POST" "/api/v1/trades/simulate" "Simulate trade" true "200" '{"pair":"BTC/USD","side":"buy","amount":"0.001","order_type":"market"}'
test_endpoint "GET" "/api/v1/trades/pricing/BTC-USD" "Get pricing info" true "200"

# =============================================================================
# TRADING PAIRS
# =============================================================================

echo -e "\n${YELLOW}🔗 TRADING PAIRS${NC}"
echo "================"

test_endpoint "GET" "/api/v1/trading-pairs" "List trading pairs" true "200"
test_endpoint "GET" "/api/v1/trading-pairs/BTCUSD" "Get specific trading pair" true "200"

# =============================================================================
# AUTHENTICATION ENDPOINTS (Should be removed/deprecated)
# =============================================================================

echo -e "\n${YELLOW}🔐 LEGACY AUTH ENDPOINTS (Should Fail)${NC}"
echo "==========================================="

test_endpoint "POST" "/api/v1/auth/login" "Legacy login (should not exist)" false "404"
test_endpoint "POST" "/api/v1/auth/register" "Legacy register (should not exist)" false "404"

# =============================================================================
# SECURITY TESTS
# =============================================================================

echo -e "\n${YELLOW}🛡️ SECURITY TESTS${NC}"
echo "=================="

test_endpoint "GET" "/api/v1/admin/api-keys" "Admin endpoint without auth" false "401"
test_endpoint "GET" "/api/v1/users/garrett_admin" "User endpoint without auth" false "401"
test_endpoint "GET" "/api/v1/balances/summary/garrett_admin" "Balance endpoint without auth" false "401"

# Invalid API key test
echo -e "\n${BLUE}Testing:${NC} Invalid API key"
echo -e "${BLUE}Endpoint:${NC} GET /api/v1/admin/api-keys"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

INVALID_RESPONSE=$(curl -s -w '%{http_code}' -H "Authorization: Bearer invalid_key_12345" "$BASE_URL/api/v1/admin/api-keys")
INVALID_STATUS=${INVALID_RESPONSE: -3}

if [ "$INVALID_STATUS" = "401" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $INVALID_STATUS (Invalid API key rejected)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ FAIL${NC} - Expected: 401, Got: $INVALID_STATUS (Invalid API key accepted!)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo -e "\n${YELLOW}📊 TEST SUMMARY${NC}"
echo "==============="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo -e "Pass Rate: $PASS_RATE%"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo "Your API is fully functional!"
else
    echo -e "\n${YELLOW}⚠️ SOME TESTS FAILED${NC}"
    echo "Review the failed endpoints above for issues to address."
fi

echo -e "\n${BLUE}💡 NEXT STEPS:${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo "1. Review failed endpoints and fix issues"
    echo "2. Ensure all route modules are properly imported"
    echo "3. Check authentication dependencies in route files"
    echo "4. Verify database has required data for tests"
else
    echo "1. ✅ All endpoints working - ready for production!"
    echo "2. Consider implementing user-scoped data access"
    echo "3. Add comprehensive error handling"
    echo "4. Set up monitoring and logging"
fi
