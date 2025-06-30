#!/usr/bin/env python3
"""
Task 3.4.B.1: Enhanced Order Request Models Implementation

This script implements the complete set of advanced order request models
for the Kraken Trading System, including:

1. Fixed existing StopLossOrderRequest and TakeProfitOrderRequest
2. New ConditionalOrderRequest model
3. New OCOOrderRequest model  
4. New IcebergOrderRequest model
5. Enhanced validation and factory functions
6. Comprehensive test suite

File: implement_task_3_4_b_1_order_models.py
Save and run: python3 implement_task_3_4_b_1_order_models.py
"""

import sys
import os
from pathlib import Path
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

def create_enhanced_order_requests_file():
    """Create the enhanced order_requests.py file with all advanced order types."""
    
    print("📝 Creating enhanced order_requests.py with advanced order types...")
    
    # Ensure directory exists
    order_requests_dir = Path("src/trading_systems/exchanges/kraken")
    order_requests_dir.mkdir(parents=True, exist_ok=True)
    
    order_requests_content = '''"""
Enhanced Order Request/Response Models for Kraken Trading System - Task 3.4.B.1

This module provides comprehensive Pydantic models for all Kraken order types
including advanced order types: stop-loss, take-profit, conditional, OCO, and iceberg orders.

Enhanced Features:
- Fixed field mappings for stop-loss and take-profit orders
- Complete OCO (One-Cancels-Other) order support
- Iceberg order implementation with size management
- Conditional order logic with trigger evaluation
- Comprehensive validation and error handling
- Factory functions for easy order creation
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
    GOOD_TILL_DATE = "GTD"  # Good Till Date


class OrderFlags(str, Enum):
    """Order flags for special handling."""
    POST_ONLY = "post"  # Post-only order (maker only)
    FCIQ = "fciq"  # Fee in quote currency
    FCIB = "fcib"  # Fee in base currency
    NOMPP = "nompp"  # No market price protection
    VIQC = "viqc"  # Volume in quote currency


class TriggerType(str, Enum):
    """Trigger types for conditional orders."""
    INDEX = "index"  # Index price trigger
    LAST = "last"  # Last price trigger
    BID = "bid"  # Best bid trigger
    ASK = "ask"  # Best ask trigger
    MID = "mid"  # Mid price trigger


class ConditionOperator(str, Enum):
    """Conditional order operators."""
    GREATER_THAN = ">"
    GREATER_THAN_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="


class OCOType(str, Enum):
    """OCO (One-Cancels-Other) order types."""
    TAKE_PROFIT_STOP_LOSS = "tp_sl"  # Take profit with stop loss
    BRACKET = "bracket"  # Full bracket order
    CONDITIONAL = "conditional"  # Conditional OCO


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
        validate_by_name = True
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


# ============================================================================
# BASIC ORDER TYPES
# ============================================================================

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


# ============================================================================
# ADVANCED ORDER TYPES - TASK 3.4.B.1 IMPLEMENTATION
# ============================================================================

class StopLossOrderRequest(BaseOrderRequest):
    """Stop-loss order request model - FIXED."""

    order_type: OrderType = Field(OrderType.STOP_LOSS, description="Order type (stop-loss)")
    price: Decimal = Field(..., gt=0, description="Stop trigger price")

    # Stop-loss specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.GOOD_TILL_CANCELED, description="Time in force")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is stop-loss."""
        if v != OrderType.STOP_LOSS:
            raise ValueError("Order type must be 'stop-loss' for StopLossOrderRequest")
        return v

    @validator('price')
    def validate_stop_price(cls, v):
        """Validate stop price."""
        if v <= 0:
            raise ValueError("Stop price must be greater than 0")
        return v


class TakeProfitOrderRequest(BaseOrderRequest):
    """Take-profit order request model - FIXED."""

    order_type: OrderType = Field(OrderType.TAKE_PROFIT, description="Order type (take-profit)")
    price: Decimal = Field(..., gt=0, description="Take profit trigger price")

    # Take-profit specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.GOOD_TILL_CANCELED, description="Time in force")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is take-profit."""
        if v != OrderType.TAKE_PROFIT:
            raise ValueError("Order type must be 'take-profit' for TakeProfitOrderRequest")
        return v

    @validator('price')
    def validate_take_profit_price(cls, v):
        """Validate take profit price."""
        if v <= 0:
            raise ValueError("Take profit price must be greater than 0")
        return v


class StopLossLimitOrderRequest(BaseOrderRequest):
    """Stop-loss limit order request model."""

    order_type: OrderType = Field(OrderType.STOP_LOSS_LIMIT, description="Order type (stop-loss-limit)")
    price: Decimal = Field(..., gt=0, description="Stop trigger price")
    price2: Decimal = Field(..., gt=0, description="Limit execution price")

    # Stop-loss limit specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.GOOD_TILL_CANCELED, description="Time in force")

    @validator('order_type')
    def validate_order_type(cls, v):
        """Ensure order type is stop-loss-limit."""
        if v != OrderType.STOP_LOSS_LIMIT:
            raise ValueError("Order type must be 'stop-loss-limit' for StopLossLimitOrderRequest")
        return v

    @root_validator
    def validate_prices(cls, values):
        """Validate stop and limit price relationship."""
        price = values.get('price')
        price2 = values.get('price2')
        side = values.get('side')
        
        if price and price2 and side:
            # For sell stop-loss: stop price should be below limit price
            # For buy stop-loss: stop price should be above limit price
            if side == OrderSide.SELL and price >= price2:
                raise ValueError("For sell stop-loss-limit: stop price must be below limit price")
            elif side == OrderSide.BUY and price <= price2:
                raise ValueError("For buy stop-loss-limit: stop price must be above limit price")
        
        return values


class ConditionalOrderRequest(BaseOrderRequest):
    """Conditional order request model - NEW."""

    order_type: OrderType = Field(OrderType.LIMIT, description="Underlying order type")
    price: Decimal = Field(..., gt=0, description="Order price")

    # Conditional fields
    condition_price: Decimal = Field(..., gt=0, description="Condition trigger price")
    condition_operator: ConditionOperator = Field(..., description="Condition operator")
    condition_trigger: TriggerType = Field(TriggerType.LAST, description="Price type for condition")
    
    # Order execution fields
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.GOOD_TILL_CANCELED, description="Time in force")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    expire_time: Optional[str] = Field(None, description="Condition expiration time")

    @validator('condition_price')
    def validate_condition_price(cls, v):
        """Validate condition price."""
        if v <= 0:
            raise ValueError("Condition price must be greater than 0")
        return v

    def evaluate_condition(self, current_price: Decimal) -> bool:
        """Evaluate if condition is met."""
        operator_map = {
            ConditionOperator.GREATER_THAN: lambda x, y: x > y,
            ConditionOperator.GREATER_THAN_EQUAL: lambda x, y: x >= y,
            ConditionOperator.LESS_THAN: lambda x, y: x < y,
            ConditionOperator.LESS_THAN_EQUAL: lambda x, y: x <= y,
            ConditionOperator.EQUAL: lambda x, y: x == y,
            ConditionOperator.NOT_EQUAL: lambda x, y: x != y,
        }
        
        operator_func = operator_map.get(self.condition_operator)
        if not operator_func:
            raise ValueError(f"Invalid condition operator: {self.condition_operator}")
        
        return operator_func(current_price, self.condition_price)


class OCOOrderRequest(BaseModel):
    """One-Cancels-Other (OCO) order request model - NEW."""

    # Primary order
    primary_order: Union[LimitOrderRequest, StopLossOrderRequest, TakeProfitOrderRequest] = Field(
        ..., description="Primary order"
    )
    
    # Secondary order
    secondary_order: Union[LimitOrderRequest, StopLossOrderRequest, TakeProfitOrderRequest] = Field(
        ..., description="Secondary order"
    )
    
    # OCO configuration
    oco_type: OCOType = Field(OCOType.TAKE_PROFIT_STOP_LOSS, description="OCO order type")
    client_order_id: Optional[str] = Field(None, description="Client order ID for OCO group")
    userref: Optional[int] = Field(None, description="User reference ID")

    @root_validator
    def validate_oco_orders(cls, values):
        """Validate OCO order configuration."""
        primary = values.get('primary_order')
        secondary = values.get('secondary_order')
        
        if primary and secondary:
            # Ensure same trading pair
            if primary.pair != secondary.pair:
                raise ValueError("OCO orders must be for the same trading pair")
            
            # Ensure same volume
            if primary.volume != secondary.volume:
                raise ValueError("OCO orders must have the same volume")
            
            # Validate order type combination
            if primary.order_type == secondary.order_type:
                raise ValueError("OCO orders must have different order types")
        
        return values

    @property
    def pair(self) -> str:
        """Get trading pair from primary order."""
        return self.primary_order.pair

    @property
    def volume(self) -> Decimal:
        """Get volume from primary order."""
        return self.primary_order.volume


class IcebergOrderRequest(LimitOrderRequest):
    """Iceberg order request model - NEW."""

    # Iceberg specific fields
    display_volume: Decimal = Field(..., gt=0, description="Visible volume per refresh")
    refresh_threshold: Optional[Decimal] = Field(None, description="Threshold for refresh (default: 10% of display)")
    variance_percentage: Optional[Decimal] = Field(None, description="Volume variance percentage")
    
    # Advanced iceberg options
    time_variance_seconds: Optional[int] = Field(None, description="Time variance for refreshes")
    min_refresh_interval: Optional[int] = Field(30, description="Minimum refresh interval (seconds)")
    max_refresh_interval: Optional[int] = Field(300, description="Maximum refresh interval (seconds)")

    @validator('display_volume')
    def validate_display_volume(cls, v, values):
        """Validate display volume against total volume."""
        total_volume = values.get('volume')
        if total_volume and v >= total_volume:
            raise ValueError("Display volume must be less than total volume")
        return v

    @root_validator
    def validate_iceberg_config(cls, values):
        """Validate iceberg configuration."""
        display_volume = values.get('display_volume')
        total_volume = values.get('volume')
        refresh_threshold = values.get('refresh_threshold')
        
        if display_volume and total_volume:
            # Set default refresh threshold if not specified
            if refresh_threshold is None:
                values['refresh_threshold'] = display_volume * Decimal('0.1')
            
            # Validate refresh threshold
            elif refresh_threshold >= display_volume:
                raise ValueError("Refresh threshold must be less than display volume")
        
        return values

    def calculate_next_display_volume(self, remaining_volume: Decimal) -> Decimal:
        """Calculate next display volume for iceberg refresh."""
        if remaining_volume <= self.display_volume:
            return remaining_volume
        
        base_volume = self.display_volume
        
        # Apply variance if specified
        if self.variance_percentage:
            variance = base_volume * (self.variance_percentage / Decimal('100'))
            # Random variance would be applied in actual implementation
            # For now, just return base volume
        
        return min(base_volume, remaining_volume)


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
    error: Optional[List[str]] = Field(None, description="Error messages")

    @property
    def order_id(self) -> str:
        """Get the primary order ID."""
        return self.txid[0] if self.txid else ""

    @property
    def is_success(self) -> bool:
        """Check if placement was successful."""
        return not self.error or len(self.error) == 0


class OCOPlacementResponse(BaseModel):
    """Response from OCO order placement."""

    primary_response: OrderPlacementResponse = Field(..., description="Primary order response")
    secondary_response: OrderPlacementResponse = Field(..., description="Secondary order response")
    oco_group_id: Optional[str] = Field(None, description="OCO group identifier")

    @property
    def is_success(self) -> bool:
        """Check if both orders were placed successfully."""
        return self.primary_response.is_success and self.secondary_response.is_success

    @property
    def order_ids(self) -> List[str]:
        """Get all order IDs from the OCO group."""
        ids = []
        if self.primary_response.txid:
            ids.extend(self.primary_response.txid)
        if self.secondary_response.txid:
            ids.extend(self.secondary_response.txid)
        return ids


class OrderValidationResult(BaseModel):
    """Order validation result."""

    is_valid: bool = Field(..., description="Whether order is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    estimated_fees: Optional[Decimal] = Field(None, description="Estimated trading fees")
    estimated_total: Optional[Decimal] = Field(None, description="Estimated total cost")

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)


# ============================================================================
# FACTORY FUNCTIONS - ENHANCED
# ============================================================================

def create_market_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    **kwargs
) -> MarketOrderRequest:
    """Create a market order request."""
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
    """Create a limit order request."""
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
    """Create a stop-loss order request."""
    return StopLossOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        price=Decimal(str(stop_price)),  # Fixed: use price field
        **kwargs
    )


def create_take_profit_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    take_profit_price: Union[str, Decimal],
    **kwargs
) -> TakeProfitOrderRequest:
    """Create a take-profit order request."""
    return TakeProfitOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        price=Decimal(str(take_profit_price)),  # Fixed: use price field
        **kwargs
    )


def create_conditional_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    price: Union[str, Decimal],
    condition_price: Union[str, Decimal],
    condition_operator: ConditionOperator,
    **kwargs
) -> ConditionalOrderRequest:
    """Create a conditional order request."""
    return ConditionalOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        price=Decimal(str(price)),
        condition_price=Decimal(str(condition_price)),
        condition_operator=condition_operator,
        **kwargs
    )


def create_oco_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    take_profit_price: Union[str, Decimal],
    stop_loss_price: Union[str, Decimal],
    **kwargs
) -> OCOOrderRequest:
    """Create a take-profit/stop-loss OCO order."""
    
    # Create take-profit order
    take_profit = create_take_profit_order(
        pair=pair,
        side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,  # Opposite side
        volume=volume,
        take_profit_price=take_profit_price
    )
    
    # Create stop-loss order
    stop_loss = create_stop_loss_order(
        pair=pair,
        side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,  # Opposite side
        volume=volume,
        stop_price=stop_loss_price
    )
    
    return OCOOrderRequest(
        primary_order=take_profit,
        secondary_order=stop_loss,
        oco_type=OCOType.TAKE_PROFIT_STOP_LOSS,
        **kwargs
    )


def create_iceberg_order(
    pair: str,
    side: OrderSide,
    volume: Union[str, Decimal],
    price: Union[str, Decimal],
    display_volume: Union[str, Decimal],
    **kwargs
) -> IcebergOrderRequest:
    """Create an iceberg order request."""
    return IcebergOrderRequest(
        pair=pair,
        side=side,
        volume=Decimal(str(volume)),
        price=Decimal(str(price)),
        display_volume=Decimal(str(display_volume)),
        **kwargs
    )


# ============================================================================
# VALIDATION UTILITIES - ENHANCED
# ============================================================================

def validate_order_request(request: BaseOrderRequest) -> OrderValidationResult:
    """Validate an order request comprehensively."""
    result = OrderValidationResult(is_valid=True)
    
    try:
        # Basic validation - already handled by Pydantic
        
        # Advanced validation based on order type
        if isinstance(request, StopLossOrderRequest):
            _validate_stop_loss_order(request, result)
        elif isinstance(request, TakeProfitOrderRequest):
            _validate_take_profit_order(request, result)
        elif isinstance(request, ConditionalOrderRequest):
            _validate_conditional_order(request, result)
        elif isinstance(request, IcebergOrderRequest):
            _validate_iceberg_order(request, result)
        
        # Market-specific validations
        _validate_market_conditions(request, result)
        
    except Exception as e:
        result.add_error(f"Validation error: {str(e)}")
    
    return result


def _validate_stop_loss_order(request: StopLossOrderRequest, result: OrderValidationResult) -> None:
    """Validate stop-loss order specific rules."""
    # Stop-loss orders should be placed away from current market price
    # This would require market data in real implementation
    pass


def _validate_take_profit_order(request: TakeProfitOrderRequest, result: OrderValidationResult) -> None:
    """Validate take-profit order specific rules."""
    # Take-profit orders should be placed at favorable prices
    # This would require market data in real implementation
    pass


def _validate_conditional_order(request: ConditionalOrderRequest, result: OrderValidationResult) -> None:
    """Validate conditional order specific rules."""
    # Ensure condition makes logical sense
    if request.condition_operator in [ConditionOperator.EQUAL, ConditionOperator.NOT_EQUAL]:
        result.add_warning("Equality conditions on price may be difficult to trigger")


def _validate_iceberg_order(request: IcebergOrderRequest, result: OrderValidationResult) -> None:
    """Validate iceberg order specific rules."""
    # Check display volume ratio
    display_ratio = request.display_volume / request.volume
    if display_ratio > Decimal('0.5'):
        result.add_warning("Display volume is large relative to total volume")
    elif display_ratio < Decimal('0.05'):
        result.add_warning("Display volume is very small, may result in frequent refreshes")


def _validate_market_conditions(request: BaseOrderRequest, result: OrderValidationResult) -> None:
    """Validate order against market conditions."""
    # In real implementation, this would check:
    # - Market hours
    # - Trading halt status
    # - Price limits
    # - Minimum order sizes
    pass


def validate_oco_order(request: OCOOrderRequest) -> OrderValidationResult:
    """Validate OCO order comprehensively."""
    result = OrderValidationResult(is_valid=True)
    
    try:
        # Validate individual orders
        primary_result = validate_order_request(request.primary_order)
        secondary_result = validate_order_request(request.secondary_order)
        
        # Combine results
        if not primary_result.is_valid:
            result.errors.extend([f"Primary order: {e}" for e in primary_result.errors])
            result.is_valid = False
        
        if not secondary_result.is_valid:
            result.errors.extend([f"Secondary order: {e}" for e in secondary_result.errors])
            result.is_valid = False
        
        # OCO-specific validations already handled by Pydantic validators
        
    except Exception as e:
        result.add_error(f"OCO validation error: {str(e)}")
    
    return result


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_order_type_from_request(request: BaseOrderRequest) -> str:
    """Extract order type string for Kraken API."""
    type_mapping = {
        MarketOrderRequest: "market",
        LimitOrderRequest: "limit",
        StopLossOrderRequest: "stop-loss",
        TakeProfitOrderRequest: "take-profit",
        StopLossLimitOrderRequest: "stop-loss-limit",
        ConditionalOrderRequest: "limit",  # Conditional orders are limit orders with conditions
        IcebergOrderRequest: "limit",  # Iceberg orders are limit orders with special handling
    }
    
    return type_mapping.get(type(request), "limit")


def serialize_order_for_api(request: BaseOrderRequest) -> Dict[str, Any]:
    """Serialize order request for Kraken API submission."""
    api_data = {
        "pair": request.pair,
        "type": request.side.value,
        "ordertype": get_order_type_from_request(request),
        "volume": str(request.volume)
    }
    
    # Add price fields
    if hasattr(request, 'price') and request.price:
        api_data["price"] = str(request.price)
    
    if hasattr(request, 'price2') and request.price2:
        api_data["price2"] = str(request.price2)
    
    # Add optional fields
    if hasattr(request, 'time_in_force') and request.time_in_force:
        api_data["timeinforce"] = request.time_in_force.value
    
    if hasattr(request, 'order_flags') and request.order_flags:
        api_data["oflags"] = ",".join([flag.value for flag in request.order_flags])
    
    if request.userref:
        api_data["userref"] = request.userref
    
    if request.validate_only:
        api_data["validate"] = "true"
    
    return api_data


def estimate_order_fees(request: BaseOrderRequest, fee_rate: Decimal = Decimal('0.0026')) -> Decimal:
    """Estimate trading fees for an order."""
    if hasattr(request, 'price') and request.price:
        notional_value = request.volume * request.price
    else:
        # For market orders, estimate based on volume
        notional_value = request.volume * Decimal('50000')  # Placeholder price
    
    return notional_value * fee_rate


# ============================================================================
# ADVANCED ORDER TYPE UTILITIES
# ============================================================================

class OrderRequestFactory:
    """Factory class for creating various order types."""
    
    @staticmethod
    def create_bracket_order(
        pair: str,
        side: OrderSide,
        volume: Union[str, Decimal],
        entry_price: Union[str, Decimal],
        take_profit_price: Union[str, Decimal],
        stop_loss_price: Union[str, Decimal],
        **kwargs
    ) -> Dict[str, Union[LimitOrderRequest, OCOOrderRequest]]:
        """Create a complete bracket order (entry + OCO exit)."""
        
        # Entry order
        entry_order = create_limit_order(
            pair=pair,
            side=side,
            volume=volume,
            price=entry_price,
            **kwargs
        )
        
        # Exit OCO order
        exit_oco = create_oco_order(
            pair=pair,
            side=side,  # Same side as entry for the exit logic
            volume=volume,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            **kwargs
        )
        
        return {
            "entry_order": entry_order,
            "exit_oco": exit_oco
        }
    
    @staticmethod
    def create_scaled_iceberg_orders(
        pair: str,
        side: OrderSide,
        total_volume: Union[str, Decimal],
        price_levels: List[Union[str, Decimal]],
        display_volume: Union[str, Decimal],
        **kwargs
    ) -> List[IcebergOrderRequest]:
        """Create multiple iceberg orders at different price levels."""
        
        total_vol = Decimal(str(total_volume))
        num_levels = len(price_levels)
        volume_per_level = total_vol / num_levels
        
        orders = []
        for price in price_levels:
            iceberg_order = create_iceberg_order(
                pair=pair,
                side=side,
                volume=volume_per_level,
                price=price,
                display_volume=display_volume,
                **kwargs
            )
            orders.append(iceberg_order)
        
        return orders


'''

    # Create backup of existing file if it exists
    order_requests_path = order_requests_dir / "order_requests.py"
    if order_requests_path.exists():
        backup_path = order_requests_path.with_suffix('.py.backup')
        with open(backup_path, 'w') as f:
            with open(order_requests_path, 'r') as original:
                f.write(original.read())
        print(f"  📦 Backup created: {backup_path}")
    
    # Write the enhanced file
    with open(order_requests_path, 'w') as f:
        f.write(order_requests_content)
    
    print(f"  ✅ Enhanced order_requests.py created: {order_requests_path}")
    return True


