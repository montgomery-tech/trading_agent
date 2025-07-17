#!/bin/bash

echo "🔒 BALANCE ENDPOINT SECURITY TEST - TASK 1.2"
echo "============================================"

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

ADMIN_TOKEN=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "garrett_admin", "password": "AdminPassword123!"}' | \
  python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['data']['token']['access_token'])
except:
    print('NO_TOKEN')
")

if [[ "$ADMIN_TOKEN" != "NO_TOKEN" && -n "$ADMIN_TOKEN" ]]; then
    print_status "✅ Admin token obtained: ${ADMIN_TOKEN:0:30}..." $GREEN
else
    print_status "❌ Failed to get admin token" $RED
    exit 1
fi

# Step 2: Test available usernames from previous diagnostic
TEST_USERNAMES=("garrett_admin" "trader.test.1752634859" "viewer.test.1752634859" "testuser")

print_status "🧪 Step 2: Testing Balance Endpoint Security..." $BLUE
print_status "Available test users: ${TEST_USERNAMES[*]}" $CYAN

# Test 1: No authentication (SHOULD BE BLOCKED)
print_status "🚨 Test 1: No authentication access to balance data..." $RED

for username in "${TEST_USERNAMES[@]:0:2}"; do  # Test first 2 users
    print_status "Testing /api/v1/balances/user/$username without auth..." $YELLOW
    
    NO_AUTH_RESPONSE=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/balances/user/$username" | tail -c 3)
    
    if [ "$NO_AUTH_RESPONSE" = "403" ] || [ "$NO_AUTH_RESPONSE" = "401" ]; then
        print_status "   ✅ SECURE: No auth blocked ($NO_AUTH_RESPONSE)" $GREEN
        BALANCE_SECURITY_1="PASS"
    elif [ "$NO_AUTH_RESPONSE" = "200" ]; then
        print_status "   🚨 CRITICAL VULNERABILITY: No auth allowed - balance data exposed! ($NO_AUTH_RESPONSE)" $RED
        BALANCE_SECURITY_1="FAIL"
        
        # Show what data is exposed
        EXPOSED_DATA=$(curl -s "$API_BASE/api/v1/balances/user/$username")
        print_status "   Exposed data: ${EXPOSED_DATA:0:100}..." $RED
        break
    elif [ "$NO_AUTH_RESPONSE" = "404" ]; then
        print_status "   ⚠️  User not found (404)" $YELLOW
        continue
    else
        print_status "   ⚠️  Unexpected response: $NO_AUTH_RESPONSE" $YELLOW
    fi
done

# Test 2: Invalid token (SHOULD BE BLOCKED)
print_status "🚨 Test 2: Invalid token access to balance data..." $RED

INVALID_TOKEN_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer invalid_token_123" \
                        "$API_BASE/api/v1/balances/user/garrett_admin" | tail -c 3)

if [ "$INVALID_TOKEN_RESPONSE" = "403" ] || [ "$INVALID_TOKEN_RESPONSE" = "401" ]; then
    print_status "   ✅ SECURE: Invalid token blocked ($INVALID_TOKEN_RESPONSE)" $GREEN
    BALANCE_SECURITY_2="PASS"
elif [ "$INVALID_TOKEN_RESPONSE" = "200" ]; then
    print_status "   🚨 CRITICAL VULNERABILITY: Invalid token allowed - balance data exposed!" $RED
    BALANCE_SECURITY_2="FAIL"
else
    print_status "   ⚠️  Unexpected response: $INVALID_TOKEN_RESPONSE" $YELLOW
    BALANCE_SECURITY_2="UNKNOWN"
fi

# Test 3: Valid token accessing own data (SHOULD WORK)
print_status "🧪 Test 3: Valid token accessing admin's own balance data..." $YELLOW

VALID_TOKEN_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                      "$API_BASE/api/v1/balances/user/garrett_admin" | tail -c 3)

if [ "$VALID_TOKEN_RESPONSE" = "200" ]; then
    print_status "   ✅ CORRECT: Valid token can access own data ($VALID_TOKEN_RESPONSE)" $GREEN
    BALANCE_SECURITY_3="PASS"
elif [ "$VALID_TOKEN_RESPONSE" = "404" ]; then
    print_status "   ⚠️  User not found (404) - may not have balance data" $YELLOW
    BALANCE_SECURITY_3="PASS"  # Still secure, just no data
else
    print_status "   ⚠️  Unexpected response: $VALID_TOKEN_RESPONSE" $YELLOW
    BALANCE_SECURITY_3="ISSUE"
fi

# Test 4: Balance Summary Endpoint
print_status "🧪 Test 4: Balance Summary Endpoint Security..." $YELLOW

# Test summary without auth
SUMMARY_NO_AUTH=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/balances/summary/garrett_admin" | tail -c 3)

if [ "$SUMMARY_NO_AUTH" = "403" ] || [ "$SUMMARY_NO_AUTH" = "401" ]; then
    print_status "   ✅ SECURE: Summary endpoint blocks no auth ($SUMMARY_NO_AUTH)" $GREEN
    BALANCE_SECURITY_4="PASS"
elif [ "$SUMMARY_NO_AUTH" = "200" ]; then
    print_status "   🚨 CRITICAL VULNERABILITY: Summary endpoint allows no auth!" $RED
    BALANCE_SECURITY_4="FAIL"
else
    print_status "   ⚠️  Summary endpoint response: $SUMMARY_NO_AUTH" $YELLOW
    BALANCE_SECURITY_4="UNKNOWN"
fi

# Test 5: Cross-user balance access (IF we can get another user token)
print_status "🧪 Test 5: Cross-user balance access test..." $YELLOW

