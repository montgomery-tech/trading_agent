"""
Order Request/Response Models for Kraken Trading System

This module provides comprehensive Pydantic models for order placement requests
and responses, ensuring type safety, validation, and documentation.

Task 3.2.B: Create Order Request/Response Models

File Location: src/trading_systems/exchanges/kraken/order_requests.py
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator

from .account_models import OrderSide, OrderType, OrderStatus


class TimeInForce(str, Enum):
    """Order time in force options."""
    GOOD_TILL_CANCELED = "GTC"  # Good Till Canceled (default)
    IMMEDIATE_OR_CANCEL = "IOC"  # Immediate Or Cancel
    FILL_OR_KILL = "FOK"  # Fill Or Kill


class OrderFlags(str, Enum):
    """Order flags for special handling."""
    POST_ONLY = "post"  # Post-only order (maker only)
    FCIQ = "fciq"  # Fee in quote currency
    FCIB = "fcib"  # Fee in base currency
    NOMPP = "nompp"  # No market price protection


class TriggerType(str, Enum):
    """Trigger types for conditional orders."""
    INDEX = "index"  # Index price trigger
    LAST = "last"  # Last price trigger


# ============================================================================
# BASE REQUEST MODELS
# ============================================================================

class BaseOrderRequest(BaseModel):
    """Base class for all order requests."""

    pair: str = Field(..., description="Trading pair (e.g., 'XBTUSD')")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    volume: Decimal = Field(..., gt=0, description="Order volume")

    # Optional fields
    userref: Optional[int] = Field(None, description="User reference ID")
    client_order_id: Optional[str] = Field(None, description="Client order ID", alias="cl_ord_id")
    validate_only: bool = Field(False, description="Validate order without placing")

    class Config:
        validate_by_name = True  # FIXED: Updated for Pydantic V2
        use_enum_values = True

    @validator('pair')
    def validate_pair(cls, v):
        """Validate trading pair format."""
        if not v or len(v) < 3:
            raise ValueError("Invalid trading pair")
        return v.upper()

    @validator('volume')
    def validate_volume(cls, v):
        """Validate order volume."""
        if v <= 0:
            raise ValueError("Order volume must be greater than 0")
        return v


class MarketOrderRequest(BaseOrderRequest):
    """Market order request model."""

    order_type: OrderType = Field(OrderType.MARKET, description="Order type (market)")

    # Market order specific fields
    time_in_force: Optional[TimeInForce] = Field(None, description="Time in force")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is market."""
        if v != OrderType.MARKET:
            raise ValueError("Order type must be 'market' for MarketOrderRequest")
        return v


class LimitOrderRequest(BaseOrderRequest):
    """Limit order request model."""

    order_type: OrderType = Field(OrderType.LIMIT, description="Order type (limit)")
    price: Decimal = Field(..., gt=0, description="Limit price")

    # Limit order specific fields
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.GOOD_TILL_CANCELED, description="Time in force")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    start_time: Optional[str] = Field(None, description="Scheduled start time")
    expire_time: Optional[str] = Field(None, description="Expiration time")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is limit."""
        if v != OrderType.LIMIT:
            raise ValueError("Order type must be 'limit' for LimitOrderRequest")
        return v

    @validator('price')
    def validate_price(cls, v):
        """Validate limit price."""
        if v <= 0:
            raise ValueError("Limit price must be greater than 0")
        return v


class StopLossOrderRequest(BaseOrderRequest):
    """Stop-loss order request model."""

    order_type: OrderType = Field(OrderType.STOP_LOSS, description="Order type (stop-loss)")
    price: Decimal = Field(..., gt=0, description="Stop price")  # FIXED: Use price instead of stop_price

    # Stop-loss specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is stop-loss."""
        if v != OrderType.STOP_LOSS:
            raise ValueError("Order type must be 'stop-loss' for StopLossOrderRequest")
        return v


class TakeProfitOrderRequest(BaseOrderRequest):
    """Take-profit order request model."""

    order_type: OrderType = Field(OrderType.TAKE_PROFIT, description="Order type (take-profit)")
    price: Decimal = Field(..., gt=0, description="Take profit price")  # FIXED: Use price instead of stop_price

    # Take-profit specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is take-profit."""
        if v != OrderType.TAKE_PROFIT:
            raise ValueError("Order type must be 'take-profit' for TakeProfitOrderRequest")
        return v


