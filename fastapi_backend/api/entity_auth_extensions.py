#!/usr/bin/env python3
"""
Entity-Based Authentication Extensions
Task 2.1: Extend API key authentication to support entity-scoped access control

This extends the existing API key system to include entity context and permissions,
enabling multi-tenant data isolation while maintaining backward compatibility.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request, Header
from pydantic import BaseModel, Field

from api.api_key_models import AuthenticatedAPIKeyUser, UserRole, APIKeyScope
from api.api_key_service import get_api_key_service, APIKeyService
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)


# =============================================================================
# Enhanced Entity-Aware Models
# =============================================================================

class EntityInfo(BaseModel):
    """Entity information for authenticated users"""
    entity_id: str = Field(..., description="Entity ID")
    entity_code: str = Field(..., description="Entity code")
    entity_name: str = Field(..., description="Entity name")
    entity_role: str = Field(..., description="User's role within this entity")
    is_active: bool = Field(..., description="Entity membership is active")


class EntityAuthenticatedUser(AuthenticatedAPIKeyUser):
    """Enhanced authenticated user with entity context"""
    # Entity information (None for admin users who can access all entities)
    entity_info: Optional[EntityInfo] = Field(None, description="Entity context if user is entity-scoped")
    accessible_entities: List[str] = Field(default_factory=list, description="List of entity IDs user can access")

    def has_entity_access(self, entity_id: str) -> bool:
        """Check if user has access to a specific entity"""
        # Admins have access to all entities
        if self.role == UserRole.ADMIN:
            return True

        # Entity-scoped users only have access to their assigned entities
        return entity_id in self.accessible_entities


# =============================================================================
# Entity-Enhanced API Key Service
# =============================================================================

class EntityAPIKeyService(APIKeyService):
    """Extended API key service with entity-aware authentication"""

    async def authenticate_with_entity_context(
        self,
        api_key: str,
        db: DatabaseManager,
        required_entity_id: Optional[str] = None
    ) -> EntityAuthenticatedUser:
        """
        Authenticate API key and include entity context.

        Args:
            api_key: API key to authenticate
            db: Database manager
            required_entity_id: Optional specific entity ID that must be accessible

        Returns:
            EntityAuthenticatedUser with entity context

        Raises:
            HTTPException: If authentication fails or entity access denied
        """
        # First perform standard API key authentication
        base_user = await self.authenticate_api_key(api_key, db)
        if not base_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        # Get entity information for the user
        entity_info, accessible_entities = await self._get_user_entity_context(
            base_user.id, db
        )

        # Create enhanced user object
        entity_user = EntityAuthenticatedUser(
            **base_user.dict(),
            entity_info=entity_info,
            accessible_entities=accessible_entities
        )

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

    async def _get_user_entity_context(
        self,
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


# =============================================================================
# Entity-Aware Authentication Dependencies
# =============================================================================

async def get_current_user_with_entity_context(
    authorization: Optional[str] = Header(None),
    db: DatabaseManager = Depends(get_database),
    entity_service: EntityAPIKeyService = Depends(lambda: EntityAPIKeyService())
) -> EntityAuthenticatedUser:
    """
    Get current user with entity context from API key.

    This is the enhanced base authentication dependency that includes entity information.
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
        return await entity_service.authenticate_with_entity_context(api_key, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity-aware authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


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
        current_user: EntityAuthenticatedUser = Depends(get_current_user_with_entity_context)
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

        # Check if user has required role within the entity
        if current_user.entity_info and current_user.entity_info.entity_id == entity_id:
            user_entity_role = current_user.entity_info.entity_role
        else:
            # If the requested entity is not the user's primary entity,
            # we need to look up their role in that specific entity
            # For now, assume they have 'viewer' role if they have access
            user_entity_role = 'viewer'

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


def require_entity_trader_access(entity_id_param: str = "entity_id"):
    """Dependency to require trader access within an entity."""
    return require_entity_role(['trader'], entity_id_param)


def require_entity_any_access(entity_id_param: str = "entity_id"):
    """Dependency to require any access (trader or viewer) within an entity."""
    return require_entity_role(['trader', 'viewer'], entity_id_param)


# =============================================================================
# Entity Query Helpers
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


# =============================================================================
# Convenience Dependencies (Drop-in Replacements)
# =============================================================================

# Enhanced entity-aware authentication
get_current_user_entity_aware = get_current_user_with_entity_context

# Backward compatibility aliases
AuthenticatedUser = EntityAuthenticatedUser


# =============================================================================
# Migration Helper Functions
# =============================================================================

async def ensure_user_has_entity_access(
    user_id: Union[str, UUID],
    db: DatabaseManager
) -> bool:
    """
    Ensure a user has at least one entity membership.

    This is a helper for migration - assigns users to default entity if needed.
    """
    try:
        # Check if user has any entity memberships
        if db.db_type == 'postgresql':
            query = """
                SELECT COUNT(*) as count
                FROM entity_memberships em
                WHERE em.user_id = %s AND em.is_active = true
            """
            params = (str(user_id),)
        else:
            query = """
                SELECT COUNT(*) as count
                FROM entity_memberships em
                WHERE em.user_id = ? AND em.is_active = 1
            """
            params = (str(user_id),)

        result = db.execute_query(query, params)
        has_membership = result[0]['count'] > 0 if result else False

        if not has_membership:
            # Assign to default entity
            if db.db_type == 'postgresql':
                default_entity_query = "SELECT id FROM entities WHERE code = 'SYSTEM_DEFAULT'"
                insert_query = """
                    INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                    VALUES (%s, %s, 'trader', true)
                """
            else:
                default_entity_query = "SELECT id FROM entities WHERE code = 'SYSTEM_DEFAULT'"
                insert_query = """
                    INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                    VALUES (?, ?, 'trader', 1)
                """

            default_entity_result = db.execute_query(default_entity_query)
            if default_entity_result:
                default_entity_id = default_entity_result[0]['id']
                db.execute_query(insert_query, (default_entity_id, str(user_id)))
                logger.info(f"Assigned user {user_id} to default entity")
                return True

        return has_membership

    except Exception as e:
        logger.error(f"Failed to ensure user {user_id} has entity access: {e}")
        return False


# =============================================================================
# Example Usage Documentation
# =============================================================================

"""
Example usage of entity-aware authentication dependencies:

# Entity-aware authentication
@router.get("/protected")
async def protected_route(
    user: EntityAuthenticatedUser = Depends(get_current_user_entity_aware)
):
    return {
        "user": user.username,
        "entity": user.entity_info.entity_name if user.entity_info else "Admin (All Entities)",
        "accessible_entities": user.accessible_entities
    }

# Require access to specific entity
@router.get("/entities/{entity_id}/data")
async def get_entity_data(
    entity_id: str,
    user: EntityAuthenticatedUser = Depends(require_entity_access())
):
    return {"entity_id": entity_id, "user": user.username}

# Require trader role within entity
@router.post("/entities/{entity_id}/trades")
async def create_trade(
    entity_id: str,
    trade_data: dict,
    user: EntityAuthenticatedUser = Depends(require_entity_trader_access())
):
    return {"message": "Trade created", "entity": entity_id}

# Query with entity filtering
@router.get("/entities/{entity_id}/balances")
async def get_balances(
    entity_id: str,
    user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    db: DatabaseManager = Depends(get_database)
):
    # Get entity filter for SQL queries
    where_condition, params = await get_user_accessible_entity_filter(user, db, "b")

    query = f"SELECT * FROM balances b WHERE b.entity_id = %s"
    if where_condition:
        query += f" AND {where_condition}"

    # Execute query with entity filtering
    results = db.execute_query(query, [entity_id] + params)
    return {"balances": results}
"""
