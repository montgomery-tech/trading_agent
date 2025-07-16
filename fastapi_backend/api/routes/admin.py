"""
Complete Enhanced Admin Routes for Balance Tracking API
Combines existing functionality with new admin management features
"""

import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field, validator

from api.dependencies import get_database
from api.database import DatabaseManager
from api.jwt_service import password_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# All Admin Request/Response Models
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


class UpdateUserRoleRequest(BaseModel):
    """Request model for updating user role"""
    role: str = Field(..., description="New user role")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for role change")

    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['admin', 'trader', 'viewer']
        if v.lower() not in valid_roles:
            raise ValueError(f'Role must be one of: {valid_roles}')
        return v.lower()


class UpdateUserStatusRequest(BaseModel):
    """Request model for updating user status"""
    is_active: bool = Field(..., description="User active status")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")


class ResetPasswordRequest(BaseModel):
    """Request model for admin password reset"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for password reset")


class UserActionResponse(BaseModel):
    """Response for user management actions"""
    success: bool = True
    message: str
    user_id: str
    action_performed: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
        query = "SELECT id FROM users WHERE username = {}"
        query = query.format('%s' if db.db_type == 'postgresql' else '?')
        results = db.execute_query(query, (username,))
        return len(results) > 0
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
# Core Admin User Management Endpoints
# =============================================================================

@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Create a new user

    Creates a new user with a temporary password that must be changed on first login.
    """
    try:
        # Check if email already exists
        check_query = "SELECT id FROM users WHERE email = {}"
        check_query = check_query.format('%s' if db.db_type == 'postgresql' else '?')
        existing = db.execute_query(check_query, (request.email,))

        if existing:
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
        if db.db_type == 'postgresql':
            insert_query = """
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, role, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                user_id, username, request.email, password_hash, first_name, last_name,
                True, True, True, request.role, datetime.now(timezone.utc), datetime.now(timezone.utc)
            )
        else:
            # SQLite - without role column initially
            insert_query = """
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                user_id, username, request.email, password_hash, first_name, last_name,
                True, True, True, datetime.now(timezone.utc), datetime.now(timezone.utc)
            )

        db.execute_command(insert_query, params)

        logger.info(f"Created new user: {username} ({request.email}) with role {request.role}")

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
        logger.error(f"User creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}"
        )


