"""
Admin User Creation Routes - Task 2.1a
Handles admin-only user provisioning with email notifications
FIXED VERSION - No import errors, works with dictionary database results
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import List
import secrets
import bcrypt
from datetime import datetime
import logging
import uuid
import re

# Local imports - FIXED: Removed PasswordChangeRequest
from api.models.user_admin import (
    CreateUserRequest, CreateUserResponse, UserListResponse, UserRole
)
from api.services.email_service import email_service
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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


# =============================================================================
# ADMIN USER CREATION ENDPOINT
# =============================================================================

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
            # FIXED: Use compatible query without CONCAT
            cursor.execute("""
                SELECT id, username, email, first_name, last_name,
                       is_active, created_at, last_login
                FROM users
                ORDER BY created_at DESC
            """)

            users = []
            for row in cursor.fetchall():
                # FIXED: Use dictionary access instead of index access
                full_name = None
                if row['first_name'] and row['last_name']:
                    full_name = f"{row['first_name']} {row['last_name']}"
                elif row['first_name']:
                    full_name = row['first_name']
                elif row['last_name']:
                    full_name = row['last_name']

                users.append(UserListResponse(
                    id=str(row['id']),
                    username=row['username'],
                    email=row['email'],
                    full_name=full_name,
                    role=UserRole.TRADER,
                    is_active=bool(row['is_active']),
                    created_at=row['created_at'] if isinstance(row['created_at'], datetime) else datetime.fromisoformat(str(row['created_at'])),
                    last_login=row['last_login'] if row['last_login'] and isinstance(row['last_login'], datetime) else None,
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
