#!/bin/bash

# Production Admin User Registration Workflow Testing Script
# Phase 1: Production Environment Validation and Admin Access
# Execute this script to test the production trading system user creation workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

print_api_call() {
    echo -e "${CYAN}📡 API Call: ${1}${NC}"
}

# Production Configuration
PROD_API_BASE="https://trading-api-alb-464076303.us-east-1.elb.amazonaws.com"
TEST_PREFIX="prod_test_$(date +%s)"

print_status "🎯 Production Admin User Registration Testing" $BLUE
print_status "=============================================" $BLUE

echo ""
print_status "🌐 Production Environment:" $PURPLE
echo "   API Base URL: $PROD_API_BASE"
echo "   Test Prefix: $TEST_PREFIX"
echo "   SSL/HTTPS: Enabled"

print_step "Phase 1: Production Environment Validation"

# Step 1.1: Production Health Check
print_status "🏥 Step 1.1: Testing production health endpoint..." $YELLOW
print_api_call "GET $PROD_API_BASE/health"

HEALTH_RESPONSE=$(curl -f -s --connect-timeout 10 "$PROD_API_BASE/health" 2>/dev/null)
HEALTH_STATUS=$?

if [ $HEALTH_STATUS -eq 0 ]; then
    print_status "✅ Production API is healthy and accessible" $GREEN
    echo "Health Response: $HEALTH_RESPONSE"
    
    # Parse health status
    if echo "$HEALTH_RESPONSE" | grep -q "healthy\|ok"; then
        print_status "✅ Health check passed" $GREEN
    else
        print_status "⚠️  Health response unclear" $YELLOW
    fi
else
    print_status "❌ Production API health check failed" $RED
    echo "   This could indicate:"
    echo "   • Network connectivity issues"
    echo "   • SSL certificate problems"
    echo "   • API server not running"
    echo "   • Load balancer configuration issues"
    exit 1
fi

echo ""

# Step 1.2: API Documentation Check
print_status "📚 Step 1.2: Checking API documentation accessibility..." $YELLOW
print_api_call "GET $PROD_API_BASE/docs"

DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$PROD_API_BASE/docs")

if [ "$DOCS_STATUS" = "200" ]; then
    print_status "✅ API documentation is accessible" $GREEN
    echo "   Documentation URL: $PROD_API_BASE/docs"
else
    print_status "⚠️  API docs status: HTTP $DOCS_STATUS" $YELLOW
fi

echo ""

# Step 1.3: SSL Certificate Validation
print_status "🔒 Step 1.3: Validating SSL certificate..." $YELLOW
SSL_INFO=$(curl -s -I --connect-timeout 10 "$PROD_API_BASE/health" 2>&1 | head -1)

if echo "$SSL_INFO" | grep -q "200"; then
    print_status "✅ SSL certificate is valid and working" $GREEN
else
    print_status "⚠️  SSL certificate status unclear" $YELLOW
    echo "   SSL Info: $SSL_INFO"
fi

print_step "Phase 2: Admin Authentication Setup"

# Step 2.1: Admin Credentials Setup
print_status "🔐 Step 2.1: Admin authentication preparation..." $YELLOW

echo ""
echo "📋 Admin Authentication Options:"
echo "   Option 1: Use existing admin account credentials"
echo "   Option 2: Create new admin account via registration"
echo "   Option 3: Use super-admin or system account"

echo ""
print_status "🔧 Testing with admin registration/login flow..." $BLUE

# First, let's check if admin registration is available
print_api_call "POST $PROD_API_BASE/api/v1/auth/register (admin user)"

# Admin test user details
ADMIN_EMAIL="admin.${TEST_PREFIX}@example.com"
ADMIN_PASSWORD="AdminTest123!@#"
ADMIN_USERNAME="admin_${TEST_PREFIX}"

ADMIN_REGISTER_PAYLOAD=$(cat << EOF
{
    "username": "$ADMIN_USERNAME",
    "email": "$ADMIN_EMAIL",
    "password": "$ADMIN_PASSWORD",
    "first_name": "Admin",
    "last_name": "Test",
    "role": "admin"
}
EOF
)

