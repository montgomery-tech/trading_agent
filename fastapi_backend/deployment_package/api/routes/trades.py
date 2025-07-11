#!/usr/bin/env python3
"""
api/routes/trades.py
Trade execution and management routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import logging

from api.models import (
    TradeRequest, TradeResponse, TradeSimulationRequest, TradeSimulationResponse,
    TradeHistoryResponse, DataResponse, ListResponse
)
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager
from api.services.trade_service import TradeService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_trade_service(db: DatabaseManager = Depends(get_database)) -> TradeService:
    """Dependency to get trade service instance"""
    return TradeService(db)


@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade_request: TradeRequest,
    trade_service: TradeService = Depends(get_trade_service)
):
    """
    Execute a trade order

    Args:
        trade_request: Trade execution request
        trade_service: Trade service dependency

    Returns:
        Trade execution response with details
    """
    try:
        logger.info(f"Executing trade: {trade_request.side.value} {trade_request.amount} {trade_request.symbol} for user {trade_request.username}")

        # Execute the trade
        trade_response = await trade_service.execute_trade(trade_request)

        logger.info(f"Trade executed successfully: {trade_response.trade_id}")
        return trade_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade execution failed: {str(e)}"
        )


@router.post("/simulate", response_model=TradeSimulationResponse)
async def simulate_trade(
    simulation_request: TradeSimulationRequest,
    trade_service: TradeService = Depends(get_trade_service)
):
    """
    Simulate a trade without executing it

    Args:
        simulation_request: Trade simulation request
        trade_service: Trade service dependency

    Returns:
        Trade simulation response with projected results
    """
    logger.info(f"Simulating trade: {simulation_request.side.value} {simulation_request.amount} {simulation_request.symbol}")

    # Convert simulation request to trade request
    trade_request = TradeRequest(
        username=simulation_request.username,
        symbol=simulation_request.symbol,
        side=simulation_request.side,
        amount=simulation_request.amount,
        price=simulation_request.price,
        order_type=simulation_request.order_type
    )

    # Simulate the trade (this will raise HTTPException for invalid user/pair)
    simulation_result = await trade_service.simulate_trade(trade_request)

    # Convert to response model
    return TradeSimulationResponse(
        success=simulation_result['success'],
        message=simulation_result['message'],
        symbol=simulation_result.get('symbol', simulation_request.symbol),
        side=simulation_result.get('side', simulation_request.side.value),
        amount=simulation_result.get('amount', simulation_request.amount),
        estimated_price=simulation_result.get('estimated_price', Decimal('0')),
        estimated_total=simulation_result.get('estimated_total', Decimal('0')),
        estimated_fee=simulation_result.get('estimated_fee', Decimal('0')),
        fee_currency=simulation_result.get('fee_currency', 'USD'),
        current_balances=simulation_result.get('current_balances', {}),
        projected_balances=simulation_result.get('projected_balances', {}),
        validation_errors=simulation_result.get('validation_errors', []),
        warnings=simulation_result.get('warnings', [])
    )


@router.get("/user/{username}", response_model=ListResponse)
async def get_user_trades(
    username: str,
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    status: Optional[str] = None,
    pagination: dict = Depends(get_pagination_params),
    db: DatabaseManager = Depends(get_database)
):
    """
    Get trade history for a user

    Args:
        username: Username to get trades for
        limit: Maximum number of trades to return
        offset: Number of trades to skip
        symbol: Optional filter by trading pair symbol
        side: Optional filter by trade side (buy/sell)
        status: Optional filter by trade status
        pagination: Pagination parameters
        db: Database manager dependency

    Returns:
        List of user's trades with pagination
    """
    try:
        # First get user ID
        user_query = "SELECT id FROM users WHERE username = ?"
        user_results = db.execute_query(user_query, (username,))

        if not user_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        user_id = user_results[0]['id']

        # Build query with optional filters
        query = """
            SELECT t.id, t.side, t.amount, t.price, t.total_value, t.fee_amount,
                   t.fee_currency_code, t.status, t.executed_at, t.created_at,
                   tp.symbol, tp.base_currency, tp.quote_currency
            FROM trades t
            JOIN trading_pairs tp ON t.trading_pair_id = tp.id
            WHERE t.user_id = ?
        """
        params = [user_id]

        # Add optional filters
        if symbol:
            query += " AND tp.symbol = ?"
            params.append(symbol.upper())

        if side:
            query += " AND t.side = ?"
            params.append(side.lower())

        if status:
            query += " AND t.status = ?"
            params.append(status.lower())

        # Add ordering and pagination
        query += " ORDER BY t.created_at DESC"
        query += f" LIMIT {pagination['page_size']} OFFSET {pagination['offset']}"

        # Execute query
        trades = db.execute_query(query, params)

        # Format response
        formatted_trades = []
        for trade in trades:
            formatted_trade = TradeHistoryResponse(
                trade_id=trade['id'],
                symbol=trade['symbol'],
                side=trade['side'],
                amount=Decimal(str(trade['amount'])),
                price=Decimal(str(trade['price'])),
                total_value=Decimal(str(trade['total_value'])),
                fee_amount=Decimal(str(trade['fee_amount'])),
                fee_currency=trade['fee_currency_code'],
                status=trade['status'],
                executed_at=trade['executed_at'],
                created_at=trade['created_at']
            )
            formatted_trades.append(formatted_trade.dict())

        return ListResponse(
            message=f"Retrieved {len(formatted_trades)} trades for user {username}",
            data=formatted_trades,
            pagination=pagination
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trades for user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trades: {str(e)}"
        )


@router.get("/stats/summary", response_model=DataResponse)
async def get_trade_statistics(
    username: Optional[str] = None,
    symbol: Optional[str] = None,
    days: int = 30,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get trade statistics and summary

    Args:
        username: Optional filter by username
        symbol: Optional filter by trading pair symbol
        days: Number of days to include in statistics (default 30)
        db: Database manager dependency

    Returns:
        Trade statistics summary
    """
    try:
        # Build base query
        base_query = """
            FROM trades t
            JOIN trading_pairs tp ON t.trading_pair_id = tp.id
            JOIN users u ON t.user_id = u.id
            WHERE t.created_at >= date('now', '-{} days')
        """.format(days)

        params = []

        # Add optional filters
        if username:
            base_query += " AND u.username = ?"
            params.append(username)

        if symbol:
            base_query += " AND tp.symbol = ?"
            params.append(symbol.upper())

        # Get statistics
        stats_query = f"""
            SELECT
                COUNT(*) as total_trades,
                COUNT(CASE WHEN t.side = 'buy' THEN 1 END) as buy_trades,
                COUNT(CASE WHEN t.side = 'sell' THEN 1 END) as sell_trades,
                COALESCE(SUM(t.total_value), 0) as total_volume,
                COALESCE(SUM(t.fee_amount), 0) as total_fees,
                COALESCE(AVG(t.total_value), 0) as avg_trade_size,
                COUNT(DISTINCT t.user_id) as unique_users,
                COUNT(DISTINCT tp.symbol) as unique_pairs
            {base_query}
        """

        stats_results = db.execute_query(stats_query, params)
        stats = stats_results[0] if stats_results else {}

        # Get top trading pairs
        top_pairs_query = f"""
            SELECT tp.symbol, COUNT(*) as trade_count, COALESCE(SUM(t.total_value), 0) as volume
            {base_query}
            GROUP BY tp.symbol
            ORDER BY volume DESC
            LIMIT 5
        """

        top_pairs = db.execute_query(top_pairs_query, params)

        # Format response
        statistics = {
            "period_days": days,
            "total_trades": stats.get('total_trades', 0),
            "buy_trades": stats.get('buy_trades', 0),
            "sell_trades": stats.get('sell_trades', 0),
            "total_volume": float(stats.get('total_volume', 0)),
            "total_fees": float(stats.get('total_fees', 0)),
            "average_trade_size": float(stats.get('avg_trade_size', 0)),
            "unique_users": stats.get('unique_users', 0),
            "unique_pairs": stats.get('unique_pairs', 0),
            "top_trading_pairs": [
                {
                    "symbol": pair['symbol'],
                    "trade_count": pair['trade_count'],
                    "volume": float(pair['volume'])
                }
                for pair in top_pairs
            ]
        }

        if username:
            statistics["filtered_by_user"] = username
        if symbol:
            statistics["filtered_by_symbol"] = symbol

        return DataResponse(
            message=f"Trade statistics for last {days} days",
            data=statistics
        )

    except Exception as e:
        logger.error(f"Error getting trade statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trade statistics: {str(e)}"
        )


