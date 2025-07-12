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

