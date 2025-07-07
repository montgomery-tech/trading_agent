# ============================================================================
# api/routes/users.py
# ============================================================================

"""
User management routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from api.models import UserResponse, DataResponse, ListResponse
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager
import logging
from typing import Optional
logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{username}", response_model=UserResponse)
async def get_user(
    username: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get user by username"""
    try:
        query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, created_at, updated_at, last_login
            FROM users
            WHERE username = ?
        """

        results = db.execute_query(query, (username,))

        if not results:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")

        user = results[0]

        return UserResponse(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            created_at=user['created_at'],
            updated_at=user['updated_at'],
            last_login=user['last_login']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user: {str(e)}")


@router.get("/", response_model=ListResponse)
async def list_users(
    active_only: bool = True,
    pagination: dict = Depends(get_pagination_params),
    db: DatabaseManager = Depends(get_database)
):
    """List all users"""
    try:
        query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, created_at, last_login
            FROM users
        """
        params = []

        if active_only:
            query += " WHERE is_active = 1"

        query += " ORDER BY created_at DESC"
        query += f" LIMIT {pagination['page_size']} OFFSET {pagination['offset']}"

        users = db.execute_query(query, params)

        return ListResponse(
            message=f"Retrieved {len(users)} users",
            data=users,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")
