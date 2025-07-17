#!/bin/bash

echo "🔒 SECURITY VALIDATION WITH FRESH TEST USERS"
echo "============================================="

API_BASE="http://localhost:8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

# Step 1: Create fresh test users
echo ""
print_status "🔧 Step 1: Creating fresh test users..." $BLUE

# Create trader user
TRADER_USERNAME="security_test_trader_$(date +%s)"
TRADER_EMAIL="$TRADER_USERNAME@example.com"
TRADER_PASSWORD="TraderTest123!"

print_status "Creating trader user: $TRADER_USERNAME" $YELLOW

TRADER_REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$TRADER_USERNAME\",
    \"email\": \"$TRADER_EMAIL\",
    \"password\": \"$TRADER_PASSWORD\",
    \"first_name\": \"Test\",
    \"last_name\": \"Trader\"
  }")

echo "Trader registration response: $TRADER_REGISTER_RESPONSE"

# Create viewer user  
VIEWER_USERNAME="security_test_viewer_$(date +%s)"
VIEWER_EMAIL="$VIEWER_USERNAME@example.com"
VIEWER_PASSWORD="ViewerTest123!"

print_status "Creating viewer user: $VIEWER_USERNAME" $YELLOW

VIEWER_REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$VIEWER_USERNAME\",
    \"email\": \"$VIEWER_EMAIL\",
    \"password\": \"$VIEWER_PASSWORD\",
    \"first_name\": \"Test\",
    \"last_name\": \"Viewer\"
  }")

echo "Viewer registration response: $VIEWER_REGISTER_RESPONSE"

# Step 2: Login and get tokens
echo ""
print_status "🔑 Step 2: Getting authentication tokens..." $BLUE

# Login trader
print_status "Logging in trader..." $YELLOW
TRADER_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$TRADER_USERNAME\", \"password\": \"$TRADER_PASSWORD\"}")

echo "Trader login response: $TRADER_LOGIN_RESPONSE"

TRADER_TOKEN=$(echo "$TRADER_LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'access_token' in data:
        print(data['access_token'])
    elif 'data' in data and 'token' in data['data'] and 'access_token' in data['data']['token']:
        print(data['data']['token']['access_token'])
    else:
        print('NO_TOKEN')
except:
    print('PARSE_ERROR')
")

# Login viewer
print_status "Logging in viewer..." $YELLOW
VIEWER_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$VIEWER_USERNAME\", \"password\": \"$VIEWER_PASSWORD\"}")

echo "Viewer login response: $VIEWER_LOGIN_RESPONSE"

