#!/usr/bin/env python3
"""
API Key Service Implementation
Task 1.3: Core API key authentication and management service

Provides secure API key generation, validation, management, and authentication
with audit trail support and role-based access control.
"""

import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple
from uuid import UUID

from passlib.context import CryptContext
from fastapi import HTTPException, status
from api.password_service import password_service
from api.api_key_models import (
    APIKey, APIKeyWithUser, APIKeyAuthData, AuthenticatedAPIKeyUser,
    CreateAPIKeyRequest, UpdateAPIKeyRequest, APIKeyScope, UserRole,
    APIKeyGeneration, APIKeyValidation, APIKeyError, APIKeyUsageStats
)
from api.database import DatabaseManager
from api.config import settings

logger = logging.getLogger(__name__)


class APIKeyService:
    """
    Core API key service for authentication and management.

    Provides secure key generation, validation, CRUD operations,
    and usage tracking with admin-managed key distribution.
    """

    def __init__(self):
        # Configure bcrypt context for key hashing
        self.hash_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Balance security and performance
        )

        # Key generation settings
        self.key_prefix = "btapi"
        self.key_id_length = 16
        self.secret_length = 32

        logger.info("API Key Service initialized")

    # =============================================================================
    # Key Generation and Hashing
    # =============================================================================

    def generate_api_key(self) -> Tuple[str, str]:
        """
        Generate a new API key pair (key_id, full_key).

        Returns:
            Tuple of (key_id, full_api_key)
            - key_id: Public identifier (btapi_16chars)
            - full_api_key: Complete key (btapi_16chars_32chars)
        """
        try:
            # Generate secure random components
            chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

            # Generate key ID part (public)
            key_id_suffix = ''.join(secrets.choice(chars) for _ in range(self.key_id_length))
            key_id = f"{self.key_prefix}_{key_id_suffix}"

            # Generate secret part
            secret_part = ''.join(secrets.choice(chars) for _ in range(self.secret_length))

            # Combine into full API key
            full_api_key = f"{key_id}_{secret_part}"

            logger.debug(f"Generated API key with ID: {key_id}")
            return key_id, full_api_key

        except Exception as e:
            logger.error(f"Failed to generate API key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate API key"
            )

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key using bcrypt.

        Args:
            api_key: Full API key string

        Returns:
            Hashed API key
        """
        try:
            return self.hash_context.hash(api_key)
        except Exception as e:
            logger.error(f"Failed to hash API key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process API key"
            )

    def verify_api_key(self, plain_key: str, hashed_key: str) -> bool:
        """
        Verify an API key against its hash.

        Args:
            plain_key: Plain text API key
            hashed_key: Hashed API key from database

        Returns:
            True if key matches, False otherwise
        """
        try:
            return self.hash_context.verify(plain_key, hashed_key)
        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return False

    def extract_key_id(self, api_key: str) -> str:
        """
        Extract the key ID from a full API key.

        Args:
            api_key: Full API key (btapi_16chars_32chars)

        Returns:
            Key ID (btapi_16chars)
        """
        if not APIKeyValidation.validate_key_format(api_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API key format"
            )

        parts = api_key.split('_')
        return f"{parts[0]}_{parts[1]}"

    # =============================================================================
    # Database Operations
    # =============================================================================

    async def create_api_key(
        self,
        request: CreateAPIKeyRequest,
        created_by_user_id: Union[str, UUID],
        db: DatabaseManager
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key in the database.

        Args:
            request: API key creation request
            created_by_user_id: ID of admin creating the key
            db: Database manager instance

        Returns:
            Tuple of (APIKey object, full_api_key)
        """
        try:
            # Validate user exists
            user = await self._get_user_by_id(request.user_id, db)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Generate API key
            key_id, full_api_key = self.generate_api_key()
            key_hash = self.hash_api_key(full_api_key)

            # Insert into database
            if db.db_type == 'postgresql':
                query = """
                    INSERT INTO api_keys (
                        key_id, key_hash, user_id, name, description,
                        permissions_scope, expires_at, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """
                params = (
                    key_id, key_hash, str(request.user_id), request.name,
                    request.description, request.permissions_scope.value,
                    request.expires_at, str(created_by_user_id)
                )
            else:
                query = """
                    INSERT INTO api_keys (
                        key_id, key_hash, user_id, name, description,
                        permissions_scope, expires_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    key_id, key_hash, str(request.user_id), request.name,
                    request.description, request.permissions_scope.value,
                    request.expires_at, str(created_by_user_id)
                )

            result = db.execute_query(query, params)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create API key"
                )

            # Create API key object
            api_key = APIKey(
                id=result[0]['id'] if db.db_type == 'postgresql' else key_id[:16],
                key_id=key_id,
                user_id=request.user_id,
                name=request.name,
                description=request.description,
                permissions_scope=request.permissions_scope,
                expires_at=request.expires_at,
                created_by=created_by_user_id,
                created_at=result[0]['created_at'] if db.db_type == 'postgresql' else datetime.now(timezone.utc),
                is_active=True
            )

            logger.info(f"Created API key {key_id} for user {request.user_id}")
            return api_key, full_api_key

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )

    async def get_api_key_by_id(
        self,
        key_id: str,
        db: DatabaseManager,
        include_user_info: bool = False
    ) -> Optional[Union[APIKey, APIKeyWithUser]]:
        """
        Get API key by key ID.

        Args:
            key_id: API key identifier
            db: Database manager instance
            include_user_info: Whether to include user information

        Returns:
            APIKey or APIKeyWithUser object, or None if not found
        """
        try:
            if include_user_info:
                if db.db_type == 'postgresql':
                    query = """
                        SELECT ak.*, u.username, u.email, u.role,
                               cb.username as created_by_username
                        FROM api_keys ak
                        JOIN users u ON ak.user_id = u.id
                        LEFT JOIN users cb ON ak.created_by = cb.id
                        WHERE ak.key_id = %s
                    """
                    params = (key_id,)
                else:
                    query = """
                        SELECT ak.*, u.username, u.email, u.role,
                               cb.username as created_by_username
                        FROM api_keys ak
                        JOIN users u ON ak.user_id = u.id
                        LEFT JOIN users cb ON ak.created_by = cb.id
                        WHERE ak.key_id = ?
                    """
                    params = (key_id,)

                result = db.execute_query(query, params)
                if not result:
                    return None

                row = result[0]
                return APIKeyWithUser(
                    id=row['id'],
                    key_id=row['key_id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    description=row['description'],
                    permissions_scope=APIKeyScope(row['permissions_scope']),
                    expires_at=row['expires_at'],
                    is_active=row['is_active'],
                    created_by=row['created_by'],
                    created_at=row['created_at'],
                    last_used_at=row['last_used_at'],
                    user_username=row['username'],
                    user_email=row['email'],
                    user_role=UserRole(row['role']),
                    created_by_username=row['created_by_username']
                )
            else:
                if db.db_type == 'postgresql':
                    query = "SELECT * FROM api_keys WHERE key_id = %s"
                    params = (key_id,)
                else:
                    query = "SELECT * FROM api_keys WHERE key_id = ?"
                    params = (key_id,)

                result = db.execute_query(query, params)
                if not result:
                    return None

                row = result[0]
                return APIKey(
                    id=row['id'],
                    key_id=row['key_id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    description=row['description'],
                    permissions_scope=APIKeyScope(row['permissions_scope']),
                    expires_at=row['expires_at'],
                    is_active=row['is_active'],
                    created_by=row['created_by'],
                    created_at=row['created_at'],
                    last_used_at=row['last_used_at']
                )

        except Exception as e:
            logger.error(f"Failed to get API key {key_id}: {e}")
            return None

    async def list_api_keys(
        self,
        db: DatabaseManager,
        user_id: Optional[Union[str, UUID]] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[APIKeyWithUser]:
        """
        List API keys with optional filtering.

        Args:
            db: Database manager instance
            user_id: Filter by user ID (optional)
            active_only: Only return active keys
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of APIKeyWithUser objects
        """
        try:
            where_conditions = []
            params = []

            if user_id:
                where_conditions.append("ak.user_id = %s" if db.db_type == 'postgresql' else "ak.user_id = ?")
                params.append(str(user_id))

            if active_only:
                where_conditions.append("ak.is_active = %s" if db.db_type == 'postgresql' else "ak.is_active = ?")
                params.append(True)

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            if db.db_type == 'postgresql':
                query = f"""
                    SELECT ak.*, u.username, u.email, u.role,
                           cb.username as created_by_username
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.id
                    LEFT JOIN users cb ON ak.created_by = cb.id
                    WHERE {where_clause}
                    ORDER BY ak.created_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
            else:
                query = f"""
                    SELECT ak.*, u.username, u.email, u.role,
                           cb.username as created_by_username
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.id
                    LEFT JOIN users cb ON ak.created_by = cb.id
                    WHERE {where_clause}
                    ORDER BY ak.created_at DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])

            results = db.execute_query(query, params)

            api_keys = []
            for row in results:
                api_keys.append(APIKeyWithUser(
                    id=row['id'],
                    key_id=row['key_id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    description=row['description'],
                    permissions_scope=APIKeyScope(row['permissions_scope']),
                    expires_at=row['expires_at'],
                    is_active=row['is_active'],
                    created_by=row['created_by'],
                    created_at=row['created_at'],
                    last_used_at=row['last_used_at'],
                    user_username=row['username'],
                    user_email=row['email'],
                    user_role=UserRole(row['role']),
                    created_by_username=row['created_by_username']
                ))

            return api_keys

        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return []

    async def update_api_key(
        self,
        key_id: str,
        request: UpdateAPIKeyRequest,
        db: DatabaseManager
    ) -> Optional[APIKey]:
        """
        Update an API key.

        Args:
            key_id: API key identifier
            request: Update request
            db: Database manager instance

        Returns:
            Updated APIKey object or None if not found
        """
        try:
            # Build update query dynamically
            update_fields = []
            params = []

            if request.name is not None:
                update_fields.append("name = %s" if db.db_type == 'postgresql' else "name = ?")
                params.append(request.name)

            if request.description is not None:
                update_fields.append("description = %s" if db.db_type == 'postgresql' else "description = ?")
                params.append(request.description)

            if request.is_active is not None:
                update_fields.append("is_active = %s" if db.db_type == 'postgresql' else "is_active = ?")
                params.append(request.is_active)

            if request.expires_at is not None:
                update_fields.append("expires_at = %s" if db.db_type == 'postgresql' else "expires_at = ?")
                params.append(request.expires_at)

            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )

            # Add updated timestamp
            update_fields.append("updated_at = %s" if db.db_type == 'postgresql' else "updated_at = ?")
            params.append(datetime.now(timezone.utc))

            # Add WHERE condition
            params.append(key_id)

            query = f"""
                UPDATE api_keys
                SET {', '.join(update_fields)}
                WHERE key_id = {'%s' if db.db_type == 'postgresql' else '?'}
            """

            affected_rows = db.execute_command(query, params)

            if affected_rows == 0:
                return None

            # Return updated API key
            return await self.get_api_key_by_id(key_id, db)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update API key {key_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update API key"
            )

    async def revoke_api_key(
        self,
        key_id: str,
        reason: Optional[str],
        db: DatabaseManager
    ) -> bool:
        """
        Revoke (deactivate) an API key.

        Args:
            key_id: API key identifier
            reason: Reason for revocation
            db: Database manager instance

        Returns:
            True if revoked successfully, False if not found
        """
        try:
            if db.db_type == 'postgresql':
                query = """
                    UPDATE api_keys
                    SET is_active = %s, updated_at = %s
                    WHERE key_id = %s
                """
                params = (False, datetime.now(timezone.utc), key_id)
            else:
                query = """
                    UPDATE api_keys
                    SET is_active = ?, updated_at = ?
                    WHERE key_id = ?
                """
                params = (False, datetime.now(timezone.utc), key_id)

            affected_rows = db.execute_command(query, params)

            if affected_rows > 0:
                logger.info(f"Revoked API key {key_id}" + (f" - Reason: {reason}" if reason else ""))
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False

    # =============================================================================
    # Authentication and Validation
    # =============================================================================

    async def authenticate_api_key(
        self,
        api_key: str,
        db: DatabaseManager
    ) -> Optional[AuthenticatedAPIKeyUser]:
        """
        Authenticate an API key and return user information.

        Args:
            api_key: Full API key
            db: Database manager instance

        Returns:
            AuthenticatedAPIKeyUser object or None if invalid
        """
        try:
            # Validate key format
            if not APIKeyValidation.validate_key_format(api_key):
                logger.warning("Invalid API key format received")
                return None

            # Extract key ID
            key_id = self.extract_key_id(api_key)

            # Get key info with user data
            if db.db_type == 'postgresql':
                query = """
                    SELECT ak.*, u.username, u.email, u.first_name, u.last_name,
                           u.role, u.is_active as user_active, u.is_verified,
                           u.created_at as user_created_at, u.last_login
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.id
                    WHERE ak.key_id = %s AND ak.is_active = %s
                """
                params = (key_id, True)
            else:
                query = """
                    SELECT ak.*, u.username, u.email, u.first_name, u.last_name,
                           u.role, u.is_active as user_active, u.is_verified,
                           u.created_at as user_created_at, u.last_login
                    FROM api_keys ak
                    JOIN users u ON ak.user_id = u.id
                    WHERE ak.key_id = ? AND ak.is_active = ?
                """
                params = (key_id, True)

            result = db.execute_query(query, params)
            if not result:
                logger.warning(f"API key not found or inactive: {key_id}")
                return None

            row = result[0]

            # Verify API key hash
            if not self.verify_api_key(api_key, row['key_hash']):
                logger.warning(f"API key hash verification failed: {key_id}")
                return None

            # Check if user is active
            if not row['user_active']:
                logger.warning(f"User account inactive for API key: {key_id}")
                return None

            # Check if key is expired
            if row['expires_at'] and datetime.now(timezone.utc) > row['expires_at']:
                logger.warning(f"API key expired: {key_id}")
                return None

            # Log usage (async)
            await self._log_api_key_usage(row['id'], db)

            # Create authenticated user object
            user = AuthenticatedAPIKeyUser(
                id=row['user_id'],
                username=row['username'],
                email=row['email'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=UserRole(row['role']),
                is_active=row['user_active'],
                is_verified=row['is_verified'],
                created_at=row['user_created_at'],
                last_login=row['last_login'],
                api_key_id=key_id,
                api_key_name=row['name'],
                api_key_scope=APIKeyScope(row['permissions_scope'])
            )

            logger.debug(f"Successfully authenticated API key: {key_id}")
            return user

        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            return None

    # =============================================================================
    # Usage Tracking and Statistics
    # =============================================================================

    async def _log_api_key_usage(
        self,
        api_key_db_id: Union[str, UUID],
        db: DatabaseManager,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log API key usage to audit trail.

        Args:
            api_key_db_id: Database ID of the API key
            db: Database manager instance
            endpoint: API endpoint accessed
            method: HTTP method
            status_code: Response status code
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            if db.db_type == 'postgresql':
                query = """
                    INSERT INTO api_key_usage_log (
                        api_key_id, endpoint, method, status_code,
                        ip_address, user_agent
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (
                    str(api_key_db_id), endpoint, method,
                    status_code, ip_address, user_agent
                )
            else:
                query = """
                    INSERT INTO api_key_usage_log (
                        api_key_id, endpoint, method, status_code,
                        ip_address, user_agent
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (
                    str(api_key_db_id), endpoint, method,
                    status_code, ip_address, user_agent
                )

            db.execute_command(query, params)

        except Exception as e:
            # Don't raise exception for logging failures
            logger.error(f"Failed to log API key usage: {e}")

    async def get_api_key_usage_stats(
        self,
        key_id: str,
        db: DatabaseManager
    ) -> Optional[APIKeyUsageStats]:
        """
        Get usage statistics for an API key.

        Args:
            key_id: API key identifier
            db: Database manager instance

        Returns:
            APIKeyUsageStats object or None if not found
        """
        try:
            if db.db_type == 'postgresql':
                query = """
                    SELECT
                        ak.key_id,
                        ak.created_at,
                        ak.last_used_at,
                        COUNT(ul.id) as total_requests,
                        COUNT(CASE WHEN ul.request_timestamp > NOW() - INTERVAL '24 hours' THEN 1 END) as last_24h_requests,
                        COUNT(CASE WHEN ul.request_timestamp > NOW() - INTERVAL '7 days' THEN 1 END) as last_7d_requests,
                        COUNT(CASE WHEN ul.request_timestamp > NOW() - INTERVAL '30 days' THEN 1 END) as last_30d_requests,
                        MODE() WITHIN GROUP (ORDER BY ul.endpoint) as most_used_endpoint
                    FROM api_keys ak
                    LEFT JOIN api_key_usage_log ul ON ak.id = ul.api_key_id
                    WHERE ak.key_id = %s
                    GROUP BY ak.id, ak.key_id, ak.created_at, ak.last_used_at
                """
                params = (key_id,)
            else:
                query = """
                    SELECT
                        ak.key_id,
                        ak.created_at,
                        ak.last_used_at,
                        COUNT(ul.id) as total_requests,
                        COUNT(CASE WHEN ul.request_timestamp > datetime('now', '-24 hours') THEN 1 END) as last_24h_requests,
                        COUNT(CASE WHEN ul.request_timestamp > datetime('now', '-7 days') THEN 1 END) as last_7d_requests,
                        COUNT(CASE WHEN ul.request_timestamp > datetime('now', '-30 days') THEN 1 END) as last_30d_requests,
                        (SELECT endpoint FROM api_key_usage_log WHERE api_key_id = ak.id GROUP BY endpoint ORDER BY COUNT(*) DESC LIMIT 1) as most_used_endpoint
                    FROM api_keys ak
                    LEFT JOIN api_key_usage_log ul ON ak.id = ul.api_key_id
                    WHERE ak.key_id = ?
                    GROUP BY ak.id
                """
                params = (key_id,)

            result = db.execute_query(query, params)
            if not result:
                return None

            row = result[0]
            return APIKeyUsageStats(
                key_id=row['key_id'],
                total_requests=row['total_requests'] or 0,
                last_24h_requests=row['last_24h_requests'] or 0,
                last_7d_requests=row['last_7d_requests'] or 0,
                last_30d_requests=row['last_30d_requests'] or 0,
                most_used_endpoint=row['most_used_endpoint'],
                last_used_at=row['last_used_at'],
                created_at=row['created_at']
            )

        except Exception as e:
            logger.error(f"Failed to get usage stats for API key {key_id}: {e}")
            return None

    # =============================================================================
    # Helper Methods
    # =============================================================================

    async def _get_user_by_id(
        self,
        user_id: Union[str, UUID],
        db: DatabaseManager
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User identifier
            db: Database manager instance

        Returns:
            User dictionary or None if not found
        """
        try:
            if db.db_type == 'postgresql':
                query = "SELECT * FROM users WHERE id = %s"
                params = (str(user_id),)
            else:
                query = "SELECT * FROM users WHERE id = ?"
                params = (str(user_id),)

            result = db.execute_query(query, params)
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    def get_effective_permissions(
        self,
        user_role: UserRole,
        key_scope: APIKeyScope
    ) -> UserRole:
        """
        Get effective permissions based on user role and key scope.

        Args:
            user_role: User's role
            key_scope: API key permission scope

        Returns:
            Effective role for permission checking
        """
        if key_scope == APIKeyScope.INHERIT:
            return user_role
        elif key_scope == APIKeyScope.READ_ONLY:
            return UserRole.VIEWER
        elif key_scope == APIKeyScope.FULL_ACCESS:
            # Only admins can have full access keys
            if user_role == UserRole.ADMIN:
                return UserRole.ADMIN
            else:
                # For non-admins, treat as inherit
                return user_role
        else:
            return user_role


# Global service instance
api_key_service = APIKeyService()


# =============================================================================
# Utility Functions for Dependencies
# =============================================================================

def get_api_key_service() -> APIKeyService:
    """
    Get the global API key service instance.

    Returns:
        APIKeyService instance
    """
    return api_key_service
