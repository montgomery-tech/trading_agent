#!/usr/bin/env python3
"""
api/routes/simple_trades.py
FIXED: Now actually places orders on Kraken when ENABLE_LIVE_TRADING=true
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
import logging
import os
import uuid
import asyncio

from api.models import TradeRequest, DataResponse
from api.dependencies import get_database
from api.database import DatabaseManager
from api.services.kraken_integrated_trade_service import KrakenIntegratedTradeService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_trade_service(db: DatabaseManager = Depends(get_database)) -> KrakenIntegratedTradeService:
    """Dependency to get Kraken-integrated trade service instance"""
    return KrakenIntegratedTradeService(db)


@router.post("/execute-simple", response_model=DataResponse)
async def execute_trade_simple(
    trade_request: TradeRequest,
    trade_service: KrakenIntegratedTradeService = Depends(get_trade_service)
):
    """
    ENHANCED: Trade execution that actually places orders on Kraken
    """
    try:
        # Validate order type
        if trade_request.order_type.lower() != "market":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only market orders are supported"
            )

        live_trading = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        mode = "LIVE" if live_trading else "SANDBOX"

        logger.info(f"[{mode}] Executing trade: {trade_request.side.value} "
                   f"{trade_request.amount} {trade_request.symbol} for user {trade_request.username}")

        # Initialize execution variables
        execution_price = None
        kraken_order_ids = []
        kraken_execution_data = None
        actual_order_placed = False

        if live_trading:
            # PLACE ACTUAL ORDER ON KRAKEN
            try:
                logger.info(f"🚀 PLACING REAL ORDER ON KRAKEN!")
                logger.info(f"   Symbol: {trade_request.symbol}")
                logger.info(f"   Side: {trade_request.side.value}")
                logger.info(f"   Amount: {trade_request.amount}")

                # Get Kraken client and place order
                kraken_client = await trade_service._get_kraken_client()

                # Place market order directly
                order_result = await kraken_client.place_market_order(
                    trade_request.symbol,
                    trade_request.side.value,
                    trade_request.amount
                )

                if order_result.get("success"):
                    kraken_order_ids = order_result.get("order_ids", [])
                    actual_order_placed = True

                    logger.info(f"✅ KRAKEN ORDER PLACED SUCCESSFULLY!")
                    logger.info(f"   Order IDs: {kraken_order_ids}")

                    # Get execution price from order status
                    await asyncio.sleep(1)  # Wait for order to execute

                    try:
                        order_status = await kraken_client.get_order_status(kraken_order_ids)

                        # Extract execution price from order status
                        for order_id, order_data in order_status.items():
                            if "price" in order_data:
                                execution_price = Decimal(str(order_data["price"]))
                                break
                            elif "cost" in order_data and "vol_exec" in order_data:
                                # Calculate price from cost and volume
                                cost = Decimal(str(order_data["cost"]))
                                vol = Decimal(str(order_data["vol_exec"]))
                                if vol > 0:
                                    execution_price = cost / vol
                                break

                        kraken_execution_data = order_status

                    except Exception as e:
                        logger.warning(f"Could not get order status: {e}")
                        # Fallback to current price
                        execution_price = await trade_service.get_current_price(trade_request.symbol)

                else:
                    raise Exception(f"Order placement failed: {order_result}")

            except Exception as e:
                logger.error(f"❌ KRAKEN ORDER PLACEMENT FAILED: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to place order on Kraken: {str(e)}"
                )
        else:
            # Sandbox mode - just get current price
            logger.info(f"🧪 Sandbox mode - getting current price only")
            execution_price = await trade_service.get_current_price(trade_request.symbol)

        # If we still don't have execution price, get current price
        if execution_price is None:
            execution_price = await trade_service.get_current_price(trade_request.symbol)

        # Calculate trade details with spread markup
        amount = trade_request.amount
        total_value = amount * execution_price
        fee_rate = Decimal("0.0026")  # 0.26% fee
        fee_amount = total_value * fee_rate

        # Apply spread (2% markup)
        spread_rate = Decimal("0.02")  # 2% spread
        if trade_request.side.value.lower() == "buy":
            client_price = execution_price * (1 + spread_rate)
            client_total = amount * client_price + fee_amount
        else:
            client_price = execution_price * (1 - spread_rate)
            client_total = amount * client_price - fee_amount

        # Calculate profit
        spread_amount = abs(client_total - total_value - fee_amount)

        # Generate a trade ID
        trade_id = str(uuid.uuid4())

        # Create detailed response
        execution_result = {
            "trade_id": trade_id,
            "status": "executed" if actual_order_placed else "simulated",
            "symbol": trade_request.symbol,
            "side": trade_request.side.value,
            "amount": str(amount),
            "execution_price": str(execution_price),
            "client_price": str(client_price),
            "total_value": str(client_total),
            "fee_amount": str(fee_amount),
            "fee_currency": trade_request.symbol.split("-")[1] if "-" in trade_request.symbol else "USD",
            "spread_amount": str(spread_amount),
            "spread_percentage": "2.00%",
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat(),

            # KRAKEN EXECUTION DETAILS
            "kraken_execution": {
                "order_placed_on_kraken": actual_order_placed,
                "kraken_order_ids": kraken_order_ids,
                "kraken_execution_price": str(execution_price),
                "kraken_order_data": kraken_execution_data
            },

            "note": f"{'REAL ORDER PLACED ON KRAKEN EXCHANGE' if actual_order_placed else 'Sandbox mode - no actual order placed'}"
        }

        # Log the execution
        if actual_order_placed:
            logger.info(f"🎉 [{mode}] REAL KRAKEN ORDER EXECUTED!")
            logger.info(f"   Trade ID: {trade_id}")
            logger.info(f"   Kraken Order IDs: {kraken_order_ids}")
            logger.info(f"   Execution Price: ${execution_price}")
            logger.info(f"   Client Price: ${client_price}")
            logger.info(f"   Your Spread Profit: ${spread_amount}")
            logger.info(f"   🔍 CHECK YOUR KRAKEN ACCOUNT FOR THE ORDER!")
        else:
            logger.info(f"🧪 [{mode}] Simulated trade: {trade_id}")

        return DataResponse(
            success=True,
            message=f"{'KRAKEN ORDER EXECUTED' if actual_order_placed else 'Trade simulated'}: {trade_request.side.value} {amount} {trade_request.symbol}",
            data=execution_result
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade execution failed: {str(e)}"
        )


@router.get("/kraken-status")
async def get_kraken_status(
    trade_service: KrakenIntegratedTradeService = Depends(get_trade_service)
):
    """Check Kraken API connection status"""
    try:
        client = await trade_service._get_kraken_client()

        # Test connection
        is_connected = await client.validate_connection()

        live_trading = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        has_credentials = bool(client.api_key and client.api_secret)

        return {
            "kraken_connection": "connected" if is_connected else "disconnected",
            "live_trading_enabled": live_trading,
            "credentials_configured": has_credentials,
            "api_base_url": client.base_url,
            "ready_for_trading": is_connected and has_credentials and live_trading
        }

    except Exception as e:
        return {
            "kraken_connection": "error",
            "error": str(e),
            "live_trading_enabled": os.getenv("ENABLE_LIVE_TRADING", "false"),
            "ready_for_trading": False
        }
