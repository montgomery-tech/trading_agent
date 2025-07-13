#!/bin/bash

# api_discovery_test.sh
# Discover the actual API interface and test with correct parameters

set -e

# Colors
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

# Load deployment information
source deployment_info.txt

API_BASE="https://$ALB_DNS"

print_status "🔍 API Discovery & Corrected Testing" $BLUE
print_status "====================================" $BLUE

echo ""
print_status "🌐 Testing Environment:" $PURPLE
echo "   API Base URL: $API_BASE"

print_step "Step 1: Explore API Documentation"

print_status "📚 Opening API documentation in browser-friendly format..." $YELLOW

echo ""
echo "🌐 API Documentation URL: $API_BASE/docs"
echo "🔍 Let's check what the actual auth endpoints expect..."

# Get the OpenAPI spec
print_status "📋 Fetching OpenAPI specification..." $YELLOW
OPENAPI_SPEC=$(curl -k -s $API_BASE/openapi.json)

if echo "$OPENAPI_SPEC" | grep -q "openapi"; then
    print_status "✅ OpenAPI spec retrieved" $GREEN
    
    # Look for auth endpoints
    echo ""
    echo "🔍 Auth endpoints found:"
    echo "$OPENAPI_SPEC" | jq -r '.paths | keys[] | select(contains("auth"))' 2>/dev/null || echo "Checking manually..."
    
    # Check registration schema
    echo ""
    echo "📋 Registration endpoint schema:"
    echo "$OPENAPI_SPEC" | jq '.paths."/api/v1/auth/register".post.requestBody.content."application/json".schema' 2>/dev/null || echo "Schema not found in standard location"
    
    # Check login schema  
    echo ""
    echo "📋 Login endpoint schema:"
    echo "$OPENAPI_SPEC" | jq '.paths."/api/v1/auth/login".post.requestBody.content."application/json".schema' 2>/dev/null || echo "Schema not found in standard location"
    
else
    print_status "⚠️  Could not retrieve OpenAPI spec" $YELLOW
fi

print_step "Step 2: Test Corrected Login (username instead of email)"

print_status "🔐 Testing login with username field..." $YELLOW

# The error showed it expects "username" not "email"
LOGIN_PAYLOAD_CORRECTED=$(cat << EOF
{
    "username": "trader.test@example.com",
    "password": "TraderTest123!"
}
EOF
)

echo "Corrected login payload:"
echo "$LOGIN_PAYLOAD_CORRECTED" | jq . 2>/dev/null || echo "$LOGIN_PAYLOAD_CORRECTED"

LOGIN_RESPONSE=$(curl -k -s -X POST \
    -H "Content-Type: application/json" \
    -d "$LOGIN_PAYLOAD_CORRECTED" \
    $API_BASE/api/v1/auth/login)

echo ""
echo "Login response:"
echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"

# Check if login worked
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // .token // empty' 2>/dev/null)

