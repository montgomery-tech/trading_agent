#!/usr/bin/env python3
"""
Admin Authentication and Role-Based Access Control Middleware
Fixed version compatible with existing auth system
"""

import logging
from typing import Optional, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.dependencies import get_database
from api.database import DatabaseManager
from api.jwt_service import jwt_service
from api.auth_models import UserRole, TokenType, AuthenticatedUser

logger = logging.getLogger(__name__)
security = HTTPBearer()


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_database)
) -> AuthenticatedUser:
    """
    Get current authenticated user from JWT token.
    Enhanced version with role information.
    """
    token = credentials.credentials

    # Validate token
    try:
        token_data = jwt_service.validate_token(token, expected_type=TokenType.ACCESS)
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # Get user from database with role information
    user = await get_user_by_id_with_role(token_data.user_id, db)
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

    # Map role string to UserRole enum, default to USER if not found
    role_mapping = {
        'admin': UserRole.ADMIN,
        'trader': UserRole.TRADER,
        'viewer': UserRole.VIEWER  # Use USER instead of VIEWER
    }
    user_role = role_mapping.get(user.get('role', 'viewer'), UserRole.VIEWER)

    return AuthenticatedUser(
        id=user['id'],
        username=user['username'],
        email=user['email'],
        first_name=user['first_name'],
        last_name=user['last_name'],
        role=user_role,
        is_active=user['is_active'],
        is_verified=user['is_verified'],
        created_at=user['created_at'],
        last_login=user['last_login']
    )


async def get_user_by_id_with_role(user_id: str, db: DatabaseManager) -> Optional[dict]:
    """Get user by ID with role information."""
    try:
        # Basic user query with role column
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, password_hash, first_name, last_name,
                       is_active, is_verified, must_change_password, created_at,
                       updated_at, last_login, COALESCE(role, 'trader') as role
                FROM users
                WHERE id = %s
            """
            params = (user_id,)
        else:
            # SQLite
            query = """
                SELECT id, username, email, password_hash, first_name, last_name,
                       is_active, is_verified, must_change_password, created_at,
                       updated_at, last_login, COALESCE(role, 'trader') as role
                FROM users
                WHERE id = ?
            """
            params = (user_id,)

        results = db.execute_query(query, params)
        return results[0] if results else None

    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        # Fallback to basic user query without role
        query = """
            SELECT id, username, email, password_hash, first_name, last_name,
                   is_active, is_verified, must_change_password, created_at,
                   updated_at, last_login
            FROM users
            WHERE id = {}
        """.format('%s' if db.db_type == 'postgresql' else '?')

        results = db.execute_query(query, (user_id,))
        if results:
            user = results[0]
            user['role'] = 'trader'  # Default role
            return user
        return None


# =============================================================================
# Role-Based Access Control Functions
# =============================================================================

async def require_admin_user(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Dependency that requires admin role"""
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Admin access denied for user: {current_user.username} (role: {current_user.role})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    logger.info(f"Admin access granted to user: {current_user.username}")
    return current_user


async def require_trading_permission(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Dependency that requires trading permission (admin or trader)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
        logger.warning(f"Trading access denied for user: {current_user.username} (role: {current_user.role})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trading access requires admin or trader role"
        )
    return current_user


async def require_authenticated_user(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Dependency for any authenticated user"""
    return current_user


# =============================================================================
# Permission Checking Functions
# =============================================================================

def check_user_permission(current_user: AuthenticatedUser, target_user_id: str) -> bool:
    """
    Check if current user can access target user's data.
    Admins can access anyone's data, users can only access their own.
    """
    if current_user.role == UserRole.ADMIN:
        return True
    return current_user.id == target_user_id


def ensure_user_permission(current_user: AuthenticatedUser, target_user_id: str) -> None:
    """
    Ensure current user has permission to access target user's data.
    Raises HTTPException if permission denied.
    """
    if not check_user_permission(current_user, target_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own data."
        )


# =============================================================================
# Admin Action Logging
# =============================================================================

async def log_admin_action(
    action: str,
    target_resource: str,
    admin_user: AuthenticatedUser,
    details: Optional[dict] = None,
    db: DatabaseManager = None
):
    """Log admin actions for audit trail"""
    try:
        logger.info(f"ADMIN ACTION: {admin_user.username} performed '{action}' on {target_resource}. Details: {details}")
        # Future: Insert into admin_actions table for audit trail

    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


# =============================================================================
# Utility Functions
# =============================================================================

def get_user_context_for_request(username: str, current_user: AuthenticatedUser) -> dict:
    """
    Get user context for API requests with proper access control.
    Returns user_id if current user can access target user's data.
    """
    if current_user.username == username or current_user.role == UserRole.ADMIN:
        return {"allowed": True, "target_username": username}

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. You can only access your own data."
    )
