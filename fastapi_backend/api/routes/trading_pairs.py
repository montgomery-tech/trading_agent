#!/usr/bin/env python3
"""
api/routes/trading_pairs.py
Trading pairs management routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import logging

from api.models import DataResponse, ListResponse
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ListResponse)
async def get_trading_pairs(
    active_only: bool = True,
    base_currency: Optional[str] = None,
    quote_currency: Optional[str] = None,
    pagination: dict = Depends(get_pagination_params),
    db: DatabaseManager = Depends(get_database)
):
    """
    Get list of available trading pairs

    Args:
        active_only: Only return active trading pairs
        base_currency: Filter by base currency (e.g., 'BTC')
        quote_currency: Filter by quote currency (e.g., 'USD')
        pagination: Pagination parameters
        db: Database manager dependency

    Returns:
        List of trading pairs with metadata
    """
    try:
        query = """
            SELECT tp.id, tp.base_currency, tp.quote_currency, tp.symbol,
                   tp.min_trade_amount, tp.max_trade_amount, tp.price_precision,
                   tp.amount_precision, tp.is_active, tp.created_at, tp.updated_at,
                   bc.name as base_currency_name, bc.symbol as base_currency_symbol,
                   qc.name as quote_currency_name, qc.symbol as quote_currency_symbol,
                   bc.is_fiat as base_is_fiat, qc.is_fiat as quote_is_fiat
            FROM trading_pairs tp
            JOIN currencies bc ON tp.base_currency = bc.code
            JOIN currencies qc ON tp.quote_currency = qc.code
            WHERE 1=1
        """
        params = []

        if active_only:
            query += " AND tp.is_active = 1"

        if base_currency:
            query += " AND tp.base_currency = ?"
            params.append(base_currency.upper())

        if quote_currency:
            query += " AND tp.quote_currency = ?"
            params.append(quote_currency.upper())

        query += " ORDER BY tp.symbol"
        query += f" LIMIT {pagination['page_size']} OFFSET {pagination['offset']}"

        trading_pairs = db.execute_query(query, params)

        # Format the response data
        formatted_pairs = []
        for pair in trading_pairs:
            formatted_pair = {
                "id": pair['id'],
                "symbol": pair['symbol'],
                "base_currency": {
                    "code": pair['base_currency'],
                    "name": pair['base_currency_name'],
                    "symbol": pair['base_currency_symbol'],
                    "is_fiat": pair['base_is_fiat']
                },
                "quote_currency": {
                    "code": pair['quote_currency'],
                    "name": pair['quote_currency_name'],
                    "symbol": pair['quote_currency_symbol'],
                    "is_fiat": pair['quote_is_fiat']
                },
                "min_trade_amount": float(pair['min_trade_amount']) if pair['min_trade_amount'] else None,
                "max_trade_amount": float(pair['max_trade_amount']) if pair['max_trade_amount'] else None,
                "price_precision": pair['price_precision'],
                "amount_precision": pair['amount_precision'],
                "is_active": pair['is_active'],
                "created_at": pair['created_at'],
                "updated_at": pair['updated_at']
            }
            formatted_pairs.append(formatted_pair)

        return ListResponse(
            message=f"Retrieved {len(formatted_pairs)} trading pairs",
            data=formatted_pairs,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"Error retrieving trading pairs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trading pairs: {str(e)}"
        )


@router.get("/{base_currency}/{quote_currency}", response_model=DataResponse)
async def get_trading_pair(
    base_currency: str,
    quote_currency: str,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get specific trading pair by base and quote currency

    Args:
        base_currency: Base currency code (e.g., 'BTC')
        quote_currency: Quote currency code (e.g., 'USD')
        db: Database manager dependency

    Returns:
        Trading pair details with metadata
    """
    try:
        # Construct the symbol from base and quote currencies
        symbol = f"{base_currency.upper()}/{quote_currency.upper()}"

        query = """
            SELECT tp.id, tp.base_currency, tp.quote_currency, tp.symbol,
                   tp.min_trade_amount, tp.max_trade_amount, tp.price_precision,
                   tp.amount_precision, tp.is_active, tp.created_at, tp.updated_at,
                   bc.name as base_currency_name, bc.symbol as base_currency_symbol,
                   qc.name as quote_currency_name, qc.symbol as quote_currency_symbol,
                   bc.is_fiat as base_is_fiat, qc.is_fiat as quote_is_fiat
            FROM trading_pairs tp
            JOIN currencies bc ON tp.base_currency = bc.code
            JOIN currencies qc ON tp.quote_currency = qc.code
            WHERE tp.symbol = ?
        """

        results = db.execute_query(query, (symbol,))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading pair '{symbol}' not found"
            )

        pair = results[0]

        # Format the response data
        formatted_pair = {
            "id": pair['id'],
            "symbol": pair['symbol'],
            "base_currency": {
                "code": pair['base_currency'],
                "name": pair['base_currency_name'],
                "symbol": pair['base_currency_symbol'],
                "is_fiat": pair['base_is_fiat']
            },
            "quote_currency": {
                "code": pair['quote_currency'],
                "name": pair['quote_currency_name'],
                "symbol": pair['quote_currency_symbol'],
                "is_fiat": pair['quote_is_fiat']
            },
            "min_trade_amount": float(pair['min_trade_amount']) if pair['min_trade_amount'] else None,
            "max_trade_amount": float(pair['max_trade_amount']) if pair['max_trade_amount'] else None,
            "price_precision": pair['price_precision'],
            "amount_precision": pair['amount_precision'],
            "is_active": pair['is_active'],
            "created_at": pair['created_at'],
            "updated_at": pair['updated_at']
        }

        return DataResponse(
            message=f"Retrieved trading pair: {symbol}",
            data=formatted_pair
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trading pair '{base_currency}/{quote_currency}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trading pair: {str(e)}"
        )


