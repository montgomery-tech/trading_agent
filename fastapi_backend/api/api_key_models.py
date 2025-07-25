#!/usr/bin/env python3
"""
API Key Models and Validation
Task 1.2: Pydantic models for API key authentication system

Provides comprehensive models for API key management, validation,
and request/response handling with admin-managed key distribution.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from enum import Enum
import re
import secrets
from uuid import UUID
from pydantic import BaseModel, Field, validator, model_validator

class APIKeyScope(str, Enum):
    """API key permission scopes"""
    INHERIT = "inherit"        # Inherit user role permissions
    READ_ONLY = "read_only"    # Read-only access regardless of user role
    FULL_ACCESS = "full_access"  # Full access regardless of user role (admin only)


class APIKeyStatus(str, Enum):
    """API key status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"


class UserRole(str, Enum):
    """User roles (mirrored from auth_models for consistency)"""
    VIEWER = "viewer"
    TRADER = "trader"
    ADMIN = "admin"


# =============================================================================
# API Key Core Models
# =============================================================================

class APIKeyBase(BaseModel):
    """Base API key model with common fields"""
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable key name")
    description: Optional[str] = Field(None, max_length=500, description="Optional key description")
    permissions_scope: APIKeyScope = Field(APIKeyScope.INHERIT, description="Permission scope")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")

    @validator('name')
    def validate_name(cls, v):
        """Validate API key name"""
        v = v.strip()
        if not v:
            raise ValueError('API key name cannot be empty')

        # Only allow alphanumeric, spaces, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('API key name can only contain letters, numbers, spaces, hyphens, and underscores')

        return v

    @validator('expires_at')
    def validate_expiration(cls, v):
        """Validate expiration date"""
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Expiration date must be in the future')
        return v


class APIKey(APIKeyBase):
    """Complete API key model (database representation)"""
    id: Union[str, UUID] = Field(..., description="Unique API key ID")
    key_id: str = Field(..., description="Public key identifier (btapi_xxxxx)")
    user_id: Union[str, UUID] = Field(..., description="Owner user ID")
    is_active: bool = Field(True, description="Whether key is active")
    created_by: Optional[Union[str, UUID]] = Field(None, description="Admin who created the key")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }
        validate_assignment = True


class APIKeyWithUser(APIKey):
    """API key model with user information"""
    user_username: str = Field(..., description="Username of key owner")
    user_email: str = Field(..., description="Email of key owner")
    user_role: UserRole = Field(..., description="Role of key owner")
    created_by_username: Optional[str] = Field(None, description="Username of admin who created key")


# =============================================================================
# Request Models
# =============================================================================

class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key"""
    user_id: Union[str, UUID] = Field(..., description="User ID to create key for")
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    description: Optional[str] = Field(None, max_length=500, description="Key description")
    permissions_scope: APIKeyScope = Field(APIKeyScope.INHERIT, description="Permission scope")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")

    @validator('name')
    def validate_name(cls, v):
        """Validate API key name"""
        v = v.strip()
        if not v:
            raise ValueError('API key name cannot be empty')

        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('API key name can only contain letters, numbers, spaces, hyphens, and underscores')

        return v

    @validator('expires_at')
    def validate_expiration(cls, v):
        """Validate expiration date"""
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Expiration date must be in the future')
        return v


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an API key"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="New key name")
    description: Optional[str] = Field(None, max_length=500, description="New key description")
    is_active: Optional[bool] = Field(None, description="Active status")
    expires_at: Optional[datetime] = Field(None, description="New expiration date")

    @validator('name')
    def validate_name(cls, v):
        """Validate API key name if provided"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('API key name cannot be empty')

            if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
                raise ValueError('API key name can only contain letters, numbers, spaces, hyphens, and underscores')

        return v

    @model_validator(mode='before')
    @classmethod
    def validate_update_fields(cls, values):
        """Ensure at least one field is being updated"""
        provided_fields = {k: v for k, v in values.items() if v is not None}
        if not provided_fields:
            raise ValueError('At least one field must be provided for update')
        return values


class RevokeAPIKeyRequest(BaseModel):
    """Request to revoke an API key"""
    reason: Optional[str] = Field(None, max_length=255, description="Reason for revocation")


# =============================================================================
# Response Models
# =============================================================================

