"""
Authentication Routes with Forced Password Change
Task 2.1b: Implements login and forced password change system
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from typing import Optional
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
import logging

# Local imports
from api.models.auth import (
    LoginRequest, LoginResponse, PasswordChangeRequired,
    PasswordChangeRequest, PasswordChangeResponse,
    ForcedPasswordChangeRequest, AuthenticatedUser,
    TokenResponse, AuthError, UserRole
)
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()

# Get JWT settings from environment
import os
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_temporary_token(user_data: dict):
    """Create temporary token for forced password change"""
    to_encode = {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "role": user_data.get("role", "trader"),
        "temp_token": True,
        "must_change_password": True
    }
    expire = datetime.utcnow() + timedelta(hours=1)  # Short expiration
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, require_temp: bool = False):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        if require_temp and not payload.get("temp_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Temporary token required"
            )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_user_by_username(username: str, db: DatabaseManager):
    """Get user by username or email"""
    with db.get_cursor() as cursor:
        # Try username first
        if db.db_type == 'postgresql':
            cursor.execute("""
                SELECT id, username, email, password_hash, first_name, last_name,
                       role, is_active, is_verified, must_change_password, last_login, created_at
                FROM users 
                WHERE (username = %s OR email = %s) AND is_active = %s
            """, (username, username, True))
        else:
            cursor.execute("""
                SELECT id, username, email, password_hash, first_name, last_name,
                       role, is_active, is_verified, must_change_password, last_login, created_at
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = ?
            """, (username, username, 1))
        
        row = cursor.fetchone()
        return row


# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    User login with forced password change detection
    
    - Authenticates user credentials
    - Checks if password change is required
    - Returns appropriate response based on password status
    """
    try:
        # Get user from database
        user = await get_user_by_username(login_data.username, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if account is active
        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Update last login
        with db.get_cursor() as cursor:
            if db.db_type == 'postgresql':
                cursor.execute(
                    "UPDATE users SET last_login = %s WHERE id = %s",
                    (datetime.utcnow(), user['id'])
                )
            else:
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.utcnow(), user['id'])
                )
        
        # Check if password change is required
        must_change_password = user.get('must_change_password', False)
        
        if must_change_password:
            # Return temporary token and password change requirement
            temporary_token = create_temporary_token(user)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "password_change_required",
                    "message": "You must change your password before accessing this resource",
                    "temporary_token": temporary_token,
                    "change_password_url": "/api/v1/auth/change-password"
                }
            )
        
        # Create access token for normal login
        token_data = {
            "user_id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "role": user.get('role', 'trader'),
            "must_change_password": False
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_access_token(
            {**token_data, "token_type": "refresh"}, 
            timedelta(days=7)
        )
        
        # Construct user data for response
        user_data = {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or None,
            "role": user.get('role', 'trader'),
            "is_active": user['is_active'],
            "is_verified": user.get('is_verified', False),
            "must_change_password": False
        }
        
        return LoginResponse(
            message="Login successful",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=JWT_EXPIRE_MINUTES * 60,
            user=user_data,
            must_change_password=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for {login_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to internal error"
        )


@router.post("/change-password", response_model=PasswordChangeResponse)
async def change_password(
    password_data: ForcedPasswordChangeRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Change password for users with forced password change requirement
    
    - Validates temporary token
    - Updates password in database
    - Removes must_change_password flag
    - Returns new access tokens
    """
    try:
        # Verify temporary token
        token_payload = verify_token(password_data.temporary_token, require_temp=True)
        
        # Get user from database
        user = await get_user_by_username(token_payload['username'], db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash new password
        new_password_hash = bcrypt.hashpw(
            password_data.new_password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Update password and remove must_change_password flag
        with db.get_cursor() as cursor:
            if db.db_type == 'postgresql':
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = %s, must_change_password = %s, 
                        password_changed_at = %s, updated_at = %s
                    WHERE id = %s
                """, (
                    new_password_hash, False, datetime.utcnow(), 
                    datetime.utcnow(), user['id']
                ))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = ?, must_change_password = ?, 
                        password_changed_at = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    new_password_hash, 0, datetime.utcnow(), 
                    datetime.utcnow(), user['id']
                ))
        
        # Create new access tokens (password change complete)
        token_data = {
            "user_id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "role": user.get('role', 'trader'),
            "must_change_password": False
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_access_token(
            {**token_data, "token_type": "refresh"}, 
            timedelta(days=7)
        )
        
        # Construct updated user data
        user_data = {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or None,
            "role": user.get('role', 'trader'),
            "is_active": user['is_active'],
            "is_verified": user.get('is_verified', False),
            "must_change_password": False
        }
        
        logger.info(f"Password changed successfully for user: {user['username']}")
        
        return PasswordChangeResponse(
            message="Password changed successfully. You can now access all features.",
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/me")
async def get_current_user(
    token: str = Depends(security),
    db: DatabaseManager = Depends(get_database)
):
    """
    Get current user information
    
    - Validates JWT token
    - Checks for forced password change requirement
    - Returns user profile or password change requirement
    """
    try:
        # Verify token
        token_payload = verify_token(token.credentials)
        
        # Get user from database
        user = await get_user_by_username(token_payload['username'], db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if password change is still required
        if user.get('must_change_password', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "password_change_required",
                    "message": "You must change your password before accessing this resource",
                    "change_password_url": "/api/v1/auth/change-password"
                }
            )
        
        # Return user profile
        user_data = {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or None,
            "role": user.get('role', 'trader'),
            "is_active": user['is_active'],
            "is_verified": user.get('is_verified', False),
            "must_change_password": False,
            "last_login": user.get('last_login'),
            "created_at": user.get('created_at')
        }
        
        return {"success": True, "user": user_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/logout")
async def logout():
    """
    Logout endpoint
    
    Note: In a stateless JWT system, logout is primarily client-side
    The client should discard the tokens
    """
    return {"success": True, "message": "Logged out successfully"}
