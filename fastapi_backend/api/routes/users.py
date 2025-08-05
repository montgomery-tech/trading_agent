"""
User management routes - With API Key Authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{username}")
async def get_user(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    db: DatabaseManager = Depends(get_database)
):
    """Get user by username - Requires authentication"""
    try:
        # Check if user exists and is active
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at, updated_at, last_login
                FROM users 
                WHERE username = %s AND is_active = %s
            """
            params = (username, True)
        else:
            query = """
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at, updated_at, last_login
                FROM users 
                WHERE username = ? AND is_active = ?
            """
            params = (username, 1)
        
        results = db.execute_query(query, params)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found or inactive"
            )
        
        user = results[0]
        
        return {
            "success": True,
            "data": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "first_name": user['first_name'],
                "last_name": user['last_name'],
                "is_active": user['is_active'],
                "is_verified": user['is_verified'],
                "created_at": user['created_at'],
                "updated_at": user['updated_at'],
                "last_login": user['last_login']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {username}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user: {str(e)}"
        )
