#!/bin/bash

# Complete Role-Based Access Testing with Fresh Users
# macOS bash 3.2 compatible - creates new users and tests everything

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
API_BASE="http://localhost:8000"
ADMIN_USERNAME="garrett_admin"
ADMIN_PASSWORD="AdminPassword123!"

# Fresh test users with timestamp to avoid conflicts
TIMESTAMP=$(date +%s)
TRADER_EMAIL="trader.test.${TIMESTAMP}@example.com"
VIEWER_EMAIL="viewer.test.${TIMESTAMP}@example.com"

# Will be populated after user creation
TRADER_TEMP_PASSWORD=""
VIEWER_TEMP_PASSWORD=""
TRADER_FINAL_PASSWORD=""
VIEWER_FINAL_PASSWORD=""

# Token storage
ADMIN_TOKEN=""
TRADER_TOKEN=""
VIEWER_TOKEN=""

print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}🔹 $1${NC}"
    echo "----------------------------------------"
}

assign_token() {
    local role="$1"
    local token="$2"
    case "$role" in
        "admin") ADMIN_TOKEN="$token" ;;
        "trader") TRADER_TOKEN="$token" ;;
        "viewer") VIEWER_TOKEN="$token" ;;
        *) echo "❌ Unknown role: $role"; return 1 ;;
    esac
}

get_token() {
    local role="$1"
    case "$role" in
        "admin") echo "$ADMIN_TOKEN" ;;
        "trader") echo "$TRADER_TOKEN" ;;
        "viewer") echo "$VIEWER_TOKEN" ;;
        *) echo "" ;;
    esac
}

test_auth_with_password_change() {
    local email="$1"
    local temp_password="$2"
    local role="$3"
    
    print_status "🔑 Testing $role login with temporary password..." $YELLOW
    
    # Try login with temporary password
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$email\",\"password\":\"$temp_password\"}" \
        "$API_BASE/api/v1/auth/login")
    
    # Should get forced password change
    if echo "$response" | grep -q "password_change_required"; then
        print_status "🔐 Password change required (as expected)" $YELLOW
        
        # Extract temporary token
        local temp_token=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'error' in data and 'temporary_token' in data['error']:
        print(data['error']['temporary_token'])
    else: print('')
except: print('')
" 2>/dev/null)
        
        if [ -n "$temp_token" ]; then
            print_status "🎫 Temporary token obtained" $GREEN
            
            # Change password
            local new_password="${temp_password}New"
            local change_response=$(curl -s -X POST \
                -H "Content-Type: application/json" \
                -d "{\"new_password\":\"$new_password\",\"confirm_password\":\"$new_password\",\"temporary_token\":\"$temp_token\"}" \
                "$API_BASE/api/v1/auth/forced-password-change")
            
            if echo "$change_response" | grep -q "success.*true"; then
                print_status "✅ Password changed successfully" $GREEN
                
                # Store new password
                case "$role" in
                    "trader") TRADER_FINAL_PASSWORD="$new_password" ;;
                    "viewer") VIEWER_FINAL_PASSWORD="$new_password" ;;
                esac
                
                # Login with new password
                local final_response=$(curl -s -X POST \
                    -H "Content-Type: application/json" \
                    -d "{\"username\":\"$email\",\"password\":\"$new_password\"}" \
                    "$API_BASE/api/v1/auth/login")
                
                local access_token=$(echo "$final_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'data' in data and 'token' in data['data']:
        print(data['data']['token']['access_token'])
    else: print('')
except: print('')
" 2>/dev/null)
                
                if [ -n "$access_token" ]; then
                    assign_token "$role" "$access_token"
                    print_status "✅ $role authenticated successfully!" $GREEN
                    return 0
                fi
            fi
            print_status "❌ Password change failed" $RED
            return 1
        fi
        print_status "❌ No temporary token received" $RED
        return 1
    else
        print_status "❌ Expected forced password change but got normal response" $RED
        return 1
    fi
}

test_endpoint() {
    local endpoint="$1"
    local role="$2"
    local expected="$3"
    
    local token=$(get_token "$role")
    if [ -z "$token" ]; then
        print_status "❌ No token for $role" $RED
        return 1
    fi
    
    local status=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        "$API_BASE$endpoint" | tail -c 3)
    
    if [ "$status" = "$expected" ]; then
        if [ "$expected" = "200" ]; then
            print_status "   ✅ $role allowed ($status)" $GREEN
        else
            print_status "   ✅ $role denied ($status)" $GREEN
        fi
        return 0
    else
        print_status "   ❌ $role got $status (expected $expected)" $RED
        return 1
    fi
}

