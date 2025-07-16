"""
User management routes - PostgreSQL Compatible
"""
#api/routes/users.py
from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{username}")
async def get_user(
    username: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get user by username - PostgreSQL compatible"""
    try:
        # Use parameterized query compatible with both SQLite and PostgreSQL
        query = """
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, created_at, updated_at, last_login
            FROM users
            WHERE username = %s AND is_active = %s
        """

        # PostgreSQL uses %s for parameters
        if db.db_type == 'postgresql':
            params = (username, True)
        else:
            # SQLite uses ? for parameters
            query = query.replace('%s', '?')
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
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "is_active": bool(user["is_active"]),
                "is_verified": bool(user["is_verified"]),
                "created_at": user["created_at"],
                "updated_at": user["updated_at"],
                "last_login": user["last_login"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user: {str(e)}"
        )


@router.get("/")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = True,
    db: DatabaseManager = Depends(get_database)
):
    """List users with pagination - PostgreSQL compatible"""
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        offset = (page - 1) * page_size

        # Build query based on database type
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, created_at, updated_at
                FROM users
            """
            count_query = "SELECT COUNT(*) as total FROM users"
            params = []
            count_params = []

            if active_only:
                query += " WHERE is_active = %s"
                count_query += " WHERE is_active = %s"
                params.append(True)
                count_params.append(True)

            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

        else:
            # SQLite
            query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, created_at, updated_at
                FROM users
            """
            count_query = "SELECT COUNT(*) as total FROM users"
            params = []
            count_params = []

            if active_only:
                query += " WHERE is_active = ?"
                count_query += " WHERE is_active = ?"
                params.append(1)
                count_params.append(1)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, offset])

        # Get users
        users = db.execute_query(query, params)

        # Get total count
        count_result = db.execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0

        # Convert boolean fields for consistency
        for user in users:
            user['is_active'] = bool(user['is_active'])
            user['is_verified'] = bool(user['is_verified'])

        return {
            "success": True,
            "data": users,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing users: {str(e)}"
        )
