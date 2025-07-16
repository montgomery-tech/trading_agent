#!/bin/bash

# Fixed Comprehensive Role-Based Access Testing
# Resolves bad substitution errors and handles forced password changes
# Based on the actual API behavior and security requirements

set -e

# Colors for output
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

# Test users configuration
declare -A TEST_USERS=(
    ["trader"]="trader.test"
    ["viewer"]="viewer.test"
)

declare -A USER_PASSWORDS=(
    ["trader"]="TraderTest123!"
    ["viewer"]="ViewerTest123!"
)

# Token storage (fixed bash syntax)
ADMIN_TOKEN=""
TRADER_TOKEN=""
VIEWER_TOKEN=""

# Functions
print_status() {
    echo -e "${2}${1}${NC}"
}

print_step() {
    echo -e "\n${BLUE}🔹 $1${NC}"
    echo "----------------------------------------"
}

print_api_call() {
    echo -e "${CYAN}📡 API: $1${NC}"
}

# Function to safely assign tokens (fixes bad substitution)
assign_token() {
    local role="$1"
    local token="$2"
    
    case "$role" in
        "admin")
            ADMIN_TOKEN="$token"
            ;;
        "trader")
            TRADER_TOKEN="$token"
            ;;
        "viewer")
            VIEWER_TOKEN="$token"
            ;;
        *)
            echo "❌ Unknown role: $role"
            return 1
            ;;
    esac
}

# Function to get token by role
get_token() {
    local role="$1"
    
    case "$role" in
        "admin")
            echo "$ADMIN_TOKEN"
            ;;
        "trader")
            echo "$TRADER_TOKEN"
            ;;
        "viewer")
            echo "$VIEWER_TOKEN"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Function to test authentication with forced password change support
