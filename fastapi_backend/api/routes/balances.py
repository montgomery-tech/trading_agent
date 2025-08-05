"""
Balance management routes - With API Key Authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_balances(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    currency: str = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get balances for a user - Requires authentication"""
    try:
        # First verify user exists and is active
        if db.db_type == 'postgresql':
            user_query = "SELECT id FROM users WHERE username = %s AND is_active = %s"
            user_params = (username, True)
        else:
            user_query = "SELECT id FROM users WHERE username = ? AND is_active = ?"
            user_params = (username, 1)

        user_results = db.execute_query(user_query, user_params)

        if not user_results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found or inactive"
            )

        user_id = user_results[0]['id']

        # Build balances query
        if db.db_type == 'postgresql':
            query = """
                SELECT ub.id, ub.currency_code, ub.total_balance,
                       ub.available_balance, ub.locked_balance,
                       c.name as currency_name, c.symbol, c.is_fiat,
                       ub.created_at, ub.updated_at
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = %s
            """
            params = [user_id]

            if currency:
                query += " AND ub.currency_code = %s"
                params.append(currency.upper())

        else:
            # SQLite
            query = """
                SELECT ub.id, ub.currency_code, ub.total_balance,
                       ub.available_balance, ub.locked_balance,
                       c.name as currency_name, c.symbol, c.is_fiat,
                       ub.created_at, ub.updated_at
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = ?
            """
            params = [user_id]

            if currency:
                query += " AND ub.currency_code = ?"
                params.append(currency.upper())

        query += " ORDER BY c.is_fiat DESC, ub.total_balance DESC"

        balances = db.execute_query(query, params)

        # Convert boolean fields for consistency
        for balance in balances:
            balance['is_fiat'] = bool(balance['is_fiat'])

        return {
            "success": True,
            "data": balances,
            "user": username,
            "total_balances": len(balances)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balances: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving balances: {str(e)}"
        )
