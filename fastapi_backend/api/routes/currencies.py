# ============================================================================
# api/routes/currencies.py
# ============================================================================

"""
Currency management routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from api.models import CurrencyResponse, ListResponse, DataResponse
from api.dependencies import get_database
from api.database import DatabaseManager
import logging
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ListResponse)
async def get_currencies(
    active_only: bool = True,
    fiat_only: Optional[bool] = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get list of available currencies"""
    try:
        query = "SELECT code, name, symbol, decimal_places, is_fiat, is_active FROM currencies"
        params = []
        conditions = []

        if active_only:
            conditions.append("is_active = 1")

        if fiat_only is not None:
            conditions.append("is_fiat = ?")
            params.append(1 if fiat_only else 0)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY is_fiat DESC, code"

        currencies = db.execute_query(query, params)

        response_currencies = []
        for currency in currencies:
            response_currencies.append(CurrencyResponse(
                code=currency['code'],
                name=currency['name'],
                symbol=currency['symbol'],
                decimal_places=currency['decimal_places'],
                is_fiat=currency['is_fiat'],
                is_active=currency['is_active']
            ))

        return ListResponse(
            message=f"Retrieved {len(response_currencies)} currencies",
            data=response_currencies
        )

    except Exception as e:
        logger.error(f"Error retrieving currencies: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving currencies: {str(e)}")


@router.get("/{currency_code}", response_model=DataResponse)
async def get_currency(
    currency_code: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get specific currency details"""
    try:
        query = """
            SELECT code, name, symbol, decimal_places, is_fiat, is_active,
                   created_at, updated_at
            FROM currencies
            WHERE code = %s
        """ if db.db_type == "postgresql" else """
            SELECT code, name, symbol, decimal_places, is_fiat, is_active,
                   created_at, updated_at
            FROM currencies
            WHERE code = ?
        """

        results = db.execute_query(query, (currency_code.upper(),))

        if not results:
            raise HTTPException(status_code=404, detail=f"Currency '{currency_code}' not found")

        return DataResponse(
            message=f"Retrieved currency {currency_code}",
            data=results[0]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving currency: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving currency: {str(e)}")