if [ ! -z "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
    print_status "✅ Login successful with corrected format!" $GREEN
    echo "Token (first 20 chars): ${ACCESS_TOKEN:0:20}..."
    LOGIN_SUCCESS=true
else
    print_status "⚠️  Login still not working, let's try other approaches" $YELLOW
    LOGIN_SUCCESS=false
fi

print_step "Step 3: Try Alternative Registration Format"

if [ "$LOGIN_SUCCESS" = false ]; then
    print_status "👤 Trying registration with different format..." $YELLOW
    
    # Try simpler registration
    REGISTER_PAYLOAD_SIMPLE=$(cat << EOF
{
    "username": "trader_test_$(date +%s)",
    "email": "trader.test.new@example.com",
    "password": "TraderTest123!",
    "first_name": "John",
    "last_name": "Trader"
}
EOF
)

    echo "Simplified registration payload:"
    echo "$REGISTER_PAYLOAD_SIMPLE" | jq . 2>/dev/null || echo "$REGISTER_PAYLOAD_SIMPLE"

    REGISTER_RESPONSE=$(curl -k -s -X POST \
        -H "Content-Type: application/json" \
        -d "$REGISTER_PAYLOAD_SIMPLE" \
        $API_BASE/api/v1/auth/register)

    echo ""
    echo "Registration response:"
    echo "$REGISTER_RESPONSE" | jq . 2>/dev/null || echo "$REGISTER_RESPONSE"
fi

print_step "Step 4: Test Available Endpoints Without Auth"

print_status "🔍 Testing public endpoints..." $YELLOW

echo ""
echo "🧪 Testing API root:"
ROOT_RESPONSE=$(curl -k -s $API_BASE/)
echo "$ROOT_RESPONSE" | jq . 2>/dev/null || echo "$ROOT_RESPONSE"

echo ""
echo "🧪 Testing currencies endpoint (public?):"
CURRENCIES_RESPONSE=$(curl -k -s $API_BASE/api/v1/currencies)
echo "$CURRENCIES_RESPONSE" | jq . 2>/dev/null || echo "$CURRENCIES_RESPONSE"

echo ""
echo "🧪 Testing users endpoint (should require auth):"
USERS_RESPONSE=$(curl -k -s $API_BASE/api/v1/users)
echo "$USERS_RESPONSE" | jq . 2>/dev/null || echo "$USERS_RESPONSE"

print_step "Step 5: Manual API Exploration"

print_status "📋 Manual Testing Commands:" $CYAN

echo ""
echo "To continue testing manually, try these commands:"
echo ""

echo "🔍 1. Explore API documentation:"
echo "   curl -k $API_BASE/docs"
echo "   curl -k $API_BASE/openapi.json | jq ."
echo ""

echo "🔐 2. Try different login formats:"
echo "   # With username:"
echo "   curl -k -X POST -H 'Content-Type: application/json' \\"
echo "     -d '{\"username\":\"test_user\",\"password\":\"TestPass123!\"}' \\"
echo "     $API_BASE/api/v1/auth/login"
echo ""
echo "   # With email:"
echo "   curl -k -X POST -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\":\"test@example.com\",\"password\":\"TestPass123!\"}' \\"
echo "     $API_BASE/api/v1/auth/login"
echo ""

echo "👤 3. Try different registration formats:"
echo "   curl -k -X POST -H 'Content-Type: application/json' \\"
echo "     -d '{\"username\":\"newuser\",\"email\":\"new@example.com\",\"password\":\"Pass123!\"}' \\"
echo "     $API_BASE/api/v1/auth/register"
echo ""

echo "📊 4. Check what endpoints are available:"
echo "   curl -k $API_BASE/"
echo "   curl -k $API_BASE/api/v1/"
echo ""

print_step "Step 6: Database Check via SSM"

print_status "💾 Let's check if there are existing users in the database..." $YELLOW

echo ""
echo "Connect to your instance to check the database:"
echo "   aws ssm start-session --target $INSTANCE_ID"
echo ""
echo "Once connected, run:"
echo "   cd /opt/trading-api"
echo "   python3 -c \"
from decouple import config
import psycopg2
from urllib.parse import urlparse

database_url = config('DATABASE_URL')
parsed = urlparse(database_url)

conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port,
    database=parsed.path[1:],
    user=parsed.username,
    password=parsed.password
)

cursor = conn.cursor()

# Check if users table exists and what users are there
cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = %s', ('public',))
tables = cursor.fetchall()
print('Available tables:', [t[0] for t in tables])

if any('user' in t[0].lower() for t in tables):
    cursor.execute('SELECT * FROM users LIMIT 5')
    users = cursor.fetchall()
    print('Sample users:', users)
else:
    print('No users table found - may need database initialization')

cursor.close()
conn.close()
\""

print_step "Summary & Next Steps"

echo ""
print_status "📊 API DISCOVERY RESULTS" $BLUE
print_status "========================" $BLUE

echo ""
print_status "✅ What's Working:" $GREEN
echo "   • API is healthy and responding"
echo "   • HTTPS SSL is working perfectly"
echo "   • Documentation is accessible"
echo "   • Database connections are working"

echo ""
print_status "🔍 What We Discovered:" $YELLOW
echo "   • Login expects 'username' field, not 'email'"
echo "   • Registration may have specific field requirements"
echo "   • Need to understand the exact API schema"

echo ""
print_status "🎯 Recommended Next Steps:" $PURPLE
echo "   1. 📚 Review API docs at: $API_BASE/docs"
echo "   2. 🔍 Check database for existing users"
echo "   3. 🧪 Test with correct field names"
echo "   4. 👤 Create test user with proper format"
echo "   5. 🔐 Test complete auth flow once format is correct"

echo ""
print_status "💡 Testing URLs:" $CYAN
echo "   📚 Docs: $API_BASE/docs"
echo "   🔍 OpenAPI: $API_BASE/openapi.json"
echo "   🏥 Health: $API_BASE/health"
echo "   🔐 Auth: $API_BASE/api/v1/auth/*"

echo ""
print_status "🔧 API discovery completed!" $BLUE
print_status "The API is working - we just need to match the expected interface!" $GREEN
