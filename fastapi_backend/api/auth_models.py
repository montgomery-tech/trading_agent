#!/usr/bin/env python3
"""
Authentication models for the Balance Tracking API
JWT tokens, user authentication, and registration models
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import re


class UserRole(str, Enum):
    """User roles for role-based access control"""
    VIEWER = "viewer"  # View only access
    TRADER = "trader"  # Can trade, view balances, view transactions, request withdrawals
    ADMIN = "admin"    # Full access


class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


# =============================================================================
# User Registration and Login Models
# =============================================================================

class UserRegistrationRequest(BaseModel):
    """User registration request model"""
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8+ characters)")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    role: Optional[UserRole] = Field(UserRole.VIEWER, description="User role")

    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        return v

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        """Validate name fields"""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if not re.match(r'^[a-zA-Z\s\'-]+$', v):
                raise ValueError('Names can only contain letters, spaces, hyphens, and apostrophes')
        return v


class UserLoginRequest(BaseModel):
    """User login request model"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Extended session duration")

    @validator('username')
    def validate_username(cls, v):
        return v.strip().lower()


class PasswordChangeRequest(BaseModel):
    """Password change request model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        return v


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr = Field(..., description="Email address for password reset")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class EmailVerificationRequest(BaseModel):
    """Email verification request model"""
    token: str = Field(..., description="Email verification token")


# =============================================================================
# JWT Token Models
# =============================================================================

class Token(BaseModel):
    """JWT token response model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token (if applicable)")
    scope: Optional[str] = Field(None, description="Token scope")


class TokenData(BaseModel):
    """Token payload data model"""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email")
    role: UserRole = Field(..., description="User role")
    token_type: TokenType = Field(..., description="Token type")
    issued_at: datetime = Field(..., description="Token issued time")
    expires_at: datetime = Field(..., description="Token expiration time")
    jti: str = Field(..., description="JWT ID (unique token identifier)")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str = Field(..., description="Refresh token")


# =============================================================================
# User Response Models
# =============================================================================

class AuthenticatedUser(BaseModel):
    """Authenticated user response model"""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserProfile(BaseModel):
    """User profile response model"""
    id: str
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuthenticationResponse(BaseModel):
    """Complete authentication response model"""
    success: bool = Field(True, description="Authentication success status")
    message: str = Field(..., description="Response message")
    user: AuthenticatedUser = Field(..., description="User information")
    token: Token = Field(..., description="JWT tokens")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# API Response Models
# =============================================================================

class AuthSuccessResponse(BaseModel):
    """Authentication success response"""
    success: bool = True
    message: str = "Authentication successful"
    data: AuthenticationResponse
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuthErrorResponse(BaseModel):
    """Authentication error response"""
    success: bool = False
    message: str
    error_code: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserCreatedResponse(BaseModel):
    """User creation success response"""
    success: bool = True
    message: str = "User created successfully"
    user_id: str
    username: str
    email: str
    email_verification_required: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Validation Models
# =============================================================================

class UsernameAvailability(BaseModel):
    """Username availability check response"""
    username: str
    available: bool
    suggestions: Optional[List[str]] = None


class EmailAvailability(BaseModel):
    """Email availability check response"""
    email: str
    available: bool


class PasswordStrength(BaseModel):
    """Password strength analysis"""
    score: int = Field(..., ge=0, le=100, description="Password strength score (0-100)")
    feedback: List[str] = Field(default_factory=list, description="Password improvement suggestions")
    is_strong: bool = Field(..., description="Whether password meets minimum requirements")


# =============================================================================
# Settings and Configuration Models
# =============================================================================

class JWTSettings(BaseModel):
    """JWT configuration settings"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    issuer: str = "balance-tracking-api"
    audience: str = "balance-tracking-users"


class AuthSettings(BaseModel):
    """Authentication configuration settings"""
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = False
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    email_verification_required: bool = True
    email_verification_expire_hours: int = 24
    password_reset_expire_hours: int = 2
