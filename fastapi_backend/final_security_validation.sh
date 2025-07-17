#!/bin/bash

echo "🔒 FINAL SECURITY VALIDATION - TASK 1.1 VERIFICATION"
echo "===================================================="

API_BASE="http://localhost:8000"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

# Step 1: Get admin token
print_status "🔑 Step 1: Getting admin authentication..." $BLUE

ADMIN_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "garrett_admin", "password": "AdminPassword123!"}')

ADMIN_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['data']['token']['access_token'])
except:
    print('NO_TOKEN')
")

ADMIN_USERNAME=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['data']['user']['username'])
except:
    print('NO_USERNAME')
")

print_status "Admin username: $ADMIN_USERNAME" $CYAN
print_status "Admin token: ${ADMIN_TOKEN:0:30}..." $CYAN

# Step 2: Create a test user for cross-access testing
print_status "🔧 Step 2: Creating test user for cross-access validation..." $BLUE

TEST_USERNAME="final_security_test_$(date +%s)"
TEST_PASSWORD="SecureTest123!"

REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$TEST_USERNAME\",
    \"email\": \"$TEST_USERNAME@example.com\",
    \"password\": \"$TEST_PASSWORD\",
    \"first_name\": \"Security\",
    \"last_name\": \"Test\"
  }")

print_status "Registration response: $REGISTER_RESPONSE" $CYAN

# Login test user
TEST_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$TEST_USERNAME\", \"password\": \"$TEST_PASSWORD\"}")

TEST_TOKEN=$(echo "$TEST_LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['data']['token']['access_token'])
except:
    print('NO_TOKEN')
")

# Step 3: CRITICAL SECURITY TESTS
print_status "🚨 Step 3: CRITICAL CROSS-USER SECURITY TESTS" $RED
print_status "==============================================" $RED

if [[ "$TEST_TOKEN" != "NO_TOKEN" && -n "$TEST_TOKEN" ]]; then
    print_status "✅ Test user created and authenticated" $GREEN
    
    # Test 1: Regular user trying to access admin profile (MUST BE BLOCKED)
    print_status "Test 1: Regular user accessing admin profile..." $YELLOW
    CROSS_ACCESS_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TEST_TOKEN" \
                           "$API_BASE/api/v1/users/$ADMIN_USERNAME" | tail -c 3)
    
    if [ "$CROSS_ACCESS_RESPONSE" = "403" ]; then
        print_status "   ✅ SECURE: Cross-user access properly blocked (403)" $GREEN
        SECURITY_TEST_1="PASS"
    elif [ "$CROSS_ACCESS_RESPONSE" = "401" ]; then
        print_status "   ✅ SECURE: Cross-user access properly blocked (401)" $GREEN
        SECURITY_TEST_1="PASS"
    elif [ "$CROSS_ACCESS_RESPONSE" = "200" ]; then
        print_status "   🚨 CRITICAL VULNERABILITY: Cross-user access allowed!" $RED
        SECURITY_TEST_1="FAIL"
    else
        print_status "   ⚠️  Unexpected response: $CROSS_ACCESS_RESPONSE" $YELLOW
        SECURITY_TEST_1="UNKNOWN"
    fi
    
    # Test 2: Regular user accessing own profile (SHOULD WORK)
    print_status "Test 2: Regular user accessing own profile..." $YELLOW
    OWN_ACCESS_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TEST_TOKEN" \
                         "$API_BASE/api/v1/users/$TEST_USERNAME" | tail -c 3)
    
    if [ "$OWN_ACCESS_RESPONSE" = "200" ]; then
        print_status "   ✅ CORRECT: User can access own profile (200)" $GREEN
        SECURITY_TEST_2="PASS"
    else
        print_status "   ⚠️  Issue: User cannot access own profile ($OWN_ACCESS_RESPONSE)" $YELLOW
        SECURITY_TEST_2="ISSUE"
    fi
    
else
    print_status "❌ Could not create test user - using existing admin only" $RED
    SECURITY_TEST_1="SKIP"
    SECURITY_TEST_2="SKIP"
fi

# Test 3: Admin accessing user profile (SHOULD WORK)
print_status "Test 3: Admin accessing user profile..." $YELLOW
if [[ "$TEST_USERNAME" != "" ]]; then
    ADMIN_ACCESS_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                           "$API_BASE/api/v1/users/$TEST_USERNAME" | tail -c 3)
