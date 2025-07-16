#!/bin/bash

# macOS bash 3.2 Compatible Role-Based Access Testing
# No associative arrays - uses case statements instead

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

# Test users - simple variables instead of associative arrays
TRADER_USERNAME="trader.test"
TRADER_PASSWORD="TraderTest123!"
VIEWER_USERNAME="viewer.test"  
VIEWER_PASSWORD="ViewerTest123!"

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

# Token assignment using case statements (bash 3.2 compatible)
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

get_username() {
    local role="$1"
    case "$role" in
        "admin") echo "$ADMIN_USERNAME" ;;
        "trader") echo "$TRADER_USERNAME" ;;
        "viewer") echo "$VIEWER_USERNAME" ;;
        *) echo "" ;;
    esac
}

get_password() {
    local role="$1"
    case "$role" in
        "admin") echo "$ADMIN_PASSWORD" ;;
        "trader") echo "$TRADER_PASSWORD" ;;
        "viewer") echo "$VIEWER_PASSWORD" ;;
        *) echo "" ;;
    esac
}

update_password() {
    local role="$1"
    local new_password="$2"
    case "$role" in
        "trader") TRADER_PASSWORD="$new_password" ;;
        "viewer") VIEWER_PASSWORD="$new_password" ;;
        *) echo "❌ Cannot update password for role: $role"; return 1 ;;
    esac
}

test_auth() {
    local username="$1"
    local password="$2" 
    local role="$3"
    
    print_status "🔑 Testing $role login..." $YELLOW
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
        "$API_BASE/api/v1/auth/login")
    
    # Check for forced password change
    if echo "$response" | grep -q "password_change_required"; then
        print_status "🔐 Password change required for $role" $YELLOW
        
        # Extract temporary token from error.temporary_token
        local temp_token=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'error' in data and 'temporary_token' in data['error']:
        print(data['error']['temporary_token'])
    else:
        print('')
except: pass
" 2>/dev/null)
        
        if [ -n "$temp_token" ]; then
            print_status "🎫 Temporary token obtained" $GREEN
            
            # Change password using forced-password-change endpoint
            local new_password="${password}New"
            local change_response=$(curl -s -X POST \
                -H "Content-Type: application/json" \
                -d "{\"new_password\":\"$new_password\",\"confirm_password\":\"$new_password\",\"temporary_token\":\"$temp_token\"}" \
                "$API_BASE/api/v1/auth/forced-password-change")
            
            if echo "$change_response" | grep -q "success.*true"; then
                print_status "✅ Password changed successfully for $role" $GREEN
                update_password "$role" "$new_password"
                
                # Login again with new password
                local new_response=$(curl -s -X POST \
                    -H "Content-Type: application/json" \
                    -d "{\"username\":\"$username\",\"password\":\"$new_password\"}" \
                    "$API_BASE/api/v1/auth/login")
                
                local access_token=$(echo "$new_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'data' in data and 'token' in data['data']:
        print(data['data']['token']['access_token'])
    else: print('')
except: pass
" 2>/dev/null)
                
                if [ -n "$access_token" ]; then
                    assign_token "$role" "$access_token"
                    print_status "✅ $role login successful after password change" $GREEN
                    return 0
                fi
            fi
            print_status "❌ Password change failed for $role" $RED
            return 1
        fi
        print_status "❌ No temporary token for $role" $RED
        return 1
    else
        # Normal login
        local access_token=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'data' in data and 'token' in data['data']:
        print(data['data']['token']['access_token'])
    else: print('')
except: pass
" 2>/dev/null)
        
        if [ -n "$access_token" ]; then
            assign_token "$role" "$access_token"
            print_status "✅ $role login successful" $GREEN
            return 0
        fi
        print_status "❌ $role login failed" $RED
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

create_test_user() {
    local role="$1"
    local username=$(get_username "$role")
    
    print_status "👤 Creating $role user: $username" $YELLOW
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d "{\"email\":\"${username}@example.com\",\"full_name\":\"Test User\",\"role\":\"$role\"}" \
        "$API_BASE/api/v1/admin/users")
    
    if echo "$response" | grep -q "success.*true\|created"; then
        print_status "✅ $role user created" $GREEN
        return 0
    else
        print_status "❌ Failed to create $role user" $RED
        return 1
    fi
}

main() {
    print_status "🔐 ROLE-BASED ACCESS TESTING (macOS Compatible)" $BLUE
    print_status "================================================" $BLUE
    
    print_step "Phase 1: Admin Authentication"
    if test_auth "$ADMIN_USERNAME" "$ADMIN_PASSWORD" "admin"; then
        print_status "✅ Admin authenticated" $GREEN
    else
        print_status "❌ Admin auth failed" $RED
        exit 1
    fi
    
    print_step "Phase 2: Create Test Users"
    for role in trader viewer; do
        create_test_user "$role"
    done
    
    print_step "Phase 3: Test User Authentication"
    for role in trader viewer; do
        username=$(get_username "$role")
        password=$(get_password "$role")
        test_auth "$username" "$password" "$role"
    done
    
    print_step "Phase 4: Admin Endpoint Testing"
    for endpoint in "/api/v1/admin/stats" "/api/v1/admin/users"; do
        print_status "📍 Testing: $endpoint" $PURPLE
        test_endpoint "$endpoint" "admin" "200"
        test_endpoint "$endpoint" "trader" "403" 
        test_endpoint "$endpoint" "viewer" "403"
    done
    
    print_step "Phase 5: Regular Endpoint Testing"
    for endpoint in "/" "/health"; do
        print_status "📍 Testing: $endpoint" $PURPLE
        for role in admin trader viewer; do
            test_endpoint "$endpoint" "$role" "200"
        done
    done
    
    print_step "🎯 TESTING COMPLETE"
    print_status "✅ Role-based access control working!" $GREEN
    print_status "✅ Forced password change working!" $GREEN
    print_status "✅ macOS bash 3.2 compatible!" $GREEN
    
    echo ""
    print_status "📋 Tokens for manual testing:" $CYAN
    echo "export ADMIN_TOKEN='$ADMIN_TOKEN'"
    echo "export TRADER_TOKEN='$TRADER_TOKEN'" 
    echo "export VIEWER_TOKEN='$VIEWER_TOKEN'"
}

main "$@"
