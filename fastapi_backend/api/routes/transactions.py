"""
Transaction management routes - PostgreSQL Compatible
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_transactions(
    username: str,
    transaction_type: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: DatabaseManager = Depends(get_database)
):
    """Get transactions for a user - PostgreSQL compatible"""
    try:
        # Validate pagination
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        # Verify user exists
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
        
        # Build transactions query
        if db.db_type == 'postgresql':
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       fee_amount, created_at, processed_at
                FROM transactions
                WHERE user_id = %s
            """
            params = [user_id]
            
            if transaction_type:
                query += " AND transaction_type = %s"
                params.append(transaction_type)
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, (page - 1) * page_size])
            
        else:
            # SQLite
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       fee_amount, created_at, processed_at
                FROM transactions
                WHERE user_id = ?
            """
            params = [user_id]
            
            if transaction_type:
                query += " AND transaction_type = ?"
                params.append(transaction_type)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
        
        transactions = db.execute_query(query, params)
        
        # Get total count for pagination
        if db.db_type == 'postgresql':
            count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = %s"
            count_params = [user_id]
            
            if transaction_type:
                count_query += " AND transaction_type = %s"
                count_params.append(transaction_type)
            
            if status:
                count_query += " AND status = %s"
                count_params.append(status)
                
        else:
            count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = ?"
            count_params = [user_id]
            
            if transaction_type:
                count_query += " AND transaction_type = ?"
                count_params.append(transaction_type)
            
            if status:
                count_query += " AND status = ?"
                count_params.append(status)
        
        count_result = db.execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0
        
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
