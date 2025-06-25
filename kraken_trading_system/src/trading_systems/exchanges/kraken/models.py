"""
Kraken-specific data models and message structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class KrakenMessageType(str, Enum):
    """Kraken WebSocket message types."""
    SYSTEM_STATUS = "systemStatus"
    SUBSCRIPTION_STATUS = "subscriptionStatus"
    HEARTBEAT = "heartbeat"
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


class KrakenChannelName(str, Enum):
    """Kraken WebSocket channel names."""
    TICKER = "ticker"
    OHLC = "ohlc"
    TRADE = "trade"
    BOOK = "book"
    SPREAD = "spread"
    OWN_TRADES = "ownTrades"
    OPEN_ORDERS = "openOrders"


class SubscriptionStatus(str, Enum):
    """WebSocket subscription status."""
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    ERROR = "error"


class SystemStatus(str, Enum):
    """Kraken system status."""
    ONLINE = "online"
    MAINTENANCE = "maintenance"
    CANCEL_ONLY = "cancel_only"
    POST_ONLY = "post_only"


class KrakenSystemStatusMessage(BaseModel):
    """Kraken system status message."""
    connectionID: int
    event: str = Field(..., regex="^systemStatus$")
    status: SystemStatus
    version: str


class KrakenSubscription(BaseModel):
    """Kraken subscription configuration."""
    name: KrakenChannelName
    interval: Optional[int] = None  # For OHLC
    depth: Optional[int] = None  # For orderbook
    ratecounter: Optional[bool] = None
    snapshot: Optional[bool] = None
    token: Optional[str] = None  # For private channels


class KrakenSubscribeMessage(BaseModel):
    """Kraken subscribe message."""
    event: str = Field("subscribe", regex="^subscribe$")
    pair: Optional[List[str]] = None
    subscription: KrakenSubscription
    reqid: Optional[int] = None


class KrakenUnsubscribeMessage(BaseModel):
    """Kraken unsubscribe message."""
    event: str = Field("unsubscribe", regex="^unsubscribe$")
    pair: Optional[List[str]] = None
    subscription: KrakenSubscription
    reqid: Optional[int] = None


class KrakenSubscriptionStatusMessage(BaseModel):
    """Kraken subscription status message."""
    channelID: Optional[int] = None
    channelName: Optional[str] = None
    event: str = Field(..., regex="^subscriptionStatus$")
    pair: Optional[str] = None
    reqid: Optional[int] = None
    status: SubscriptionStatus
    subscription: KrakenSubscription
    errorMessage: Optional[str] = None


class KrakenHeartbeatMessage(BaseModel):
    """Kraken heartbeat message."""
    event: str = Field(..., regex="^heartbeat$")


class KrakenPingMessage(BaseModel):
    """Kraken ping message."""
    event: str = Field("ping", regex="^ping$")
    reqid: Optional[int] = None


class KrakenPongMessage(BaseModel):
    """Kraken pong message."""
    event: str = Field(..., regex="^pong$")
    reqid: Optional[int] = None


class KrakenTickerData(BaseModel):
    """Kraken ticker data structure."""
    a: List[str] = Field(..., description="Ask [price, whole_lot_volume, lot_volume]")
    b: List[str] = Field(..., description="Bid [price, whole_lot_volume, lot_volume]")
    c: List[str] = Field(..., description="Last trade closed [price, lot_volume]")
    v: List[str] = Field(..., description="Volume [today, last_24_hours]")
    p: List[str] = Field(..., description="Volume weighted average price [today, last_24_hours]")
    t: List[int] = Field(..., description="Number of trades [today, last_24_hours]")
    l: List[str] = Field(..., description="Low [today, last_24_hours]")
    h: List[str] = Field(..., description="High [today, last_24_hours]")
    o: List[str] = Field(..., description="Today's opening price [today, last_24_hours]")


class KrakenOHLCData(BaseModel):
    """Kraken OHLC data structure."""
    time: str = Field(..., description="Begin time of interval, in seconds since epoch")
    etime: str = Field(..., description="End time of interval, in seconds since epoch")
    open: str = Field(..., description="Open price of interval")
    high: str = Field(..., description="High price of interval")
    low: str = Field(..., description="Low price of interval")
    close: str = Field(..., description="Close price of interval")
    vwap: str = Field(..., description="Volume weighted average price of interval")
    volume: str = Field(..., description="Volume of interval")
    count: int = Field(..., description="Count of trades in interval")


class KrakenTradeData(BaseModel):
    """Kraken trade data structure."""
    price: str = Field(..., description="Price of trade")
    volume: str = Field(..., description="Volume of trade")
    time: str = Field(..., description="Time of trade")
    side: str = Field(..., description="Side of trade (buy/sell)")
    orderType: str = Field(..., description="Order type (market/limit)")
    misc: str = Field(..., description="Miscellaneous info")


class KrakenOrderBookLevel(BaseModel):
    """Single order book level."""
    price: str = Field(..., description="Price level")
    volume: str = Field(..., description="Volume at price level")
    timestamp: str = Field(..., description="Timestamp")
    
    @validator('price', 'volume')
    def validate_numeric_strings(cls, v):
        """Validate that price and volume are valid numeric strings."""
        try:
            float(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid numeric value: {v}")


class KrakenOrderBookData(BaseModel):
    """Kraken order book data structure."""
    asks: Optional[List[KrakenOrderBookLevel]] = None
    bids: Optional[List[KrakenOrderBookLevel]] = None
    checksum: Optional[int] = None


class KrakenSpreadData(BaseModel):
    """Kraken spread data structure."""
    bid: str = Field(..., description="Bid price")
    ask: str = Field(..., description="Ask price")
    timestamp: str = Field(..., description="Timestamp")
    bidVolume: str = Field(..., description="Bid volume")
    askVolume: str = Field(..., description="Ask volume")


class KrakenError(BaseModel):
    """Kraken error message structure."""
    errorMessage: str
    error: Optional[List[str]] = None


def parse_kraken_message(data: Dict[str, Any]) -> BaseModel:
    """
    Parse a Kraken WebSocket message into appropriate model.
    
    Args:
        data: Raw message data from WebSocket
        
    Returns:
        Parsed message as appropriate Pydantic model
        
    Raises:
        ValueError: If message format is not recognized
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}")
    
    # Check for error messages first
    if "errorMessage" in data:
        return KrakenError(**data)
    
    # Parse by event type
    event = data.get("event")
    
    if event == "systemStatus":
        return KrakenSystemStatusMessage(**data)
    elif event == "subscriptionStatus":
        return KrakenSubscriptionStatusMessage(**data)
    elif event == "heartbeat":
        return KrakenHeartbeatMessage(**data)
    elif event == "pong":
        return KrakenPongMessage(**data)
    else:
        # This might be market data (array format) or unknown message
        # For now, return the raw data
        # TODO: Implement market data parsing based on channel ID mapping
        raise ValueError(f"Unknown message type: {event or 'no_event'}")