@router.get("/", response_model=ListResponse)
async def list_all_trades(
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    status_filter: Optional[str] = None,
    pagination: dict = Depends(get_pagination_params),
    db: DatabaseManager = Depends(get_database)
):
    """
    List all trades (admin/monitoring endpoint)

    Args:
        symbol: Optional filter by trading pair symbol
        side: Optional filter by trade side (buy/sell)
        status_filter: Optional filter by trade status
        pagination: Pagination parameters
        db: Database manager dependency

    Returns:
        List of all trades with pagination
    """
    try:
        # Build query with optional filters
        query = """
            SELECT t.id, t.side, t.amount, t.price, t.total_value, t.fee_amount,
                   t.fee_currency_code, t.status, t.executed_at, t.created_at,
                   tp.symbol, tp.base_currency, tp.quote_currency, u.username
            FROM trades t
            JOIN trading_pairs tp ON t.trading_pair_id = tp.id
            JOIN users u ON t.user_id = u.id
            WHERE 1=1
        """
        params = []

        # Add optional filters
        if symbol:
            query += " AND tp.symbol = ?"
            params.append(symbol.upper())

        if side:
            query += " AND t.side = ?"
            params.append(side.lower())

        if status_filter:
            query += " AND t.status = ?"
            params.append(status_filter.lower())

        # Add ordering and pagination
        query += " ORDER BY t.created_at DESC"
        query += f" LIMIT {pagination['page_size']} OFFSET {pagination['offset']}"

        # Execute query
        trades = db.execute_query(query, params)

        # Format response
        formatted_trades = []
        for trade in trades:
            formatted_trade = {
                "trade_id": trade['id'],
                "username": trade['username'],
                "symbol": trade['symbol'],
                "side": trade['side'],
                "amount": float(trade['amount']),
                "price": float(trade['price']),
                "total_value": float(trade['total_value']),
                "fee_amount": float(trade['fee_amount']),
                "fee_currency": trade['fee_currency_code'],
                "status": trade['status'],
                "executed_at": trade['executed_at'],
                "created_at": trade['created_at']
            }
            formatted_trades.append(formatted_trade)

        return ListResponse(
            message=f"Retrieved {len(formatted_trades)} trades",
            data=formatted_trades,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"Error listing trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing trades: {str(e)}"
        )