VIEWER_TOKEN=$(echo "$VIEWER_LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'access_token' in data:
        print(data['access_token'])
    elif 'data' in data and 'token' in data['data'] and 'access_token' in data['data']['token']:
        print(data['data']['token']['access_token'])
    else:
        print('NO_TOKEN')
except:
    print('PARSE_ERROR')
")

# Step 3: Test security
echo ""
print_status "🚨 Step 3: Testing Cross-User Data Access Security..." $RED

if [[ "$TRADER_TOKEN" != "NO_TOKEN" && "$TRADER_TOKEN" != "PARSE_ERROR" && -n "$TRADER_TOKEN" ]]; then
    print_status "✅ Trader token obtained: ${TRADER_TOKEN:0:20}..." $GREEN
    
    # Test 1: Trader accessing viewer profile (SHOULD BE BLOCKED)
    echo ""
    print_status "Test 1: Trader accessing viewer profile (should be 403)..." $YELLOW
    RESPONSE1=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TRADER_TOKEN" \
               "$API_BASE/api/v1/users/$VIEWER_USERNAME" | tail -c 3)
    
    if [ "$RESPONSE1" = "403" ]; then
        print_status "   ✅ SECURE: Trader blocked from viewer data (403)" $GREEN
    elif [ "$RESPONSE1" = "401" ]; then
        print_status "   ✅ SECURE: Trader blocked from viewer data (401)" $GREEN
    elif [ "$RESPONSE1" = "404" ]; then
        print_status "   ⚠️  INFO: User not found (404) - check if user exists" $YELLOW
    else
        print_status "   🚨 SECURITY RISK: Trader can access viewer data ($RESPONSE1)" $RED
    fi
    
    # Test 2: Trader accessing own profile (SHOULD WORK)
    echo ""
    print_status "Test 2: Trader accessing own profile (should be 200)..." $YELLOW
    RESPONSE2=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TRADER_TOKEN" \
               "$API_BASE/api/v1/users/$TRADER_USERNAME" | tail -c 3)
    
    if [ "$RESPONSE2" = "200" ]; then
        print_status "   ✅ CORRECT: Trader can access own data (200)" $GREEN
    else
        print_status "   ❌ PROBLEM: Trader cannot access own data ($RESPONSE2)" $RED
    fi
    
else
    print_status "❌ Failed to get trader token: $TRADER_TOKEN" $RED
fi

if [[ "$VIEWER_TOKEN" != "NO_TOKEN" && "$VIEWER_TOKEN" != "PARSE_ERROR" && -n "$VIEWER_TOKEN" ]]; then
    print_status "✅ Viewer token obtained: ${VIEWER_TOKEN:0:20}..." $GREEN
    
    # Test 3: Viewer accessing trader profile (SHOULD BE BLOCKED)
    echo ""
    print_status "Test 3: Viewer accessing trader profile (should be 403)..." $YELLOW
    RESPONSE3=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $VIEWER_TOKEN" \
               "$API_BASE/api/v1/users/$TRADER_USERNAME" | tail -c 3)
    
    if [ "$RESPONSE3" = "403" ]; then
        print_status "   ✅ SECURE: Viewer blocked from trader data (403)" $GREEN
    elif [ "$RESPONSE3" = "401" ]; then
        print_status "   ✅ SECURE: Viewer blocked from trader data (401)" $GREEN
    elif [ "$RESPONSE3" = "404" ]; then
        print_status "   ⚠️  INFO: User not found (404) - check if user exists" $YELLOW
    else
        print_status "   🚨 SECURITY RISK: Viewer can access trader data ($RESPONSE3)" $RED
    fi
    
else
    print_status "❌ Failed to get viewer token: $VIEWER_TOKEN" $RED
fi

# Test 4: No authorization (SHOULD BE BLOCKED)
echo ""
print_status "Test 4: No authorization header (should be 401/403)..." $YELLOW
RESPONSE4=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/users/$TRADER_USERNAME" | tail -c 3)

if [ "$RESPONSE4" = "403" ] || [ "$RESPONSE4" = "401" ]; then
    print_status "   ✅ SECURE: No auth blocked ($RESPONSE4)" $GREEN
else
    print_status "   🚨 SECURITY RISK: No auth allowed ($RESPONSE4)" $RED
fi

# Test 5: Invalid token (SHOULD BE BLOCKED)
echo ""
print_status "Test 5: Invalid token (should be 401/403)..." $YELLOW
RESPONSE5=$(curl -s -w "%{http_code}" -H "Authorization: Bearer invalid_token_123" \
           "$API_BASE/api/v1/users/$TRADER_USERNAME" | tail -c 3)

if [ "$RESPONSE5" = "403" ] || [ "$RESPONSE5" = "401" ]; then
    print_status "   ✅ SECURE: Invalid token blocked ($RESPONSE5)" $GREEN
else
    print_status "   🚨 SECURITY RISK: Invalid token allowed ($RESPONSE5)" $RED
fi

echo ""
print_status "🎯 SECURITY TEST SUMMARY" $BLUE
print_status "=========================" $BLUE
print_status "Test Users Created:" $CYAN
print_status "  Trader: $TRADER_USERNAME" $CYAN
print_status "  Viewer: $VIEWER_USERNAME" $CYAN
print_status "" $NC
print_status "Expected Results:" $CYAN
print_status "  Cross-user access: 403 Forbidden" $CYAN
print_status "  Own data access: 200 OK" $CYAN
print_status "  No auth: 401/403 Denied" $CYAN
print_status "  Invalid token: 401/403 Denied" $CYAN
