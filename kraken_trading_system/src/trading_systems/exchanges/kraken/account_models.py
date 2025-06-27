"""
Kraken account data models for private WebSocket feeds.

This module defines Pydantic models for parsing and storing account data
from Kraken's private WebSocket feeds (ownTrades, openOrders, etc.).
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop-loss"
    TAKE_PROFIT = "take-profit"
    STOP_LOSS_LIMIT = "stop-loss-limit"
    TAKE_PROFIT_LIMIT = "take-profit-limit"
    SETTLE_POSITION = "settle-position"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class TradeType(str, Enum):
    """Trade type enumeration."""
    BUY = "buy"
    SELL = "sell"


class KrakenTrade(BaseModel):
    """
    Model for individual trade data from ownTrades feed.

    Represents a completed trade execution.
    """
    trade_id: str = Field(..., description="Unique trade identifier")
    order_id: str = Field(..., description="Order ID that generated this trade")
    pair: str = Field(..., description="Trading pair (e.g., 'XBT/USD')")
    time: datetime = Field(..., description="Trade execution time")
    type: TradeType = Field(..., description="Trade type (buy/sell)")
    order_type: OrderType = Field(..., description="Order type that generated trade")
    price: Decimal = Field(..., description="Trade execution price")
    volume: Decimal = Field(..., description="Trade volume")
    fee: Decimal = Field(..., description="Trade fee")
    fee_currency: str = Field(..., description="Fee currency")
    margin: Optional[Decimal] = Field(None, description="Margin used (if margin trade)")
    misc: Optional[str] = Field(None, description="Miscellaneous trade info")

    @validator('time', pre=True)
    def parse_time(cls, v):
        """Parse time from various formats."""
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        elif isinstance(v, str):
            try:
                return datetime.fromtimestamp(float(v))
            except ValueError:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v

    @validator('price', 'volume', 'fee', 'margin', pre=True)
    def parse_decimal(cls, v):
        """Parse decimal values from strings."""
        if v is None:
            return v
        return Decimal(str(v))


class KrakenOrder(BaseModel):
    """
    Model for order data from openOrders feed.

    Represents current order status and details.
    """
    order_id: str = Field(..., description="Unique order identifier")
    pair: str = Field(..., description="Trading pair (e.g., 'XBT/USD')")
    status: OrderStatus = Field(..., description="Current order status")
    type: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type (market/limit/etc)")
    volume: Decimal = Field(..., description="Order volume")
    volume_executed: Decimal = Field(0, description="Volume already executed")
    price: Optional[Decimal] = Field(None, description="Order price (for limit orders)")
    price2: Optional[Decimal] = Field(None, description="Secondary price (for stop orders)")
    leverage: Optional[str] = Field(None, description="Leverage ratio")
    order_flags: Optional[str] = Field(None, description="Order flags")
    start_time: Optional[datetime] = Field(None, description="Order start time")
    expire_time: Optional[datetime] = Field(None, description="Order expiration time")
    user_ref: Optional[int] = Field(None, description="User reference ID")
    last_update: datetime = Field(default_factory=datetime.now, description="Last update time")

    # Computed properties
    @property
    def volume_remaining(self) -> Decimal:
        """Calculate remaining volume to be executed."""
        return self.volume - self.volume_executed

    @property
    def fill_percentage(self) -> float:
        """Calculate percentage of order filled."""
        if self.volume == 0:
            return 0.0
        return float(self.volume_executed / self.volume * 100)

    @property
    def is_fully_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.volume_executed >= self.volume

    @validator('volume', 'volume_executed', 'price', 'price2', pre=True)
    def parse_decimal(cls, v):
        """Parse decimal values from strings."""
        if v is None or v == '':
            return None if v is None else Decimal('0')
        return Decimal(str(v))

    @validator('start_time', 'expire_time', pre=True)
    def parse_time(cls, v):
        """Parse time from various formats."""
        if v is None or v == '':
            return None
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        elif isinstance(v, str):
            try:
                return datetime.fromtimestamp(float(v))
            except ValueError:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v


class AccountBalance(BaseModel):
    """
    Model for account balance data.

    Represents current asset balances in the account.
    """
    currency: str = Field(..., description="Currency code (e.g., 'USD', 'XBT')")
    balance: Decimal = Field(..., description="Total balance")
    hold: Decimal = Field(0, description="Amount on hold (in orders)")
    available: Optional[Decimal] = Field(None, description="Available balance")
    last_update: datetime = Field(default_factory=datetime.now, description="Last update time")

    @property
    def available_balance(self) -> Decimal:
        """Calculate available balance if not provided."""
        if self.available is not None:
            return self.available
        return self.balance - self.hold

    @validator('balance', 'hold', 'available', pre=True)
    def parse_decimal(cls, v):
        """Parse decimal values from strings."""
        if v is None or v == '':
            return None if v is None else Decimal('0')
        return Decimal(str(v))


class AccountSnapshot(BaseModel):
    """
    Complete account state snapshot.

    Aggregates all account data for a point in time.
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="Snapshot timestamp")
    balances: Dict[str, AccountBalance] = Field(default_factory=dict, description="Currency balances")
    open_orders: Dict[str, KrakenOrder] = Field(default_factory=dict, description="Active orders")
    recent_trades: List[KrakenTrade] = Field(default_factory=list, description="Recent trades")

    def get_balance(self, currency: str) -> Optional[AccountBalance]:
        """Get balance for specific currency."""
        return self.balances.get(currency.upper())

    def get_order(self, order_id: str) -> Optional[KrakenOrder]:
        """Get order by ID."""
        return self.open_orders.get(order_id)

    def get_orders_for_pair(self, pair: str) -> List[KrakenOrder]:
        """Get all orders for a specific trading pair."""
        return [order for order in self.open_orders.values() if order.pair == pair]

    def get_recent_trades_for_pair(self, pair: str, limit: int = 10) -> List[KrakenTrade]:
        """Get recent trades for a specific trading pair."""
        pair_trades = [trade for trade in self.recent_trades if trade.pair == pair]
        return sorted(pair_trades, key=lambda t: t.time, reverse=True)[:limit]


