#!/bin/bash
# Admin Authentication Testing Commands
# Test the enhanced admin routes with authentication protection

echo "🔐 ADMIN AUTHENTICATION TESTING"
echo "================================"

# Step 1: Test unauthenticated access (should fail with 401)
echo "🚫 Step 1: Testing unauthenticated access (should return 401)..."
echo "Command:"
echo 'curl -X GET "http://localhost:8000/api/v1/admin/users/search?query=garrett"'
echo ""
echo "Response:"
curl -X GET "http://localhost:8000/api/v1/admin/users/search?query=garrett"
echo ""
echo ""

# Step 2: Login to get admin token
echo "🔑 Step 2: Getting admin authentication token..."
echo "Command:"
echo 'curl -X POST "http://localhost:8000/api/v1/auth/login" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"username": "garrett_admin", "password": "AdminPassword123!"}'"'"
echo ""
echo "Response:"

LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "garrett_admin", "password": "AdminPassword123!"}')

echo "$LOGIN_RESPONSE"
echo ""

# Extract the access token from the response
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    # Handle nested token structure
    if 'data' in data and 'token' in data['data']:
        print(data['data']['token']['access_token'])
    elif 'token' in data:
        print(data['token']['access_token'])
    elif 'access_token' in data:
        print(data['access_token'])
    else:
        print('TOKEN_NOT_FOUND')
except:
    print('PARSE_ERROR')
")

if [[ "$TOKEN" == "TOKEN_NOT_FOUND" || "$TOKEN" == "PARSE_ERROR" || -z "$TOKEN" ]]; then
    echo "❌ Failed to extract token from login response"
    echo "Please check the login response above and manually extract the token"
    echo ""
    echo "Manual token extraction:"
    echo "TOKEN='YOUR_ACCESS_TOKEN_HERE'"
    echo ""
    exit 1
fi

echo "✅ Token extracted successfully!"
echo "Token: ${TOKEN:0:50}..."
echo ""

# Step 3: Test authenticated admin endpoints
echo "🔓 Step 3: Testing authenticated admin endpoints..."
echo ""

echo "📊 Testing new admin stats endpoint:"
echo "Command:"
echo "curl -X GET \"http://localhost:8000/api/v1/admin/stats\" \\"
echo "  -H \"Authorization: Bearer \$TOKEN\""
echo ""
echo "Response:"
curl -s -X GET "http://localhost:8000/api/v1/admin/stats" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "🔍 Testing user search with authentication:"
echo "Command:"
echo "curl -X GET \"http://localhost:8000/api/v1/admin/users/search?query=garrett\" \\"
echo "  -H \"Authorization: Bearer \$TOKEN\""
echo ""
echo "Response:"
curl -s -X GET "http://localhost:8000/api/v1/admin/users/search?query=garrett" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "📋 Testing user list with authentication:"
echo "Command:"
echo "curl -X GET \"http://localhost:8000/api/v1/admin/users?page=1&page_size=5\" \\"
echo "  -H \"Authorization: Bearer \$TOKEN\""
echo ""
echo "Response:"
curl -s -X GET "http://localhost:8000/api/v1/admin/users?page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

# Step 4: Test role management
echo "🎭 Testing role management (if other users exist):"
echo "Command to update a user role (replace USER_ID with actual ID):"
echo "curl -X PUT \"http://localhost:8000/api/v1/admin/users/USER_ID/role\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
echo "  -d '{\"role\": \"viewer\", \"reason\": \"Testing role update\"}'"
echo ""

# Step 5: Test user creation
echo "👤 Testing user creation:"
echo "Command:"
echo "curl -X POST \"http://localhost:8000/api/v1/admin/users\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
echo "  -d '{\"email\": \"testuser@example.com\", \"full_name\": \"Test User\", \"role\": \"trader\"}'"
echo ""
echo "Response:"
curl -s -X POST "http://localhost:8000/api/v1/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"email": "testuser@example.com", "full_name": "Test User", "role": "trader"}' | python3 -m json.tool
echo ""

echo "✅ AUTHENTICATION TESTING COMPLETE"
echo "=================================="
echo ""
echo "🎯 Summary of what to verify:"
echo "1. ❌ Unauthenticated requests should return 401 Unauthorized"
echo "2. ✅ Login should return a valid JWT token"
echo "3. ✅ Authenticated requests should work with proper token"
echo "4. ✅ All admin endpoints should be accessible with admin token"
echo "5. ✅ New /admin/stats endpoint should return comprehensive statistics"
echo ""
echo "📝 Notes:"
echo "- If any endpoint returns 401 with a valid token, check token expiration"
echo "- If any endpoint returns 403, verify the user has admin role"
echo "- User creation may fail if email already exists (that's expected)"
echo ""
echo "🔑 Token for manual testing:"
echo "export ADMIN_TOKEN='$TOKEN'"
echo ""
echo "🧪 Manual test command examples:"
echo "curl -H \"Authorization: Bearer \$ADMIN_TOKEN\" http://localhost:8000/api/v1/admin/stats"
echo "curl -H \"Authorization: Bearer \$ADMIN_TOKEN\" http://localhost:8000/api/v1/admin/users"
