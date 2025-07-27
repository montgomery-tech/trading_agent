#!/usr/bin/env python3
"""
Enhanced Admin Routes for Balance Tracking API with API Key Authentication
Complete admin management features with API key-based authentication and role-based access control
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
from api.auth_dependencies import require_admin_api_key, AuthenticatedAPIKeyUser
from api.password_service import password_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
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


class AdminStatsResponse(BaseModel):
    """Response model for admin statistics"""
    total_users: int
    active_users: int
    inactive_users: int
    verified_users: int
    unverified_users: int
    users_by_role: dict
    users_requiring_password_change: int
    recent_registrations: int


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


async def log_admin_action(
    admin_user: AuthenticatedAPIKeyUser,
    action: str,
    target_user_id: str,
    details: Optional[dict] = None
):
    """Log admin actions for audit trail"""
    logger.info(
        f"ADMIN ACTION: {admin_user.username} ({admin_user.id}) performed '{action}' "
        f"on user {target_user_id}. Details: {details}"
    )


# =============================================================================
# Admin Statistics Endpoint
# =============================================================================

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Get comprehensive admin statistics"""
    try:
        # Total users
        total_query = "SELECT COUNT(*) as count FROM users"
        total_result = db.execute_query(total_query)
        total_users = total_result[0]['count'] if total_result else 0

        # Active/Inactive users
        active_query = "SELECT COUNT(*) as count FROM users WHERE is_active = {}"
        active_query = active_query.format('%s' if db.db_type == 'postgresql' else '?')
        active_result = db.execute_query(active_query, (True,))
        active_users = active_result[0]['count'] if active_result else 0
        inactive_users = total_users - active_users

        # Verified/Unverified users
        verified_query = "SELECT COUNT(*) as count FROM users WHERE is_verified = {}"
        verified_query = verified_query.format('%s' if db.db_type == 'postgresql' else '?')
        verified_result = db.execute_query(verified_query, (True,))
        verified_users = verified_result[0]['count'] if verified_result else 0
        unverified_users = total_users - verified_users

        # Users by role
        role_query = """
            SELECT COALESCE(role, 'trader') as role, COUNT(*) as count
            FROM users
            GROUP BY COALESCE(role, 'trader')
        """
        role_results = db.execute_query(role_query)
        users_by_role = {row['role']: row['count'] for row in role_results}

        # Users requiring password change
        password_query = "SELECT COUNT(*) as count FROM users WHERE must_change_password = {}"
        password_query = password_query.format('%s' if db.db_type == 'postgresql' else '?')
        password_result = db.execute_query(password_query, (True,))
        users_requiring_password_change = password_result[0]['count'] if password_result else 0

        # Recent registrations (last 7 days)
        if db.db_type == 'postgresql':
            recent_query = "SELECT COUNT(*) as count FROM users WHERE created_at >= NOW() - INTERVAL '7 days'"
            recent_result = db.execute_query(recent_query)
        else:
            recent_query = "SELECT COUNT(*) as count FROM users WHERE created_at >= datetime('now', '-7 days')"
            recent_result = db.execute_query(recent_query)

        recent_registrations = recent_result[0]['count'] if recent_result else 0

        await log_admin_action(admin_user, "view_stats", "system", {"stats_requested": True})

        return AdminStatsResponse(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            verified_users=verified_users,
            unverified_users=unverified_users,
            users_by_role=users_by_role,
            users_requiring_password_change=users_requiring_password_change,
            recent_registrations=recent_registrations
        )

    except Exception as e:
        logger.error(f"Failed to get admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve admin statistics"
        )


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Create a new user (Admin Only)"""
    try:
        # Check if email already exists
        email_check_query = "SELECT id FROM users WHERE email = {}"
        email_check_query = email_check_query.format('%s' if db.db_type == 'postgresql' else '?')
        existing_email = db.execute_query(email_check_query, (request.email,))

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email '{request.email}' already exists"
            )

        # Generate unique username
        username = generate_username(request.email, db)

        # Generate temporary password
        temporary_password = generate_temporary_password()
        password_hash = password_service.hash_password(temporary_password)

        # Split full name
        name_parts = request.full_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Generate user ID
        user_id = str(uuid.uuid4())

        # Insert user
        if db.db_type == 'postgresql':
            insert_query = """
                INSERT INTO users (id, username, email, password_hash, first_name, last_name,
                                 is_active, is_verified, must_change_password, role, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                user_id, username, request.email, password_hash, first_name, last_name,
                True, True, True, request.role, datetime.now(timezone.utc), datetime.now(timezone.utc)
            )
        else:
            insert_query = """
                INSERT INTO users (id, username, email, password_hash, first_name, last_name,
                                 is_active, is_verified, must_change_password, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                user_id, username, request.email, password_hash, first_name, last_name,
                True, True, True, request.role, datetime.now(timezone.utc), datetime.now(timezone.utc)
            )

        db.execute_command(insert_query, params)

        await log_admin_action(
            admin_user,
            "create_user",
            user_id,
            {"email": request.email, "role": request.role, "username": username}
        )

        logger.info(f"Admin {admin_user.username} created new user: {username} ({request.email}) with role {request.role}")

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


@router.get("/users/search")
async def search_users(
    query: str,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 20,
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Search users by username, email, or name (Admin Only)"""
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
                "role": row.get('role', 'trader'),
                "is_active": row['is_active'],
                "is_verified": row['is_verified'],
                "created_at": row['created_at'],
                "last_login": row['last_login']
            })

        await log_admin_action(
            admin_user,
            "search_users",
            "system",
            {"query": query, "results_count": len(users)}
        )

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
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Get user details (Admin Only)"""
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
                detail=f"User with ID '{user_id}' not found"
            )

        row = results[0]
        full_name = f"{row['first_name']} {row['last_name']}".strip()

        await log_admin_action(admin_user, "view_user", user_id, {"action": "get_user_details"})

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


@router.get("/users", response_model=List[AdminUserInfo])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
    role_filter: Optional[str] = None,
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """List all users with filtering options (Admin Only)"""
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

        await log_admin_action(
            admin_user,
            "list_users",
            "system",
            {"page": page, "filters": {"active_only": active_only, "role_filter": role_filter}}
        )

        logger.info(f"Admin {admin_user.username} listed users (page {page}, {len(users)} results)")
        return users

    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.put("/users/{user_id}/role", response_model=UserActionResponse)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Update user role (Admin Only)"""
    try:
        # Get current user data
        check_query = "SELECT username, role FROM users WHERE id = {}"
        check_query = check_query.format('%s' if db.db_type == 'postgresql' else '?')
        current_user_data = db.execute_query(check_query, (user_id,))

        if not current_user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found"
            )

        current_role = current_user_data[0].get('role', 'trader')
        username = current_user_data[0]['username']

        # Update role
        update_query = "UPDATE users SET role = {}, updated_at = {} WHERE id = {}"
        if db.db_type == 'postgresql':
            update_query = update_query.format('%s', 'NOW()', '%s')
            params = (request.role, user_id)
        else:
            update_query = update_query.format('?', "datetime('now')", '?')
            params = (request.role, user_id)

        db.execute_command(update_query, params)

        await log_admin_action(
            admin_user,
            "update_user_role",
            user_id,
            {
                "old_role": current_role,
                "new_role": request.role,
                "reason": request.reason,
                "target_username": username
            }
        )

        logger.info(f"User role updated: {username} from {current_role} to {request.role}")

        return UserActionResponse(
            message=f"User role updated from '{current_role}' to '{request.role}'",
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
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Update user status (activate/deactivate) (Admin Only)"""
    try:
        # Get current user data
        check_query = "SELECT username, is_active FROM users WHERE id = {}"
        check_query = check_query.format('%s' if db.db_type == 'postgresql' else '?')
        current_user_data = db.execute_query(check_query, (user_id,))

        if not current_user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found"
            )

        username = current_user_data[0]['username']
        current_status = current_user_data[0]['is_active']

        # Prevent admin from deactivating themselves
        if user_id == admin_user.id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account"
            )

        # Update status
        update_query = "UPDATE users SET is_active = {}, updated_at = {} WHERE id = {}"
        if db.db_type == 'postgresql':
            update_query = update_query.format('%s', 'NOW()', '%s')
            params = (request.is_active, user_id)
        else:
            update_query = update_query.format('?', "datetime('now')", '?')
            params = (request.is_active, user_id)

        db.execute_command(update_query, params)

        action = "activate_user" if request.is_active else "deactivate_user"
        await log_admin_action(
            admin_user,
            action,
            user_id,
            {
                "old_status": current_status,
                "new_status": request.is_active,
                "reason": request.reason,
                "target_username": username
            }
        )

        status_word = "activated" if request.is_active else "deactivated"
        logger.info(f"User {status_word}: {username}")

        return UserActionResponse(
            message=f"User {status_word} successfully",
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
async def reset_user_password(
    user_id: str,
    request: ResetPasswordRequest,
    admin_user: AuthenticatedAPIKeyUser = Depends(require_admin_api_key()),
    db: DatabaseManager = Depends(get_database)
):
    """Reset user password to a new temporary password (Admin Only)"""
    try:
        # Check if user exists
        check_query = "SELECT username FROM users WHERE id = {}"
        check_query = check_query.format('%s' if db.db_type == 'postgresql' else '?')
        user_data = db.execute_query(check_query, (user_id,))

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found"
            )

        username = user_data[0]['username']

        # Generate new temporary password
        new_temporary_password = generate_temporary_password()
        password_hash = password_service.hash_password(new_temporary_password)

        # Update password and force password change
        update_query = """
            UPDATE users
            SET password_hash = {}, must_change_password = {}, updated_at = {}
            WHERE id = {}
        """
        if db.db_type == 'postgresql':
            update_query = update_query.format('%s', '%s', 'NOW()', '%s')
            params = (password_hash, True, user_id)
        else:
            update_query = update_query.format('?', '?', "datetime('now')", '?')
            params = (password_hash, True, user_id)

        db.execute_command(update_query, params)

        await log_admin_action(
            admin_user,
            "reset_user_password",
            user_id,
            {
                "reason": request.reason,
                "target_username": username,
                "temporary_password_generated": True
            }
        )

        logger.info(f"Password reset for user: {username}")

        return UserActionResponse(
            message=f"Password reset successfully. New temporary password: {new_temporary_password}",
            user_id=user_id,
            action_performed="password_reset"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
