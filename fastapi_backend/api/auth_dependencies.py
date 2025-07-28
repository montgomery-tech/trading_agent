#!/usr/bin/env python3
"""
API Key Authentication Dependencies
Task 2.1: New authentication dependencies for API key authentication system

Replaces JWT authentication dependencies with API key authentication
while maintaining the same interface patterns for seamless migration.
"""

import logging
from typing import List, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.api_key_models import AuthenticatedAPIKeyUser, UserRole, APIKeyScope
from api.api_key_service import get_api_key_service, APIKeyService
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)

# Use HTTPBearer for compatibility, but we'll extract the API key differently
security = HTTPBearer()


# =============================================================================
# Core API Key Authentication Dependencies
# =============================================================================

async def get_current_user_from_api_key(
    authorization: Optional[str] = Header(None),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> AuthenticatedAPIKeyUser:
    """
    Extract and validate current user from API key.

    This is the base authentication dependency for API key authentication.
    Supports both 'Authorization: Bearer' and 'Authorization: ApiKey' headers.
    """
    if not authorization:
        logger.warning("No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Support both "Bearer" and "ApiKey" prefixes for flexibility
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]  # Remove "Bearer " prefix
        elif authorization.startswith("ApiKey "):
            api_key = authorization[7:]  # Remove "ApiKey " prefix
        else:
            # Try without prefix for backward compatibility
            api_key = authorization

        # Authenticate using API key service
        authenticated_user = await api_key_service.authenticate_api_key(api_key, db)

        if not authenticated_user:
            logger.warning("API key authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "Bearer"}
            )

        logger.debug(f"Authenticated user via API key: {authenticated_user.username} ({authenticated_user.role.value})")
        return authenticated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_from_api_key_with_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> AuthenticatedAPIKeyUser:
    """
    Alternative authentication method using HTTPBearer security.

    This maintains compatibility with existing FastAPI security patterns
    while using API keys instead of JWT tokens.
    """
    api_key = credentials.credentials

    try:
        # Authenticate using API key service
        authenticated_user = await api_key_service.authenticate_api_key(api_key, db)

        if not authenticated_user:
            logger.warning("API key authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key"
            )

        logger.debug(f"Authenticated user via API key (Bearer): {authenticated_user.username}")
        return authenticated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# =============================================================================
# Role-Based Access Control Dependencies (API Key Compatible)
# =============================================================================

def require_roles_api_key(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control with API keys.

    Handles permission scope resolution for API keys while maintaining
    the same interface as JWT role checking.

    Args:
        allowed_roles: List of roles that can access the endpoint

    Returns:
        Dependency function that checks effective user permissions
    """
    async def role_checker(
        current_user: AuthenticatedAPIKeyUser = Depends(get_current_user_from_api_key),
        api_key_service: APIKeyService = Depends(get_api_key_service)
    ) -> AuthenticatedAPIKeyUser:

        # Get effective permissions based on user role and key scope
        effective_role = api_key_service.get_effective_permissions(
            current_user.role,
            current_user.api_key_scope
        )

        if effective_role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.username} "
                f"(role: {current_user.role.value}, key_scope: {current_user.api_key_scope.value}, "
                f"effective: {effective_role.value}, required: {[r.value for r in allowed_roles]})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}. "
                       f"Your effective permission: {effective_role.value}"
            )

        # Store effective role for use in route handlers
        current_user.effective_role = effective_role
        return current_user

    return role_checker


def require_admin_api_key():
    """Dependency to require admin role via API key."""
    return require_roles_api_key([UserRole.ADMIN])


def require_trader_or_admin_api_key():
    """Dependency to require trader or admin role via API key."""
    return require_roles_api_key([UserRole.TRADER, UserRole.ADMIN])


def require_any_authenticated_api_key():
    """Dependency to require any authenticated user via API key."""
    return require_roles_api_key([UserRole.VIEWER, UserRole.TRADER, UserRole.ADMIN])


def require_verified_user_api_key():
    """
    Dependency to require email-verified user account via API key.
    """
    async def verified_checker(
        current_user: AuthenticatedAPIKeyUser = Depends(get_current_user_from_api_key)
    ) -> AuthenticatedAPIKeyUser:
        if not current_user.is_verified:
            logger.warning(f"Unverified user attempted access: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required. Please verify your email address."
            )
        return current_user

    return verified_checker


def require_verified_trader_api_key():
    """Dependency to require verified trader or admin via API key."""
    async def verified_trader_checker(
        current_user: AuthenticatedAPIKeyUser = Depends(require_trader_or_admin_api_key())
    ) -> AuthenticatedAPIKeyUser:
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

async def get_current_user_optional_api_key(
    request: Request,
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> Optional[AuthenticatedAPIKeyUser]:
    """
    Get current user if authenticated via API key, otherwise return None.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        # Extract API key
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]
        elif authorization.startswith("ApiKey "):
            api_key = authorization[7:]
        else:
            api_key = authorization

        # Authenticate user
        authenticated_user = await api_key_service.authenticate_api_key(api_key, db)
        return authenticated_user

    except Exception as e:
        logger.debug(f"Optional API key authentication failed: {e}")
        return None


# =============================================================================
# Resource Owner Validation Dependencies (API Key Compatible)
# =============================================================================

def require_resource_owner_or_admin_api_key(resource_user_field: str = "username"):
    """
    Dependency factory to ensure user can only access their own resources via API key.

    Args:
        resource_user_field: Field name in path parameters that contains the resource owner identifier

    Returns:
        Dependency function that validates resource ownership
    """
    async def ownership_checker(
        request: Request,
        current_user: AuthenticatedAPIKeyUser = Depends(get_current_user_from_api_key),
        api_key_service: APIKeyService = Depends(get_api_key_service)
    ) -> AuthenticatedAPIKeyUser:

        # Get effective permissions
        effective_role = api_key_service.get_effective_permissions(
            current_user.role,
            current_user.api_key_scope
        )

        # Admins can access any resource
        if effective_role == UserRole.ADMIN:
            return current_user

        # Get resource identifier from path parameters
        resource_identifier = request.path_params.get(resource_user_field)

        if not resource_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {resource_user_field} in request"
            )

        # Check if user owns the resource
        if resource_user_field == "username":
            user_identifier = current_user.username
        elif resource_user_field == "user_id":
            user_identifier = str(current_user.id)
        else:
            # For other fields, assume it's a user identifier
            user_identifier = current_user.username

        if user_identifier != resource_identifier:
            logger.warning(
                f"User {current_user.username} attempted to access resource belonging to {resource_identifier}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own resources."
            )

        return current_user

    return ownership_checker


