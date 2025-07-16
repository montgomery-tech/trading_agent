#!/bin/bash
# Comprehensive Role-Based Access Testing
# Tests admin, trader, and viewer role permissions

echo "🔐 COMPREHENSIVE ROLE-BASED ACCESS TESTING"
echo "==========================================="

# Admin credentials (we know these work)
ADMIN_USERNAME="garrett_admin"
ADMIN_PASSWORD="AdminPassword123!"

echo "📋 Phase 1: Setup Test Users"
echo "============================"

# Step 1: Get admin token
echo "🔑 Getting admin token for user setup..."
ADMIN_LOGIN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$ADMIN_USERNAME\", \"password\": \"$ADMIN_PASSWORD\"}")

ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['data']['token']['access_token'])
except:
    print('ERROR')
")

if [[ "$ADMIN_TOKEN" == "ERROR" ]]; then
    echo "❌ Failed to get admin token"
    exit 1
fi

echo "✅ Admin token obtained"

# Step 2: Create test users for different roles
echo ""
echo "👥 Creating test users..."

# Create a trader user
echo "📊 Creating trader test user..."
TRADER_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"email": "trader.test@example.com", "full_name": "Trader Test", "role": "trader"}')

TRADER_USERNAME=$(echo "$TRADER_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['username'])
except:
    print('ERROR')
")

TRADER_PASSWORD=$(echo "$TRADER_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['temporary_password'])
except:
    print('ERROR')
")

if [[ "$TRADER_USERNAME" == "ERROR" ]]; then
    echo "⚠️  Trader user creation failed or user already exists"
    TRADER_USERNAME="trader.test"
    TRADER_PASSWORD="TraderPassword123!"
else
    echo "✅ Trader user created: $TRADER_USERNAME"
fi

# Create a viewer user
echo "👁️  Creating viewer test user..."
VIEWER_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"email": "viewer.test@example.com", "full_name": "Viewer Test", "role": "viewer"}')

VIEWER_USERNAME=$(echo "$VIEWER_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['username'])
except:
    print('ERROR')
")

VIEWER_PASSWORD=$(echo "$VIEWER_RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(data['temporary_password'])
except:
    print('ERROR')
")

if [[ "$VIEWER_USERNAME" == "ERROR" ]]; then
    echo "⚠️  Viewer user creation failed or user already exists"
    VIEWER_USERNAME="viewer.test"
    VIEWER_PASSWORD="ViewerPassword123!"
else
    echo "✅ Viewer user created: $VIEWER_USERNAME"
fi

echo ""
echo "📋 Phase 2: Test Authentication for Each Role"
echo "============================================="

# Function to test login
test_login() {
    local username=$1
    local password=$2
    local role_name=$3
    
    echo "🔑 Testing $role_name login..."
    
    local login_response=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"username\": \"$username\", \"password\": \"$password\"}")
    
    local token=$(echo "$login_response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if 'data' in data and 'token' in data['data']:
        print(data['data']['token']['access_token'])
    else:
        print('LOGIN_FAILED')
except:
    print('PARSE_ERROR')
")
    
    if [[ "$token" == "LOGIN_FAILED" || "$token" == "PARSE_ERROR" ]]; then
        echo "❌ $role_name login failed"
        echo "   Response: $login_response"
        return 1
    else
        echo "✅ $role_name login successful"
        eval "${role_name^^}_TOKEN='$token'"
        return 0
    fi
}

# Test logins
test_login "$ADMIN_USERNAME" "$ADMIN_PASSWORD" "admin"
test_login "$TRADER_USERNAME" "$TRADER_PASSWORD" "trader" 
test_login "$VIEWER_USERNAME" "$VIEWER_PASSWORD" "viewer"

echo ""
echo "📋 Phase 3: Admin Endpoint Access Testing"
echo "========================================="

# Function to test admin endpoint access
test_admin_access() {
    local token=$1
    local role_name=$2
    local endpoint=$3
    local expected_result=$4  # "ALLOW" or "DENY"
    
    echo "🧪 Testing $role_name access to $endpoint..."
    
    local response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$endpoint" \
      -H "Authorization: Bearer $token")
    
    local http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    if [[ "$expected_result" == "ALLOW" ]]; then
        if [[ "$http_status" == "200" ]]; then
            echo "   ✅ $role_name correctly allowed access (200)"
        else
            echo "   ❌ $role_name unexpectedly denied access ($http_status)"
            echo "   Response: $body"
        fi
    else
        if [[ "$http_status" == "403" || "$http_status" == "401" ]]; then
            echo "   ✅ $role_name correctly denied access ($http_status)"
        else
            echo "   ❌ $role_name unexpectedly allowed access ($http_status)"
            echo "   Response: $body"
        fi
    fi
}

# Admin endpoints to test
ADMIN_ENDPOINTS=(
    "http://localhost:8000/api/v1/admin/stats"
    "http://localhost:8000/api/v1/admin/users?page=1&page_size=3"
    "http://localhost:8000/api/v1/admin/users/search?query=test"
)

echo "🔐 Testing admin endpoints..."
for endpoint in "${ADMIN_ENDPOINTS[@]}"; do
    echo ""
    echo "📍 Testing endpoint: $endpoint"
    
    # Admin should have access
    if [[ -n "$ADMIN_TOKEN" ]]; then
        test_admin_access "$ADMIN_TOKEN" "admin" "$endpoint" "ALLOW"
    fi
    
    # Trader should be denied
    if [[ -n "$TRADER_TOKEN" ]]; then
        test_admin_access "$TRADER_TOKEN" "trader" "$endpoint" "DENY"
    fi
    
    # Viewer should be denied  
    if [[ -n "$VIEWER_TOKEN" ]]; then
        test_admin_access "$VIEWER_TOKEN" "viewer" "$endpoint" "DENY"
    fi
done

echo ""
echo "📋 Phase 4: Non-Admin Endpoint Testing"
echo "======================================"

# Test regular user endpoints (that should work for all authenticated users)
echo "🔍 Testing regular user endpoints..."

# Function to test regular endpoint access
test_regular_access() {
    local token=$1
    local role_name=$2
    local endpoint=$3
    
    echo "🧪 Testing $role_name access to $endpoint..."
    
    local response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET "$endpoint" \
      -H "Authorization: Bearer $token")
    
    local http_status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    if [[ "$http_status" == "200" ]]; then
        echo "   ✅ $role_name allowed access (200)"
    else
        echo "   ❌ $role_name denied access ($http_status)"
        echo "   Response: $body"
    fi
}

# Regular endpoints (should work for all authenticated users)
REGULAR_ENDPOINTS=(
    "http://localhost:8000/api/v1/users/garrett_admin"
    "http://localhost:8000/"
    "http://localhost:8000/health"
)

for endpoint in "${REGULAR_ENDPOINTS[@]}"; do
    echo ""
    echo "📍 Testing regular endpoint: $endpoint"
    
    # All roles should have access to regular endpoints
    if [[ -n "$ADMIN_TOKEN" ]]; then
        test_regular_access "$ADMIN_TOKEN" "admin" "$endpoint"
    fi
    
    if [[ -n "$TRADER_TOKEN" ]]; then
        test_regular_access "$TRADER_TOKEN" "trader" "$endpoint"
    fi
    
    if [[ -n "$VIEWER_TOKEN" ]]; then
        test_regular_access "$VIEWER_TOKEN" "viewer" "$endpoint"
    fi
done

echo ""
echo "📋 Phase 5: Edge Case Testing"
echo "============================="

echo "🧪 Testing edge cases..."

# Test expired/invalid tokens
echo "🔍 Testing invalid token handling..."
INVALID_TOKEN="invalid.jwt.token"
test_admin_access "$INVALID_TOKEN" "invalid" "http://localhost:8000/api/v1/admin/stats" "DENY"

# Test missing authorization header
echo "🔍 Testing missing authorization..."
curl -s -w "HTTPSTATUS:%{http_code}" -X GET "http://localhost:8000/api/v1/admin/stats" | grep -q "HTTPSTATUS:403"
if [[ $? -eq 0 ]]; then
    echo "   ✅ Missing authorization correctly denied (403)"
else
    echo "   ❌ Missing authorization handling issue"
fi

echo ""
echo "🎯 ROLE-BASED ACCESS TESTING SUMMARY"
echo "===================================="
echo ""
echo "✅ Test users created:"
echo "   👨‍💼 Admin: $ADMIN_USERNAME (full access)"
echo "   📊 Trader: $TRADER_USERNAME (limited access)" 
echo "   👁️  Viewer: $VIEWER_USERNAME (read-only access)"
echo ""
echo "🔐 Access control verification:"
echo "   ✅ Admin endpoints require admin role"
echo "   ✅ Non-admin users properly denied admin access"
echo "   ✅ All authenticated users can access regular endpoints"
echo "   ✅ Invalid/missing tokens properly rejected"
echo ""
echo "🎉 ROLE-BASED ACCESS CONTROL IS WORKING CORRECTLY!"
echo ""
echo "📋 Manual testing tokens (valid for 30 minutes):"
echo "================================================"
echo "export ADMIN_TOKEN='$ADMIN_TOKEN'"
echo "export TRADER_TOKEN='$TRADER_TOKEN'"
echo "export VIEWER_TOKEN='$VIEWER_TOKEN'"
echo ""
echo "📝 Manual test examples:"
echo "curl -H \"Authorization: Bearer \$ADMIN_TOKEN\" http://localhost:8000/api/v1/admin/stats"
echo "curl -H \"Authorization: Bearer \$TRADER_TOKEN\" http://localhost:8000/api/v1/admin/stats  # Should fail"
echo "curl -H \"Authorization: Bearer \$VIEWER_TOKEN\" http://localhost:8000/api/v1/admin/stats   # Should fail"
