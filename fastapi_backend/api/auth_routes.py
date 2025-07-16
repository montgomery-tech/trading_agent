
#!/usr/bin/env python3
#auth_routes.py
"""
Authentication routes for the Balance Tracking API
User registration, login, logout, and token management
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth_models import (
    UserRegistrationRequest, UserLoginRequest, PasswordChangeRequest,
    PasswordResetRequest, PasswordResetConfirm, EmailVerificationRequest,
    AuthenticationResponse, AuthenticatedUser, Token, TokenData,
    UserCreatedResponse, AuthSuccessResponse, RefreshTokenRequest,
    UserRole, TokenType
)
from api.dependencies import get_database
from api.database import DatabaseManager
from api.jwt_service import jwt_service, password_service

import jwt
import bcrypt
from fastapi import HTTPException, status
from pydantic import BaseModel, validator, Field

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

class ForcedPasswordChangeRequest(BaseModel):
    """Forced password change request (no current password required)"""
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")
    temporary_token: str = Field(..., description="Temporary token from login response")

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class ForcedPasswordChangeResponse(BaseModel):
    """Response after successful forced password change"""
    success: bool = True
    message: str = "Password changed successfully. You can now log in with your new password."
    access_token: str
    refresh_token: str
    user: dict
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# =============================================================================
# Helper Functions
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_database)
) -> AuthenticatedUser:
    """
    Get current authenticated user from JWT token.
    """
    token = credentials.credentials

    # Validate token
    token_data = jwt_service.validate_token(token, expected_type=TokenType.ACCESS)

    # Get user from database
    user = await get_user_by_id(token_data.user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )

    role_mapping = {
        'admin': UserRole.ADMIN,
        'trader': UserRole.TRADER,
        'viewer': UserRole.VIEWER
    }
    user_role = role_mapping.get(user.get('role', 'viewer'), UserRole.VIEWER)

    return AuthenticatedUser(
        id=user['id'],
        username=user['username'],
        email=user['email'],
        first_name=user['first_name'],
        last_name=user['last_name'],
        role=user_role,  # Use the mapped role instead
        is_active=user['is_active'],
        is_verified=user['is_verified'],
        created_at=user['created_at'],
        last_login=user['last_login']
    )


async def get_user_by_username_or_email(identifier: str, db: DatabaseManager) -> Optional[dict]:
    """Get user by username or email."""
    query = """
        SELECT id, username, email, password_hash, first_name, last_name,
               is_active, is_verified, must_change_password, created_at, updated_at, last_login
        FROM users
        WHERE username = %s OR email = %s
    """
    results = db.execute_query(query, (identifier.lower(), identifier.lower()))
    return results[0] if results else None


async def get_user_by_id(user_id: str, db: DatabaseManager) -> Optional[dict]:
    """Get user by ID."""
    query = """
        SELECT id, username, email, password_hash, first_name, last_name,
               is_active, is_verified, must_change_password, created_at, updated_at, last_login
        FROM users
        WHERE id = %s
    """
    results = db.execute_query(query, (user_id,))
    return results[0] if results else None


async def update_last_login(user_id: str, db: DatabaseManager) -> None:
    """Update user's last login timestamp."""
    query = "UPDATE users SET last_login = %s WHERE id = %s"
    db.execute_command(query, (datetime.now(timezone.utc), user_id))