class StopLossLimitOrderRequest(BaseOrderRequest):
    """Stop-loss limit order request model."""

    order_type: OrderType = Field(OrderType.STOP_LOSS_LIMIT, description="Order type (stop-loss-limit)")
    price: Decimal = Field(..., gt=0, description="Stop price")
    price2: Decimal = Field(..., gt=0, description="Limit price")

    # Stop-loss limit specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is stop-loss-limit."""
        if v != OrderType.STOP_LOSS_LIMIT:
            raise ValueError("Order type must be 'stop-loss-limit' for StopLossLimitOrderRequest")
        return v


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class OrderDescription(BaseModel):
    """Order description from Kraken response."""

    pair: str = Field(..., description="Trading pair")
    type: str = Field(..., description="Order side")
    ordertype: str = Field(..., description="Order type")
    price: Optional[str] = Field(None, description="Price")
    price2: Optional[str] = Field(None, description="Secondary price")
    leverage: Optional[str] = Field(None, description="Leverage")
    order: str = Field(..., description="Order description text")
    close: Optional[str] = Field(None, description="Close order description")


class OrderPlacementResponse(BaseModel):
    """Response from order placement."""

    txid: List[str] = Field(..., description="Transaction IDs")
    descr: OrderDescription = Field(..., description="Order description")

    # Optional fields from response
    error: Optional[List[str]] = Field(None, description="Error messages")

    @property
    def order_id(self) -> str:
        """Get the primary order ID."""
        return self.txid[0] if self.txid else ""

    @property
    def is_successful(self) -> bool:
        """Check if order placement was successful."""
        return bool(self.txid and not self.error)


class OrderStatusResponse(BaseModel):
    """Response from order status query."""

    order_id: str = Field(..., description="Order ID")
    status: OrderStatus = Field(..., description="Order status")
    open_time: Optional[float] = Field(None, description="Open timestamp")
    close_time: Optional[float] = Field(None, description="Close timestamp")
    volume: Decimal = Field(..., description="Order volume")
    volume_executed: Decimal = Field(0, description="Executed volume")
    cost: Decimal = Field(0, description="Total cost")
    fee: Decimal = Field(0, description="Total fee")
    price: Optional[Decimal] = Field(None, description="Average price")
    stop_price: Optional[Decimal] = Field(None, description="Stop price")
    limit_price: Optional[Decimal] = Field(None, description="Limit price")
    misc: Optional[str] = Field(None, description="Miscellaneous info")
    order_flags: Optional[str] = Field(None, description="Order flags")

    @property
    def remaining_volume(self) -> Decimal:
        """Calculate remaining volume."""
        return self.volume - self.volume_executed

    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        if self.volume == 0:
            return 0.0
        return float(self.volume_executed / self.volume * 100)


class OpenOrdersResponse(BaseModel):
    """Response from open orders query."""

    open: Dict[str, Dict[str, Any]] = Field(..., description="Open orders")

    def get_orders(self) -> List[OrderStatusResponse]:
        """Convert to list of OrderStatusResponse objects."""
        orders = []
        for order_id, order_data in self.open.items():
            try:
                order = OrderStatusResponse(
                    order_id=order_id,
                    **order_data
                )
                orders.append(order)
            except Exception as e:
                # Log error but continue processing other orders
                continue
        return orders


class ClosedOrdersResponse(BaseModel):
    """Response from closed orders query."""

    closed: Dict[str, Dict[str, Any]] = Field(..., description="Closed orders")
    count: Optional[int] = Field(None, description="Total count")

    def get_orders(self) -> List[OrderStatusResponse]:
        """Convert to list of OrderStatusResponse objects."""
        orders = []
        for order_id, order_data in self.closed.items():
            try:
                order = OrderStatusResponse(
                    order_id=order_id,
                    **order_data
                )
                orders.append(order)
            except Exception as e:
                # Log error but continue processing other orders
                continue
        return orders


class OrderCancellationResponse(BaseModel):
    """Response from order cancellation."""

    count: int = Field(..., description="Number of orders canceled")
    pending: Optional[List[str]] = Field(None, description="Pending cancellations")

    @property
    def is_successful(self) -> bool:
        """Check if cancellation was successful."""
        return self.count > 0


# ============================================================================
# UTILITY MODELS
# ============================================================================