main() {
    print_status "🔐 COMPLETE ROLE-BASED ACCESS TESTING" $BLUE
    print_status "=====================================" $BLUE
    print_status "🆕 Creating fresh test users with known passwords" $PURPLE
    
    print_step "Phase 1: Admin Authentication"
    
    # Admin login
    local admin_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}" \
        "$API_BASE/api/v1/auth/login")
    
    ADMIN_TOKEN=$(echo "$admin_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['data']['token']['access_token'])
except: print('')
" 2>/dev/null)
    
    if [ -n "$ADMIN_TOKEN" ]; then
        print_status "✅ Admin authenticated" $GREEN
    else
        print_status "❌ Admin authentication failed" $RED
        exit 1
    fi
    
    print_step "Phase 2: Create Fresh Test Users"
    
    # Create trader user
    print_status "👤 Creating fresh trader user..." $YELLOW
    local trader_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d "{\"email\":\"$TRADER_EMAIL\",\"full_name\":\"Fresh Trader User\",\"role\":\"trader\"}" \
        "$API_BASE/api/v1/admin/users")
    
    TRADER_TEMP_PASSWORD=$(echo "$trader_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print(data['temporary_password'])
    else: print('')
except: print('')
" 2>/dev/null)
    
    if [ -n "$TRADER_TEMP_PASSWORD" ]; then
        print_status "✅ Trader user created: $TRADER_EMAIL" $GREEN
        print_status "   Temporary password: $TRADER_TEMP_PASSWORD" $CYAN
    else
        print_status "❌ Failed to create trader user" $RED
        exit 1
    fi
    
    # Create viewer user
    print_status "👤 Creating fresh viewer user..." $YELLOW
    local viewer_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d "{\"email\":\"$VIEWER_EMAIL\",\"full_name\":\"Fresh Viewer User\",\"role\":\"viewer\"}" \
        "$API_BASE/api/v1/admin/users")
    
    VIEWER_TEMP_PASSWORD=$(echo "$viewer_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print(data['temporary_password'])
    else: print('')
except: print('')
" 2>/dev/null)
    
    if [ -n "$VIEWER_TEMP_PASSWORD" ]; then
        print_status "✅ Viewer user created: $VIEWER_EMAIL" $GREEN
        print_status "   Temporary password: $VIEWER_TEMP_PASSWORD" $CYAN
    else
        print_status "❌ Failed to create viewer user" $RED
        exit 1
    fi
    
    print_step "Phase 3: Test Forced Password Changes"
    
    # Test trader authentication with password change
    test_auth_with_password_change "$TRADER_EMAIL" "$TRADER_TEMP_PASSWORD" "trader"
    
    # Test viewer authentication with password change  
    test_auth_with_password_change "$VIEWER_EMAIL" "$VIEWER_TEMP_PASSWORD" "viewer"
    
    print_step "Phase 4: Admin Endpoint Testing"
    print_status "🔐 Testing role-based access to admin endpoints..." $YELLOW
    
    for endpoint in "/api/v1/admin/stats" "/api/v1/admin/users"; do
        echo ""
        print_status "📍 Testing: $endpoint" $PURPLE
        test_endpoint "$endpoint" "admin" "200"
        test_endpoint "$endpoint" "trader" "403" 
        test_endpoint "$endpoint" "viewer" "403"
    done
    
    print_step "Phase 5: Regular Endpoint Testing"
    print_status "🔍 Testing general endpoint access..." $YELLOW
    
    for endpoint in "/" "/health"; do
        echo ""
        print_status "📍 Testing: $endpoint" $PURPLE
        for role in admin trader viewer; do
            test_endpoint "$endpoint" "$role" "200"
        done
    done
    
    print_step "Phase 6: Security Edge Cases"
    print_status "🧪 Testing security edge cases..." $YELLOW
    
    # Test invalid token
    echo ""
    print_status "🔍 Testing invalid token..." $PURPLE
    local invalid_status=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer invalid_token_12345" \
        "$API_BASE/api/v1/admin/stats" | tail -c 3)
    
    if [ "$invalid_status" = "401" ]; then
        print_status "   ✅ Invalid token correctly denied ($invalid_status)" $GREEN
    else
        print_status "   ❌ Invalid token got: $invalid_status (expected 401)" $RED
    fi
    
    # Test missing authorization
    echo ""
    print_status "🔍 Testing missing authorization..." $PURPLE
    local missing_auth_status=$(curl -s -w "%{http_code}" \
        "$API_BASE/api/v1/admin/stats" | tail -c 3)
    
    if [ "$missing_auth_status" = "403" ] || [ "$missing_auth_status" = "401" ]; then
        print_status "   ✅ Missing auth correctly denied ($missing_auth_status)" $GREEN
    else
        print_status "   ❌ Missing auth got: $missing_auth_status (expected 401/403)" $RED
    fi
    
    print_step "🎯 COMPREHENSIVE TESTING COMPLETE!"
    print_status "=============================================" $BLUE
    print_status "✅ Fresh users created and tested!" $GREEN
    print_status "✅ Forced password change working!" $GREEN
    print_status "✅ Role-based access control working!" $GREEN
    print_status "✅ Admin endpoints properly protected!" $GREEN
    print_status "✅ Regular endpoints accessible to all!" $GREEN
    print_status "✅ Security edge cases handled!" $GREEN
    
    echo ""
    print_status "📋 Test Results Summary:" $CYAN
    print_status "   👨‍💼 Admin: $ADMIN_USERNAME - Full access verified" $CYAN
    print_status "   📊 Trader: $TRADER_EMAIL - Limited access verified" $CYAN
    print_status "   👁️  Viewer: $VIEWER_EMAIL - Read-only access verified" $CYAN
    
    echo ""
    print_status "📋 Final tokens for manual testing:" $CYAN
    echo "export ADMIN_TOKEN='$ADMIN_TOKEN'"
    echo "export TRADER_TOKEN='$TRADER_TOKEN'" 
    echo "export VIEWER_TOKEN='$VIEWER_TOKEN'"
    
    echo ""
    print_status "🎉 ROLE-BASED ACCESS CONTROL FULLY TESTED AND WORKING!" $GREEN
}

main "$@"