def parse_own_trades_message(data: Dict[str, Any]) -> List[KrakenTrade]:
    """
    Parse ownTrades WebSocket message into KrakenTrade objects.

    Args:
        data: Raw ownTrades message from Kraken WebSocket

    Returns:
        List of parsed KrakenTrade objects
    """
    trades = []

    # Kraken ownTrades format: [channelID, trade_data, channelName, pair]
    if isinstance(data, list) and len(data) >= 2:
        trade_data = data[1]  # Second element contains trade data

        if isinstance(trade_data, dict):
            for trade_id, trade_info in trade_data.items():
                try:
                    # Parse individual trade
                    trade = KrakenTrade(
                        trade_id=trade_id,
                        order_id=trade_info.get('ordertxid', ''),
                        pair=trade_info.get('pair', ''),
                        time=trade_info.get('time', 0),
                        type=TradeType(trade_info.get('type', 'buy')),
                        order_type=OrderType(trade_info.get('ordertype', 'market')),
                        price=trade_info.get('price', '0'),
                        volume=trade_info.get('vol', '0'),
                        fee=trade_info.get('fee', '0'),
                        fee_currency=trade_info.get('fee_currency', 'USD'),
                        margin=trade_info.get('margin'),
                        misc=trade_info.get('misc')
                    )
                    trades.append(trade)
                except Exception as e:
                    # Log error but continue processing other trades
                    print(f"Error parsing trade {trade_id}: {e}")

    return trades


def parse_open_orders_message(data: Dict[str, Any]) -> List[KrakenOrder]:
    """
    Parse openOrders WebSocket message into KrakenOrder objects.

    Args:
        data: Raw openOrders message from Kraken WebSocket

    Returns:
        List of parsed KrakenOrder objects
    """
    orders = []

    # Kraken openOrders format: [channelID, order_data, channelName]
    if isinstance(data, list) and len(data) >= 2:
        order_data = data[1]  # Second element contains order data

        if isinstance(order_data, dict):
            for order_id, order_info in order_data.items():
                try:
                    # Parse individual order
                    descr = order_info.get('descr', {})

                    order = KrakenOrder(
                        order_id=order_id,
                        pair=descr.get('pair', ''),
                        status=OrderStatus(order_info.get('status', 'open')),
                        type=OrderSide(descr.get('type', 'buy')),
                        order_type=OrderType(descr.get('ordertype', 'market')),
                        volume=order_info.get('vol', '0'),
                        volume_executed=order_info.get('vol_exec', '0'),
                        price=descr.get('price'),
                        price2=descr.get('price2'),
                        leverage=descr.get('leverage'),
                        order_flags=order_info.get('oflags'),
                        start_time=order_info.get('starttm'),
                        expire_time=order_info.get('expiretm'),
                        user_ref=order_info.get('userref')
                    )
                    orders.append(order)
                except Exception as e:
                    # Log error but continue processing other orders
                    print(f"Error parsing order {order_id}: {e}")

    return orders
