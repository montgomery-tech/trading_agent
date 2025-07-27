"""
Authentication Models with Forced Password Change Support
Task 2.1b: Forced Password Change System
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import re


class UserRole(str, Enum):
    """User roles for access control"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


# =============================================================================
# LOGIN AND AUTHENTICATION MODELS
# =============================================================================

class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(False, description="Extend session duration")

    @validator('username')
    def validate_username(cls, v):
        return v.strip()


class LoginResponse(BaseModel):
    """Login response with JWT tokens"""
    success: bool = True
    message: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: dict
    must_change_password: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PasswordChangeRequired(BaseModel):
    """Response when password change is required"""
    success: bool = False
    error: str = "password_change_required"
    message: str = "You must change your password before accessing this resource"
    change_password_url: str = "/api/v1/auth/change-password"
    temporary_token: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# PASSWORD CHANGE MODELS
# =============================================================================

class PasswordChangeRequest(BaseModel):
    """Password change request model"""
    current_password: Optional[str] = Field(None, description="Current password (not required for forced change)")
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        # Check for at least one number
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordChangeResponse(BaseModel):
    """Password change response"""
    success: bool = True
    message: str = "Password changed successfully"
    access_token: str
    refresh_token: str
    user: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ForcedPasswordChangeRequest(BaseModel):
    """Forced password change request (no current password required)"""
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    temporary_token: str = Field(..., description="Temporary token from login")

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# =============================================================================
# TOKEN AND USER MODELS
# =============================================================================

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class AuthenticatedUser(BaseModel):
    """Authenticated user information"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    must_change_password: bool
    last_login: Optional[datetime]
    created_at: datetime


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: str
    username: str
    email: str
    role: UserRole
    token_type: TokenType
    must_change_password: bool = False
    exp: datetime
    iat: datetime
    jti: str


# =============================================================================
# PASSWORD RESET MODELS
# =============================================================================

class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetResponse(BaseModel):
    """Password reset response"""
    success: bool = True
    message: str = "If the email exists, a password reset link has been sent"


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# =============================================================================
# ERROR MODELS
# =============================================================================

class AuthError(BaseModel):
    """Authentication error response"""
    success: bool = False
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationError(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "validation_error"
    message: str
    details: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