else
    ADMIN_ACCESS_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                           "$API_BASE/api/v1/users/$ADMIN_USERNAME" | tail -c 3)
fi

if [ "$ADMIN_ACCESS_RESPONSE" = "200" ]; then
    print_status "   ✅ CORRECT: Admin can access user profiles (200)" $GREEN
    SECURITY_TEST_3="PASS"
else
    print_status "   ⚠️  Issue: Admin access returned $ADMIN_ACCESS_RESPONSE" $YELLOW
    SECURITY_TEST_3="ISSUE"
fi

# Test 4: No authentication (MUST BE BLOCKED)
print_status "Test 4: No authentication header..." $YELLOW
NO_AUTH_RESPONSE=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/users/$ADMIN_USERNAME" | tail -c 3)

if [ "$NO_AUTH_RESPONSE" = "403" ] || [ "$NO_AUTH_RESPONSE" = "401" ]; then
    print_status "   ✅ SECURE: No authentication properly blocked ($NO_AUTH_RESPONSE)" $GREEN
    SECURITY_TEST_4="PASS"
else
    print_status "   🚨 SECURITY RISK: No authentication allowed ($NO_AUTH_RESPONSE)" $RED
    SECURITY_TEST_4="FAIL"
fi

# Test 5: Invalid token (MUST BE BLOCKED)
print_status "Test 5: Invalid authentication token..." $YELLOW
INVALID_AUTH_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer invalid_token_123" \
                       "$API_BASE/api/v1/users/$ADMIN_USERNAME" | tail -c 3)

if [ "$INVALID_AUTH_RESPONSE" = "403" ] || [ "$INVALID_AUTH_RESPONSE" = "401" ]; then
    print_status "   ✅ SECURE: Invalid token properly blocked ($INVALID_AUTH_RESPONSE)" $GREEN
    SECURITY_TEST_5="PASS"
else
    print_status "   🚨 SECURITY RISK: Invalid token allowed ($INVALID_AUTH_RESPONSE)" $RED
    SECURITY_TEST_5="FAIL"
fi

# Final Assessment
print_status "🎯 FINAL SECURITY ASSESSMENT" $BLUE
print_status "============================" $BLUE

echo ""
print_status "Security Test Results:" $CYAN
print_status "  Test 1 - Cross-user access blocking: $SECURITY_TEST_1" $CYAN
print_status "  Test 2 - Own profile access: $SECURITY_TEST_2" $CYAN
print_status "  Test 3 - Admin profile access: $SECURITY_TEST_3" $CYAN
print_status "  Test 4 - No authentication blocking: $SECURITY_TEST_4" $CYAN
print_status "  Test 5 - Invalid token blocking: $SECURITY_TEST_5" $CYAN

echo ""
if [[ "$SECURITY_TEST_1" = "PASS" && "$SECURITY_TEST_4" = "PASS" && "$SECURITY_TEST_5" = "PASS" ]]; then
    print_status "🎉 TASK 1.1 COMPLETED SUCCESSFULLY!" $GREEN
    print_status "✅ User profile endpoint security is properly implemented" $GREEN
    print_status "✅ Cross-user data access is blocked" $GREEN
    print_status "✅ Authentication is required" $GREEN
    print_status "✅ Resource ownership validation is working" $GREEN
    
    echo ""
    print_status "📋 READY FOR NEXT TASK:" $BLUE
    print_status "Task 1.2: Audit Balance Endpoint Security" $BLUE
    print_status "Task 1.3: Audit Transaction Endpoint Security" $BLUE
    
elif [[ "$SECURITY_TEST_1" = "FAIL" || "$SECURITY_TEST_4" = "FAIL" || "$SECURITY_TEST_5" = "FAIL" ]]; then
    print_status "🚨 CRITICAL SECURITY VULNERABILITIES DETECTED!" $RED
    print_status "System is not safe for production deployment" $RED
else
    print_status "⚠️  MIXED RESULTS - Additional investigation needed" $YELLOW
fi
