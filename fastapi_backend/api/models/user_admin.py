"""
Enhanced User Models for Admin User Creation System
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


class CreateUserRequest(BaseModel):
    """Request model for admin user creation"""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole
    initial_balance: Optional[str] = Field("0.00", description="Initial balance as string")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        return v.strip()
    
    @validator('initial_balance')
    def validate_initial_balance(cls, v):
        try:
            float(v)
            if float(v) < 0:
                raise ValueError('Initial balance cannot be negative')
            return v
        except ValueError:
            raise ValueError('Initial balance must be a valid number')


class CreateUserResponse(BaseModel):
    """Response model for successful user creation"""
    success: bool = True
    message: str
    user_id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    temporary_password: str
    login_url: str
    must_change_password: bool = True
    created_at: datetime


class UserListResponse(BaseModel):
    """Response for listing users"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    must_change_password: bool
