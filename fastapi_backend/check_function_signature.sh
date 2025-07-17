#!/bin/bash

echo "🔍 CHECKING USER ENDPOINT FUNCTION SIGNATURE"
echo "============================================"

# Check if the security dependency is in the function signature
echo "📄 Current get_user function signature:"
echo "======================================="

grep -A 10 "async def get_user" deployment_package/api/routes/users.py

echo ""
echo "🔍 Looking for security dependency..."
echo "===================================="

if grep -q "require_resource_owner_or_admin" deployment_package/api/routes/users.py; then
    echo "✅ Found require_resource_owner_or_admin in file"
    
    if grep -A 5 "async def get_user" deployment_package/api/routes/users.py | grep -q "current_user.*AuthenticatedUser.*Depends"; then
        echo "✅ Security dependency appears to be in function signature"
    else
        echo "❌ Security dependency NOT in function signature!"
        echo ""
        echo "🔧 PROBLEM IDENTIFIED:"
        echo "The import is there, but the function signature wasn't updated!"
        echo ""
        echo "📝 YOUR FUNCTION SHOULD LOOK LIKE:"
        echo "=================================="
        cat << 'EOF'
@router.get("/{username}")
async def get_user(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    db: DatabaseManager = Depends(get_database)
):
EOF
    fi
else
    echo "❌ require_resource_owner_or_admin NOT found in file!"
fi

echo ""
echo "🧪 QUICK FIX TEST"
echo "================"
echo "Run this to test the current endpoint:"

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
    
    # Test with authentication
    echo "Testing with admin token..."
    RESPONSE_WITH_AUTH=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $ADMIN_TOKEN" \
                        "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)
    
    echo "Response with auth: $RESPONSE_WITH_AUTH"
    
    # Test without authentication
    echo "Testing without authentication..."
    RESPONSE_NO_AUTH=$(curl -s -w "%{http_code}" "$API_BASE/api/v1/users/garrett_admin" | tail -c 3)
    
    echo "Response without auth: $RESPONSE_NO_AUTH"
    
    echo ""
    echo "🎯 DIAGNOSIS:"
    if [ "$RESPONSE_WITH_AUTH" = "$RESPONSE_NO_AUTH" ]; then
        echo "❌ SECURITY NOT APPLIED: Both requests return same code ($RESPONSE_WITH_AUTH)"
        echo "   The function signature needs the security dependency!"
    elif [ "$RESPONSE_NO_AUTH" = "401" ] || [ "$RESPONSE_NO_AUTH" = "403" ]; then
        echo "✅ SECURITY WORKING: No auth blocked ($RESPONSE_NO_AUTH)"
        if [ "$RESPONSE_WITH_AUTH" = "200" ]; then
            echo "✅ SECURITY WORKING: Auth allowed ($RESPONSE_WITH_AUTH)"
        else
            echo "⚠️  AUTH ISSUE: Even with auth got $RESPONSE_WITH_AUTH"
        fi
    else
        echo "⚠️  MIXED RESULTS: Auth=$RESPONSE_WITH_AUTH, NoAuth=$RESPONSE_NO_AUTH"
    fi
fi
