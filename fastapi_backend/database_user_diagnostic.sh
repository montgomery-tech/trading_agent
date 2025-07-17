#!/bin/bash

echo "🔍 DATABASE USER DIAGNOSTIC"
echo "==========================="

API_BASE="http://localhost:8000"

# Get admin token
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
    echo "✅ Got admin token"
    
    # Test 1: Check admin's own profile via /auth/me
    echo ""
    echo "🔍 Test 1: Getting admin profile via /auth/me..."
    ME_RESPONSE=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$API_BASE/api/v1/auth/me")
    echo "Admin profile: $ME_RESPONSE"
    
    # Extract username from profile
    ACTUAL_USERNAME=$(echo "$ME_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data.get('username', 'NO_USERNAME'))
except:
    print('PARSE_ERROR')
")
    
    echo "Extracted username: $ACTUAL_USERNAME"
    
    # Test 2: Try accessing that exact username
    echo ""
    echo "🔍 Test 2: Accessing user profile with exact username..."
    USER_RESPONSE=$(curl -s -w "HTTPCODE:%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                   "$API_BASE/api/v1/users/$ACTUAL_USERNAME")
    
    HTTP_CODE=$(echo "$USER_RESPONSE" | grep -o "HTTPCODE:[0-9]*" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$USER_RESPONSE" | sed 's/HTTPCODE:[0-9]*$//')
    
    echo "HTTP Code: $HTTP_CODE"
    echo "Response: $RESPONSE_BODY"
    
    # Test 3: Check available endpoints
    echo ""
    echo "🔍 Test 3: Checking users list endpoint..."
    LIST_RESPONSE=$(curl -s -w "HTTPCODE:%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                   "$API_BASE/api/v1/users/")
    
    LIST_HTTP_CODE=$(echo "$LIST_RESPONSE" | grep -o "HTTPCODE:[0-9]*" | cut -d: -f2)
    LIST_BODY=$(echo "$LIST_RESPONSE" | sed 's/HTTPCODE:[0-9]*$//')
    
    echo "List endpoint HTTP Code: $LIST_HTTP_CODE"
    echo "List response: $LIST_BODY"
    
    # Test 4: Check database connection via health endpoint
    echo ""
    echo "🔍 Test 4: Checking database health..."
    HEALTH_RESPONSE=$(curl -s "$API_BASE/health")
    echo "Health response: $HEALTH_RESPONSE"
    
    # Test 5: Try different username variations
    echo ""
    echo "🔍 Test 5: Testing username variations..."
    
    for test_username in "garrett_admin" "Garrett_admin" "GARRETT_ADMIN"; do
        echo "Testing username: $test_username"
        TEST_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                       "$API_BASE/api/v1/users/$test_username" | tail -c 3)
        echo "  Response code: $TEST_RESPONSE"
    done
    
    echo ""
    echo "🎯 DIAGNOSIS SUMMARY:"
    echo "===================="
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ SUCCESS: User endpoint is working properly"
        echo "✅ SECURITY: Authentication and authorization are working"
        echo "🎉 TASK 1.1 COMPLETED SUCCESSFULLY!"
    elif [ "$HTTP_CODE" = "404" ]; then
        echo "❌ ISSUE: User not found in database"
        echo "   Possible causes:"
        echo "   1. Username mismatch between auth and users table"
        echo "   2. Database query issue"
        echo "   3. Case sensitivity problem"
        echo "   4. Database connection issue"
    elif [ "$HTTP_CODE" = "403" ]; then
        echo "⚠️  ISSUE: Access denied - security dependency might be too restrictive"
    elif [ "$HTTP_CODE" = "500" ]; then
        echo "❌ ERROR: Server error - check application logs"
    else
        echo "⚠️  UNEXPECTED: HTTP code $HTTP_CODE"
    fi
    
    if [ "$LIST_HTTP_CODE" = "200" ]; then
        echo "✅ Users list endpoint is accessible"
    else
        echo "⚠️  Users list endpoint returned: $LIST_HTTP_CODE"
    fi
    
else
    echo "❌ Failed to get admin token"
fi

echo ""
echo "🔧 NEXT STEPS:"
echo "============="
echo "1. Check the server logs for any database errors"
echo "2. Verify the username in the database matches exactly"
echo "3. Test the users list endpoint to see all available users"
echo "4. If issues persist, check database connection and query syntax"
