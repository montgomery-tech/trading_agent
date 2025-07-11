#!/usr/bin/env python3
"""
Authentication dependencies for the Balance Tracking API
Role-based access control and authentication middleware
"""

import logging
from typing import List, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth_models import AuthenticatedUser, UserRole, TokenType
from api.dependencies import get_database
from api.database import DatabaseManager
from api.jwt_service import jwt_service

logger = logging.getLogger(__name__)
security = HTTPBearer()


# =============================================================================
# Core Authentication Dependencies
# =============================================================================

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_database)
) -> AuthenticatedUser:
    """
    Extract and validate current user from JWT token.

    This is the base authentication dependency used by all protected routes.
    """
    token = credentials.credentials

    try:
        # Validate access token
        token_data = jwt_service.validate_token(token, expected_type=TokenType.ACCESS)

        # Get user from database to ensure they still exist and are active
        query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, created_at, updated_at, last_login
            FROM users
            WHERE id = ?
        """
        results = db.execute_query(query, (token_data.user_id,))

        if not results:
            logger.warning(f"Token valid but user not found: {token_data.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        user = results[0]

        # Check if user account is active
        if not user['is_active']:
            logger.warning(f"Inactive user attempted access: {user['username']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )

        # Create authenticated user object
        authenticated_user = AuthenticatedUser(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=token_data.role,
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            created_at=user['created_at'],
            last_login=user['last_login']
        )

        logger.debug(f"Authenticated user: {user['username']} ({token_data.role.value})")
        return authenticated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# =============================================================================
# Role-Based Access Control Dependencies
# =============================================================================

def require_roles(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of roles that can access the endpoint

    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user_from_token)
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.username} "
                f"(role: {current_user.role.value}, required: {[r.value for r in allowed_roles]})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


def require_admin():
    """Dependency to require admin role."""
    return require_roles([UserRole.ADMIN])


def require_trader_or_admin():
    """Dependency to require trader or admin role."""
    return require_roles([UserRole.TRADER, UserRole.ADMIN])


def require_verified_user():
    """
    Dependency to require email-verified user account.
    """
    async def verified_checker(
        current_user: AuthenticatedUser = Depends(get_current_user_from_token)
    ) -> AuthenticatedUser:
        if not current_user.is_verified:
            logger.warning(f"Unverified user attempted access: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required. Please verify your email address."
            )
        return current_user

    return verified_checker


def require_verified_trader():
    """Dependency to require verified trader or admin."""
    async def verified_trader_checker(
        current_user: AuthenticatedUser = Depends(require_trader_or_admin())
    ) -> AuthenticatedUser:
        if not current_user.is_verified:
            logger.warning(f"Unverified trader attempted access: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required for trading operations"
            )
        return current_user

    return verified_trader_checker


# =============================================================================
# Optional Authentication Dependencies
# =============================================================================

async def get_current_user_optional(
    request: Request,
    db: DatabaseManager = Depends(get_database)
) -> Optional[AuthenticatedUser]:
    """
    Get current user if authenticated, otherwise return None.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None

        token = authorization.split(" ")[1]

        # Validate token
        token_data = jwt_service.validate_token(token, expected_type=TokenType.ACCESS)

        # Get user from database
        query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, created_at, updated_at, last_login
            FROM users
            WHERE id = ?
        """
        results = db.execute_query(query, (token_data.user_id,))

        if not results or not results[0]['is_active']:
            return None

        user = results[0]
        return AuthenticatedUser(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=token_data.role,
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            created_at=user['created_at'],
            last_login=user['last_login']
        )

    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


# =============================================================================
# Resource Owner Validation Dependencies
# =============================================================================

def require_resource_owner_or_admin(resource_user_field: str = "username"):
    """
    Dependency factory to ensure user can only access their own resources.

    Args:
        resource_user_field: Name of the path parameter containing the resource owner identifier

    Returns:
        Dependency function that validates resource ownership
    """
    async def ownership_checker(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user_from_token)
    ) -> AuthenticatedUser:
        # Admin users can access any resource
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Get the resource owner from path parameters
        path_params = request.path_params
        resource_owner = path_params.get(resource_user_field)

        if not resource_owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {resource_user_field} parameter"
            )

        # Check if current user owns the resource
        if current_user.username != resource_owner:
            logger.warning(
                f"User {current_user.username} attempted to access resource owned by {resource_owner}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own resources."
            )

        return current_user

    return ownership_checker


# =============================================================================
# Rate Limiting Dependencies (Future Enhancement)
# =============================================================================

async def check_rate_limit(
    request: Request,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional)
) -> None:
    """
    Check rate limits for API endpoints.

    This is a placeholder for future rate limiting implementation.
    Different limits can be applied based on user role and endpoint type.
    """
    # TODO: Implement rate limiting logic
    # - Anonymous users: stricter limits
    # - Authenticated users: moderate limits
    # - Premium/Admin users: higher limits
    # - Different limits for different endpoint types
    pass


# =============================================================================
# Security Headers Middleware Dependencies
# =============================================================================

async def add_security_headers(request: Request) -> None:
    """
    Add security headers to responses.

    This would typically be implemented as middleware, but can be used
    as a dependency for specific routes that need extra security.
    """
    # TODO: Implement security headers
    # - X-Content-Type-Options: nosniff
    # - X-Frame-Options: DENY
    # - X-XSS-Protection: 1; mode=block
    # - Strict-Transport-Security (for HTTPS)
    # - Content-Security-Policy
    pass


# =============================================================================
# Convenience Aliases
# =============================================================================

# Common authentication dependencies with descriptive names
get_current_user = get_current_user_from_token
require_authentication = get_current_user_from_token
require_admin_access = require_admin()
require_trader_access = require_trader_or_admin()
require_verified_access = require_verified_user()
require_verified_trader_access = require_verified_trader()

# Resource ownership dependencies
require_own_resource = require_resource_owner_or_admin()
require_own_user_resource = require_resource_owner_or_admin("username")
require_own_id_resource = require_resource_owner_or_admin("user_id")


# =============================================================================
# Authentication Decorators (Alternative API)
# =============================================================================

def authenticated(roles: Optional[List[UserRole]] = None, verified: bool = False):
    """
    Decorator for route functions that require authentication.

    Args:
        roles: Required roles (optional)
        verified: Require email verification (default: False)

    Usage:
        @authenticated(roles=[UserRole.ADMIN], verified=True)
        async def admin_only_route(user: AuthenticatedUser = Depends(get_current_user)):
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is just a documentation decorator
            # Actual authentication is handled by the dependencies
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Example Usage Documentation
# =============================================================================

"""
Example usage of authentication dependencies:

# Basic authentication
@router.get("/protected")
async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
    return {"message": f"Hello {user.username}"}

# Admin only
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: AuthenticatedUser = Depends(require_admin_access)
):
    return {"message": "User deleted"}

# Trader or admin
@router.post("/trades")
async def create_trade(
    trade_data: dict,
    trader: AuthenticatedUser = Depends(require_trader_access)
):
    return {"message": "Trade created"}

# Verified users only
@router.post("/verified-only")
async def verified_route(
    user: AuthenticatedUser = Depends(require_verified_access)
):
    return {"message": "Verified user access"}

# Resource ownership
@router.get("/users/{username}/profile")
async def get_user_profile(
    username: str,
    user: AuthenticatedUser = Depends(require_own_user_resource)
):
    return {"message": f"Profile for {username}"}

# Optional authentication
@router.get("/public-or-private")
async def mixed_route(
    user: Optional[AuthenticatedUser] = Depends(get_current_user_optional)
):
    if user:
        return {"message": f"Hello {user.username}"}
    else:
        return {"message": "Hello anonymous user"}
"""