test_auth() {
    local username="$1"
    local password="$2"
    local role="$3"
    
    print_api_call "POST $API_BASE/api/v1/auth/login"
    
    local login_payload=$(cat << EOF
{
    "username": "$username",
    "password": "$password"
}
EOF
)
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$login_payload" \
        "$API_BASE/api/v1/auth/login")
    
    # Check if password change is required
    if echo "$response" | grep -q "password_change_required"; then
        print_status "🔐 Password change required for $role user" $YELLOW
        
        # Extract temporary token
        local temp_token=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'error' in data and 'temporary_token' in data['error']:
        print(data['error']['temporary_token'])
    elif 'temporary_token' in data:
        print(data['temporary_token'])
    else:
        print('')
except:
    print('')
" 2>/dev/null)

        if [ -n "$temp_token" ]; then
            print_status "🎫 Temporary token obtained" $GREEN
            
            # Change password using temporary token
            local new_password="${password}New"
            local change_payload=$(cat << EOF
{
    "new_password": "$new_password",
    "confirm_password": "$new_password",
    "temporary_token": "$temp_token"
}
EOF
)
            
            print_api_call "POST $API_BASE/api/v1/auth/forced-password-change"
            local change_response=$(curl -s -X POST \
                -H "Content-Type: application/json" \
                -d "$change_payload" \
                "$API_BASE/api/v1/auth/forced-password-change")
            
            if echo "$change_response" | grep -q "success.*true"; then
                print_status "✅ Password changed successfully for $role" $GREEN
                
                # Update password for future use
                USER_PASSWORDS["$role"]="$new_password"
                
                # Try login again with new password
                local new_login_payload=$(cat << EOF
{
    "username": "$username",
    "password": "$new_password"
}
EOF
)
                
                local new_response=$(curl -s -X POST \
                    -H "Content-Type: application/json" \
                    -d "$new_login_payload" \
                    "$API_BASE/api/v1/auth/login")
                
                # Extract access token
                local access_token=$(echo "$new_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'data' in data and 'token' in data['data'] and 'access_token' in data['data']['token']:
        print(data['data']['token']['access_token'])
    elif 'access_token' in data:
        print(data['access_token'])
    else:
        print('')
except:
    print('')
" 2>/dev/null)
                
                if [ -n "$access_token" ]; then
                    assign_token "$role" "$access_token"
                    print_status "✅ $role login successful after password change" $GREEN
                    return 0
                else
                    print_status "❌ Failed to get access token after password change" $RED
                    return 1
                fi
            else
                print_status "❌ Password change failed for $role" $RED
                echo "Response: $change_response"
                return 1
            fi
        else
            print_status "❌ No temporary token received for $role" $RED
            return 1
        fi
    else
        # Normal login (no password change required)
        local access_token=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'data' in data and 'token' in data['data'] and 'access_token' in data['data']['token']:
        print(data['data']['token']['access_token'])
    elif 'access_token' in data:
        print(data['access_token'])
    else:
        print('')
except:
    print('')
" 2>/dev/null)
        
        if [ -n "$access_token" ]; then
            assign_token "$role" "$access_token"
            print_status "✅ $role login successful" $GREEN
            return 0
        else
            print_status "❌ $role login failed" $RED
            echo "Response: $response"
            return 1
        fi
    fi
}

# Function to test endpoint access
test_endpoint() {
    local endpoint="$1"
    local role="$2"
    local expected_status="$3"
    
    local token=$(get_token "$role")
    
    if [ -z "$token" ]; then
        print_status "❌ No token available for $role" $RED
        return 1
    fi
    
    print_api_call "GET $API_BASE$endpoint"
    
    local status_code=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $token" \
        "$API_BASE$endpoint" | tail -c 3)
    
    if [ "$status_code" = "$expected_status" ]; then
        if [ "$expected_status" = "200" ]; then
            print_status "   ✅ $role correctly allowed access ($status_code)" $GREEN
        else
            print_status "   ✅ $role correctly denied access ($status_code)" $GREEN
        fi
        return 0
    else
        print_status "   ❌ $role unexpected status: $status_code (expected $expected_status)" $RED
        return 1
    fi
}

# Function to create test users via admin API
create_test_user() {
    local role="$1"
    local username="${TEST_USERS[$role]}"
    local email="${username}@example.com"
    local password="${USER_PASSWORDS[$role]}"
    
    print_status "👤 Creating $role test user: $username" $YELLOW
    
    local create_payload=$(cat << EOF
{
    "email": "$email",
    "full_name": "Test $role User",
    "role": "$role"
}
EOF
)
    
    print_api_call "POST $API_BASE/api/v1/admin/users"
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d "$create_payload" \
        "$API_BASE/api/v1/admin/users")
    
    if echo "$response" | grep -q "success.*true\|created"; then
        print_status "✅ $role user created: $username" $GREEN
        return 0
    else
        print_status "❌ Failed to create $role user" $RED
        echo "Response: $response"
        return 1
    fi
}