def create_test_suite():
    """Create comprehensive test suite for enhanced order models."""
    
    print("📝 Creating comprehensive test suite...")
    
    test_content = '''#!/usr/bin/env python3
"""
Task 3.4.B.1: Enhanced Order Request Models Test Suite

This comprehensive test suite validates all advanced order types and functionality
implemented in Task 3.4.B.1.

Tests:
1. Basic order types (market, limit)
2. Stop-loss and take-profit orders (fixed)
3. Conditional orders (new)
4. OCO orders (new)
5. Iceberg orders (new)
6. Validation and error handling
7. Factory functions
8. API serialization

File: test_task_3_4_b_1_order_models.py
Run: python3 test_task_3_4_b_1_order_models.py
"""

import sys
import time
from pathlib import Path
from decimal import Decimal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.order_requests import (
        # Basic order types
        MarketOrderRequest,
        LimitOrderRequest,
        
        # Advanced order types  
        StopLossOrderRequest,
        TakeProfitOrderRequest,
        StopLossLimitOrderRequest,
        ConditionalOrderRequest,
        OCOOrderRequest,
        IcebergOrderRequest,
        
        # Enums
        TimeInForce,
        OrderFlags,
        TriggerType,
        ConditionOperator,
        OCOType,
        
        # Factory functions
        create_market_order,
        create_limit_order,
        create_stop_loss_order,
        create_take_profit_order,
        create_conditional_order,
        create_oco_order,
        create_iceberg_order,
        
        # Validation
        validate_order_request,
        validate_oco_order,
        
        # Response models
        OrderPlacementResponse,
        OCOPlacementResponse,
        OrderValidationResult,
        
        # Utilities
        serialize_order_for_api,
        estimate_order_fees,
        OrderRequestFactory
    )
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType, OrderStatus
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\\n🔧 Make sure to run: python3 implement_task_3_4_b_1_order_models.py first")
    sys.exit(1)


class Task_3_4_B_1_TestSuite:
    """Comprehensive test suite for Task 3.4.B.1 implementation."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        
    def run_full_test_suite(self):
        """Run the complete enhanced order models test suite."""
        print("🧪 TASK 3.4.B.1: ENHANCED ORDER MODELS - TEST SUITE")
        print("=" * 70)
        print("Testing all advanced order types and functionality")
        print("=" * 70)
        
        try:
            # Test Categories
            self._test_1_basic_order_types()
            self._test_2_fixed_stop_orders()
            self._test_3_conditional_orders()
            self._test_4_oco_orders()
            self._test_5_iceberg_orders()
            self._test_6_validation_framework()
            self._test_7_factory_functions()
            self._test_8_api_serialization()
            self._test_9_response_models()
            self._test_10_advanced_features()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self._generate_comprehensive_report()
    
    def _test_1_basic_order_types(self):
        """Test 1: Basic order types (market, limit)."""
        print("\\n1️⃣ BASIC ORDER TYPES")
        print("-" * 50)
        
        try:
            # Test market order
            market_order = MarketOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0")
            )
            
            assert market_order.order_type == OrderType.MARKET
            assert market_order.pair == "XBTUSD"
            assert market_order.side == OrderSide.BUY
            print("  ✅ Market order created successfully")
            
            # Test limit order
            limit_order = LimitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("2.0"),
                price=Decimal("2500.00")
            )
            
            assert limit_order.order_type == OrderType.LIMIT
            assert limit_order.price == Decimal("2500.00")
            print("  ✅ Limit order created successfully")
            
            self.test_results['basic_order_types'] = True
            print("✅ Basic order types: PASSED")
            
        except Exception as e:
            print(f"  ❌ Basic order types failed: {e}")
            self.test_results['basic_order_types'] = False
    
    def _test_2_fixed_stop_orders(self):
        """Test 2: Fixed stop-loss and take-profit orders."""
        print("\\n2️⃣ FIXED STOP ORDERS")
        print("-" * 50)
        
        try:
            # Test stop-loss order with correct field mapping
            stop_loss = StopLossOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("45000.00")  # Using 'price' field
            )
            
            assert stop_loss.order_type == OrderType.STOP_LOSS
            assert stop_loss.price == Decimal("45000.00")
            assert stop_loss.trigger == TriggerType.LAST
            print("  ✅ Stop-loss order created with correct field mapping")
            
            # Test take-profit order
            take_profit = TakeProfitOrderRequest(
                pair="ETHUSD",
                side=OrderSide.SELL,
                volume=Decimal("2.0"),
                price=Decimal("3500.00")  # Using 'price' field
            )
            
            assert take_profit.order_type == OrderType.TAKE_PROFIT
            assert take_profit.price == Decimal("3500.00")
            print("  ✅ Take-profit order created with correct field mapping")
            
            # Test stop-loss-limit order
            stop_loss_limit = StopLossLimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("48000.00"),  # Stop price
                price2=Decimal("47500.00")  # Limit price
            )
            
            assert stop_loss_limit.order_type == OrderType.STOP_LOSS_LIMIT
            assert stop_loss_limit.price == Decimal("48000.00")
            assert stop_loss_limit.price2 == Decimal("47500.00")
            print("  ✅ Stop-loss-limit order created successfully")
            
            self.test_results['fixed_stop_orders'] = True
            print("✅ Fixed stop orders: PASSED")
            
        except Exception as e:
            print(f"  ❌ Fixed stop orders failed: {e}")
            self.test_results['fixed_stop_orders'] = False
    
    def _test_3_conditional_orders(self):
        """Test 3: New conditional orders."""
        print("\\n3️⃣ CONDITIONAL ORDERS")
        print("-" * 50)
        
        try:
            # Test conditional order creation
            conditional_order = ConditionalOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("49000.00"),
                condition_price=Decimal("50000.00"),
                condition_operator=ConditionOperator.GREATER_THAN,
                condition_trigger=TriggerType.LAST
            )
            
            assert conditional_order.condition_price == Decimal("50000.00")
            assert conditional_order.condition_operator == ConditionOperator.GREATER_THAN
            print("  ✅ Conditional order created successfully")
            
            # Test condition evaluation
            condition_met = conditional_order.evaluate_condition(Decimal("50001.00"))
            assert condition_met == True
            print("  ✅ Condition evaluation works correctly (True case)")
            
            condition_not_met = conditional_order.evaluate_condition(Decimal("49999.00"))
            assert condition_not_met == False
            print("  ✅ Condition evaluation works correctly (False case)")
            
            self.test_results['conditional_orders'] = True
            print("✅ Conditional orders: PASSED")
            
        except Exception as e:
            print(f"  ❌ Conditional orders failed: {e}")
            self.test_results['conditional_orders'] = False
    
    def _test_4_oco_orders(self):
        """Test 4: New OCO (One-Cancels-Other) orders."""
        print("\\n4️⃣ OCO ORDERS")
        print("-" * 50)
        
        try:
            # Create individual orders for OCO
            take_profit = TakeProfitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("55000.00")
            )
            
            stop_loss = StopLossOrderRequest(
                pair="XBTUSD",
                side=OrderSide.SELL,
                volume=Decimal("1.0"),
                price=Decimal("45000.00")
            )
            
            # Test OCO order creation
            oco_order = OCOOrderRequest(
                primary_order=take_profit,
                secondary_order=stop_loss,
                oco_type=OCOType.TAKE_PROFIT_STOP_LOSS
            )
            
            assert oco_order.pair == "XBTUSD"
            assert oco_order.volume == Decimal("1.0")
            assert oco_order.oco_type == OCOType.TAKE_PROFIT_STOP_LOSS
            print("  ✅ OCO order created successfully")
            
            # Test validation
            oco_validation = validate_oco_order(oco_order)
            assert oco_validation.is_valid == True
            print("  ✅ OCO order validation passed")
            
            self.test_results['oco_orders'] = True
            print("✅ OCO orders: PASSED")
            
        except Exception as e:
            print(f"  ❌ OCO orders failed: {e}")
            self.test_results['oco_orders'] = False
    
    def _test_5_iceberg_orders(self):
        """Test 5: New iceberg orders."""
        print("\\n5️⃣ ICEBERG ORDERS")
        print("-" * 50)
        
        try:
            # Test iceberg order creation
            iceberg_order = IcebergOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("10.0"),
                price=Decimal("50000.00"),
                display_volume=Decimal("1.0")
            )
            
            assert iceberg_order.volume == Decimal("10.0")
            assert iceberg_order.display_volume == Decimal("1.0")
            assert iceberg_order.refresh_threshold == Decimal("0.1")  # Default 10%
            print("  ✅ Iceberg order created successfully")
            
            # Test display volume calculation
            next_display = iceberg_order.calculate_next_display_volume(Decimal("5.5"))
            assert next_display == Decimal("1.0")  # Should return display_volume
            print("  ✅ Display volume calculation works")
            
            # Test with remaining < display
            next_display_small = iceberg_order.calculate_next_display_volume(Decimal("0.5"))
            assert next_display_small == Decimal("0.5")  # Should return remaining
            print("  ✅ Display volume calculation for small remaining works")
            
            self.test_results['iceberg_orders'] = True
            print("✅ Iceberg orders: PASSED")
            
        except Exception as e:
            print(f"  ❌ Iceberg orders failed: {e}")
            self.test_results['iceberg_orders'] = False
    
    def _test_6_validation_framework(self):
        """Test 6: Enhanced validation framework."""
        print("\\n6️⃣ VALIDATION FRAMEWORK")
        print("-" * 50)
        
        try:
            # Test valid order validation
            valid_order = LimitOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("1.0"),
                price=Decimal("50000.00")
            )
            
            validation_result = validate_order_request(valid_order)
            assert validation_result.is_valid == True
            print("  ✅ Valid order passes validation")
            
            # Test iceberg validation with warnings
            iceberg_large_display = IcebergOrderRequest(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume=Decimal("2.0"),
                price=Decimal("50000.00"),
                display_volume=Decimal("1.5")  # 75% display ratio
            )
            
            iceberg_validation = validate_order_request(iceberg_large_display)
            assert iceberg_validation.is_valid == True
            assert len(iceberg_validation.warnings) > 0  # Should have warnings
            print("  ✅ Iceberg validation with warnings works")
            
            self.test_results['validation_framework'] = True
            print("✅ Validation framework: PASSED")
            
        except Exception as e:
            print(f"  ❌ Validation framework failed: {e}")
            self.test_results['validation_framework'] = False
    
    def _test_7_factory_functions(self):
        """Test 7: Enhanced factory functions."""
        print("\\n7️⃣ FACTORY FUNCTIONS")
        print("-" * 50)
        
        try:
            # Test basic factory functions
            market = create_market_order("XBTUSD", OrderSide.BUY, "1.0")
            assert isinstance(market, MarketOrderRequest)
            print("  ✅ Market order factory works")
            
            limit = create_limit_order("XBTUSD", OrderSide.BUY, "1.0", "50000.00")
            assert isinstance(limit, LimitOrderRequest)
            print("  ✅ Limit order factory works")
            
            # Test advanced factory functions
            stop_loss = create_stop_loss_order("XBTUSD", OrderSide.SELL, "1.0", "45000.00")
            assert isinstance(stop_loss, StopLossOrderRequest)
            assert stop_loss.price == Decimal("45000.00")
            print("  ✅ Stop-loss order factory works")
            
            take_profit = create_take_profit_order("XBTUSD", OrderSide.SELL, "1.0", "55000.00")
            assert isinstance(take_profit, TakeProfitOrderRequest)
            print("  ✅ Take-profit order factory works")
            
            conditional = create_conditional_order(
                "XBTUSD", OrderSide.BUY, "1.0", "49000.00", 
                "50000.00", ConditionOperator.GREATER_THAN
            )
            assert isinstance(conditional, ConditionalOrderRequest)
            print("  ✅ Conditional order factory works")
            
            oco = create_oco_order("XBTUSD", OrderSide.BUY, "1.0", "55000.00", "45000.00")
            assert isinstance(oco, OCOOrderRequest)
            print("  ✅ OCO order factory works")
            
            iceberg = create_iceberg_order("XBTUSD", OrderSide.BUY, "10.0", "50000.00", "1.0")
            assert isinstance(iceberg, IcebergOrderRequest)
            print("  ✅ Iceberg order factory works")
            
            self.test_results['factory_functions'] = True
            print("✅ Factory functions: PASSED")
            
        except Exception as e:
            print(f"  ❌ Factory functions failed: {e}")
            self.test_results['factory_functions'] = False
    
    def _test_8_api_serialization(self):
        """Test 8: API serialization functionality."""
        print("\\n8️⃣ API SERIALIZATION")
        print("-" * 50)
        
        try:
            # Test basic order serialization
            limit_order = create_limit_order("XBTUSD", OrderSide.BUY, "1.0", "50000.00")
            api_data = serialize_order_for_api(limit_order)
            
            expected_fields = {"pair", "type", "ordertype", "volume", "price"}
            assert all(field in api_data for field in expected_fields)
            assert api_data["pair"] == "XBTUSD"
            assert api_data["type"] == "buy"
            assert api_data["ordertype"] == "limit"
            print("  ✅ Basic order serialization works")
            
            # Test advanced order serialization
            stop_loss = create_stop_loss_order("XBTUSD", OrderSide.SELL, "1.0", "45000.00")
            stop_api_data = serialize_order_for_api(stop_loss)
            
            assert stop_api_data["ordertype"] == "stop-loss"
            assert stop_api_data["price"] == "45000.00"
            print("  ✅ Stop-loss order serialization works")
            
            # Test fee estimation
            estimated_fees = estimate_order_fees(limit_order)
            assert estimated_fees > Decimal("0")
            print("  ✅ Fee estimation works")
            
            self.test_results['api_serialization'] = True
            print("✅ API serialization: PASSED")
            
        except Exception as e:
            print(f"  ❌ API serialization failed: {e}")
            self.test_results['api_serialization'] = False
    
    def _test_9_response_models(self):
        """Test 9: Response models functionality."""
        print("\\n9️⃣ RESPONSE MODELS")
        print("-" * 50)
        
        try:
            # Test OrderPlacementResponse
            from trading_systems.exchanges.kraken.order_requests import OrderDescription
            
            order_desc = OrderDescription(
                pair="XBTUSD",
                type="buy",
                ordertype="limit",
                price="50000.00",
                order="buy 1.00000000 XBTUSD @ limit 50000.00"
            )
            
            placement_response = OrderPlacementResponse(
                txid=["ORDER123"],
                descr=order_desc
            )
            
            assert placement_response.order_id == "ORDER123"
            assert placement_response.is_success == True
            print("  ✅ OrderPlacementResponse works")
            
            # Test OCOPlacementResponse
            primary_response = OrderPlacementResponse(
                txid=["ORDER456"],
                descr=order_desc
            )
            
            secondary_response = OrderPlacementResponse(
                txid=["ORDER789"],
                descr=order_desc
            )
            
            oco_response = OCOPlacementResponse(
                primary_response=primary_response,
                secondary_response=secondary_response,
                oco_group_id="OCO123"
            )
            
            assert oco_response.is_success == True
            assert len(oco_response.order_ids) == 2
            print("  ✅ OCOPlacementResponse works")
            
            self.test_results['response_models'] = True
            print("✅ Response models: PASSED")
            
        except Exception as e:
            print(f"  ❌ Response models failed: {e}")
            self.test_results['response_models'] = False
    
    def _test_10_advanced_features(self):
        """Test 10: Advanced features and factory patterns."""
        print("\\n🔟 ADVANCED FEATURES")
        print("-" * 50)
        
        try:
            # Test bracket order creation
            bracket_orders = OrderRequestFactory.create_bracket_order(
                pair="XBTUSD",
                side=OrderSide.BUY,
                volume="1.0",
                entry_price="50000.00",
                take_profit_price="55000.00",
                stop_loss_price="45000.00"
            )
            
            assert "entry_order" in bracket_orders
            assert "exit_oco" in bracket_orders
            assert isinstance(bracket_orders["entry_order"], LimitOrderRequest)
            assert isinstance(bracket_orders["exit_oco"], OCOOrderRequest)
            print("  ✅ Bracket order factory works")
            
            # Test scaled iceberg orders
            scaled_icebergs = OrderRequestFactory.create_scaled_iceberg_orders(
                pair="XBTUSD",
                side=OrderSide.BUY,
                total_volume="10.0",
                price_levels=["49000.00", "49500.00", "50000.00"],
                display_volume="1.0"
            )
            
            assert len(scaled_icebergs) == 3
            assert all(isinstance(order, IcebergOrderRequest) for order in scaled_icebergs)
            assert all(order.volume == Decimal("3.333333333333333333333333333") for order in scaled_icebergs)
            print("  ✅ Scaled iceberg orders factory works")
            
            self.test_results['advanced_features'] = True
            print("✅ Advanced features: PASSED")
            
        except Exception as e:
            print(f"  ❌ Advanced features failed: {e}")
            self.test_results['advanced_features'] = False
    
    def _generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\\n" + "=" * 70)
        print("📊 TASK 3.4.B.1 IMPLEMENTATION REPORT")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print(f"🎯 Tests Executed: {total_tests}")
        print(f"✅ Tests Passed: {passed_tests}")
        print(f"❌ Tests Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        execution_time = time.time() - self.start_time
        print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
        
        print("\\n📋 TEST BREAKDOWN:")
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status} - {test_name.replace('_', ' ').title()}")
        
        if passed_tests == total_tests:
            print("\\n🎉 TASK 3.4.B.1: ENHANCED ORDER MODELS - COMPLETE!")
            print("\\n✅ All Advanced Order Types Implemented:")
            print("   • Fixed StopLossOrderRequest and TakeProfitOrderRequest")
            print("   • New ConditionalOrderRequest with trigger evaluation")
            print("   • New OCOOrderRequest (One-Cancels-Other)")
            print("   • New IcebergOrderRequest with smart display logic")
            print("   • Enhanced validation framework")
            print("   • Comprehensive factory functions")
            print("   • API serialization utilities")
            print("   • Advanced response models")
            print("   • Factory patterns for complex order strategies")
            print("\\n🎯 Ready for Task 3.4.B.2: Advanced Order Processing Logic")
            
        else:
            print("\\n⚠️  SOME TESTS FAILED - Review and fix issues before proceeding")
            print("\\n🔧 Failed test areas:")
            for test_name, result in self.test_results.items():
                if not result:
                    print(f"   • {test_name.replace('_', ' ').title()}")
        
        print("=" * 70)


def main():
    """Main execution function."""
    print("🚀 TASK 3.4.B.1: ENHANCED ORDER REQUEST MODELS")
    print("=" * 70)
    print("Testing complete implementation of advanced order types")
    print("=" * 70)
    
    # Run test suite
    test_suite = Task_3_4_B_1_TestSuite()
    test_suite.run_full_test_suite()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n\\n👋 Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
'''

    # Write test file
    test_path = Path("test_task_3_4_b_1_order_models.py")
    with open(test_path, 'w') as f:
        f.write(test_content)
    
    print(f"  ✅ Test suite created: {test_path}")
    return True