# =============================================================================
# API Key Scope Validation Dependencies
# =============================================================================

def require_api_key_scope(required_scopes: List[APIKeyScope]):
    """
    Dependency to require specific API key scopes.

    Args:
        required_scopes: List of API key scopes that can access the endpoint

    Returns:
        Dependency function that checks API key scope
    """
    async def scope_checker(
        current_user: AuthenticatedAPIKeyUser = Depends(get_current_user_from_api_key)
    ) -> AuthenticatedAPIKeyUser:

        if current_user.api_key_scope not in required_scopes:
            logger.warning(
                f"Access denied for API key {current_user.api_key_id} "
                f"(scope: {current_user.api_key_scope.value}, required: {[s.value for s in required_scopes]})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required API key scopes: {[s.value for s in required_scopes]}"
            )

        return current_user

    return scope_checker


def require_full_access_api_key():
    """Dependency to require full access API key."""
    return require_api_key_scope([APIKeyScope.FULL_ACCESS])


def require_read_write_api_key():
    """Dependency to require read-write API key (inherit or full access)."""
    return require_api_key_scope([APIKeyScope.INHERIT, APIKeyScope.FULL_ACCESS])


# =============================================================================
# Convenience Aliases (Drop-in Replacements for JWT Dependencies)
# =============================================================================

# These aliases provide drop-in replacement for existing JWT dependencies
get_current_user = get_current_user_from_api_key
require_authentication = get_current_user_from_api_key
require_admin_access = require_admin_api_key()
require_trader_access = require_trader_or_admin_api_key()
require_verified_access = require_verified_user_api_key()()
require_verified_trader_access = require_verified_trader_api_key()()

# Resource ownership dependencies
require_own_resource = require_resource_owner_or_admin_api_key()
require_own_user_resource = require_resource_owner_or_admin_api_key("username")
require_own_id_resource = require_resource_owner_or_admin_api_key("user_id")

# Optional authentication
get_current_user_optional = get_current_user_optional_api_key

# Role checking functions (keeping same interface)
require_roles = require_roles_api_key
require_admin = require_admin_api_key()
require_trader_or_admin = require_trader_or_admin_api_key()
AuthenticatedUser = AuthenticatedAPIKeyUser

# =============================================================================
# Migration Helper: Dual Authentication Support (Temporary)
# =============================================================================