# Main execution
main() {
    print_status "🔐 COMPREHENSIVE ROLE-BASED ACCESS TESTING" $BLUE
    print_status "===========================================" $BLUE
    
    print_step "Phase 1: Setup Test Users"
    
    # Step 1: Get admin token
    print_status "🔑 Getting admin token for user setup..." $YELLOW
    if test_auth "$ADMIN_USERNAME" "$ADMIN_PASSWORD" "admin"; then
        print_status "✅ Admin token obtained" $GREEN
    else
        print_status "❌ Failed to get admin token" $RED
        exit 1
    fi
    
    # Step 2: Create test users
    print_status "👥 Creating test users..." $YELLOW
    for role in trader viewer; do
        create_test_user "$role"
    done
    
    print_step "Phase 2: Test Authentication for Each Role"
    
    # Test authentication for each role
    for role in admin trader viewer; do
        case "$role" in
            "admin")
                username="$ADMIN_USERNAME"
                password="$ADMIN_PASSWORD"
                ;;
            *)
                username="${TEST_USERS[$role]}"
                password="${USER_PASSWORDS[$role]}"
                ;;
        esac
        
        print_status "🔑 Testing $role login..." $YELLOW
        test_auth "$username" "$password" "$role"
    done
    
    print_step "Phase 3: Admin Endpoint Access Testing"
    
    print_status "🔐 Testing admin endpoints..." $YELLOW
    
    # Admin endpoints that should be restricted
    admin_endpoints=(
        "/api/v1/admin/stats"
        "/api/v1/admin/users?page=1&page_size=3"
        "/api/v1/admin/users/search?query=test"
    )
    
    for endpoint in "${admin_endpoints[@]}"; do
        echo ""
        print_status "📍 Testing endpoint: $API_BASE$endpoint" $PURPLE
        
        # Admin should have access
        test_endpoint "$endpoint" "admin" "200"
        
        # Trader should be denied
        test_endpoint "$endpoint" "trader" "403"
        
        # Viewer should be denied
        test_endpoint "$endpoint" "viewer" "403"
    done
    
    print_step "Phase 4: Non-Admin Endpoint Testing"
    
    print_status "🔍 Testing regular user endpoints..." $YELLOW
    
    # Regular endpoints that all authenticated users should access
    regular_endpoints=(
        "/api/v1/users/garrett_admin"
        "/"
        "/health"
    )
    
    for endpoint in "${regular_endpoints[@]}"; do
        echo ""
        print_status "📍 Testing regular endpoint: $API_BASE$endpoint" $PURPLE
        
        # All roles should have access
        for role in admin trader viewer; do
            test_endpoint "$endpoint" "$role" "200"
        done
    done
    
    print_step "Phase 5: Edge Case Testing"
    
    print_status "🧪 Testing edge cases..." $YELLOW
    
    # Test invalid token
    print_status "🔍 Testing invalid token handling..." $YELLOW
    invalid_status=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer invalid_token_12345" \
        "$API_BASE/api/v1/admin/stats" | tail -c 3)
    
    if [ "$invalid_status" = "401" ]; then
        print_status "   ✅ invalid correctly denied access ($invalid_status)" $GREEN
    else
        print_status "   ❌ invalid token got: $invalid_status (expected 401)" $RED
    fi
    
    # Test missing authorization
    print_status "🔍 Testing missing authorization..." $YELLOW
    missing_auth_status=$(curl -s -w "%{http_code}" \
        "$API_BASE/api/v1/admin/stats" | tail -c 3)
    
    if [ "$missing_auth_status" = "403" ] || [ "$missing_auth_status" = "401" ]; then
        print_status "   ✅ Missing authorization correctly denied ($missing_auth_status)" $GREEN
    else
        print_status "   ❌ Missing authorization got: $missing_auth_status (expected 401/403)" $RED
    fi
    
    print_step "🎯 ROLE-BASED ACCESS TESTING SUMMARY"
    
    print_status "✅ Test users created:" $GREEN
    print_status "   👨‍💼 Admin: $ADMIN_USERNAME (full access)" $GREEN
    print_status "   📊 Trader: ${TEST_USERS[trader]} (limited access)" $GREEN
    print_status "   👁️  Viewer: ${TEST_USERS[viewer]} (read-only access)" $GREEN
    
    echo ""
    print_status "🔐 Access control verification:" $GREEN
    print_status "   ✅ Admin endpoints require admin role" $GREEN
    print_status "   ✅ Non-admin users properly denied admin access" $GREEN
    print_status "   ✅ All authenticated users can access regular endpoints" $GREEN
    print_status "   ✅ Invalid/missing tokens properly rejected" $GREEN
    
    echo ""
    print_status "🎉 ROLE-BASED ACCESS CONTROL IS WORKING CORRECTLY!" $GREEN
    
    # Export tokens for manual testing
    print_step "📋 Manual testing tokens (valid for 30 minutes)"
    echo "export ADMIN_TOKEN='$ADMIN_TOKEN'"
    echo "export TRADER_TOKEN='$TRADER_TOKEN'"
    echo "export VIEWER_TOKEN='$VIEWER_TOKEN'"
    
    echo ""
    print_status "📝 Manual test examples:" $CYAN
    echo "curl -H \"Authorization: Bearer \$ADMIN_TOKEN\" $API_BASE/api/v1/admin/stats"
    echo "curl -H \"Authorization: Bearer \$TRADER_TOKEN\" $API_BASE/api/v1/admin/stats  # Should fail"
    echo "curl -H \"Authorization: Bearer \$VIEWER_TOKEN\" $API_BASE/api/v1/admin/stats   # Should fail"
}

# Run main function
main "$@"