@router.get("/{base_currency}/{quote_currency}/validate", response_model=DataResponse)
async def validate_trading_pair(
    base_currency: str,
    quote_currency: str,
    amount: Optional[Decimal] = None,
    db: DatabaseManager = Depends(get_database)
):
    """
    Validate a trading pair and optionally check trade amount constraints

    Args:
        base_currency: Base currency code (e.g., 'BTC')
        quote_currency: Quote currency code (e.g., 'USD')
        amount: Optional trade amount to validate
        db: Database manager dependency

    Returns:
        Validation result with constraints and status
    """
    try:
        # Construct the symbol from base and quote currencies
        symbol = f"{base_currency.upper()}/{quote_currency.upper()}"

        query = """
            SELECT tp.id, tp.base_currency, tp.quote_currency, tp.symbol,
                   tp.min_trade_amount, tp.max_trade_amount, tp.price_precision,
                   tp.amount_precision, tp.is_active
            FROM trading_pairs tp
            WHERE tp.symbol = ?
        """

        results = db.execute_query(query, (symbol,))

        if not results:
            return DataResponse(
                message=f"Trading pair '{symbol}' not found",
                data={
                    "is_valid": False,
                    "errors": [f"Trading pair '{symbol}' does not exist"],
                    "symbol": symbol
                }
            )

        pair = results[0]
        errors = []
        warnings = []

        # Check if pair is active
        if not pair['is_active']:
            errors.append(f"Trading pair '{symbol}' is not active")

        # Check amount constraints if provided
        if amount is not None:
            if pair['min_trade_amount'] and amount < pair['min_trade_amount']:
                errors.append(f"Trade amount {amount} is below minimum {pair['min_trade_amount']}")

            if pair['max_trade_amount'] and amount > pair['max_trade_amount']:
                errors.append(f"Trade amount {amount} exceeds maximum {pair['max_trade_amount']}")

        is_valid = len(errors) == 0

        validation_result = {
            "is_valid": is_valid,
            "symbol": pair['symbol'],
            "base_currency": pair['base_currency'],
            "quote_currency": pair['quote_currency'],
            "constraints": {
                "min_trade_amount": float(pair['min_trade_amount']) if pair['min_trade_amount'] else None,
                "max_trade_amount": float(pair['max_trade_amount']) if pair['max_trade_amount'] else None,
                "price_precision": pair['price_precision'],
                "amount_precision": pair['amount_precision'],
                "is_active": pair['is_active']
            },
            "errors": errors,
            "warnings": warnings
        }

        if amount is not None:
            validation_result["validated_amount"] = float(amount)

        return DataResponse(
            message=f"Validation result for trading pair: {symbol}",
            data=validation_result
        )

    except Exception as e:
        logger.error(f"Error validating trading pair '{base_currency}/{quote_currency}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating trading pair: {str(e)}"
        )
@router.get("/by-symbol/{symbol}", response_model=DataResponse)
async def get_trading_pair_by_symbol(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get specific trading pair by exact symbol (alternative endpoint)

    Args:
        symbol: Trading pair symbol with URL encoding (e.g., 'BTC%2FUSD' for 'BTC/USD')
        db: Database manager dependency

    Returns:
        Trading pair details with metadata
    """
    try:
        # URL decode the symbol (handles %2F for /)
        import urllib.parse
        decoded_symbol = urllib.parse.unquote(symbol).upper()

        query = """
            SELECT tp.id, tp.base_currency, tp.quote_currency, tp.symbol,
                   tp.min_trade_amount, tp.max_trade_amount, tp.price_precision,
                   tp.amount_precision, tp.is_active, tp.created_at, tp.updated_at,
                   bc.name as base_currency_name, bc.symbol as base_currency_symbol,
                   qc.name as quote_currency_name, qc.symbol as quote_currency_symbol,
                   bc.is_fiat as base_is_fiat, qc.is_fiat as quote_is_fiat
            FROM trading_pairs tp
            JOIN currencies bc ON tp.base_currency = bc.code
            JOIN currencies qc ON tp.quote_currency = qc.code
            WHERE tp.symbol = ?
        """

        results = db.execute_query(query, (decoded_symbol,))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading pair '{decoded_symbol}' not found"
            )

        pair = results[0]

        # Format the response data
        formatted_pair = {
            "id": pair['id'],
            "symbol": pair['symbol'],
            "base_currency": {
                "code": pair['base_currency'],
                "name": pair['base_currency_name'],
                "symbol": pair['base_currency_symbol'],
                "is_fiat": pair['base_is_fiat']
            },
            "quote_currency": {
                "code": pair['quote_currency'],
                "name": pair['quote_currency_name'],
                "symbol": pair['quote_currency_symbol'],
                "is_fiat": pair['quote_is_fiat']
            },
            "min_trade_amount": float(pair['min_trade_amount']) if pair['min_trade_amount'] else None,
            "max_trade_amount": float(pair['max_trade_amount']) if pair['max_trade_amount'] else None,
            "price_precision": pair['price_precision'],
            "amount_precision": pair['amount_precision'],
            "is_active": pair['is_active'],
            "created_at": pair['created_at'],
            "updated_at": pair['updated_at']
        }

        return DataResponse(
            message=f"Retrieved trading pair: {decoded_symbol}",
            data=formatted_pair
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trading pair by symbol '{symbol}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trading pair: {str(e)}"
        )
