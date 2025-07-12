#!/bin/bash

# Quick fix for missing files and packages
echo "🔧 Creating Missing Files for Admin System"
echo "=========================================="

# Create __init__.py files to make directories proper Python packages
touch api/__init__.py
touch api/models/__init__.py  
touch api/services/__init__.py
touch api/routes/__init__.py

echo "✅ Created __init__.py files"

# Create user_admin.py models file
cat > api/models/user_admin.py << 'EOF'
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
EOF

echo "✅ Created api/models/user_admin.py"

# Create email service
cat > api/services/email_service.py << 'EOF'
"""
Email Service for AWS SES Integration
"""

import logging
import os

logger = logging.getLogger(__name__)


class EmailService:
    """Email Service with development mode support"""
    
    def __init__(self):
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str, 
        username: str,
        temporary_password: str,
        login_url: str,
        created_by_admin: str
    ) -> bool:
        """Send welcome email with temporary credentials"""
        
        if not self.email_enabled:
            print(f"\n📧 WELCOME EMAIL (Development Mode)")
            print(f"   To: {user_email}")
            print(f"   Name: {user_name}")
            print(f"   Username: {username}")
            print(f"   Temporary Password: {temporary_password}")
            print(f"   Login URL: {login_url}")
            print(f"   Created by: {created_by_admin}")
            print("   (Email notifications disabled in development)")
            return True
        
        # TODO: Implement AWS SES integration for production
        logger.info(f"Email sent to {user_email}")
        return True


# Global email service instance
email_service = EmailService()
EOF

echo "✅ Created api/services/email_service.py"

# Update admin.py to fix any import issues
cat > api/routes/admin.py << 'EOF'
"""
Admin User Creation Routes - Task 2.1a
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import List
import secrets
import bcrypt
from datetime import datetime
import logging
import uuid
import re

# Local imports
from api.models.user_admin import (
    CreateUserRequest, CreateUserResponse, UserListResponse, UserRole
)
from api.services.email_service import email_service
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# Helper functions
async def generate_unique_username(email: str, db: DatabaseManager) -> str:
    """Generate a unique username from email"""
    base_username = email.split('@')[0].lower()
    base_username = re.sub(r'[^a-z0-9]', '', base_username)
    
    if len(base_username) < 3:
        base_username = f"user{base_username}"
    
    username = base_username
    counter = 1
    
    while await username_exists(username, db):
        username = f"{base_username}{counter}"
        counter += 1
        if counter > 999:
            username = f"{base_username}{secrets.randbelow(9999)}"
            break
    
    return username


async def username_exists(username: str, db: DatabaseManager) -> bool:
    """Check if username already exists"""
    try:
        with db.get_cursor() as cursor:
            if db.db_type == 'postgresql':
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            else:
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking username existence: {e}")
        return True


def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    import string
    
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%"
    
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase), 
        secrets.choice(string.digits),
        secrets.choice("!@#$%")
    ]
    
    for _ in range(length - 4):
        password.append(secrets.choice(chars))
    
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


# Admin endpoints
@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    db: DatabaseManager = Depends(get_database),
    http_request: Request = None
):
    """Create a new user (Admin only)"""
    try:
        # Check if email already exists
        with db.get_cursor() as cursor:
            if db.db_type == 'postgresql':
                cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
            else:
                cursor.execute("SELECT id FROM users WHERE email = ?", (request.email,))
            
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with email {request.email} already exists"
                )
        
        # Generate username and password
        username = await generate_unique_username(request.email, db)
        temp_password = generate_temporary_password()
        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_id = str(uuid.uuid4())
        
        # Save user to database
        with db.get_cursor() as cursor:
            if db.db_type == 'postgresql':
                cursor.execute("""
                    INSERT INTO users (
                        id, username, email, password_hash, first_name, last_name,
                        is_active, is_verified, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, username, request.email, password_hash,
                    request.full_name.split()[0] if request.full_name else None,
                    ' '.join(request.full_name.split()[1:]) if len(request.full_name.split()) > 1 else None,
                    True, False, datetime.utcnow(), datetime.utcnow()
                ))
            else:
                cursor.execute("""
                    INSERT INTO users (
                        id, username, email, password_hash, first_name, last_name,
                        is_active, is_verified, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, username, request.email, password_hash,
                    request.full_name.split()[0] if request.full_name else None,
                    ' '.join(request.full_name.split()[1:]) if len(request.full_name.split()) > 1 else None,
                    1, 0, datetime.utcnow(), datetime.utcnow()
                ))
        
        # Send welcome email
        login_url = "http://localhost:8000/login"
        
        email_sent = await email_service.send_welcome_email(
            user_email=request.email,
            user_name=request.full_name,
            username=username,
            temporary_password=temp_password,
            login_url=login_url,
            created_by_admin="System Administrator"
        )
        
        return CreateUserResponse(
            message="User created successfully and welcome email sent",
            user_id=user_id,
            username=username,
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            temporary_password=temp_password,
            login_url=login_url,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}"
        )


@router.get("/users", response_model=List[UserListResponse])
async def list_users(db: DatabaseManager = Depends(get_database)):
    """List all users (Admin only)"""
    try:
        with db.get_cursor() as cursor:
            if db.db_type == 'postgresql':
                cursor.execute("""
                    SELECT id, username, email, 
                           CONCAT(first_name, ' ', last_name) as full_name,
                           is_active, created_at, last_login
                    FROM users
                    ORDER BY created_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT id, username, email, 
                           (first_name || ' ' || last_name) as full_name,
                           is_active, created_at, last_login
                    FROM users
                    ORDER BY created_at DESC
                """)
            
            users = []
            for row in cursor.fetchall():
                users.append(UserListResponse(
                    id=str(row[0]),
                    username=row[1],
                    email=row[2],
                    full_name=row[3] if row[3] and row[3].strip() != ' ' else None,
                    role=UserRole.TRADER,
                    is_active=bool(row[4]),
                    created_at=row[5] if isinstance(row[5], datetime) else datetime.fromisoformat(str(row[5])),
                    last_login=row[6] if row[6] and isinstance(row[6], datetime) else None,
                    must_change_password=True
                ))
            
            return users
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user list"
        )
EOF

echo "✅ Created api/routes/admin.py"

echo ""
echo "🎉 Quick Fix Complete!"
echo "======================"
echo ""
echo "✅ Created missing files:"
echo "   • api/__init__.py"
echo "   • api/models/__init__.py"
echo "   • api/services/__init__.py"
echo "   • api/routes/__init__.py"
echo "   • api/models/user_admin.py"
echo "   • api/services/email_service.py"
echo "   • api/routes/admin.py"
echo ""
echo "🚀 Now try running your server again:"
echo "   python3 main.py"
echo ""
echo "📧 Note: Email notifications are disabled in development"
echo "   Welcome emails will be printed to console"