class OrderValidationResult(BaseModel):
    """Result of order validation."""

    is_valid: bool = Field(..., description="Whether order is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    sanitized_data: Optional[Dict[str, Any]] = Field(None, description="Sanitized order data")


class BatchOrderRequest(BaseModel):
    """Request for placing multiple orders."""

    orders: List[Union[MarketOrderRequest, LimitOrderRequest]] = Field(
        ...,
        description="List of orders to place",
        max_items=100  # Kraken's typical batch limit
    )
    fail_on_first_error: bool = Field(True, description="Stop on first error")

    @validator('orders')
    def validate_orders_not_empty(cls, v):
        """Ensure at least one order in batch."""
        if not v:
            raise ValueError("Batch must contain at least one order")
        return v


class BatchOrderResponse(BaseModel):
    """Response from batch order placement."""

    successful: List[OrderPlacementResponse] = Field(
        default_factory=list,
        description="Successfully placed orders"
    )
    failed: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Failed order attempts"
    )

    @property
    def success_count(self) -> int:
        """Number of successful orders."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed orders."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_market_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    **kwargs
) -> MarketOrderRequest:
    """
    Create a market order request.

    Args:
        pair: Trading pair
        side: Order side (buy/sell)
        volume: Order volume
        **kwargs: Additional order parameters

    Returns:
        MarketOrderRequest instance
    """
    return MarketOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        **kwargs
    )


def create_limit_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    price: Union[str, Decimal],
    **kwargs
) -> LimitOrderRequest:
    """
    Create a limit order request.

    Args:
        pair: Trading pair
        side: Order side (buy/sell)
        volume: Order volume
        price: Limit price
        **kwargs: Additional order parameters

    Returns:
        LimitOrderRequest instance
    """
    return LimitOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        price=Decimal(str(price)),
        **kwargs
    )


def create_stop_loss_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    stop_price: Union[str, Decimal],
    **kwargs
) -> StopLossOrderRequest:
    """
    Create a stop-loss order request.

    Args:
        pair: Trading pair
        side: Order side (buy/sell)
        volume: Order volume
        stop_price: Stop price
        **kwargs: Additional order parameters

    Returns:
        StopLossOrderRequest instance
    """
    return StopLossOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        price=Decimal(str(stop_price)),  # FIXED: Use price field
        **kwargs
    )


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_order_request(request: BaseOrderRequest) -> OrderValidationResult:
    """
    Validate an order request.

    Args:
        request: Order request to validate

    Returns:
        OrderValidationResult with validation details
    """
    errors = []
    warnings = []

    try:
        # Basic validation through Pydantic
        request.model_dump()  # FIXED: Use model_dump instead of dict()

        # Additional business logic validation
        if request.volume > Decimal('1000000'):
            warnings.append("Large order volume detected")

        # Price validation for limit orders
        if isinstance(request, LimitOrderRequest):
            if request.price > request.volume * Decimal('1000000'):
                warnings.append("Very high price relative to volume")

        return OrderValidationResult(
            is_valid=True,
            errors=errors,
            warnings=warnings,
            sanitized_data=request.model_dump()  # FIXED: Use model_dump instead of dict()
        )

    except Exception as e:
        errors.append(str(e))
        return OrderValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings
        )


def sanitize_order_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize order data for API submission.

    Args:
        data: Raw order data

    Returns:
        Sanitized order data
    """
    sanitized = {}

    # Map common field names
    field_mapping = {
        'side': 'type',
        'order_type': 'ordertype',
        'stop_price': 'price',
        'limit_price': 'price2',
        'client_order_id': 'cl_ord_id'
    }

    for key, value in data.items():
        if value is not None:
            # Use mapped field name if available
            api_key = field_mapping.get(key, key)

            # Convert Decimal to string
            if isinstance(value, Decimal):
                sanitized[api_key] = str(value)
            # Convert enums to values - ENHANCED HANDLING
            elif hasattr(value, 'value'):
                sanitized[api_key] = value.value
            elif hasattr(value, 'name') and hasattr(value, '__class__'):
                # Handle enum instances
                sanitized[api_key] = str(value.value if hasattr(value, 'value') else value)
            # Convert lists to comma-separated strings - ENHANCED HANDLING
            elif isinstance(value, list):
                if value:  # Only process non-empty lists
                    string_items = []
                    for item in value:
                        if hasattr(item, 'value'):
                            string_items.append(item.value)
                        elif hasattr(item, 'name'):
                            string_items.append(item.name.lower())
                        else:
                            string_items.append(str(item))
                    sanitized[api_key] = ','.join(string_items)
            else:
                sanitized[api_key] = str(value)

    return sanitized