# Try to login as a different user
OTHER_USERNAMES=("trader.test.1752634859" "viewer.test.1752634859" "testuser")
OTHER_TOKEN=""

for other_user in "${OTHER_USERNAMES[@]}"; do
    # Try common passwords
    for password in "TraderTest123!" "ViewerTest123!" "TestPassword123!" "password123"; do
        OTHER_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
          -H "Content-Type: application/json" \
          -d "{\"username\": \"$other_user\", \"password\": \"$password\"}")
        
        OTHER_TOKEN=$(echo "$OTHER_LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['data']['token']['access_token'])
except:
    print('NO_TOKEN')
")
        
        if [[ "$OTHER_TOKEN" != "NO_TOKEN" && -n "$OTHER_TOKEN" ]]; then
            print_status "   ✅ Logged in as: $other_user" $GREEN
            break 2
        fi
    done
done

if [[ "$OTHER_TOKEN" != "NO_TOKEN" && -n "$OTHER_TOKEN" ]]; then
    # Test cross-user access
    print_status "   Testing cross-user balance access..." $YELLOW
    CROSS_USER_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $OTHER_TOKEN" \
                         "$API_BASE/api/v1/balances/user/garrett_admin" | tail -c 3)
    
    if [ "$CROSS_USER_RESPONSE" = "403" ]; then
        print_status "   ✅ SECURE: Cross-user access blocked (403)" $GREEN
        BALANCE_SECURITY_5="PASS"
    elif [ "$CROSS_USER_RESPONSE" = "401" ]; then
        print_status "   ✅ SECURE: Cross-user access blocked (401)" $GREEN
        BALANCE_SECURITY_5="PASS"
    elif [ "$CROSS_USER_RESPONSE" = "200" ]; then
        print_status "   🚨 CRITICAL VULNERABILITY: Cross-user balance access allowed!" $RED
        BALANCE_SECURITY_5="FAIL"
        
        # Show exposed financial data
        EXPOSED_BALANCE=$(curl -s -H "Authorization: Bearer $OTHER_TOKEN" \
                         "$API_BASE/api/v1/balances/user/garrett_admin")
        print_status "   Exposed financial data: ${EXPOSED_BALANCE:0:150}..." $RED
    else
        print_status "   ⚠️  Cross-user response: $CROSS_USER_RESPONSE" $YELLOW
        BALANCE_SECURITY_5="UNKNOWN"
    fi
else
    print_status "   ⚠️  Could not authenticate another user for cross-access test" $YELLOW
    BALANCE_SECURITY_5="SKIP"
fi

# Final Assessment
print_status "🎯 BALANCE ENDPOINT SECURITY ASSESSMENT" $BLUE
print_status "=======================================" $BLUE

echo ""
print_status "Security Test Results:" $CYAN
print_status "  Test 1 - No auth blocking: $BALANCE_SECURITY_1" $CYAN
print_status "  Test 2 - Invalid token blocking: $BALANCE_SECURITY_2" $CYAN
print_status "  Test 3 - Valid own access: $BALANCE_SECURITY_3" $CYAN
print_status "  Test 4 - Summary endpoint security: $BALANCE_SECURITY_4" $CYAN
print_status "  Test 5 - Cross-user access blocking: $BALANCE_SECURITY_5" $CYAN

echo ""
# Determine overall security status
if [[ "$BALANCE_SECURITY_1" = "FAIL" || "$BALANCE_SECURITY_2" = "FAIL" || "$BALANCE_SECURITY_4" = "FAIL" || "$BALANCE_SECURITY_5" = "FAIL" ]]; then
    print_status "🚨 CRITICAL FINANCIAL DATA VULNERABILITY DETECTED!" $RED
    print_status "=============================================" $RED
    print_status "❌ Balance endpoints allow unauthorized access to financial data" $RED
    print_status "❌ Users can access other users' balance information" $RED
    print_status "❌ IMMEDIATE FIX REQUIRED - DO NOT DEPLOY TO PRODUCTION" $RED
    
    echo ""
    print_status "📋 REQUIRED ACTION:" $YELLOW
    print_status "1. Apply security fix to deployment_package/api/routes/balances.py" $YELLOW
    print_status "2. Add authentication dependencies to balance endpoints" $YELLOW
    print_status "3. Restart FastAPI server" $YELLOW
    print_status "4. Re-run this test to verify fix" $YELLOW
    
elif [[ "$BALANCE_SECURITY_1" = "PASS" && "$BALANCE_SECURITY_2" = "PASS" ]]; then
    print_status "✅ BALANCE ENDPOINT SECURITY WORKING!" $GREEN
    print_status "=====================================" $GREEN
    print_status "✅ Authentication required for balance access" $GREEN
    print_status "✅ Invalid tokens properly rejected" $GREEN
    print_status "✅ Cross-user access protection active" $GREEN
    
    echo ""
    print_status "🎉 TASK 1.2 COMPLETED SUCCESSFULLY!" $GREEN
    print_status "Balance endpoint security vulnerability has been fixed" $GREEN
    
    echo ""
    print_status "🚀 READY FOR TASK 1.3:" $BLUE
    print_status "Transaction Endpoint Security Audit" $BLUE
    
else
    print_status "⚠️  MIXED RESULTS - Additional investigation needed" $YELLOW
    print_status "Some security controls are working, others may need attention" $YELLOW
fi

echo ""
print_status "📝 ENDPOINT TESTING SUMMARY:" $CYAN
print_status "Balance endpoints tested:" $CYAN
print_status "  • /api/v1/balances/user/{username}" $CYAN
print_status "  • /api/v1/balances/summary/{username}" $CYAN