@router.get("/users", response_model=List[AdminUserInfo])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
    role_filter: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """List all users with filtering options"""
    try:
        # Validate pagination
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        offset = (page - 1) * page_size

        # Build query
        base_query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, must_change_password,
                   created_at, last_login,
                   COALESCE(role, 'trader') as role
            FROM users
        """

        conditions = []
        params = []

        if active_only:
            conditions.append("is_active = {}".format('%s' if db.db_type == 'postgresql' else '?'))
            params.append(True)

        if role_filter:
            conditions.append("COALESCE(role, 'trader') = {}".format('%s' if db.db_type == 'postgresql' else '?'))
            params.append(role_filter.lower())

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY created_at DESC"

        if db.db_type == 'postgresql':
            base_query += " LIMIT %s OFFSET %s"
        else:
            base_query += " LIMIT ? OFFSET ?"

        params.extend([page_size, offset])

        results = db.execute_query(base_query, params)

        users = []
        for row in results:
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            users.append(AdminUserInfo(
                id=row['id'],
                username=row['username'],
                email=row['email'],
                full_name=full_name or None,
                role=row.get('role', 'trader'),
                is_active=row['is_active'],
                is_verified=row['is_verified'],
                must_change_password=row['must_change_password'],
                created_at=row['created_at'],
                last_login=row['last_login']
            ))

        logger.info(f"Listed users (page {page}, {len(users)} results)")
        return users

    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )
@router.get("/users/search")
async def search_users(
    query: str,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 20,
    db: DatabaseManager = Depends(get_database)
):
    """Search users by username, email, or name"""
    try:
        if len(query.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters"
            )

        # Build search query
        if db.db_type == 'postgresql':
            search_query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, role, created_at, last_login
                FROM users
                WHERE (username ILIKE %s OR email ILIKE %s OR
                       first_name ILIKE %s OR last_name ILIKE %s)
            """
            params = [f"%{query}%"] * 4
        else:
            search_query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, role, created_at, last_login
                FROM users
                WHERE (username LIKE ? OR email LIKE ? OR
                       first_name LIKE ? OR last_name LIKE ?)
            """
            params = [f"%{query}%"] * 4

        # Add filters
        if role_filter:
            search_query += " AND role = {}".format('%s' if db.db_type == 'postgresql' else '?')
            params.append(role_filter)

        if status_filter == "active":
            search_query += " AND is_active = {}".format('%s' if db.db_type == 'postgresql' else '?')
            params.append(True)
        elif status_filter == "inactive":
            search_query += " AND is_active = {}".format('%s' if db.db_type == 'postgresql' else '?')
            params.append(False)

        search_query += " ORDER BY username LIMIT {}".format('%s' if db.db_type == 'postgresql' else '?')
        params.append(limit)

        results = db.execute_query(search_query, params)

        users = []
        for row in results:
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            users.append({
                "id": row['id'],
                "username": row['username'],
                "email": row['email'],
                "full_name": full_name or None,
                "role": row.get('role', 'viewer'),
                "is_active": row['is_active'],
                "is_verified": row['is_verified'],
                "created_at": row['created_at'],
                "last_login": row['last_login']
            })

        return {
            "success": True,
            "query": query,
            "results_count": len(users),
            "users": users
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User search failed"
        )


@router.get("/users/{user_id}", response_model=AdminUserInfo)
async def get_user(
    user_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get user details"""
    try:
        query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, must_change_password,
                   created_at, last_login,
                   COALESCE(role, 'trader') as role
            FROM users
            WHERE id = {}
        """.format('%s' if db.db_type == 'postgresql' else '?')

        results = db.execute_query(query, (user_id,))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        row = results[0]
        full_name = f"{row['first_name']} {row['last_name']}".strip()

        return AdminUserInfo(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            full_name=full_name or None,
            role=row.get('role', 'trader'),
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


# =============================================================================
# Enhanced Admin Management Endpoints
# =============================================================================

@router.put("/users/{user_id}/role", response_model=UserActionResponse)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Update a user's role

    Allows changing user roles between admin, trader, and viewer.
    """
    try:
        # Check if user exists and get current role
        user_query = "SELECT username, role FROM users WHERE id = {}"
        user_query = user_query.format('%s' if db.db_type == 'postgresql' else '?')
        user_results = db.execute_query(user_query, (user_id,))

        if not user_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        user = user_results[0]
        old_role = user.get('role', 'viewer')

        if old_role == request.role:
            return UserActionResponse(
                message=f"User already has role '{request.role}'",
                user_id=user_id,
                action_performed="no_change"
            )

        # Update user role
        update_query = "UPDATE users SET role = {}, updated_at = {} WHERE id = {}"
        update_query = update_query.format(
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?'
        )

        db.execute_command(update_query, (request.role, datetime.now(timezone.utc), user_id))

        logger.info(f"User role updated: {user['username']} from {old_role} to {request.role}")

        return UserActionResponse(
            message=f"User role updated from '{old_role}' to '{request.role}'",
            user_id=user_id,
            action_performed="role_update"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )


