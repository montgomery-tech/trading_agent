# Balance # ============================================================================
# api/routes/balances.py
# ============================================================================

"""
Balance management routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from api.models import BalanceResponse, ListResponse, DataResponse
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager
import logging
from typing import Optional
logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}", response_model=List[BalanceResponse])
async def get_user_balances(
    username: str,
    currency: Optional[str] = None,
    include_zero: bool = False,
    db: DatabaseManager = Depends(get_database)
):
    """Get balances for a specific user"""
    try:
        # Get user ID
        user_query = "SELECT id FROM users WHERE username = ? AND is_active = 1"
        user_results = db.execute_query(user_query, (username,))

        if not user_results:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")

        user_id = user_results[0]['id']

        # Build balance query
        query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance,
                   ub.locked_balance, ub.updated_at, c.name, c.symbol, c.is_fiat
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
        """
        params = [user_id]

        if not include_zero:
            query += " AND ub.total_balance > 0"

        if currency:
            query += " AND ub.currency_code = ?"
            params.append(currency.upper())

        query += " ORDER BY c.is_fiat DESC, ub.total_balance DESC, ub.currency_code"

        balances = db.execute_query(query, params)

        # Convert to response format
        response_balances = []
        for balance in balances:
            response_balances.append(BalanceResponse(
                currency_code=balance['currency_code'],
                currency_name=balance['name'],
                currency_symbol=balance['symbol'],
                total_balance=balance['total_balance'],
                available_balance=balance['available_balance'],
                locked_balance=balance['locked_balance'],
                is_fiat=balance['is_fiat'],
                updated_at=balance['updated_at']
            ))

        return response_balances

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balances: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving balances: {str(e)}")


@router.get("/summary/{currency_code}", response_model=DataResponse)
async def get_currency_summary(
    currency_code: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get balance summary for a specific currency"""
    try:
        currency_code = currency_code.upper()

        # Validate currency exists
        currency_query = "SELECT code, name, symbol FROM currencies WHERE code = ? AND is_active = 1"
        currency_results = db.execute_query(currency_query, (currency_code,))

        if not currency_results:
            raise HTTPException(status_code=404, detail=f"Currency '{currency_code}' not found")

        currency = currency_results[0]

        # Get summary statistics
        summary_query = """
            SELECT
                COUNT(ub.user_id) as user_count,
                SUM(ub.total_balance) as total_supply,
                SUM(ub.available_balance) as total_available,
                SUM(ub.locked_balance) as total_locked,
                AVG(ub.total_balance) as avg_balance,
                MIN(ub.total_balance) as min_balance,
                MAX(ub.total_balance) as max_balance
            FROM user_balances ub
            JOIN users u ON ub.user_id = u.id
            WHERE ub.currency_code = ? AND ub.total_balance > 0 AND u.is_active = 1
        """

        summary_results = db.execute_query(summary_query, (currency_code,))
        summary = summary_results[0] if summary_results else {}

        response_data = {
            "currency": currency,
            "statistics": summary
        }

        return DataResponse(
            message=f"Retrieved summary for {currency_code}",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving currency summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving summary: {str(e)}")


@router.get("/", response_model=ListResponse)
async def get_all_balances(
    min_balance: Optional[float] = None,
    currency_filter: Optional[str] = None,
    include_inactive: bool = False,
    pagination: dict = Depends(get_pagination_params),
    db: DatabaseManager = Depends(get_database)
):
    """Get all user balances with filtering"""
    try:
        # Build query
        query = """
            SELECT u.username, u.email, u.is_active,
                   ub.currency_code, ub.total_balance, ub.available_balance,
                   ub.locked_balance, c.symbol, c.is_fiat
            FROM users u
            JOIN user_balances ub ON u.id = ub.user_id
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.total_balance > 0
        """
        params = []

        if not include_inactive:
            query += " AND u.is_active = 1"

        if min_balance is not None:
            query += " AND ub.total_balance >= ?"
            params.append(str(min_balance))

        if currency_filter:
            query += " AND ub.currency_code = ?"
            params.append(currency_filter.upper())

        query += " ORDER BY u.username, c.is_fiat DESC, ub.total_balance DESC"
        query += f" LIMIT {pagination['page_size']} OFFSET {pagination['offset']}"

        balances = db.execute_query(query, params)

        return ListResponse(
            message=f"Retrieved {len(balances)} balance entries",
            data=balances,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"Error retrieving all balances: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving balances: {str(e)}")
