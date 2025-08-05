"""
Transaction management routes - With API Key Authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_transactions(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    limit: int = 50,
    offset: int = 0,
    db: DatabaseManager = Depends(get_database)
):
    """Get transactions for a user - Requires authentication"""
    try:
        # Verify user exists and is active
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
                detail=f"User '{username}' not found"
            )
        
        user_id = user_results[0]['id']
        
        # Get transactions
        if db.db_type == 'postgresql':
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       created_at, processed_at
                FROM transactions 
                WHERE user_id = %s
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            params = (user_id, limit, offset)
        else:
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       created_at, processed_at
                FROM transactions 
                WHERE user_id = ?
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            params = (user_id, limit, offset)
        
        transactions = db.execute_query(query, params)
        
        return {
            "success": True,
            "data": transactions,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(transactions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving transactions: {str(e)}"
        )