async def get_current_user_dual_auth(
    request: Request,
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> AuthenticatedAPIKeyUser:
    """
    TEMPORARY: Support both JWT and API key authentication during migration.

    This function attempts API key authentication first, then falls back to JWT.
    Remove this after migration is complete.
    """
    # Try API key authentication first
    try:
        user = await get_current_user_optional_api_key(request, db, api_key_service)
        if user:
            return user
    except Exception as e:
        logger.debug(f"API key authentication failed, trying JWT: {e}")

    # Fallback to JWT authentication
    try:
        from api.auth_dependencies import get_current_user_from_token
        # This would require adapting the JWT dependency to work with our return type
        # For now, this is just a placeholder for the migration period
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please use API key authentication."
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )


# =============================================================================
# Usage Logging Middleware Integration
# =============================================================================

async def log_api_key_usage(
    request: Request,
    current_user: AuthenticatedAPIKeyUser = Depends(get_current_user_from_api_key),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> AuthenticatedAPIKeyUser:
    """
    Dependency that logs API key usage for audit trail.

    This can be added to endpoints that need detailed usage tracking.
    """
    try:
        # Extract request information
        endpoint = str(request.url.path)
        method = request.method
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        # Log usage (this will be done automatically by the service, but can be enhanced here)
        await api_key_service._log_api_key_usage(
            api_key_db_id=current_user.api_key_id,
            db=db,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent
        )

    except Exception as e:
        # Don't fail the request if logging fails
        logger.error(f"Failed to log API key usage: {e}")

    return current_user

def require_resource_owner_or_admin(resource_user_field: str = "username"):
    """
    Dependency factory to ensure user can only access their own resources via API key.
    """
    async def ownership_checker(
        request: Request,
        current_user: AuthenticatedAPIKeyUser = Depends(get_current_user_from_api_key),
        api_key_service: APIKeyService = Depends(get_api_key_service)
    ) -> AuthenticatedAPIKeyUser:

        # Get effective permissions
        effective_role = api_key_service.get_effective_permissions(
            current_user.role,
            current_user.api_key_scope
        )

        # Admins can access any resource
        if effective_role == UserRole.ADMIN:
            return current_user

        # Get resource identifier from path parameters
        resource_identifier = request.path_params.get(resource_user_field)

        if not resource_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {resource_user_field} in request"
            )

        # Check if user owns the resource
        if resource_user_field == "username":
            user_identifier = current_user.username
        elif resource_user_field == "user_id":
            user_identifier = str(current_user.id)
        else:
            user_identifier = current_user.username

        if user_identifier != resource_identifier:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own resources."
            )

        return current_user

    return ownership_checker

# =============================================================================
# Example Usage Documentation
# =============================================================================

"""
Example usage of API key authentication dependencies:

# Basic API key authentication
@router.get("/protected")
async def protected_route(user: AuthenticatedAPIKeyUser = Depends(get_current_user)):
    return {"message": f"Hello {user.username}", "api_key": user.api_key_name}

# Admin only via API key
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: AuthenticatedAPIKeyUser = Depends(require_admin_access)
):
    return {"message": "User deleted", "effective_role": admin.effective_role}

# Trader or admin via API key
@router.post("/trades")
async def create_trade(
    trade_data: dict,
    trader: AuthenticatedAPIKeyUser = Depends(require_trader_access)
):
    return {"message": "Trade created", "key_scope": trader.api_key_scope}

# Specific API key scope required
@router.get("/sensitive-data")
async def get_sensitive_data(
    user: AuthenticatedAPIKeyUser = Depends(require_full_access_api_key())
):
    return {"message": "Sensitive data", "scope": user.api_key_scope}

# Resource ownership via API key
@router.get("/users/{username}/profile")
async def get_user_profile(
    username: str,
    user: AuthenticatedAPIKeyUser = Depends(require_own_user_resource)
):
    return {"message": f"Profile for {username}", "api_key": user.api_key_name}

# Optional authentication via API key
@router.get("/public-or-private")
async def mixed_route(
    user: Optional[AuthenticatedAPIKeyUser] = Depends(get_current_user_optional)
):
    if user:
        return {"message": f"Hello {user.username}", "api_key": user.api_key_name}
    else:
        return {"message": "Hello anonymous user"}

# With usage logging
@router.post("/tracked-endpoint")
async def tracked_route(
    data: dict,
    user: AuthenticatedAPIKeyUser = Depends(log_api_key_usage)
):
    return {"message": "Request logged", "user": user.username}
"""
