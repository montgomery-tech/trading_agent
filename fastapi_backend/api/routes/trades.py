#!/usr/bin/env python3
"""
api/routes/trades.py
Trade execution and management routes - With Entity-Wide Access Control

Updated to allow traders to place trades for any user within their entity.
Viewers can view trade data but cannot place trades.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid
import logging

# Import response models
from api.models import DataResponse, ListResponse
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager
from api.updated_auth_dependencies import (
    require_entity_any_access,
    require_entity_trader_access,
    EntityAuthenticatedUser,
    get_user_accessible_entity_filter,
    validate_user_entity_access
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def get_trading_status(
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access())
):
    """Get trading system status - Available to viewers and traders"""
    try:
        return {
            "success": True,
            "message": "Trading system is operational",
            "data": {
                "status": "active",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "entity_aware_trade_service",
                "user_info": {
                    "username": current_user.username,
                    "role": current_user.role.value,
                    "entity_access": "admin" if current_user.role.value == 'admin' else "entity_member",
                    "accessible_entities": current_user.accessible_entities
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trading status: {str(e)}"
        )


@router.get("/user/{username}")
async def get_user_trades(
    username: str,
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    limit: int = 50,
    offset: int = 0,
    pair: Optional[str] = None,
    side: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get trades for a user within the current user's accessible entities.

    Both viewers and traders can access trade data for any user within their entity.
    """
    try:
        # Validate user entity access
        target_user_id, target_entity_id = await validate_user_entity_access(
            current_user, username, db
        )

        # Build trades query with entity filtering
        if db.db_type == 'postgresql':
            query = """
                SELECT t.id, t.pair, t.side, t.amount, t.price, t.total_value,
                       t.status, t.order_type, t.created_at, t.executed_at,
                       u.entity_id, u.username
                FROM trades t
                JOIN users u ON t.user_id = u.id
                WHERE t.user_id = %s
            """
            params = [target_user_id]

            if pair:
                query += " AND t.pair = %s"
                params.append(pair.upper())

            if side:
                query += " AND t.side = %s"
                params.append(side.lower())

            query += " ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        else:
            # SQLite
            query = """
                SELECT t.id, t.pair, t.side, t.amount, t.price, t.total_value,
                       t.status, t.order_type, t.created_at, t.executed_at,
                       u.entity_id, u.username
                FROM trades t
                JOIN users u ON t.user_id = u.id
                WHERE t.user_id = ?
            """
            params = [target_user_id]

            if pair:
                query += " AND t.pair = ?"
                params.append(pair.upper())

            if side:
                query += " AND t.side = ?"
                params.append(side.lower())

            query += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        trades = db.execute_query(query, params)

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"accessed {len(trades)} trades for user {username} in entity {target_entity_id}"
        )

        return {
            "success": True,
            "data": trades,
            "user": username,
            "entity_id": target_entity_id,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(trades)
            },
            "access_info": {
                "viewer_role": current_user.role.value,
                "entity_access": "admin" if current_user.role.value == 'admin' else "entity_member"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trades for user {username}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving trades: {str(e)}"
        )