class CreateAPIKeyResponse(BaseModel):
    """Response when API key is created"""
    success: bool = True
    message: str = "API key created successfully"
    key_info: Dict[str, Any] = Field(..., description="API key information (without secret)")
    api_key: str = Field(..., description="Full API key (only shown once)")
    warning: str = "Store this API key securely. It will not be shown again."

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIKeyResponse(BaseModel):
    """Standard API key response (without secret key)"""
    id: Union[str, UUID]
    key_id: str
    name: str
    description: Optional[str]
    permissions_scope: APIKeyScope
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    user_id: Union[str, UUID]
    created_by: Optional[Union[str, UUID]]

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class APIKeyListResponse(BaseModel):
    """Response for listing API keys"""
    success: bool = True
    message: str = "API keys retrieved successfully"
    data: List[APIKeyWithUser]
    pagination: Optional[Dict[str, Any]] = None
    total_count: int

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class APIKeyUsageStats(BaseModel):
    """API key usage statistics"""
    key_id: str
    total_requests: int
    last_24h_requests: int
    last_7d_requests: int
    last_30d_requests: int
    most_used_endpoint: Optional[str]
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# Authentication Models
# =============================================================================

class APIKeyAuthData(BaseModel):
    """Authenticated API key data (equivalent to JWT TokenData)"""
    key_id: str = Field(..., description="Public key identifier")
    user_id: Union[str, UUID] = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    permissions_scope: APIKeyScope = Field(..., description="Key permission scope")
    key_name: str = Field(..., description="Key name")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Key expiration")

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class AuthenticatedAPIKeyUser(BaseModel):
    """Authenticated user via API key (equivalent to AuthenticatedUser from JWT)"""
    id: Union[str, UUID] = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="User active status")
    is_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    # API key specific fields
    api_key_id: str = Field(..., description="API key identifier used")
    api_key_name: str = Field(..., description="API key name")
    api_key_scope: APIKeyScope = Field(..., description="API key permission scope")

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


# =============================================================================
# Utility Models
# =============================================================================

class APIKeyGeneration(BaseModel):
    """API key generation configuration"""
    prefix: str = "btapi"
    length: int = 32
    include_chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    @staticmethod
    def generate_key_id() -> str:
        """Generate a unique API key identifier"""
        # Generate random string for key ID (public part)
        random_part = ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(16))
        return f"btapi_{random_part}"

    @staticmethod
    def generate_api_key() -> str:
        """Generate a complete API key"""
        # Generate key ID (public part)
        key_id = APIKeyGeneration.generate_key_id()

        # Generate secret part (32 additional characters)
        secret_part = ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(32))

        # Combine: btapi_16chars_32chars
        return f"{key_id}_{secret_part}"

    @staticmethod
    def extract_key_id(api_key: str) -> str:
        """Extract the key ID from a full API key"""
        if not api_key.startswith('btapi_'):
            raise ValueError('Invalid API key format')

        parts = api_key.split('_')
        if len(parts) < 2:
            raise ValueError('Invalid API key format')

        return f"{parts[0]}_{parts[1]}"


class APIKeyValidation(BaseModel):
    """API key validation utilities"""

    @staticmethod
    def validate_key_format(api_key: str) -> bool:
        """Validate API key format"""
        # Expected format: btapi_16chars_32chars
        pattern = r'^btapi_[a-zA-Z0-9]{16}_[a-zA-Z0-9]{32}$'
        return bool(re.match(pattern, api_key))

    @staticmethod
    def validate_key_id_format(key_id: str) -> bool:
        """Validate key ID format"""
        # Expected format: btapi_16chars
        pattern = r'^btapi_[a-zA-Z0-9]{16}$'
        return bool(re.match(pattern, key_id))


# =============================================================================
# Error Models
# =============================================================================

class APIKeyError(BaseModel):
    """API key specific error response"""
    success: bool = False
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# Export all models
# =============================================================================

__all__ = [
    # Enums
    'APIKeyScope',
    'APIKeyStatus',
    'UserRole',

    # Core models
    'APIKeyBase',
    'APIKey',
    'APIKeyWithUser',

    # Request models
    'CreateAPIKeyRequest',
    'UpdateAPIKeyRequest',
    'RevokeAPIKeyRequest',

    # Response models
    'CreateAPIKeyResponse',
    'APIKeyResponse',
    'APIKeyListResponse',
    'APIKeyUsageStats',

    # Authentication models
    'APIKeyAuthData',
    'AuthenticatedAPIKeyUser',

    # Utility models
    'APIKeyGeneration',
    'APIKeyValidation',
    'APIKeyError'
]