@router.get("/{trade_id}", response_model=DataResponse)
async def get_trade_details(
    trade_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get detailed information about a specific trade

    Args:
        trade_id: Trade ID to get details for
        db: Database manager dependency

    Returns:
        Detailed trade information
    """
    try:
        query = """
            SELECT t.id, t.user_id, t.side, t.amount, t.price, t.total_value,
                   t.fee_amount, t.fee_currency_code, t.status, t.executed_at,
                   t.created_at, t.updated_at, t.base_transaction_id,
                   t.quote_transaction_id, t.fee_transaction_id,
                   tp.symbol, tp.base_currency, tp.quote_currency,
                   u.username
            FROM trades t
            JOIN trading_pairs tp ON t.trading_pair_id = tp.id
            JOIN users u ON t.user_id = u.id
            WHERE t.id = ?
        """

        results = db.execute_query(query, (trade_id,))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade '{trade_id}' not found"
            )

        trade = results[0]

        # Format detailed trade information
        trade_details = {
            "trade_id": trade['id'],
            "username": trade['username'],
            "symbol": trade['symbol'],
            "base_currency": trade['base_currency'],
            "quote_currency": trade['quote_currency'],
            "side": trade['side'],
            "amount": float(trade['amount']),
            "price": float(trade['price']),
            "total_value": float(trade['total_value']),
            "fee_amount": float(trade['fee_amount']),
            "fee_currency": trade['fee_currency_code'],
            "status": trade['status'],
            "executed_at": trade['executed_at'],
            "created_at": trade['created_at'],
            "updated_at": trade['updated_at'],
            "transactions": {
                "base_transaction_id": trade['base_transaction_id'],
                "quote_transaction_id": trade['quote_transaction_id'],
                "fee_transaction_id": trade['fee_transaction_id']
            }
        }

        return DataResponse(
            message=f"Retrieved trade details for {trade_id}",
            data=trade_details
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trade details for {trade_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving trade details: {str(e)}"
        )
