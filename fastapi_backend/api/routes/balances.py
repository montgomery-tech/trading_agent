"""
Balance management routes - PostgreSQL Compatible
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_balances(
    username: str,
    currency: str = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get balances for a user - PostgreSQL compatible"""
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


@router.get("/summary/{username}")
async def get_balance_summary(
    username: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get balance summary for a user - PostgreSQL compatible"""
    try:
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
        
        # Get balance summary
        if db.db_type == 'postgresql':
            summary_query = """
                SELECT 
                    COUNT(*) as total_currencies,
                    COUNT(CASE WHEN ub.total_balance > 0 THEN 1 END) as currencies_with_balance,
                    COUNT(CASE WHEN c.is_fiat = true THEN 1 END) as fiat_currencies,
                    COUNT(CASE WHEN c.is_fiat = false THEN 1 END) as crypto_currencies
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = %s
            """
            params = (user_id,)
        else:
            summary_query = """
                SELECT 
                    COUNT(*) as total_currencies,
                    COUNT(CASE WHEN ub.total_balance > 0 THEN 1 END) as currencies_with_balance,
                    COUNT(CASE WHEN c.is_fiat = 1 THEN 1 END) as fiat_currencies,
                    COUNT(CASE WHEN c.is_fiat = 0 THEN 1 END) as crypto_currencies
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = ?
            """
            params = (user_id,)
        
        summary_result = db.execute_query(summary_query, params)
        summary = summary_result[0] if summary_result else {
            'total_currencies': 0,
            'currencies_with_balance': 0,
            'fiat_currencies': 0,
            'crypto_currencies': 0
        }
        
        return {
            "success": True,
            "data": {
                "user": username,
                "summary": summary
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balance summary: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving balance summary: {str(e)}"
        )
