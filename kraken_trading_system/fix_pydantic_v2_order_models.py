#!/usr/bin/env python3
"""
Fix Pydantic V2 Compatibility for Order Models

This script fixes the Pydantic v2 compatibility issues in the order_requests.py file
by updating deprecated decorators and syntax.

Issues Fixed:
1. @root_validator -> @model_validator
2. @validator -> @field_validator  
3. Config class updates
4. Field validation syntax updates

Run: python3 fix_pydantic_v2_order_models.py
"""

import sys
from pathlib import Path

def fix_pydantic_v2_compatibility():
    """Fix Pydantic v2 compatibility issues in order_requests.py."""
    
    print("🔧 FIXING PYDANTIC V2 COMPATIBILITY")
    print("=" * 60)
    
    order_requests_path = Path("src/trading_systems/exchanges/kraken/order_requests.py")
    
    if not order_requests_path.exists():
        print("❌ order_requests.py not found. Run implement_task_3_4_b_1_order_models.py first")
        return False
    
    try:
        # Read current content
        with open(order_requests_path, 'r') as f:
            content = f.read()
        
        print(f"📊 Original file size: {len(content)} characters")
        
        # Create backup
        backup_path = order_requests_path.with_suffix('.py.v1_backup')
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"💾 Backup created: {backup_path}")
        
        # Track changes
        changes_made = []
        
        # Fix 1: Update imports
        old_imports = "from pydantic import BaseModel, Field, validator, root_validator"
        new_imports = "from pydantic import BaseModel, Field, field_validator, model_validator"
        
        if old_imports in content:
            content = content.replace(old_imports, new_imports)
            changes_made.append("Updated imports")
            print("  ✅ Fixed imports")
        
        # Fix 2: Update @root_validator to @model_validator
        content = content.replace("@root_validator", "@model_validator(mode='after')")
        changes_made.append("Updated @root_validator")
        print("  ✅ Fixed @root_validator decorators")
        
        # Fix 3: Update @validator to @field_validator
        import re
        
        # Pattern for @validator('field_name')
        validator_pattern = r"@validator\('([^']+)'\)"
        matches = re.findall(validator_pattern, content)
        
        for field_name in matches:
            old_decorator = f"@validator('{field_name}')"
            new_decorator = f"@field_validator('{field_name}')"
            content = content.replace(old_decorator, new_decorator)
        
        changes_made.append(f"Updated {len(matches)} @validator decorators")
        print(f"  ✅ Fixed {len(matches)} @validator decorators")
        
        # Fix 4: Update validator function signatures for Pydantic v2
        # In Pydantic v2, field validators receive (cls, v) instead of (cls, v, values)
        # For model validators, the signature is (cls, model)
        
        # Fix root_validator function signatures
        old_root_pattern = r"def validate_([^(]+)\(cls, values\):"
        new_root_replacement = r"def validate_\1(cls, model):"
        content = re.sub(old_root_pattern, new_root_replacement, content)
        
        # Update references to values inside root validators
        content = content.replace("values.get(", "getattr(model, ")
        content = content.replace("values[", "getattr(model, ")
        content = content.replace("values = ", "# values = ")
        content = content.replace("return values", "return model")
        
        changes_made.append("Updated validator function signatures")
        print("  ✅ Fixed validator function signatures")
        
        # Fix 5: Update Config class for Pydantic v2
        old_config = """class Config:
        validate_by_name = True
        use_enum_values = True"""
        
        new_config = """class Config:
        populate_by_name = True
        use_enum_values = True"""
        
        if old_config in content:
            content = content.replace(old_config, new_config)
            changes_made.append("Updated Config class")
            print("  ✅ Fixed Config class")
        
        # Write the fixed content
        with open(order_requests_path, 'w') as f:
            f.write(content)
        
        print(f"\n📊 Updated file size: {len(content)} characters")
        print(f"🔧 Changes made: {len(changes_made)}")
        for change in changes_made:
            print(f"   • {change}")
        
        print(f"\n✅ Pydantic v2 compatibility fixes applied to {order_requests_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing Pydantic compatibility: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_complete_fixed_order_requests():
    """Create a completely rewritten order_requests.py with proper Pydantic v2 syntax."""
    
    print("📝 Creating complete Pydantic v2 compatible order_requests.py...")
    
    order_requests_content = '''"""
Enhanced Order Request/Response Models for Kraken Trading System - Task 3.4.B.1
Pydantic V2 Compatible Version

This module provides comprehensive Pydantic models for all Kraken order types
including advanced order types: stop-loss, take-profit, conditional, OCO, and iceberg orders.

Enhanced Features:
- Pydantic V2 compatible decorators and syntax
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

from pydantic import BaseModel, Field, field_validator, model_validator

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

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True
    }

    @field_validator('pair')
    @classmethod
    def validate_pair(cls, v):
        """Validate trading pair format."""
        if not v or len(v) < 3:
            raise ValueError("Invalid trading pair")
        return v.upper()

    @field_validator('volume')
    @classmethod
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

    @field_validator('order_type')
    @classmethod
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

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        """Ensure order type is limit."""
        if v != OrderType.LIMIT:
            raise ValueError("Order type must be 'limit' for LimitOrderRequest")
        return v

    @field_validator('price')
    @classmethod
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

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        """Ensure order type is stop-loss."""
        if v != OrderType.STOP_LOSS:
            raise ValueError("Order type must be 'stop-loss' for StopLossOrderRequest")
        return v

    @field_validator('price')
    @classmethod
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

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        """Ensure order type is take-profit."""
        if v != OrderType.TAKE_PROFIT:
            raise ValueError("Order type must be 'take-profit' for TakeProfitOrderRequest")
        return v

    @field_validator('price')
    @classmethod
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

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        """Ensure order type is stop-loss-limit."""
        if v != OrderType.STOP_LOSS_LIMIT:
            raise ValueError("Order type must be 'stop-loss-limit' for StopLossLimitOrderRequest")
        return v

    @model_validator(mode='after')
    def validate_prices(self):
        """Validate stop and limit price relationship."""
        price = self.price
        price2 = self.price2
        side = self.side
        
        if price and price2 and side:
            # For sell stop-loss: stop price should be below limit price
            # For buy stop-loss: stop price should be above limit price
            if side == OrderSide.SELL and price >= price2:
                raise ValueError("For sell stop-loss-limit: stop price must be below limit price")
            elif side == OrderSide.BUY and price <= price2:
                raise ValueError("For buy stop-loss-limit: stop price must be above limit price")
        
        return self


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

    @field_validator('condition_price')
    @classmethod
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

    @model_validator(mode='after')
    def validate_oco_orders(self):
        """Validate OCO order configuration."""
        primary = self.primary_order
        secondary = self.secondary_order
        
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
        
        return self

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

    @field_validator('display_volume')
    @classmethod
    def validate_display_volume(cls, v, info):
        """Validate display volume against total volume."""
        # In Pydantic v2, we need to access other fields through info.data
        if hasattr(info, 'data') and 'volume' in info.data:
            total_volume = info.data['volume']
            if total_volume and v >= total_volume:
                raise ValueError("Display volume must be less than total volume")
        return v

    @model_validator(mode='after')
    def validate_iceberg_config(self):
        """Validate iceberg configuration."""
        display_volume = self.display_volume
        total_volume = self.volume
        refresh_threshold = self.refresh_threshold
        
        if display_volume and total_volume:
            # Set default refresh threshold if not specified
            if refresh_threshold is None:
                self.refresh_threshold = display_volume * Decimal('0.1')
            
            # Validate refresh threshold
            elif refresh_threshold >= display_volume:
                raise ValueError("Refresh threshold must be less than display volume")
        
        return self

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

    # Ensure directory exists
    order_requests_dir = Path("src/trading_systems/exchanges/kraken")
    order_requests_dir.mkdir(parents=True, exist_ok=True)
    
    # Create backup of existing file if it exists
    order_requests_path = order_requests_dir / "order_requests.py"
    if order_requests_path.exists():
        backup_path = order_requests_path.with_suffix('.py.v2_backup')
        with open(backup_path, 'w') as f:
            with open(order_requests_path, 'r') as original:
                f.write(original.read())
        print(f"  📦 Backup created: {backup_path}")
    
    # Write the Pydantic v2 compatible file
    with open(order_requests_path, 'w') as f:
        f.write(order_requests_content)
    
    print(f"  ✅ Pydantic v2 compatible order_requests.py created: {order_requests_path}")
    return True


def main():
    """Main execution function."""
    
    print("🚀 PYDANTIC V2 COMPATIBILITY FIX FOR TASK 3.4.B.1")
    print("=" * 70)
    print()
    print("Fixing Pydantic v2 compatibility issues in order_requests.py")
    print("Key changes:")
    print("• @root_validator -> @model_validator(mode='after')")
    print("• @validator -> @field_validator") 
    print("• Updated Config class: validate_by_name -> populate_by_name")
    print("• Fixed validator function signatures")
    print("• Updated field validation context access")
    print()
    
    success_count = 0
    total_tasks = 1
    
    # Create completely rewritten Pydantic v2 compatible file
    print("📝 STEP 1: Creating Pydantic V2 Compatible Order Models")
    print("-" * 60)
    if create_complete_fixed_order_requests():
        success_count += 1
        print("✅ Pydantic v2 compatible order models created")
    else:
        print("❌ Failed to create Pydantic v2 compatible models")
    
    print()
    print("=" * 70)
    print("📊 PYDANTIC V2 FIX SUMMARY")
    print("=" * 70)
    print(f"🎯 Fix Tasks: {success_count}/{total_tasks}")
    
    if success_count == total_tasks:
        print("🎉 PYDANTIC V2 COMPATIBILITY FIX COMPLETED!")
        print()
        print("✅ Fixed Issues:")
        print("   • Updated all decorators to Pydantic v2 syntax")
        print("   • Fixed @root_validator -> @model_validator(mode='after')")
        print("   • Fixed @validator -> @field_validator with @classmethod")
        print("   • Updated Config class for Pydantic v2")
        print("   • Fixed validator function signatures")
        print("   • Updated field validation context access")
        print("   • Maintained all advanced order type functionality")
        print()
        print("🧪 Next Steps:")
        print("   1. Run: python3 test_task_3_4_b_1_order_models.py")
        print("   2. Verify all tests pass")
        print("   3. Proceed with Task 3.4.B.1 validation")
        
    else:
        print("❌ PYDANTIC V2 FIX INCOMPLETE - Manual review required")
    
    print("=" * 70)
    return success_count == total_tasks


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
