#!/bin/bash

echo "🔒 SIMPLE SECURITY TEST WITH EXISTING USERS"
echo "============================================"

API_BASE="http://localhost:8000"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

# Step 1: Test without authentication (should be blocked)
echo ""
print_status "🚫 Step 1: Testing endpoint without authentication..." $BLUE

RESPONSE_NO_AUTH=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)

print_status "No auth response code: $RESPONSE_NO_AUTH" $YELLOW

if [ "$RESPONSE_NO_AUTH" = "401" ] || [ "$RESPONSE_NO_AUTH" = "403" ]; then
    print_status "✅ GOOD: No auth properly blocked ($RESPONSE_NO_AUTH)" $GREEN
    SECURITY_APPLIED="YES"
elif [ "$RESPONSE_NO_AUTH" = "404" ]; then
    print_status "⚠️  ENDPOINT ISSUE: User not found (404) - endpoint may not exist" $YELLOW
    SECURITY_APPLIED="UNKNOWN"
else
    print_status "🚨 SECURITY RISK: No auth allowed ($RESPONSE_NO_AUTH)" $RED
    SECURITY_APPLIED="NO"
fi

# Step 2: Test with invalid token (should be blocked)
echo ""
print_status "🔍 Step 2: Testing with invalid token..." $BLUE

RESPONSE_INVALID_TOKEN=$(curl -s -w "%{http_code}" \
    -H "Authorization: Bearer invalid_token_123" \
    "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)

print_status "Invalid token response code: $RESPONSE_INVALID_TOKEN" $YELLOW

if [ "$RESPONSE_INVALID_TOKEN" = "401" ] || [ "$RESPONSE_INVALID_TOKEN" = "403" ]; then
    print_status "✅ GOOD: Invalid token properly blocked ($RESPONSE_INVALID_TOKEN)" $GREEN
elif [ "$RESPONSE_INVALID_TOKEN" = "404" ]; then
    print_status "⚠️  ENDPOINT ISSUE: Still getting 404 with invalid token" $YELLOW
else
    print_status "🚨 SECURITY RISK: Invalid token allowed ($RESPONSE_INVALID_TOKEN)" $RED
fi

# Step 3: Try to login with admin user
echo ""
print_status "🔑 Step 3: Testing with admin credentials..." $BLUE

ADMIN_LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "garrett_admin", "password": "AdminPassword123!"}')

print_status "Admin login response: $ADMIN_LOGIN_RESPONSE" $YELLOW

ADMIN_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "
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

if [[ "$ADMIN_TOKEN" != "NO_TOKEN" && "$ADMIN_TOKEN" != "PARSE_ERROR" && -n "$ADMIN_TOKEN" ]]; then
    print_status "✅ Admin token obtained: ${ADMIN_TOKEN:0:30}..." $GREEN
    
    # Test admin accessing user profile
    echo ""
    print_status "Testing admin access to user profile..." $YELLOW
    
    RESPONSE_ADMIN=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)
    
    print_status "Admin access response code: $RESPONSE_ADMIN" $YELLOW
    
    if [ "$RESPONSE_ADMIN" = "200" ]; then
        print_status "✅ GOOD: Admin can access user data (200)" $GREEN
    elif [ "$RESPONSE_ADMIN" = "404" ]; then
        print_status "❌ PROBLEM: User not found (404) - database or endpoint issue" $RED
    else
        print_status "⚠️  UNEXPECTED: Admin got $RESPONSE_ADMIN" $YELLOW
    fi
    
else
    print_status "❌ Failed to get admin token: $ADMIN_TOKEN" $RED
fi

# Step 4: Check if users endpoint exists
echo ""
print_status "🔍 Step 4: Checking endpoint availability..." $BLUE

# Check API docs
DOCS_RESPONSE=$(curl -s -w "%{http_code}" "$API_BASE/docs" | tail -c 3)
print_status "API docs response: $DOCS_RESPONSE" $YELLOW

# Check root endpoint
ROOT_RESPONSE=$(curl -s -w "%{http_code}" "$API_BASE/" | tail -c 3)
print_status "Root endpoint response: $ROOT_RESPONSE" $YELLOW

# Summary
echo ""
print_status "🎯 DIAGNOSIS SUMMARY" $BLUE
print_status "====================" $BLUE

if [ "$SECURITY_APPLIED" = "YES" ]; then
    print_status "✅ SECURITY STATUS: Security fix appears to be working" $GREEN
    print_status "The 401/403 responses indicate authentication is required" $GREEN
elif [ "$SECURITY_APPLIED" = "NO" ]; then
    print_status "🚨 SECURITY STATUS: Security fix NOT applied - system is vulnerable" $RED
    print_status "Need to apply the security fix to users.py endpoint" $RED
else
    print_status "⚠️  SECURITY STATUS: Cannot determine - endpoint issues detected" $YELLOW
    print_status "404 responses suggest routing or database problems" $YELLOW
fi

echo ""
print_status "📋 Next Steps:" $CYAN
if [ "$SECURITY_APPLIED" = "NO" ]; then
    print_status "1. Apply security fix to deployment_package/api/routes/users.py" $CYAN
    print_status "2. Add: current_user = Depends(require_resource_owner_or_admin(\"username\"))" $CYAN
    print_status "3. Restart FastAPI server" $CYAN
elif [ "$SECURITY_APPLIED" = "UNKNOWN" ]; then
    print_status "1. Check if users exist in database" $CYAN
    print_status "2. Verify endpoint routing in main.py" $CYAN
    print_status "3. Check server logs for errors" $CYAN
else
    print_status "1. Test with valid user credentials" $CYAN
    print_status "2. Create test users if needed" $CYAN
    print_status "3. Proceed to balance/transaction endpoint security audit" $CYAN
fi