def create_subscribe_message(
    channel: KrakenChannelName,
    pairs: Optional[List[str]] = None,
    interval: Optional[int] = None,
    depth: Optional[int] = None,
    reqid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a subscription message for Kraken WebSocket.
    
    Args:
        channel: Channel to subscribe to
        pairs: Trading pairs (not needed for some channels)
        interval: Interval for OHLC data
        depth: Depth for order book data
        reqid: Request ID for tracking
        
    Returns:
        Dictionary ready to send as JSON
    """
    subscription_config = {"name": channel.value}
    
    if interval is not None:
        subscription_config["interval"] = interval
    if depth is not None:
        subscription_config["depth"] = depth
    
    message = {
        "event": "subscribe",
        "subscription": subscription_config
    }
    
    if pairs:
        message["pair"] = pairs
    if reqid is not None:
        message["reqid"] = reqid
    
    return message


def create_unsubscribe_message(
    channel: KrakenChannelName,
    pairs: Optional[List[str]] = None,
    reqid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create an unsubscription message for Kraken WebSocket.
    
    Args:
        channel: Channel to unsubscribe from
        pairs: Trading pairs
        reqid: Request ID for tracking
        
    Returns:
        Dictionary ready to send as JSON
    """
    message = {
        "event": "unsubscribe",
        "subscription": {"name": channel.value}
    }
    
    if pairs:
        message["pair"] = pairs
    if reqid is not None:
        message["reqid"] = reqid
    
    return message
