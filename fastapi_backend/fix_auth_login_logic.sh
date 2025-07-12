#!/bin/bash

echo "🔧 Fixing Auth Login Logic for Forced Password Change"
echo "====================================================="

echo "📋 The issue: Auth login endpoint exists but doesn't handle forced password change correctly"
echo ""

# Let's check what auth routes file is actually being used
echo "🔍 Checking current auth routes implementation..."

if [ -f "api/auth_routes.py" ]; then
    echo "✅ Found api/auth_routes.py"
    AUTH_FILE="api/auth_routes.py"
elif [ -f "api/routes/auth.py" ]; then
    echo "✅ Found api/routes/auth.py" 
    AUTH_FILE="api/routes/auth.py"
else
    echo "❌ No auth routes file found!"
    exit 1
fi

echo "📋 Checking if login endpoint handles must_change_password..."

if grep -q "must_change_password" "$AUTH_FILE"; then
    echo "✅ must_change_password logic found in $AUTH_FILE"
else
    echo "❌ must_change_password logic missing from $AUTH_FILE"
    echo "🔧 Adding forced password change logic..."
    
    # Create a simple working auth login endpoint
    cat > temp_auth_fix.py << 'EOF'
"""
Temporary Auth Login Fix
Adds proper forced password change handling to login endpoint
"""

from fastapi import APIRouter, HTTPException, Depends, status
import bcrypt
import jwt
from datetime import datetime, timedelta
import logging
import uuid

from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)

# JWT settings
import os
SECRET_KEY = os.getenv("SECRET_KEY", "f19fb15492b88dbb703a5affeb215d308debaa49f91e47ce040e5ef8ad9be162")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_temporary_token(user_data: dict):
    """Create temporary token for password change"""
    to_encode = {
        "user_id": user_data["id"],
        "username": user_data["username"], 
        "email": user_data["email"],
        "temp_token": True,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)

async def get_user_by_email_or_username(identifier: str, db: DatabaseManager):
    """Get user by email or username"""
    with db.get_cursor() as cursor:
        # Try email first, then username
        cursor.execute("""
            SELECT id, username, email, password_hash, first_name, last_name,
                   is_active, is_verified, must_change_password, created_at, last_login
            FROM users 
            WHERE email = %s OR username = %s
        """, (identifier, identifier))
        
        result = cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'username': result[1], 
                'email': result[2],
                'password_hash': result[3],
                'first_name': result[4],
                'last_name': result[5],
                'is_active': result[6],
                'is_verified': result[7],
                'must_change_password': result[8],
                'created_at': result[9],
                'last_login': result[10]
            }
        return None

# Create router for this fix
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

@router.post("/login")
async def login_with_forced_password_check(
    login_data: dict,
    db: DatabaseManager = Depends(get_database)
):
    """Login endpoint that properly handles forced password changes"""
    
    try:
        username = login_data.get("username")
        password = login_data.get("password")
        
        if not username or not password:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": "Username and password required"}
            )
        
        # Get user from database
        user = await get_user_by_email_or_username(username, db)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail={"success": False, "error": "Invalid credentials"}
            )
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            raise HTTPException(
                status_code=401, 
                detail={"success": False, "error": "Invalid credentials"}
            )
        
        # Check if user is active
        if not user['is_active']:
            raise HTTPException(
                status_code=401,
                detail={"success": False, "error": "Account is deactivated"}
            )
        
        # Update last login
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE id = %s",
                (datetime.utcnow(), user['id'])
            )
            db.connection.commit()
        
        # Check if password change is required
        if user.get('must_change_password', False):
            # Create temporary token
            temp_token = create_temporary_token(user)
            
            return {
                "success": False,
                "must_change_password": True,
                "message": "Password change required",
                "temporary_token": temp_token,
                "user_id": user['id'],
                "email": user['email']
            }
        
        # Normal login - create access token
        token_data = {
            "user_id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "role": "trader"
        }
        
        access_token = create_access_token(token_data)
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRE_MINUTES * 60,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "must_change_password": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Authentication failed"}
        )

EOF

    echo "✅ Created temporary auth fix"
fi

echo ""
echo "🧪 Testing current auth endpoint behavior..."

# Test the current login endpoint with our test user
test_response=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser_forced@example.com","password":"TempPass123!"}')

echo "📋 Current login response:"
echo "$test_response" | python3 -m json.tool 2>/dev/null || echo "$test_response"

if echo "$test_response" | grep -q "must_change_password"; then
    echo "✅ Login endpoint already handles forced password change"
elif echo "$test_response" | grep -q "error.*Authentication failed"; then
    echo "❌ Login endpoint has authentication error - needs fixing"
    
    echo ""
    echo "🔧 Applying quick fix to main.py..."
    
    # Add the temporary auth fix to main.py
    echo "
# Temporary auth fix for forced password change
import temp_auth_fix
app.include_router(temp_auth_fix.router, prefix='', tags=['Auth Fix'])
" >> main.py

    echo "✅ Added temporary auth fix to main.py"
    echo "🔄 Restart server to apply fix: kill \$(lsof -t -i:8000); python3 main.py &"
    
else
    echo "⚠️  Unexpected login response format"
fi

echo ""
echo "🎯 Next steps:"
echo "1. If auth logic is missing: Restart server after applying fix"
echo "2. Test again: python3 test_simple_forced_password.py"
echo "3. The login should return must_change_password: true for new users"
