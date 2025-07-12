"""
Admin Routes for Balance Tracking API
Admin-only endpoints for user management and system administration
"""

import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr, Field, validator

from api.dependencies import get_database
from api.database import DatabaseManager
from api.jwt_service import password_service
from api.auth_models import UserRole

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Admin Request/Response Models
# =============================================================================

class CreateUserRequest(BaseModel):
    """Request model for creating a new user"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    role: str = Field(default="trader", description="User role")

    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['admin', 'trader', 'viewer']
        if v.lower() not in valid_roles:
            raise ValueError(f'Role must be one of: {valid_roles}')
        return v.lower()


class CreateUserResponse(BaseModel):
    """Response model for user creation"""
    success: bool = True
    message: str = "User created successfully"
    user_id: str
    username: str
    email: str
    temporary_password: str
    must_change_password: bool = True
    role: str


class AdminUserInfo(BaseModel):
    """Admin view of user information"""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    must_change_password: bool
    created_at: datetime
    last_login: Optional[datetime]


# =============================================================================
# Helper Functions
# =============================================================================

def generate_username(email: str, db: DatabaseManager) -> str:
    """Generate a unique username from email"""
    base_username = email.split('@')[0].lower()

    # Check if base username exists
    if not username_exists(base_username, db):
        return base_username

    # Try with numbers
    counter = 1
    while counter <= 999:
        test_username = f"{base_username}{counter}"
        if not username_exists(test_username, db):
            return test_username
        counter += 1

    # Fallback to UUID if all attempts fail
    return f"{base_username}_{str(uuid.uuid4())[:8]}"


def username_exists(username: str, db: DatabaseManager) -> bool:
    """Check if username already exists"""
    try:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking username existence: {e}")
        return True  # Assume exists on error to be safe


def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    import string

    # Ensure password has at least one of each required character type
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%"

    password = [
        secrets.choice(string.ascii_lowercase),  # At least one lowercase
        secrets.choice(string.ascii_uppercase),  # At least one uppercase
        secrets.choice(string.digits),           # At least one digit
        secrets.choice("!@#$%")                  # At least one special char
    ]

    # Fill the rest randomly
    for _ in range(length - 4):
        password.append(secrets.choice(chars))

    # Shuffle to randomize positions
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


# =============================================================================
# Admin User Management Endpoints
# =============================================================================

@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Create a new user (Admin only)

    Creates a new user with a temporary password that must be changed on first login.
    """
    try:
        # Check if email already exists
        with db.get_cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with email {request.email} already exists"
                )

            # Generate user data
            user_id = str(uuid.uuid4())
            username = generate_username(request.email, db)
            temporary_password = generate_temporary_password()
            password_hash = password_service.hash_password(temporary_password)

            # Parse full name
            name_parts = request.full_name.strip().split()
            first_name = name_parts[0] if name_parts else "User"
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            # Insert new user
            cursor.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                username,
                request.email,
                password_hash,
                first_name,
                last_name,
                True,   # is_active
                True,   # is_verified (admin-created users are pre-verified)
                True,   # must_change_password
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ))

            # CRITICAL: Explicit commit
            db.connection.commit()

            # Verify the insert worked
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                raise Exception("User creation verification failed")

        logger.info(f"Admin created new user: {username} ({request.email})")

        return CreateUserResponse(
            user_id=user_id,
            username=username,
            email=request.email,
            temporary_password=temporary_password,
            role=request.role
        )

    except HTTPException:
        raise
    except Exception as e:
        # Rollback on any error
        try:
            db.connection.rollback()
        except:
            pass

        logger.error(f"User creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}"
        )


@router.get("/users", response_model=list[AdminUserInfo])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: DatabaseManager = Depends(get_database)
):
    """List all users (Admin only)"""
    try:
        offset = (page - 1) * page_size

        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, must_change_password,
                       created_at, last_login
                FROM users
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (page_size, offset))

            users = []
            for row in cursor.fetchall():
                full_name = f"{row['first_name']} {row['last_name']}".strip()
                users.append(AdminUserInfo(
                    id=row['id'],
                    username=row['username'],
                    email=row['email'],
                    full_name=full_name or None,
                    role='trader',  # Default role, could be extended
                    is_active=row['is_active'],
                    is_verified=row['is_verified'],
                    must_change_password=row['must_change_password'],
                    created_at=row['created_at'],
                    last_login=row['last_login']
                ))

            return users

    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}", response_model=AdminUserInfo)
async def get_user(
    user_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get user details (Admin only)"""
    try:
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, must_change_password,
                       created_at, last_login
                FROM users
                WHERE id = %s
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User {user_id} not found"
                )

            full_name = f"{row['first_name']} {row['last_name']}".strip()
            return AdminUserInfo(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                full_name=full_name or None,
                role='trader',  # Default role
                is_active=row['is_active'],
                is_verified=row['is_verified'],
                must_change_password=row['must_change_password'],
                created_at=row['created_at'],
                last_login=row['last_login']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """Deactivate a user (Admin only)"""
    try:
        with db.get_cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User {user_id} not found"
                )

            # Deactivate user (don't delete, just mark inactive)
            cursor.execute("""
                UPDATE users
                SET is_active = %s, updated_at = %s
                WHERE id = %s
            """, (False, datetime.now(timezone.utc), user_id))

            # CRITICAL: Explicit commit
            db.connection.commit()

            logger.info(f"Admin deactivated user: {user['username']}")

            return {
                "success": True,
                "message": f"User {user['username']} deactivated successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        # Rollback on error
        try:
            db.connection.rollback()
        except:
            pass

        logger.error(f"Failed to deactivate user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


# =============================================================================
# Admin System Information Endpoints
# =============================================================================

@router.get("/stats")
async def get_system_stats(
    db: DatabaseManager = Depends(get_database)
):
    """Get system statistics (Admin only)"""
    try:
        with db.get_cursor() as cursor:
            # Get user counts
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total_users = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as active FROM users WHERE is_active = %s", (True,))
            active_users = cursor.fetchone()['active']

            cursor.execute("SELECT COUNT(*) as pending FROM users WHERE must_change_password = %s", (True,))
            pending_password_changes = cursor.fetchone()['pending']

            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "inactive": total_users - active_users,
                    "pending_password_changes": pending_password_changes
                },
                "system": {
                    "timestamp": datetime.now(timezone.utc),
                    "database_type": db.db_type
                }
            }

    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )
