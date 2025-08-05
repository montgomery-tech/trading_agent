#!/usr/bin/env python3
"""
Enhanced API Key Authentication Dependencies with Entity Support
Task 2.1: Updated authentication dependencies for entity-based access control

Extends the existing API key authentication system to support entity-scoped access control
while maintaining backward compatibility with existing endpoints.
"""

import logging
from typing import List, Optional, Union
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.api_key_models import AuthenticatedAPIKeyUser, UserRole, APIKeyScope
from api.api_key_service import get_api_key_service, APIKeyService
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)

# Use HTTPBearer for compatibility
security = HTTPBearer()


# =============================================================================
# Enhanced Models for Entity Context
# =============================================================================

class EntityInfo:
    """Entity information for authenticated users"""
    def __init__(self, entity_id: str, entity_code: str, entity_name: str, entity_role: str, is_active: bool):
        self.entity_id = entity_id
        self.entity_code = entity_code
        self.entity_name = entity_name
        self.entity_role = entity_role
        self.is_active = is_active


class EntityAuthenticatedUser(AuthenticatedAPIKeyUser):
    """Enhanced authenticated user with entity context"""
    def __init__(self, **data):
        super().__init__(**data)
        self.entity_info: Optional[EntityInfo] = None
        self.accessible_entities: List[str] = []

    def has_entity_access(self, entity_id: str) -> bool:
        """Check if user has access to a specific entity"""
        # Admins have access to all entities
        if self.role == UserRole.ADMIN:
            return True

        # Entity-scoped users only have access to their assigned entities
        return entity_id in self.accessible_entities


# =============================================================================
# Entity-Enhanced API Key Service Functions
# =============================================================================

async def _get_user_entity_context(
    user_id: Union[str, UUID],
    db: DatabaseManager
) -> tuple[Optional[EntityInfo], List[str]]:
    """
    Get entity context for a user.

    Args:
        user_id: User ID
        db: Database manager

    Returns:
        Tuple of (primary entity info or None, list of accessible entity IDs)
    """
    try:
        # Get user's entity memberships
        if db.db_type == 'postgresql':
            query = """
                SELECT
                    e.id as entity_id,
                    e.code as entity_code,
                    e.name as entity_name,
                    em.entity_role,
                    em.is_active,
                    em.created_at as membership_created_at
                FROM entity_memberships em
                JOIN entities e ON em.entity_id = e.id
                WHERE em.user_id = %s AND em.is_active = true AND e.is_active = true
                ORDER BY em.created_at ASC
            """
            params = (str(user_id),)
        else:
            query = """
                SELECT
                    e.id as entity_id,
                    e.code as entity_code,
                    e.name as entity_name,
                    em.entity_role,
                    em.is_active,
                    em.created_at as membership_created_at
                FROM entity_memberships em
                JOIN entities e ON em.entity_id = e.id
                WHERE em.user_id = ? AND em.is_active = 1 AND e.is_active = 1
                ORDER BY em.created_at ASC
            """
            params = (str(user_id),)

        memberships = db.execute_query(query, params)

        if not memberships:
            # User has no entity memberships (likely admin or legacy user)
            return None, []

        # Primary entity is the first (oldest) membership
        primary = memberships[0]
        primary_entity_info = EntityInfo(
            entity_id=primary['entity_id'],
            entity_code=primary['entity_code'],
            entity_name=primary['entity_name'],
            entity_role=primary['entity_role'],
            is_active=primary['is_active']
        )

        # Accessible entities are all entities user has membership in
        accessible_entities = [membership['entity_id'] for membership in memberships]

        return primary_entity_info, accessible_entities

    except Exception as e:
        logger.error(f"Failed to get entity context for user {user_id}: {e}")
        return None, []