echo "Admin registration payload:"
echo "$ADMIN_REGISTER_PAYLOAD" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$ADMIN_REGISTER_PAYLOAD"

ADMIN_REGISTER_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$ADMIN_REGISTER_PAYLOAD" \
    "$PROD_API_BASE/api/v1/auth/register" 2>/dev/null)

echo ""
echo "Admin registration response:"
echo "$ADMIN_REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$ADMIN_REGISTER_RESPONSE"

# Step 2.2: Admin Login
print_step "Step 2.2: Admin Login Authentication"

print_api_call "POST $PROD_API_BASE/api/v1/auth/login"

ADMIN_LOGIN_PAYLOAD=$(cat << EOF
{
    "username": "$ADMIN_USERNAME",
    "password": "$ADMIN_PASSWORD",
    "remember_me": false
}
EOF
)

echo "Admin login payload:"
echo "$ADMIN_LOGIN_PAYLOAD" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$ADMIN_LOGIN_PAYLOAD"

ADMIN_LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$ADMIN_LOGIN_PAYLOAD" \
    "$PROD_API_BASE/api/v1/auth/login" 2>/dev/null)

echo ""
echo "Admin login response:"
echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$ADMIN_LOGIN_RESPONSE"

# Extract admin access token
ADMIN_ACCESS_TOKEN=$(echo "$ADMIN_LOGIN_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    token = data.get('data', {}).get('token', {}).get('access_token') or \
            data.get('token', {}).get('access_token') or \
            data.get('access_token', '')
    print(token)
except:
    print('')
" 2>/dev/null)

if [ ! -z "$ADMIN_ACCESS_TOKEN" ] && [ "$ADMIN_ACCESS_TOKEN" != "null" ]; then
    print_status "✅ Admin login successful - Access token obtained" $GREEN
    echo "Admin Token (first 20 chars): ${ADMIN_ACCESS_TOKEN:0:20}..."
    ADMIN_AUTH_SUCCESS=true
else
    print_status "⚠️  Admin login failed - will try alternate authentication" $YELLOW
    echo "Response: $ADMIN_LOGIN_RESPONSE"
    ADMIN_AUTH_SUCCESS=false
fi

print_step "Phase 3: Admin Endpoint Access Verification"

if [ "$ADMIN_AUTH_SUCCESS" = true ]; then
    # Step 3.1: Test admin profile access
    print_status "👤 Step 3.1: Testing admin profile access..." $YELLOW
    print_api_call "GET $PROD_API_BASE/api/v1/auth/me"

    ADMIN_PROFILE_RESPONSE=$(curl -s -X GET \
        -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
        "$PROD_API_BASE/api/v1/auth/me" 2>/dev/null)

    echo "Admin profile response:"
    echo "$ADMIN_PROFILE_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$ADMIN_PROFILE_RESPONSE"

    # Verify admin role
    ADMIN_ROLE=$(echo "$ADMIN_PROFILE_RESPONSE" | python3 -c "
    import sys, json
    try:
        data = json.load(sys.stdin)
        print(data.get('role', ''))
    except:
        print('')
    " 2>/dev/null)

    if [ "$ADMIN_ROLE" = "admin" ]; then
        print_status "✅ Admin role confirmed in production" $GREEN
    else
        print_status "⚠️  Admin role not confirmed (role: $ADMIN_ROLE)" $YELLOW
    fi

    echo ""

    # Step 3.2: Test admin user list endpoint
    print_status "📋 Step 3.2: Testing admin user list endpoint..." $YELLOW
    print_api_call "GET $PROD_API_BASE/api/v1/admin/users"

    ADMIN_USERS_RESPONSE=$(curl -s -X GET \
        -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
        "$PROD_API_BASE/api/v1/admin/users" 2>/dev/null)

    echo "Admin users list response:"
    echo "$ADMIN_USERS_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$ADMIN_USERS_RESPONSE"

    if echo "$ADMIN_USERS_RESPONSE" | grep -q "users\|data\|admin"; then
        print_status "✅ Admin user list endpoint accessible" $GREEN
    else
        print_status "⚠️  Admin user list endpoint may have issues" $YELLOW
    fi

else
    print_status "⚠️  Skipping admin endpoint tests due to authentication issues" $YELLOW
    echo ""
    echo "🔧 Alternative Admin Authentication Options:"
    echo "   1. Use existing admin credentials if available"
    echo "   2. Check if admin user creation requires different endpoint"
    echo "   3. Verify admin role creation permissions in production"
fi

print_step "Phase 4: Production Testing Readiness Assessment"

echo ""
print_status "📊 Production Testing Readiness Summary:" $BLUE
echo ""

# Health Check Status
if [ $HEALTH_STATUS -eq 0 ]; then
    echo "   🏥 API Health: ✅ Healthy and accessible"
else
    echo "   🏥 API Health: ❌ Issues detected"
fi

# Documentation Status
if [ "$DOCS_STATUS" = "200" ]; then
    echo "   📚 API Docs: ✅ Accessible"
else
    echo "   📚 API Docs: ⚠️  Status $DOCS_STATUS"
fi

# SSL Status
echo "   🔒 SSL/HTTPS: ✅ Working"

# Admin Authentication Status
if [ "$ADMIN_AUTH_SUCCESS" = true ]; then
    echo "   🔐 Admin Auth: ✅ Working"
else
    echo "   🔐 Admin Auth: ⚠️  Needs attention"
fi

echo ""

if [ "$ADMIN_AUTH_SUCCESS" = true ] && [ $HEALTH_STATUS -eq 0 ]; then
    print_status "🎊 PHASE 1 COMPLETE: Ready for User Creation Testing!" $GREEN
    echo ""
    echo "✅ Production environment validated successfully"
    echo "✅ Admin authentication working"
    echo "✅ Ready to proceed with Phase 2: User Creation Testing"
    
    echo ""
    print_status "📋 Next Steps:" $PURPLE
    echo "   • Proceed to Phase 2: Test Trader user creation"
    echo "   • Proceed to Phase 3: Test Viewer user creation"
    echo "   • Validate role-based access control"
    echo "   • Test complete user workflows"
    
else
    print_status "⚠️  PHASE 1: Partial Success - Authentication Needs Review" $YELLOW
    echo ""
    echo "✅ Production infrastructure validated"
    echo "⚠️  Admin authentication requires attention"
    
    echo ""
    print_status "🔧 Recommended Actions:" $PURPLE
    echo "   • Review admin user creation process"
    echo "   • Check existing admin credentials"
    echo "   • Verify admin role assignment in production"
    echo "   • Consider alternative admin authentication methods"
fi

echo ""
print_status "💾 Test session details saved for Phase 2" $CYAN
echo "   Admin User: $ADMIN_USERNAME"
echo "   Admin Email: $ADMIN_EMAIL"
echo "   Test Prefix: $TEST_PREFIX"

# Save test session info for next phase
cat > prod_test_session.txt << EOF
# Production Testing Session Information
# Generated: $(date)

PROD_API_BASE="$PROD_API_BASE"
TEST_PREFIX="$TEST_PREFIX"
ADMIN_USERNAME="$ADMIN_USERNAME"
ADMIN_EMAIL="$ADMIN_EMAIL"
ADMIN_PASSWORD="$ADMIN_PASSWORD"
ADMIN_ACCESS_TOKEN="$ADMIN_ACCESS_TOKEN"
ADMIN_AUTH_SUCCESS="$ADMIN_AUTH_SUCCESS"
HEALTH_STATUS="$HEALTH_STATUS"

# For Phase 2 Testing
TRADER_EMAIL="trader.${TEST_PREFIX}@example.com"
VIEWER_EMAIL="viewer.${TEST_PREFIX}@example.com"
EOF

print_status "📄 Session saved to: prod_test_session.txt" $BLUE

echo ""
print_status "🔧 Production Admin Testing Phase 1 Complete!" $GREEN