async def create_user_in_db(user_data: UserRegistrationRequest, db: DatabaseManager) -> str:
    """Create new user in database."""
    user_id = str(uuid.uuid4())
    password_hash = password_service.hash_password(user_data.password)

    query = """
        INSERT INTO users (
            id, username, email, password_hash, first_name, last_name,
            is_active, is_verified, created_at, updated_at
        ) VALUES (?, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    db.execute_command(query, (
        user_id,
        user_data.username,
        user_data.email,
        password_hash,
        user_data.first_name,
        user_data.last_name,
        True,  # is_active
        False,  # is_verified (requires email verification)
        datetime.now(timezone.utc),
        datetime.now(timezone.utc)
    ))

    return user_id

def verify_temporary_token(token: str):
    """Verify temporary token for forced password change"""
    try:
        # Use JWT service to decode token
        import os
        SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Verify this is a temporary token
        if not payload.get("temp_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Temporary token required."
            )

        # Verify must_change_password flag
        if not payload.get("must_change_password"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not valid for password change"
            )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Temporary token has expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid temporary token"
        )
# =============================================================================
# Registration Routes
# =============================================================================

@router.post("/register", response_model=UserCreatedResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_database)
):
    """
    Register a new user account.

    Creates a new user account with email verification required.
    Sends verification email in the background.
    """
    try:
        # Check if username already exists
        existing_user = await get_user_by_username_or_email(user_data.username, db)
        if existing_user:
            if existing_user['username'] == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            elif existing_user['email'] == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

        # Create user in database
        user_id = await create_user_in_db(user_data, db)

        # Generate email verification token
        verification_token = jwt_service.create_special_token(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_hours=24
        )

        # TODO: Send verification email in background
        # background_tasks.add_task(send_verification_email, user_data.email, verification_token)

        logger.info(f"User registered successfully: {user_data.username} ({user_data.email})")

        return UserCreatedResponse(
            message="User account created successfully",
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            email_verification_required=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed for {user_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    request: EmailVerificationRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Verify user email address using verification token.
    """
    try:
        # Validate verification token
        token_data = jwt_service.validate_token(
            request.token,
            expected_type=TokenType.EMAIL_VERIFICATION
        )

        # Update user verification status
        query = "UPDATE users SET is_verified = %s, updated_at = %s WHERE id = %s"
        db.execute_command(query, (True, datetime.now(timezone.utc), token_data.user_id))

        logger.info(f"Email verified for user: {token_data.username}")

        return {
            "success": True,
            "message": "Email verified successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


# =============================================================================
# Authentication Routes
# =============================================================================

@router.post("/login", response_model=AuthSuccessResponse)
async def login_user(
    login_data: UserLoginRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Authenticate user and return JWT tokens.

    Accepts username or email for login.
    Returns access token and refresh token on success.
    """
    try:
        # Get user from database
        user = await get_user_by_username_or_email(login_data.username, db)
        if user:
            # Get the role separately
            role_query = "SELECT role FROM users WHERE id = %s"
            role_result = db.execute_query(role_query, (user['id'],))
            user_role_str = role_result[0]['role'] if role_result and role_result[0]['role'] else 'viewer'

            # Add role to user dict
            user['role'] = user_role_str
            
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        # Verify password
        if not password_service.verify_password(login_data.password, user['password_hash']):
            logger.warning(f"Failed login attempt for user: {login_data.username}")
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

        # Check if password change is required
        must_change_password = user.get('must_change_password', False)

        if must_change_password:
            # Create temporary token for forced password change
            import os
            SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
            JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

            temp_token_data = {
                "user_id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "role": user.get('role', 'trader'),
                "temp_token": True,
                "must_change_password": True
            }

            temporary_token = jwt.encode({
                **temp_token_data,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),  # Short expiration
                "iat": datetime.now(timezone.utc),
                "jti": str(uuid.uuid4())
            }, SECRET_KEY, algorithm=JWT_ALGORITHM)

            # Return 403 with temporary token
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "password_change_required",
                    "message": "You must change your password before accessing this resource",
                    "temporary_token": temporary_token,
                    "change_password_url": "/api/v1/auth/forced-password-change"
                }
            )

        # Update last login timestamp
        await update_last_login(user['id'], db)

        # Update last login timestamp
        await update_last_login(user['id'], db)

        # Create tokens
        # Map role correctly
        role_mapping = {'admin': UserRole.ADMIN, 'trader': UserRole.TRADER, 'viewer': UserRole.VIEWER}
        user_role = role_mapping.get(user.get('role', 'viewer'), UserRole.VIEWER)
        tokens = jwt_service.create_token_response(
            user_id=user['id'],
            username=user['username'],
            email=user['email'],
            role=user_role,
            include_refresh_token=True
        )

        # Create authenticated user object
        authenticated_user = AuthenticatedUser(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=user_role,
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            created_at=user['created_at'],
            last_login=datetime.now(timezone.utc)
        )

        # Create authentication response
        auth_response = AuthenticationResponse(
            message="Login successful",
            user=authenticated_user,
            token=tokens
        )

        logger.info(f"User logged in successfully: {user['username']}")

        return AuthSuccessResponse(
            message="Authentication successful",
            data=auth_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for {login_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Refresh access token using refresh token.

    Returns new access token (and optionally new refresh token).
    """
    try:
        # Validate refresh token
        token_data = jwt_service.validate_token(
            request.refresh_token,
            expected_type=TokenType.REFRESH
        )

        # Get current user data from database
        user = await get_user_by_id(token_data.user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )

        # Create new tokens
        # Map role correctly
        role_mapping = {'admin': UserRole.ADMIN, 'trader': UserRole.TRADER, 'viewer': UserRole.VIEWER}
        user_role = role_mapping.get(user.get('role', 'viewer'), UserRole.VIEWER)
        tokens = jwt_service.create_token_response(
            user_id=user['id'],
            username=user['username'],
            email=user['email'],
            role=user_role,
            include_refresh_token=True
        )

        logger.info(f"Token refreshed for user: {user['username']}")

        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


# =============================================================================
# Password Management Routes
# =============================================================================

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    Change user password (requires current password).
    """
    try:
        # Get current user's password hash
        user = await get_user_by_id(current_user.id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not password_service.verify_password(password_data.current_password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash new password
        new_password_hash = password_service.hash_password(password_data.new_password)

        # Update password in database
        query = "UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s"
        db.execute_command(query, (new_password_hash, datetime.now(timezone.utc), current_user.id))

        logger.info(f"Password changed for user: {current_user.username}")

        return {
            "success": True,
            "message": "Password changed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed for user {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.post("/forced-password-change", response_model=ForcedPasswordChangeResponse)
async def forced_password_change(
    password_data: ForcedPasswordChangeRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Change password using temporary token (for forced password changes)

    This endpoint allows users to change their password when they have a temporary token
    from login that indicated must_change_password=true. No current password required.
    """
    try:
        # Verify temporary token
        token_payload = verify_temporary_token(password_data.temporary_token)
        user_id = token_payload["user_id"]
        username = token_payload["username"]
        email = token_payload["email"]

        # Hash new password using your existing password service
        new_password_hash = password_service.hash_password(password_data.new_password)

        # Update password and clear must_change_password flag in database
        query = """
            UPDATE users
            SET password_hash = %s,
                must_change_password = %s,
                updated_at = %s
            WHERE id = %s
        """

        db.execute_command(query, (
            new_password_hash,
            False,  # Clear the must_change_password flag
            datetime.now(timezone.utc),
            user_id
        ))

        # Create new access tokens (user can now login normally)
        # Map role correctly
        role_mapping = {'admin': UserRole.ADMIN, 'trader': UserRole.TRADER, 'viewer': UserRole.VIEWER}
        user_role = role_mapping.get(token_payload.get("role", "trader"), UserRole.TRADER)
        tokens = jwt_service.create_token_response(
            user_id=user_id,
            username=username,
            email=email,
            role=user_role,
            include_refresh_token=True
        )

        # Get updated user data for response
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "role": token_payload.get("role", "trader"),
            "must_change_password": False
        }

        logger.info(f"Forced password change completed for user: {username}")

        return ForcedPasswordChangeResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            user=user_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forced password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed due to internal error"
        )

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_database)
):
    """
    Request password reset email.

    Always returns success (even if email doesn't exist) for security.
    """
    try:
        # Get user by email
        user = await get_user_by_username_or_email(request.email, db)

        if user and user['is_active']:
            # Generate password reset token
            reset_token = jwt_service.create_special_token(
                user_id=user['id'],
                username=user['username'],
                email=user['email'],
                token_type=TokenType.PASSWORD_RESET,
                expires_hours=2  # Short expiration for security
            )

            # TODO: Send password reset email in background
            # background_tasks.add_task(send_password_reset_email, user['email'], reset_token)

            logger.info(f"Password reset requested for user: {user['username']}")

        # Always return success for security (don't reveal if email exists)
        return {
            "success": True,
            "message": "If the email address exists, a password reset link has been sent"
        }

    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        # Still return success to not reveal errors
        return {
            "success": True,
            "message": "If the email address exists, a password reset link has been sent"
        }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: PasswordResetConfirm,
    db: DatabaseManager = Depends(get_database)
):
    """
    Reset password using reset token.
    """
    try:
        # Validate password reset token
        token_data = jwt_service.validate_token(
            request.token,
            expected_type=TokenType.PASSWORD_RESET
        )

        # Hash new password
        new_password_hash = password_service.hash_password(request.new_password)

        # Update password in database
        query = "UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s"
        db.execute_command(query, (new_password_hash, datetime.now(timezone.utc), token_data.user_id))

        logger.info(f"Password reset completed for user: {token_data.username}")

        return {
            "success": True,
            "message": "Password reset successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


# =============================================================================
# User Profile Routes
# =============================================================================

@router.get("/me", response_model=AuthenticatedUser)
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get current user's profile information.
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Logout user (client-side token invalidation).

    Note: In a production system, you might want to maintain a blacklist
    of invalidated tokens or use shorter token expiration times.
    """
    logger.info(f"User logged out: {current_user.username}")

    return {
        "success": True,
        "message": "Logged out successfully"
    }


# =============================================================================
# Utility Routes
# =============================================================================

@router.get("/check-username/{username}")
async def check_username_availability(
    username: str,
    db: DatabaseManager = Depends(get_database)
):
    """
    Check if a username is available.
    """
    try:
        user = await get_user_by_username_or_email(username, db)
        available = user is None

        return {
            "username": username,
            "available": available
        }

    except Exception as e:
        logger.error(f"Username availability check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Username availability check failed"
        )


@router.get("/check-email/{email}")
async def check_email_availability(
    email: str,
    db: DatabaseManager = Depends(get_database)
):
    """
    Check if an email is available.
    """
    try:
        user = await get_user_by_username_or_email(email, db)
        available = user is None

        return {
            "email": email,
            "available": available
        }

    except Exception as e:
        logger.error(f"Email availability check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email availability check failed"
        )