@router.put("/users/{user_id}/status", response_model=UserActionResponse)
async def update_user_status(
    user_id: str,
    request: UpdateUserStatusRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Activate or deactivate a user account
    """
    try:
        # Check if user exists
        user_query = "SELECT username, is_active FROM users WHERE id = {}"
        user_query = user_query.format('%s' if db.db_type == 'postgresql' else '?')
        user_results = db.execute_query(user_query, (user_id,))

        if not user_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        user = user_results[0]
        old_status = user['is_active']

        if old_status == request.is_active:
            status_text = "active" if request.is_active else "inactive"
            return UserActionResponse(
                message=f"User is already {status_text}",
                user_id=user_id,
                action_performed="no_change"
            )

        # Update user status
        update_query = "UPDATE users SET is_active = {}, updated_at = {} WHERE id = {}"
        update_query = update_query.format(
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?'
        )

        db.execute_command(update_query, (request.is_active, datetime.now(timezone.utc), user_id))

        action = "activate_user" if request.is_active else "deactivate_user"
        status_text = "activated" if request.is_active else "deactivated"

        logger.info(f"User {status_text}: {user['username']}")

        return UserActionResponse(
            message=f"User {status_text} successfully",
            user_id=user_id,
            action_performed=action
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status"
        )


@router.post("/users/{user_id}/reset-password", response_model=UserActionResponse)
async def admin_reset_user_password(
    user_id: str,
    request: ResetPasswordRequest,
    db: DatabaseManager = Depends(get_database)
):
    """
    Force password reset for a user

    Generates a new temporary password and forces the user to change it on next login.
    """
    try:
        # Check if user exists
        user_query = "SELECT username FROM users WHERE id = {}"
        user_query = user_query.format('%s' if db.db_type == 'postgresql' else '?')
        user_results = db.execute_query(user_query, (user_id,))

        if not user_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        user = user_results[0]

        # Generate new temporary password
        temporary_password = generate_temporary_password()
        password_hash = password_service.hash_password(temporary_password)

        # Update password and set must_change_password flag
        update_query = """
            UPDATE users
            SET password_hash = {}, must_change_password = {}, updated_at = {}
            WHERE id = {}
        """.format(
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?'
        )

        db.execute_command(update_query, (password_hash, True, datetime.now(timezone.utc), user_id))

        logger.info(f"Password reset for user: {user['username']}")

        return UserActionResponse(
            message=f"Password reset for user '{user['username']}'. Temporary password: {temporary_password}",
            user_id=user_id,
            action_performed="password_reset"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset user password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset user password"
        )

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """Deactivate a user"""
    try:
        # Check if user exists
        check_query = "SELECT username FROM users WHERE id = {}"
        check_query = check_query.format('%s' if db.db_type == 'postgresql' else '?')
        user_results = db.execute_query(check_query, (user_id,))

        if not user_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        user = user_results[0]

        # Deactivate user (don't delete, just mark inactive)
        update_query = """
            UPDATE users
            SET is_active = {}, updated_at = {}
            WHERE id = {}
        """.format(
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?',
            '%s' if db.db_type == 'postgresql' else '?'
        )

        db.execute_command(update_query, (False, datetime.now(timezone.utc), user_id))

        logger.info(f"Deactivated user: {user['username']}")

        return {
            "success": True,
            "message": f"User {user['username']} deactivated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
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
    """Get enhanced system statistics"""
    try:
        stats = {}

        # User statistics
        total_query = "SELECT COUNT(*) as total FROM users"
        total_result = db.execute_query(total_query, ())
        stats['total_users'] = total_result[0]['total'] if total_result else 0

        active_query = "SELECT COUNT(*) as active FROM users WHERE is_active = {}"
        active_query = active_query.format('%s' if db.db_type == 'postgresql' else '?')
        active_result = db.execute_query(active_query, (True,))
        stats['active_users'] = active_result[0]['active'] if active_result else 0

        pending_query = "SELECT COUNT(*) as pending FROM users WHERE must_change_password = {}"
        pending_query = pending_query.format('%s' if db.db_type == 'postgresql' else '?')
        pending_result = db.execute_query(pending_query, (True,))
        stats['pending_password_changes'] = pending_result[0]['pending'] if pending_result else 0

        # Role distribution
        try:
            role_query = """
                SELECT COALESCE(role, 'trader') as role, COUNT(*) as count
                FROM users
                GROUP BY COALESCE(role, 'trader')
            """
            role_results = db.execute_query(role_query, ())
            stats['users_by_role'] = {row['role']: row['count'] for row in role_results}
        except:
            stats['users_by_role'] = {'trader': stats['total_users']}

        return {
            "success": True,
            "data": {
                "users": stats,
                "system": {
                    "timestamp": datetime.now(timezone.utc),
                    "database_type": db.db_type
                }
            }
        }

    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )
