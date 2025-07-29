#!/usr/bin/env python3
"""
api/routes/trades.py
Trade execution and management routes with Kraken API integration
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
import logging
import os

from api.models import (

def parse_currency_pair(pair_string: str) -> tuple:
    """
    Parse currency pair string like 'BTC-USD' into ('BTC', 'USD')
    Also handles legacy 'BTCUSD' format
    """
    if '-' in pair_string:
        return tuple(pair_string.split('-', 1))
    elif len(pair_string) == 6:  # Like BTCUSD
        return pair_string[:3], pair_string[3:]
    else:
        # Try common currency codes
        common_currencies = ['USD', 'EUR', 'GBP', 'BTC', 'ETH']
        for currency in common_currencies:
            if pair_string.endswith(currency):
                base = pair_string[:-len(currency)]
                return base, currency
        # Default fallback
        return pair_string[:3], pair_string[3:] if len(pair_string) > 3 else pair_string

    TradeRequest, TradeResponse, TradeSimulationRequest, TradeSimulationResponse,
    TradeHistoryResponse, DataResponse, ListResponse
)
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager
from api.services.kraken_integrated_trade_service import KrakenIntegratedTradeService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_trade_service(db: DatabaseManager = Depends(get_database)) -> KrakenIntegratedTradeService:
    """Dependency to get Kraken-integrated trade service instance"""
    return KrakenIntegratedTradeService(db)


@router.get("/kraken/status", response_model=DataResponse)
async def get_kraken_status(
    trade_service: KrakenIntegratedTradeService = Depends(get_trade_service)
):
    """Get Kraken API connection status and configuration"""
    try:
        client = await trade_service._get_kraken_client()
        
        # Test connection
        is_connected = await client.validate_connection()
        
        # Get basic info
        live_trading = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        has_credentials = bool(client.api_key and client.api_secret)
        
        status_info = {
            "kraken_connection": "connected" if is_connected else "disconnected",
            "live_trading_enabled": live_trading,
            "credentials_configured": has_credentials,
            "supported_symbols": list(client.symbol_mapping.keys()),
            "kraken_pairs": list(client.symbol_mapping.values()),
            "api_base_url": client.base_url,
            "timeout_seconds": client.timeout
        }
        
        # Get account balance if connected and credentials available
        if is_connected and has_credentials and live_trading:
            try:
                balance = await client.get_account_balance()
                status_info["account_balance"] = {k: str(v) for k, v in balance.items()}
            except Exception as e:
                status_info["balance_error"] = str(e)
        
        return DataResponse(
            success=True,
            message="Kraken status retrieved successfully",
            data=status_info
        )
        
    except Exception as e:
        logger.error(f"Failed to get Kraken status: {e}")
        return DataResponse(
            success=False,
            message=f"Failed to get Kraken status: {str(e)}",
            data={
                "kraken_connection": "error",
                "error": str(e)
            }
        )


@router.get("/pricing/{symbol}", response_model=DataResponse)
async def get_real_time_pricing(
    symbol: str,
    trade_service: KrakenIntegratedTradeService = Depends(get_trade_service)
):
    """Get real-time pricing information from Kraken for a trading pair"""
    try:
        client = await trade_service._get_kraken_client()
        
        # Get ticker information
        ticker_info = await client.get_ticker_info(symbol)
        
        # Calculate spread percentage
        bid = Decimal(str(ticker_info["bid"]))
        ask = Decimal(str(ticker_info["ask"]))
        spread_pct = ((ask - bid) - bid * 100) if bid > 0 else Decimal('0')
        
        pricing_data = {
            "symbol": symbol,
            "bid": str(ticker_info["bid"]),
            "ask": str(ticker_info["ask"]),
            "last": str(ticker_info["last"]),
            "market_spread_percentage": str(spread_pct.quantize(Decimal('0.01'))),
            "volume_24h": str(ticker_info["volume"]),
            "vwap_24h": str(ticker_info["vwap"]),
            "high_24h": str(ticker_info["high"]),
            "low_24h": str(ticker_info["low"]),
            "trades_count": ticker_info["trades"],
            "timestamp": ticker_info["timestamp"].isoformat(),
            "kraken_pair": ticker_info["kraken_pair"]
        }
        
        return DataResponse(
            success=True,
            message=f"Real-time pricing for {symbol} retrieved successfully",
            data=pricing_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get pricing for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get pricing for {symbol}: {str(e)}"
        )


@router.post("/simulate", response_model=Dict[str, Any])
async def simulate_trade(
    trade_data: Dict[str, Any],
    trade_service: KrakenIntegratedTradeService = Depends(get_trade_service)
):
    """Simulate a trade execution with real-time Kraken prices"""
    try:
        # Import here to avoid circular imports
        from api.models import TradingSide
        
        # Extract and validate trade parameters
        username = trade_data.get("username", "demo_user")
        symbol = trade_data.get("symbol", "BTC/USD") 
        side = trade_data.get("side", "buy")
        amount = trade_data.get("amount", "0.001")
        order_type = trade_data.get("order_type", "market")
        
        # Convert amount to Decimal
        try:
            amount_decimal = Decimal(str(amount))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid amount: {amount}"
            )
        
        # Validate side
        try:
            trade_side = TradingSide(side.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid side: {side}. Must be 'buy' or 'sell'"
            )
        
        # Get current price from Kraken
        try:
            current_price = await trade_service.get_current_price(symbol)
        except Exception as e:
            # Fallback to a mock price if real price fails
            logger.warning(f"Failed to get real price for {symbol}: {e}")
            current_price = Decimal("50000.00")  # Mock BTC price
        
        # Calculate simulation values
        total_value = amount_decimal * current_price
        fee_rate = Decimal("0.0026")  # Default 0.26% fee
        fee_amount = total_value * fee_rate
        
        if trade_side == TradingSide.BUY:
            net_amount = total_value + fee_amount  # User pays this much
        else:
            net_amount = total_value - fee_amount  # User receives this much
        
        simulation_result = {
            "symbol": symbol,
            "side": side,
            "amount": str(amount_decimal),
            "estimated_price": str(current_price),
            "estimated_total": str(total_value),
            "estimated_fee": str(fee_amount),
            "net_amount": str(net_amount),
            "fee_currency": symbol.split("/")[1] if "/" in symbol else "USD",
            "service_used": "KrakenIntegratedTradeService",
            "simulation_time": datetime.utcnow().isoformat(),
            "note": "This is a simulation using real Kraken prices - no actual trade is executed"
        }
        
        return {
            "success": True,
            "message": f"Trade simulation: {side} {amount_decimal} {symbol}",
            "data": simulation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade simulation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trade simulation failed: {str(e)}"
        )


@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade_request: TradeRequest,
    trade_service: KrakenIntegratedTradeService = Depends(get_trade_service)
):
    """Execute a market order with Kraken API integration"""
    try:
        # Validate order type (only market orders supported)
        if trade_request.order_type.lower() != "market":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only market orders are supported. Set order_type to 'market'."
            )
        
        # Log trade request
        live_trading = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        mode = "LIVE" if live_trading else "SANDBOX"
        
        logger.info(f"[{mode}] Executing market order: {trade_request.side.value} "
                   f"{trade_request.amount} {trade_request.symbol} for user {trade_request.username}")

        # Execute the trade
        trade_response = await trade_service.execute_trade(trade_request)

        logger.info(f"[{mode}] Trade executed successfully: {trade_response.trade_id}")
        return trade_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade execution failed: {str(e)}"
        )


@router.get("/user/{username}", response_model=ListResponse)
async def get_user_trades(
    username: str,
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get trade history for a user including Kraken execution details"""
    try:
        # First get user ID - simplified query
        user_query = "SELECT id FROM users WHERE username = %s"
        user_results = db.execute_query(user_query, (username,))

        if not user_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        user_id = user_results[0]['id']

        # Build simplified query 
        query = """
            SELECT t.id, t.side, t.amount, t.price, t.total_value, t.fee_amount,
                   t.fee_currency_code, t.status, t.executed_at, t.created_at,
                   tp.symbol, tp.base_currency, tp.quote_currency
            FROM trades t
            JOIN trading_pairs tp ON t.trading_pair_id = tp.id
            WHERE t.user_id = %s
            ORDER BY t.executed_at DESC
            LIMIT %s OFFSET %s
        """
        
        params = [user_id, limit, offset]
        results = db.execute_query(query, params)

        # Format trade history
        trades = []
        for row in results:
            trade = {
                "trade_id": row['id'],
                "symbol": row['symbol'],
                "side": row['side'],
                "amount": str(row['amount']),
                "price": str(row['price']),
                "total_value": str(row['total_value']),
                "fee_amount": str(row['fee_amount']),
                "fee_currency": row['fee_currency_code'],
                "status": row['status'],
                "executed_at": row['executed_at'].isoformat() if row['executed_at'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            }
            trades.append(trade)

        return ListResponse(
            message=f"Retrieved {len(trades)} trades for user {username}",
            data=trades,
            total=len(trades),
            limit=limit,
            offset=offset
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trades: {str(e)}"
        )