async def authenticate_with_entity_context(
    api_key: str,
    db: DatabaseManager,
    api_key_service: APIKeyService,
    required_entity_id: Optional[str] = None
) -> EntityAuthenticatedUser:
    """
    Authenticate API key and include entity context.

    Args:
        api_key: API key to authenticate
        db: Database manager
        api_key_service: API key service instance
        required_entity_id: Optional specific entity ID that must be accessible

    Returns:
        EntityAuthenticatedUser with entity context

    Raises:
        HTTPException: If authentication fails or entity access denied
    """
    # First perform standard API key authentication
    base_user = await api_key_service.authenticate_api_key(api_key, db)
    if not base_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Create enhanced user object (copy all base attributes)
    entity_user = EntityAuthenticatedUser(**base_user.dict())

    # Get entity information for the user
    entity_info, accessible_entities = await _get_user_entity_context(
        base_user.id, db
    )

    # Set entity context
    entity_user.entity_info = entity_info
    entity_user.accessible_entities = accessible_entities

    # If a specific entity is required, validate access
    if required_entity_id:
        if not entity_user.has_entity_access(required_entity_id):
            logger.warning(
                f"User {entity_user.username} attempted to access entity {required_entity_id} "
                f"but only has access to: {accessible_entities}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to entity {required_entity_id}"
            )

    return entity_user


# =============================================================================
# Core Authentication Dependencies (Enhanced)
# =============================================================================

async def get_current_user_from_api_key(
    authorization: Optional[str] = Header(None),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> AuthenticatedAPIKeyUser:
    """
    Extract and validate current user from API key (backward compatible).

    This maintains the original interface for backward compatibility.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    # Extract API key from authorization header
    if authorization.startswith("Bearer "):
        api_key = authorization[7:]
    elif authorization.startswith("ApiKey "):
        api_key = authorization[7:]
    else:
        api_key = authorization

    try:
        # Authenticate using API key service
        authenticated_user = await api_key_service.authenticate_api_key(api_key, db)

        if not authenticated_user:
            logger.warning("API key authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key"
            )

        logger.debug(f"Authenticated user via API key: {authenticated_user.username}")
        return authenticated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_user_with_entity_context(
    authorization: Optional[str] = Header(None),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> EntityAuthenticatedUser:
    """
    Get current user with entity context from API key.

    This is the enhanced authentication dependency that includes entity information.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    # Extract API key from authorization header
    if authorization.startswith("Bearer "):
        api_key = authorization[7:]
    elif authorization.startswith("ApiKey "):
        api_key = authorization[7:]
    else:
        api_key = authorization

    try:
        return await authenticate_with_entity_context(api_key, db, api_key_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity-aware authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# =============================================================================
# Entity-Specific Access Control Dependencies
# =============================================================================

def require_entity_access(entity_id_param: str = "entity_id"):
    """
    Dependency factory to require access to a specific entity.

    Args:
        entity_id_param: Name of the path parameter containing the entity ID

    Returns:
        Dependency function that validates entity access
    """
    async def entity_access_checker(
        request: Request,
        current_user: EntityAuthenticatedUser = Depends(get_current_user_with_entity_context)
    ) -> EntityAuthenticatedUser:

        # Extract entity ID from path parameters
        entity_id = request.path_params.get(entity_id_param)
        if not entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {entity_id_param} in request path"
            )

        # Check entity access
        if not current_user.has_entity_access(entity_id):
            logger.warning(
                f"User {current_user.username} attempted to access entity {entity_id} "
                f"but only has access to: {current_user.accessible_entities}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to entity {entity_id}"
            )

        return current_user

    return entity_access_checker


def require_entity_role(required_roles: List[str], entity_id_param: str = "entity_id"):
    """
    Dependency factory to require specific roles within an entity.

    Args:
        required_roles: List of entity roles required (e.g., ['trader', 'viewer'])
        entity_id_param: Name of the path parameter containing the entity ID

    Returns:
        Dependency function that validates entity role access
    """
    async def entity_role_checker(
        request: Request,
        current_user: EntityAuthenticatedUser = Depends(get_current_user_with_entity_context),
        db: DatabaseManager = Depends(get_database)
    ) -> EntityAuthenticatedUser:

        # Admins bypass entity role checks
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Extract entity ID from path parameters
        entity_id = request.path_params.get(entity_id_param)
        if not entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {entity_id_param} in request path"
            )

        # Check entity access first
        if not current_user.has_entity_access(entity_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to entity {entity_id}"
            )

        # Get user's role in this specific entity
        user_entity_role = await _get_user_role_in_entity(current_user.id, entity_id, db)

        if user_entity_role not in required_roles:
            logger.warning(
                f"User {current_user.username} attempted to access entity {entity_id} "
                f"with role {user_entity_role} but requires one of: {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required entity roles: {required_roles}. "
                       f"Your role in this entity: {user_entity_role}"
            )

        return current_user

    return entity_role_checker


