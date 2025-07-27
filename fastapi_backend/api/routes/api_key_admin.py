#!/usr/bin/env python3
"""
API Key Management Endpoints
Task 2.2: Admin-managed API key CRUD endpoints

Provides comprehensive API key management functionality for admins
including creation, listing, updating, revoking, and usage statistics.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field, validator

from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_admin, AuthenticatedAPIKeyUser
from api.api_key_models import (
    CreateAPIKeyRequest, UpdateAPIKeyRequest, RevokeAPIKeyRequest,
    CreateAPIKeyResponse, APIKeyResponse, APIKeyListResponse, APIKeyUsageStats,
    APIKeyScope, UserRole, APIKeyWithUser
)
from api.api_key_service import get_api_key_service, APIKeyService

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Extended Request/Response Models for Admin Management
# =============================================================================

class AdminCreateAPIKeyRequest(BaseModel):
    """Admin request to create API key for a user"""
    user_id: str = Field(..., description="User ID to create key for")
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    description: Optional[str] = Field(None, max_length=500, description="Key description")
    permissions_scope: APIKeyScope = Field(APIKeyScope.INHERIT, description="Permission scope")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")

    @validator('name')
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('API key name cannot be empty')
        return v

    @validator('expires_at')
    def validate_expiration(cls, v):
        if v and v <= datetime.now(timezone.utc):
            raise ValueError('Expiration date must be in the future')
        return v


class APIKeySearchRequest(BaseModel):
    """Request parameters for searching API keys"""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    username: Optional[str] = Field(None, description="Filter by username")
    active_only: bool = Field(True, description="Only show active keys")
    scope: Optional[APIKeyScope] = Field(None, description="Filter by permission scope")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class APIKeyStatsResponse(BaseModel):
    """API key statistics response"""
    success: bool = True
    message: str = "API key statistics retrieved"
    stats: APIKeyUsageStats

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AdminAPIKeyListResponse(BaseModel):
    """Enhanced API key list response for admins"""
    success: bool = True
    message: str = "API keys retrieved successfully"
    data: List[APIKeyWithUser]
    pagination: Dict[str, Any]
    total_count: int
    summary: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIKeyActionResponse(BaseModel):
    """Response for API key management actions"""
    success: bool = True
    message: str
    action: str
    api_key_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# API Key CRUD Endpoints
# =============================================================================

@router.post("/api-keys", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: AdminCreateAPIKeyRequest,
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Create a new API key for a user (Admin only).

    Creates an API key with the specified permissions and returns
    the full key (shown only once) along with key information.
    """
    try:
        # Validate user exists
        user_query = "SELECT id, username, email, role FROM users WHERE id = %s AND is_active = %s"
        if db.db_type != 'postgresql':
            user_query = user_query.replace('%s', '?')

        user_result = db.execute_query(user_query, (request.user_id, True))
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive"
            )

        user = user_result[0]

        # Create API key using service
        create_request = CreateAPIKeyRequest(
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            permissions_scope=request.permissions_scope,
            expires_at=request.expires_at
        )

        api_key_obj, full_api_key = await api_key_service.create_api_key(
            create_request, admin.id, db
        )

        # Log admin action
        logger.info(
            f"Admin {admin.username} created API key '{request.name}' "
            f"for user {user['username']} ({request.user_id})"
        )

        # Prepare response
        key_info = {
            "id": api_key_obj.id,
            "key_id": api_key_obj.key_id,
            "name": api_key_obj.name,
            "description": api_key_obj.description,
            "permissions_scope": api_key_obj.permissions_scope.value,
            "user_id": api_key_obj.user_id,
            "user_username": user['username'],
            "user_email": user['email'],
            "created_at": api_key_obj.created_at,
            "expires_at": api_key_obj.expires_at,
            "created_by": admin.username
        }

        return CreateAPIKeyResponse(
            message=f"API key '{request.name}' created successfully for user {user['username']}",
            key_info=key_info,
            api_key=full_api_key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/api-keys", response_model=AdminAPIKeyListResponse)
async def list_api_keys(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    username: Optional[str] = Query(None, description="Filter by username"),
    active_only: bool = Query(True, description="Only show active keys"),
    scope: Optional[APIKeyScope] = Query(None, description="Filter by permission scope"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    List API keys with filtering and pagination (Admin only).

    Returns a paginated list of API keys with user information
    and optional filtering by user, status, or scope.
    """
    try:
        # If username is provided, get user_id
        target_user_id = user_id
        if username and not user_id:
            user_query = "SELECT id FROM users WHERE username = %s"
            if db.db_type != 'postgresql':
                user_query = user_query.replace('%s', '?')

            user_result = db.execute_query(user_query, (username,))
            if user_result:
                target_user_id = user_result[0]['id']
            else:
                # No user found, return empty list
                return AdminAPIKeyListResponse(
                    data=[],
                    pagination={
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                        "has_next": False,
                        "has_prev": False
                    },
                    total_count=0,
                    summary={
                        "total_keys": 0,
                        "active_keys": 0,
                        "inactive_keys": 0,
                        "by_scope": {}
                    }
                )

        # Calculate offset
        offset = (page - 1) * page_size

        # Get API keys with filtering
        api_keys = await api_key_service.list_api_keys(
            db=db,
            user_id=target_user_id,
            active_only=active_only,
            limit=page_size,
            offset=offset
        )

        # Filter by scope if specified
        if scope:
            api_keys = [key for key in api_keys if key.permissions_scope == scope]

        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN ak.is_active = %s THEN 1 ELSE 0 END) as active_count,
                   SUM(CASE WHEN ak.is_active = %s THEN 1 ELSE 0 END) as inactive_count
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE 1=1
        """
        count_params = [True, False]

        if target_user_id:
            count_query += " AND ak.user_id = %s"
            count_params.append(target_user_id)

        if active_only:
            count_query += " AND ak.is_active = %s"
            count_params.append(True)

        if db.db_type != 'postgresql':
            count_query = count_query.replace('%s', '?')

        count_result = db.execute_query(count_query, count_params)
        total_count = count_result[0]['total'] if count_result else 0
        active_count = count_result[0]['active_count'] if count_result else 0
        inactive_count = count_result[0]['inactive_count'] if count_result else 0

        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        # Create summary statistics
        scope_counts = {}
        for key in api_keys:
            scope = key.permissions_scope.value
            scope_counts[scope] = scope_counts.get(scope, 0) + 1

        return AdminAPIKeyListResponse(
            data=api_keys,
            pagination={
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            total_count=total_count,
            summary={
                "total_keys": total_count,
                "active_keys": active_count,
                "inactive_keys": inactive_count,
                "by_scope": scope_counts
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys"
        )


@router.get("/api-keys/{key_id}", response_model=Dict[str, Any])
async def get_api_key(
    key_id: str,
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Get detailed information about a specific API key (Admin only).

    Returns complete API key information including usage statistics.
    """
    try:
        # Get API key with user info
        api_key = await api_key_service.get_api_key_by_id(key_id, db, include_user_info=True)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Get usage statistics
        usage_stats = await api_key_service.get_api_key_usage_stats(key_id, db)

        return {
            "success": True,
            "message": "API key retrieved successfully",
            "api_key": api_key.dict(),
            "usage_stats": usage_stats.dict() if usage_stats else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key"
        )


@router.put("/api-keys/{key_id}", response_model=APIKeyActionResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Update API key metadata (Admin only).

    Allows updating name, description, active status, and expiration date.
    Cannot update permissions scope after creation for security.
    """
    try:
        # Update API key
        updated_key = await api_key_service.update_api_key(key_id, request, db)

        if not updated_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Log admin action
        logger.info(
            f"Admin {admin.username} updated API key {key_id}. "
            f"Changes: {request.dict(exclude_none=True)}"
        )

        return APIKeyActionResponse(
            message=f"API key {key_id} updated successfully",
            action="update",
            api_key_id=key_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )


@router.delete("/api-keys/{key_id}", response_model=APIKeyActionResponse)
async def revoke_api_key(
    key_id: str,
    request: Optional[RevokeAPIKeyRequest] = None,
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Revoke (deactivate) an API key (Admin only).

    Deactivates the API key immediately, preventing further use.
    The key remains in the database for audit purposes.
    """
    try:
        # Get API key info before revoking
        api_key = await api_key_service.get_api_key_by_id(key_id, db, include_user_info=True)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Revoke API key
        reason = request.reason if request else None
        success = await api_key_service.revoke_api_key(key_id, reason, db)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or already revoked"
            )

        # Log admin action
        logger.info(
            f"Admin {admin.username} revoked API key {key_id} "
            f"belonging to user {api_key.user_username}. "
            f"Reason: {reason or 'No reason provided'}"
        )

        return APIKeyActionResponse(
            message=f"API key {key_id} revoked successfully",
            action="revoke",
            api_key_id=key_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


# =============================================================================
# API Key Usage and Statistics Endpoints
# =============================================================================

@router.get("/api-keys/{key_id}/stats", response_model=APIKeyStatsResponse)
async def get_api_key_stats(
    key_id: str,
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Get usage statistics for an API key (Admin only).

    Returns detailed usage metrics including request counts,
    most used endpoints, and activity patterns.
    """
    try:
        # Verify API key exists
        api_key = await api_key_service.get_api_key_by_id(key_id, db)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Get usage statistics
        stats = await api_key_service.get_api_key_usage_stats(key_id, db)

        if not stats:
            # Create empty stats if none found
            stats = APIKeyUsageStats(
                key_id=key_id,
                total_requests=0,
                last_24h_requests=0,
                last_7d_requests=0,
                last_30d_requests=0,
                most_used_endpoint=None,
                last_used_at=None,
                created_at=api_key.created_at
            )

        return APIKeyStatsResponse(stats=stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key stats for {key_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key statistics"
        )


@router.get("/api-keys/stats/summary", response_model=Dict[str, Any])
async def get_api_keys_summary(
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database)
):
    """
    Get overall API key system statistics (Admin only).

    Returns system-wide metrics for API key usage and distribution.
    """
    try:
        # Get overall statistics
        if db.db_type == 'postgresql':
            stats_query = """
                SELECT
                    COUNT(*) as total_keys,
                    SUM(CASE WHEN ak.is_active = true THEN 1 ELSE 0 END) as active_keys,
                    SUM(CASE WHEN ak.is_active = false THEN 1 ELSE 0 END) as inactive_keys,
                    COUNT(DISTINCT ak.user_id) as unique_users,
                    ak.permissions_scope,
                    COUNT(*) as scope_count
                FROM api_keys ak
                GROUP BY ak.permissions_scope
                ORDER BY scope_count DESC
            """
            params = ()
        else:
            stats_query = """
                SELECT
                    COUNT(*) as total_keys,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_keys,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_keys,
                    COUNT(DISTINCT user_id) as unique_users,
                    permissions_scope,
                    COUNT(*) as scope_count
                FROM api_keys
                GROUP BY permissions_scope
                ORDER BY scope_count DESC
            """
            params = ()

        results = db.execute_query(stats_query, params)

        # Process results
        total_keys = 0
        active_keys = 0
        inactive_keys = 0
        unique_users = 0
        scope_distribution = {}

        if results:
            # Get totals from first row
            total_keys = results[0]['total_keys']
            active_keys = results[0]['active_keys']
            inactive_keys = results[0]['inactive_keys']
            unique_users = results[0]['unique_users']

            # Get scope distribution
            for row in results:
                scope_distribution[row['permissions_scope']] = row['scope_count']

        # Get recent activity
        if db.db_type == 'postgresql':
            recent_query = """
                SELECT COUNT(*) as recent_usage
                FROM api_key_usage_log
                WHERE request_timestamp > NOW() - INTERVAL '24 hours'
            """
        else:
            recent_query = """
                SELECT COUNT(*) as recent_usage
                FROM api_key_usage_log
                WHERE request_timestamp > datetime('now', '-24 hours')
            """

        recent_result = db.execute_query(recent_query, ())
        recent_usage = recent_result[0]['recent_usage'] if recent_result else 0

        return {
            "success": True,
            "message": "API key system statistics retrieved",
            "summary": {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "inactive_keys": inactive_keys,
                "unique_users_with_keys": unique_users,
                "scope_distribution": scope_distribution,
                "recent_24h_requests": recent_usage,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get API key system summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )


# =============================================================================
# User-specific API Key Management
# =============================================================================

@router.get("/users/{user_id}/api-keys", response_model=APIKeyListResponse)
async def get_user_api_keys(
    user_id: str,
    active_only: bool = Query(True, description="Only show active keys"),
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Get all API keys for a specific user (Admin only).

    Returns all API keys belonging to the specified user.
    """
    try:
        # Verify user exists
        user_query = "SELECT username, email FROM users WHERE id = %s"
        if db.db_type != 'postgresql':
            user_query = user_query.replace('%s', '?')

        user_result = db.execute_query(user_query, (user_id,))
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = user_result[0]

        # Get user's API keys
        api_keys = await api_key_service.list_api_keys(
            db=db,
            user_id=user_id,
            active_only=active_only,
            limit=100,
            offset=0
        )

        return APIKeyListResponse(
            message=f"API keys for user {user['username']} retrieved successfully",
            data=api_keys,
            total_count=len(api_keys)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API keys for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user API keys"
        )


@router.delete("/users/{user_id}/api-keys", response_model=APIKeyActionResponse)
async def revoke_all_user_api_keys(
    user_id: str,
    reason: Optional[str] = Query(None, description="Reason for revoking all keys"),
    admin: AuthenticatedAPIKeyUser = Depends(require_admin),
    db: DatabaseManager = Depends(get_database),
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Revoke all API keys for a user (Admin only).

    Emergency function to immediately revoke all of a user's API keys.
    """
    try:
        # Verify user exists
        user_query = "SELECT username, email FROM users WHERE id = %s"
        if db.db_type != 'postgresql':
            user_query = user_query.replace('%s', '?')

        user_result = db.execute_query(user_query, (user_id,))
        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user = user_result[0]

        # Get all active API keys for user
        api_keys = await api_key_service.list_api_keys(
            db=db,
            user_id=user_id,
            active_only=True,
            limit=1000,
            offset=0
        )

        if not api_keys:
            return APIKeyActionResponse(
                message=f"No active API keys found for user {user['username']}",
                action="revoke_all",
                api_key_id="none"
            )

        # Revoke all keys
        revoked_count = 0
        for api_key in api_keys:
            success = await api_key_service.revoke_api_key(
                api_key.key_id,
                f"Bulk revocation: {reason}" if reason else "Bulk revocation by admin",
                db
            )
            if success:
                revoked_count += 1

        # Log admin action
        logger.info(
            f"Admin {admin.username} revoked all API keys for user {user['username']} "
            f"({user_id}). Revoked {revoked_count} keys. Reason: {reason or 'No reason provided'}"
        )

        return APIKeyActionResponse(
            message=f"Revoked {revoked_count} API keys for user {user['username']}",
            action="revoke_all",
            api_key_id=f"bulk_{revoked_count}_keys"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke all API keys for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke user API keys"
        )


# =============================================================================
# Export all router endpoints
# =============================================================================

# The router is already configured above and can be imported by main.py
