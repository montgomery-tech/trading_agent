"""
Transaction management routes - PostgreSQL Compatible
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
def get_db_params(db, *params):
    """Convert parameters based on database type"""
    if db.db_type == 'postgresql':
        return params
    else:
        return params

from api.database import DatabaseManager
from decimal import Decimal
import logging
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_transactions(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    page: int = 1,
    page_size: int = 20,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get user transaction history - SECURITY ENFORCED
    Users can only access their own transaction data, admins can access any user's data
    """
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        offset = (page - 1) * page_size

        # Get user ID
        # Handle database type differences

        if db.db_type == 'postgresql':

            query = """
            SELECT id FROM users WHERE username = %s AND is_active = %s"""

        else:

            query = """
            SELECT id FROM users WHERE username = ? AND is_active = ?
        """
        user_results = db.execute_query(query, (username, True))

        if not user_results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found"
            )

        user_id = user_results[0]['id']

        # Build transactions query
        # Handle database type differences

        if db.db_type == 'postgresql':

            query = """
            SELECT id, transaction_type, status, amount, currency_code,
                   balance_before, balance_after, description, external_reference,
                   created_at, processed_at
            FROM transactions
            WHERE user_id = %s
        """

        else:

            query = """
            SELECT id, transaction_type, status, amount, currency_code,
                   balance_before, balance_after, description, external_reference,
                   created_at, processed_at
            FROM transactions
            WHERE user_id = ?
        """
        params = [user_id]

        if transaction_type:
            query += " AND transaction_type = %s"
            params.append(transaction_type)

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])

        transactions = db.execute_query(query, params)

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = %s"
        count_params = [user_id]

        if transaction_type:
            count_query += " AND transaction_type = %s"
            count_params.append(transaction_type)

        if status:
            count_query += " AND status = %s"
            count_params.append(status)

        count_results = db.execute_query(count_query, count_params)
        total = count_results[0]['total'] if count_results else 0

        # Log successful access for security monitoring
        logger.info(f"Transaction access: {current_user.username} accessed {username} transactions (role: {current_user.role.value})")

        return {
            "success": True,
            "data": transactions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
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