async def _get_user_role_in_entity(
    user_id: Union[str, UUID],
    entity_id: str,
    db: DatabaseManager
) -> str:
    """Get user's role within a specific entity"""
    try:
        if db.db_type == 'postgresql':
            query = """
                SELECT entity_role
                FROM entity_memberships
                WHERE user_id = %s AND entity_id = %s AND is_active = true
            """
            params = (str(user_id), entity_id)
        else:
            query = """
                SELECT entity_role
                FROM entity_memberships
                WHERE user_id = ? AND entity_id = ? AND is_active = 1
            """
            params = (str(user_id), entity_id)

        result = db.execute_query(query, params)
        return result[0]['entity_role'] if result else 'viewer'

    except Exception as e:
        logger.error(f"Failed to get user role in entity: {e}")
        return 'viewer'


# =============================================================================
# Convenience Entity Dependencies
# =============================================================================

def require_entity_trader_access(entity_id_param: str = "entity_id"):
    """Dependency to require trader access within an entity."""
    return require_entity_role(['trader'], entity_id_param)


def require_entity_any_access(entity_id_param: str = "entity_id"):
    """Dependency to require any access (trader or viewer) within an entity."""
    return require_entity_role(['trader', 'viewer'], entity_id_param)


# =============================================================================
# Role-Based Access Control Dependencies (Backward Compatible)
# =============================================================================

def require_roles_api_key(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control with API keys.

    Maintains backward compatibility while supporting entity context.
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


# =============================================================================
# Convenience Aliases (Drop-in Replacements)
# =============================================================================

# Standard authentication (backward compatible)
get_current_user = get_current_user_from_api_key
require_authentication = get_current_user_from_api_key
require_admin_access = require_admin_api_key()
require_trader_access = require_trader_or_admin_api_key()

# Entity-aware authentication (enhanced)
get_current_user_entity_aware = get_current_user_with_entity_context

# Type aliases for backward compatibility
AuthenticatedUser = AuthenticatedAPIKeyUser


# =============================================================================
# Entity Query Helper Functions
# =============================================================================

async def get_user_accessible_entity_filter(
    current_user: EntityAuthenticatedUser,
    db: DatabaseManager,
    table_alias: str = ""
) -> tuple[str, List[str]]:
    """
    Get SQL filter condition to limit queries to user's accessible entities.

    Args:
        current_user: Authenticated user with entity context
        db: Database manager
        table_alias: Optional table alias for the entity_id column

    Returns:
        Tuple of (WHERE condition, parameters)
    """
    # Admins can access all entities
    if current_user.role == UserRole.ADMIN:
        return "", []

    # Entity-scoped users can only access their assigned entities
    if not current_user.accessible_entities:
        # No accessible entities - should not happen but safety check
        return "1 = 0", []  # Always false condition

    # Build parameterized query
    entity_column = f"{table_alias}.entity_id" if table_alias else "entity_id"

    if db.db_type == 'postgresql':
        # PostgreSQL: entity_id = ANY(%s)
        condition = f"{entity_column} = ANY(%s)"
        params = [current_user.accessible_entities]
    else:
        # SQLite: entity_id IN (?, ?, ...)
        placeholders = ', '.join(['?' for _ in current_user.accessible_entities])
        condition = f"{entity_column} IN ({placeholders})"
        params = current_user.accessible_entities

    return condition, params