@router.get("/")
async def get_entity_trades_summary(
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    limit: int = 100,
    offset: int = 0,
    pair: Optional[str] = None,
    side: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get trade summary for all users within the current user's accessible entities.

    This endpoint allows viewers and traders to see trade data for their entire entity.
    """
    try:
        # Build entity-filtered trades query
        if db.db_type == 'postgresql':
            query = """
                SELECT
                    t.id, t.pair, t.side, t.amount, t.price, t.total_value,
                    t.status, t.order_type, t.created_at, t.executed_at,
                    u.username, u.entity_id, e.name as entity_name
                FROM trades t
                JOIN users u ON t.user_id = u.id
                JOIN entities e ON u.entity_id = e.id
                WHERE u.is_active = %s
            """
            params = [True]

            if pair:
                query += " AND t.pair = %s"
                params.append(pair.upper())

            if side:
                query += " AND t.side = %s"
                params.append(side.lower())

            if status_filter:
                query += " AND t.status = %s"
                params.append(status_filter.lower())
        else:
            # SQLite
            query = """
                SELECT
                    t.id, t.pair, t.side, t.amount, t.price, t.total_value,
                    t.status, t.order_type, t.created_at, t.executed_at,
                    u.username, u.entity_id, e.name as entity_name
                FROM trades t
                JOIN users u ON t.user_id = u.id
                JOIN entities e ON u.entity_id = e.id
                WHERE u.is_active = ?
            """
            params = [1]

            if pair:
                query += " AND t.pair = ?"
                params.append(pair.upper())

            if side:
                query += " AND t.side = ?"
                params.append(side.lower())

            if status_filter:
                query += " AND t.status = ?"
                params.append(status_filter.lower())

        # Add entity filtering for non-admin users
        if current_user.role.value != 'admin':
            entity_filter, entity_params = await get_user_accessible_entity_filter(
                current_user, db, "u"
            )
            if entity_filter:
                query += f" AND {entity_filter}"
                params.extend(entity_params)

        query += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        trades = db.execute_query(query, params)

        # Group trades by entity
        entity_trades = {}
        for trade in trades:
            entity_id = trade['entity_id']

            if entity_id not in entity_trades:
                entity_trades[entity_id] = {
                    'entity_id': entity_id,
                    'entity_name': trade['entity_name'],
                    'trades': [],
                    'total_trades': 0
                }

            entity_trades[entity_id]['trades'].append({
                'id': trade['id'],
                'pair': trade['pair'],
                'side': trade['side'],
                'amount': trade['amount'],
                'price': trade['price'],
                'total_value': trade['total_value'],
                'status': trade['status'],
                'order_type': trade['order_type'],
                'username': trade['username'],
                'created_at': trade['created_at'],
                'executed_at': trade['executed_at']
            })
            entity_trades[entity_id]['total_trades'] += 1

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"accessed entity trade summary"
        )

        return {
            "success": True,
            "data": list(entity_trades.values()),
            "total_entities": len(entity_trades),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(trades)
            },
            "access_info": {
                "viewer_role": current_user.role.value,
                "accessible_entities": current_user.accessible_entities,
                "entity_access": "admin" if current_user.role.value == 'admin' else "entity_member"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving entity trade summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving entity trade summary: {str(e)}"
        )


@router.post("/place")
async def place_trade(
    trade_data: Dict[str, Any],
    current_user: EntityAuthenticatedUser = Depends(require_entity_trader_access()),
    db: DatabaseManager = Depends(get_database)
):
    """
    Place a trade for a user within the trader's entity.

    Only traders (and admins) can place trades.
    Traders can place trades for any user within their entity.
    """
    try:
        # Extract trade parameters
        username = trade_data.get('username')
        pair = trade_data.get('pair')
        side = trade_data.get('side')
        amount = trade_data.get('amount')
        order_type = trade_data.get('order_type', 'market')
        price = trade_data.get('price')  # For limit orders

        # Validate required fields
        if not all([username, pair, side, amount]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: username, pair, side, amount"
            )

        # Validate user entity access
        target_user_id, target_entity_id = await validate_user_entity_access(
            current_user, username, db
        )

        # Validate trade parameters
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid amount value"
            )

        # Validate side
        if side.lower() not in ['buy', 'sell']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid side: {side}. Must be 'buy' or 'sell'"
            )

        # Validate order type
        if order_type.lower() not in ['market', 'limit']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order_type: {order_type}. Must be 'market' or 'limit'"
            )

        # For limit orders, price is required
        if order_type.lower() == 'limit' and not price:
            raise HTTPException(
                status_code=400,
                detail="Price required for limit orders"
            )

        # Create trade ID
        trade_id = str(uuid.uuid4())

        # Calculate total value (simplified - in production you'd get market price)
        if price:
            try:
                price_decimal = Decimal(str(price))
                total_value = amount_decimal * price_decimal
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid price value"
                )
        else:
            # For market orders, use placeholder price (would get from market)
            price_decimal = Decimal("50000")  # Placeholder
            total_value = amount_decimal * price_decimal

        # Insert trade record
        if db.db_type == 'postgresql':
            insert_query = """
                INSERT INTO trades (id, user_id, pair, side, amount, price, total_value,
                                  status, order_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = (trade_id, target_user_id, pair.upper(), side.lower(),
                     str(amount_decimal), str(price_decimal), str(total_value),
                     'pending', order_type.lower())
        else:
            insert_query = """
                INSERT INTO trades (id, user_id, pair, side, amount, price, total_value,
                                  status, order_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """
            params = (trade_id, target_user_id, pair.upper(), side.lower(),
                     str(amount_decimal), str(price_decimal), str(total_value),
                     'pending', order_type.lower())

        db.execute_query(insert_query, params)

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"placed {side} trade {trade_id} for user {username} in entity {target_entity_id}: "
            f"{amount} {pair} @ {price_decimal}"
        )

        return {
            "success": True,
            "message": f"Trade placed successfully",
            "trade_id": trade_id,
            "user": username,
            "entity_id": target_entity_id,
            "trade_details": {
                "pair": pair.upper(),
                "side": side.lower(),
                "amount": str(amount_decimal),
                "price": str(price_decimal),
                "total_value": str(total_value),
                "order_type": order_type.lower(),
                "status": "pending"
            },
            "access_info": {
                "placed_by": current_user.username,
                "trader_role": current_user.role.value,
                "entity_access": "admin" if current_user.role.value == 'admin' else "entity_trader"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing trade: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error placing trade: {str(e)}"
        )


@router.post("/simulate")
async def simulate_trade(
    trade_data: Dict[str, Any],
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access())
):
    """
    Simulate a trade execution - Available to viewers and traders.

    This endpoint allows both viewers and traders to simulate trades
    without actually executing them.
    """
    try:
        # Extract trade parameters
        pair = trade_data.get("pair", "BTC/USD")
        side = trade_data.get("side", "buy")
        amount = trade_data.get("amount", "0.001")
        order_type = trade_data.get("order_type", "market")

        # Convert amount to Decimal for validation
        try:
            amount_decimal = Decimal(str(amount))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid amount: {amount}"
            )

        # Validate side
        if side.lower() not in ['buy', 'sell']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid side: {side}. Must be 'buy' or 'sell'"
            )

        # Simulate trade calculation
        simulated_price = Decimal("50000")  # Placeholder market price
        simulated_total = amount_decimal * simulated_price

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"simulated {side} trade: {amount} {pair}"
        )

        return {
            "success": True,
            "message": "Trade simulation completed",
            "simulation_results": {
                "pair": pair.upper(),
                "side": side.lower(),
                "amount": str(amount_decimal),
                "simulated_price": str(simulated_price),
                "simulated_total": str(simulated_total),
                "order_type": order_type.lower(),
                "timestamp": datetime.utcnow().isoformat()
            },
            "user_info": {
                "username": current_user.username,
                "role": current_user.role.value,
                "can_place_trades": current_user.role.value in ['admin', 'trader']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating trade: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error simulating trade: {str(e)}"
        )


@router.get("/pairs")
async def get_trading_pairs(
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    db: DatabaseManager = Depends(get_database)
):
    """
    Get available trading pairs - Available to viewers and traders.
    """
    try:
        # Get trading pairs from database (if table exists)
        try:
            query = "SELECT * FROM trading_pairs WHERE is_active = ? ORDER BY pair"
            pairs = db.execute_query(query, (1,))
        except:
            # If trading_pairs table doesn't exist, return default pairs
            pairs = [
                {"pair": "BTC/USD", "base": "BTC", "quote": "USD", "is_active": True},
                {"pair": "ETH/USD", "base": "ETH", "quote": "USD", "is_active": True},
                {"pair": "BTC/ETH", "base": "BTC", "quote": "ETH", "is_active": True}
            ]

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"accessed trading pairs list"
        )

        return {
            "success": True,
            "data": pairs,
            "total_pairs": len(pairs),
            "user_info": {
                "username": current_user.username,
                "role": current_user.role.value,
                "can_place_trades": current_user.role.value in ['admin', 'trader']
            }
        }

    except Exception as e:
        logger.error(f"Error retrieving trading pairs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving trading pairs: {str(e)}"
        )