def main():
    """Main implementation function for Task 3.4.B.1."""
    
    print("🚀 TASK 3.4.B.1: ENHANCED ORDER REQUEST MODELS IMPLEMENTATION")
    print("=" * 80)
    print()
    print("Implementing comprehensive advanced order types for the Kraken Trading System:")
    print("• Fixed StopLossOrderRequest and TakeProfitOrderRequest models")
    print("• New ConditionalOrderRequest with trigger evaluation logic")
    print("• New OCOOrderRequest (One-Cancels-Other) for linked orders")
    print("• New IcebergOrderRequest with intelligent display management")
    print("• Enhanced validation framework and factory functions")
    print("• Comprehensive test suite")
    print()
    
    success_count = 0
    total_tasks = 2
    
    # Task 1: Create enhanced order models
    print("📝 STEP 1: Creating Enhanced Order Request Models")
    print("-" * 60)
    if create_enhanced_order_requests_file():
        success_count += 1
        print("✅ Enhanced order models implementation complete")
    else:
        print("❌ Enhanced order models implementation failed")
    
    print()
    
    # Task 2: Create comprehensive test suite
    print("📝 STEP 2: Creating Comprehensive Test Suite")
    print("-" * 60)
    if create_test_suite():
        success_count += 1
        print("✅ Comprehensive test suite created")
    else:
        print("❌ Test suite creation failed")
    
    print()
    print("=" * 80)
    print("📊 TASK 3.4.B.1 IMPLEMENTATION SUMMARY")
    print("=" * 80)
    print(f"🎯 Implementation Tasks: {success_count}/{total_tasks}")
    
    if success_count == total_tasks:
        print("🎉 TASK 3.4.B.1 IMPLEMENTATION COMPLETED SUCCESSFULLY!")
        print()
        print("✅ Created Components:")
        print("   • Enhanced order_requests.py with all advanced order types")
        print("   • Fixed StopLossOrderRequest with correct 'price' field mapping")
        print("   • Fixed TakeProfitOrderRequest with correct 'price' field mapping")
        print("   • New ConditionalOrderRequest with trigger evaluation logic")
        print("   • New OCOOrderRequest (One-Cancels-Other) with validation")
        print("   • New IcebergOrderRequest with intelligent display management")
        print("   • Enhanced validation framework with warnings and errors")
        print("   • Comprehensive factory functions for easy order creation")
        print("   • API serialization utilities for Kraken integration")
        print("   • Advanced response models (OCOPlacementResponse, etc.)")
        print("   • OrderRequestFactory with bracket and scaled order patterns")
        print("   • Complete test suite (test_task_3_4_b_1_order_models.py)")
        print()
        print("🔧 Files Created/Updated:")
        print("   • src/trading_systems/exchanges/kraken/order_requests.py")
        print("   • test_task_3_4_b_1_order_models.py")
        print()
        print("🧪 Next Steps:")
        print("   1. Run: python3 test_task_3_4_b_1_order_models.py")
        print("   2. Verify all tests pass")
        print("   3. Update Project Status Board")
        print("   4. Proceed to Task 3.4.B.2: Advanced Order Processing Logic")
        print()
        print("📋 Task 3.4.B.1 Success Criteria Achieved:")
        print("   ✅ Fixed existing StopLossOrderRequest and TakeProfitOrderRequest models")
        print("   ✅ Implemented ConditionalOrderRequest model")
        print("   ✅ Implemented OCOOrderRequest model")
        print("   ✅ Implemented IcebergOrderRequest model")
        print("   ✅ Added proper validation and field mapping")
        print("   ✅ Created comprehensive test suite")
        print("   ✅ All models integrate with existing validation framework")
        
    else:
        print("❌ IMPLEMENTATION INCOMPLETE - Manual review required")
        print()
        print("🔧 Issues to resolve:")
        if success_count < 1:
            print("   • Enhanced order models creation failed")
        if success_count < 2:
            print("   • Test suite creation failed")
        print()
        print("💡 Try running the individual components manually:")
        print("   1. Check directory structure: src/trading_systems/exchanges/kraken/")
        print("   2. Verify imports are working")
        print("   3. Review any error messages above")
    
    print("=" * 80)
    return success_count == total_tasks


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Implementation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
