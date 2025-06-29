"""
Enhanced Order Models with State Machine for Kraken Trading System.

This module extends the basic KrakenOrder model with comprehensive state machine logic,
order lifecycle management, and state transition validation.

File Location: src/trading_systems/exchanges/kraken/order_models.py
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, validator

# Import base order model from existing account_models
from .account_models import KrakenOrder as BaseKrakenOrder, OrderStatus, OrderType, OrderSide


class OrderState(str, Enum):
    """Enhanced order states with comprehensive lifecycle tracking."""
    
    # Initial states
    PENDING_NEW = "pending_new"           # Order created locally, not yet sent
    PENDING_SUBMIT = "pending_submit"     # Order submitted to exchange, awaiting confirmation
    
    # Active states
    OPEN = "open"                         # Order confirmed and active on exchange
    PARTIALLY_FILLED = "partially_filled" # Order partially executed
    
    # Terminal states
    FILLED = "filled"                     # Order completely executed
    CANCELED = "canceled"                 # Order canceled by user or system
    REJECTED = "rejected"                 # Order rejected by exchange
    EXPIRED = "expired"                   # Order expired due to time limit
    
    # Error states
    FAILED = "failed"                     # Order failed due to system error
    UNKNOWN = "unknown"                   # Order state cannot be determined


class OrderEvent(str, Enum):
    """Order lifecycle events that trigger state transitions."""
    
    # Submission events
    SUBMIT = "submit"                     # Submit order to exchange
    CONFIRM = "confirm"                   # Exchange confirms order
    REJECT = "reject"                     # Exchange rejects order
    
    # Execution events
    PARTIAL_FILL = "partial_fill"         # Order partially filled
    FULL_FILL = "full_fill"              # Order completely filled
    
    # Management events
    CANCEL_REQUEST = "cancel_request"     # User requests cancellation
    CANCEL_CONFIRM = "cancel_confirm"     # Cancellation confirmed
    MODIFY_REQUEST = "modify_request"     # User requests modification
    MODIFY_CONFIRM = "modify_confirm"     # Modification confirmed
    
    # System events
    EXPIRE = "expire"                     # Order expired
    FAIL = "fail"                        # System failure
    RESET = "reset"                      # Reset to unknown state


class OrderStateMachine:
    """
    Order state machine defining valid state transitions.
    
    Implements the complete order lifecycle with validation of state changes.
    """
    
    # Define valid state transitions
    VALID_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
        OrderState.PENDING_NEW: {
            OrderState.PENDING_SUBMIT,
            OrderState.FAILED,
            OrderState.CANCELED
        },
        OrderState.PENDING_SUBMIT: {
            OrderState.OPEN,
            OrderState.REJECTED,
            OrderState.FAILED,
            OrderState.CANCELED
        },
        OrderState.OPEN: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELED,
            OrderState.EXPIRED,
            OrderState.FAILED,
            OrderState.UNKNOWN
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.FILLED,
            OrderState.CANCELED,
            OrderState.EXPIRED,
            OrderState.FAILED,
            OrderState.UNKNOWN
        },
        # Terminal states (no transitions allowed)
        OrderState.FILLED: set(),
        OrderState.CANCELED: set(),
        OrderState.REJECTED: set(),
        OrderState.EXPIRED: set(),
        OrderState.FAILED: set(),
        OrderState.UNKNOWN: {OrderState.OPEN, OrderState.CANCELED, OrderState.FILLED}  # Recovery transitions
    }
    
    # Events that trigger specific transitions
    EVENT_TRANSITIONS: Dict[Tuple[OrderState, OrderEvent], OrderState] = {
        # From PENDING_NEW
        (OrderState.PENDING_NEW, OrderEvent.SUBMIT): OrderState.PENDING_SUBMIT,
        (OrderState.PENDING_NEW, OrderEvent.FAIL): OrderState.FAILED,
        (OrderState.PENDING_NEW, OrderEvent.CANCEL_REQUEST): OrderState.CANCELED,
        
        # From PENDING_SUBMIT
        (OrderState.PENDING_SUBMIT, OrderEvent.CONFIRM): OrderState.OPEN,
        (OrderState.PENDING_SUBMIT, OrderEvent.REJECT): OrderState.REJECTED,
        (OrderState.PENDING_SUBMIT, OrderEvent.FAIL): OrderState.FAILED,
        (OrderState.PENDING_SUBMIT, OrderEvent.CANCEL_CONFIRM): OrderState.CANCELED,
        
        # From OPEN
        (OrderState.OPEN, OrderEvent.PARTIAL_FILL): OrderState.PARTIALLY_FILLED,
        (OrderState.OPEN, OrderEvent.FULL_FILL): OrderState.FILLED,
        (OrderState.OPEN, OrderEvent.CANCEL_CONFIRM): OrderState.CANCELED,
        (OrderState.OPEN, OrderEvent.EXPIRE): OrderState.EXPIRED,
        (OrderState.OPEN, OrderEvent.FAIL): OrderState.FAILED,
        (OrderState.OPEN, OrderEvent.RESET): OrderState.UNKNOWN,
        
        # From PARTIALLY_FILLED
        (OrderState.PARTIALLY_FILLED, OrderEvent.PARTIAL_FILL): OrderState.PARTIALLY_FILLED,  # Additional fills
        (OrderState.PARTIALLY_FILLED, OrderEvent.FULL_FILL): OrderState.FILLED,
        (OrderState.PARTIALLY_FILLED, OrderEvent.CANCEL_CONFIRM): OrderState.CANCELED,
        (OrderState.PARTIALLY_FILLED, OrderEvent.EXPIRE): OrderState.EXPIRED,
        (OrderState.PARTIALLY_FILLED, OrderEvent.FAIL): OrderState.FAILED,
        (OrderState.PARTIALLY_FILLED, OrderEvent.RESET): OrderState.UNKNOWN,
        
        # From UNKNOWN (recovery transitions)
        (OrderState.UNKNOWN, OrderEvent.CONFIRM): OrderState.OPEN,
        (OrderState.UNKNOWN, OrderEvent.CANCEL_CONFIRM): OrderState.CANCELED,
        (OrderState.UNKNOWN, OrderEvent.FULL_FILL): OrderState.FILLED,
    }
    
    @classmethod
    def is_valid_transition(cls, from_state: OrderState, to_state: OrderState) -> bool:
        """Check if state transition is valid."""
        return to_state in cls.VALID_TRANSITIONS.get(from_state, set())
    
    @classmethod
    def get_next_state(cls, current_state: OrderState, event: OrderEvent) -> Optional[OrderState]:
        """Get next state for given current state and event."""
        return cls.EVENT_TRANSITIONS.get((current_state, event))
    
    @classmethod
    def is_terminal_state(cls, state: OrderState) -> bool:
        """Check if state is terminal (no further transitions)."""
        return len(cls.VALID_TRANSITIONS.get(state, set())) == 0
    
    @classmethod
    def is_active_state(cls, state: OrderState) -> bool:
        """Check if order is in an active trading state."""
        return state in {OrderState.OPEN, OrderState.PARTIALLY_FILLED}
    
    @classmethod
    def is_pending_state(cls, state: OrderState) -> bool:
        """Check if order is in a pending state."""
        return state in {OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT}


class OrderStateTransition(BaseModel):
    """Record of an order state transition event."""
    
    timestamp: datetime = Field(default_factory=datetime.now, description="When transition occurred")
    from_state: OrderState = Field(..., description="Previous state")
    to_state: OrderState = Field(..., description="New state")
    event: OrderEvent = Field(..., description="Event that triggered transition")
    reason: Optional[str] = Field(None, description="Human-readable reason for transition")
    exchange_data: Optional[Dict[str, Any]] = Field(None, description="Related exchange data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EnhancedKrakenOrder(BaseKrakenOrder):
    """
    Enhanced Kraken order model with state machine and lifecycle management.
    
    Extends the base KrakenOrder with:
    - Comprehensive state management
    - State transition tracking
    - Order lifecycle events
    - Validation and business logic
    """
    
    # Enhanced state management
    current_state: OrderState = Field(OrderState.PENDING_NEW, description="Current order state")
    state_history: List[OrderStateTransition] = Field(default_factory=list, description="State transition history")
    
    # Order lifecycle tracking
    created_at: datetime = Field(default_factory=datetime.now, description="Order creation time")
    submitted_at: Optional[datetime] = Field(None, description="Order submission time")
    first_fill_at: Optional[datetime] = Field(None, description="First fill timestamp")
    last_fill_at: Optional[datetime] = Field(None, description="Last fill timestamp")
    completed_at: Optional[datetime] = Field(None, description="Order completion time")
    
    # Enhanced execution tracking
    fill_count: int = Field(0, description="Number of fills received")
    average_fill_price: Optional[Decimal] = Field(None, description="Volume-weighted average fill price")
    total_fees_paid: Decimal = Field(Decimal('0'), description="Total fees paid across all fills")
    
    # Order management
    client_order_id: Optional[str] = Field(None, description="Client-side order identifier")
    parent_order_id: Optional[str] = Field(None, description="Parent order for linked orders")
    tags: List[str] = Field(default_factory=list, description="Order tags for classification")
    
    # Risk and limits
    max_show_size: Optional[Decimal] = Field(None, description="Maximum visible size (iceberg orders)")
    time_in_force: Optional[str] = Field(None, description="Order time in force")
    post_only: bool = Field(False, description="Post-only order flag")
    
    # State machine integration
    _state_machine: OrderStateMachine = OrderStateMachine()
    
    # PROPERTY ALIASES FOR BACKWARD COMPATIBILITY
    
    @property
    def state(self) -> OrderState:
        """Alias for current_state for backward compatibility."""
        return self.current_state
    
    @state.setter
    def state(self, value: OrderState) -> None:
        """Setter for state alias."""
        self.current_state = value
    
    @property
    def side(self) -> OrderSide:
        """Alias for type (order side) for backward compatibility."""
        return self.type
    
    @side.setter
    def side(self, value: OrderSide) -> None:
        """Setter for side alias."""
        self.type = value
    
    @property
    def order_type(self) -> OrderType:
        """Alias for order_type field for consistency."""
        return getattr(self, '_order_type', OrderType.LIMIT)
    
    @order_type.setter
    def order_type(self, value: OrderType) -> None:
        """Setter for order_type."""
        self._order_type = value

    def transition_to(self, new_state: OrderState, event: OrderEvent, 
                     reason: Optional[str] = None, exchange_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Transition order to new state with validation and logging.
        
        Args:
            new_state: Target state
            event: Event triggering the transition
            reason: Human-readable reason
            exchange_data: Related exchange data
            
        Returns:
            True if transition successful, False otherwise
        """
        # Validate transition
        if not self._state_machine.is_valid_transition(self.current_state, new_state):
            return False
        
        # Create transition record
        transition = OrderStateTransition(
            from_state=self.current_state,
            to_state=new_state,
            event=event,
            reason=reason,
            exchange_data=exchange_data
        )
        
        # Update state and record transition
        old_state = self.current_state
        self.current_state = new_state
        self.state_history.append(transition)
        
        # Update lifecycle timestamps
        self._update_lifecycle_timestamps(new_state, event)
        
        return True
    
    def _update_lifecycle_timestamps(self, new_state: OrderState, event: OrderEvent) -> None:
        """Update lifecycle timestamps based on state transition."""
        now = datetime.now()
        
        if new_state == OrderState.PENDING_SUBMIT and self.submitted_at is None:
            self.submitted_at = now
        elif event == OrderEvent.PARTIAL_FILL:
            if self.first_fill_at is None:
                self.first_fill_at = now
            self.last_fill_at = now
        elif event == OrderEvent.FULL_FILL:
            if self.first_fill_at is None:
                self.first_fill_at = now
            self.last_fill_at = now
            self.completed_at = now
        elif new_state in {OrderState.CANCELED, OrderState.REJECTED, OrderState.EXPIRED, OrderState.FAILED}:
            if self.completed_at is None:
                self.completed_at = now
    
    def handle_fill(self, fill_volume: Decimal, fill_price: Decimal, fill_fee: Decimal = Decimal('0')) -> bool:
        """
        Handle order fill and update state accordingly.
        
        Args:
            fill_volume: Volume filled in this execution
            fill_price: Price of the fill
            fill_fee: Fee charged for this fill
            
        Returns:
            True if fill processed successfully
        """
        # Update execution tracking
        old_executed = self.volume_executed
        self.volume_executed += fill_volume
        self.fill_count += 1
        self.total_fees_paid += fill_fee
        
        # Update average fill price
        if self.average_fill_price is None:
            self.average_fill_price = fill_price
        else:
            total_notional = (old_executed * self.average_fill_price) + (fill_volume * fill_price)
            self.average_fill_price = total_notional / self.volume_executed
        
        # Determine appropriate state transition
        if self.volume_executed >= self.volume:
            # Order fully filled
            return self.transition_to(OrderState.FILLED, OrderEvent.FULL_FILL, 
                                    f"Order fully filled: {self.volume_executed}/{self.volume}")
        else:
            # Partial fill
            return self.transition_to(OrderState.PARTIALLY_FILLED, OrderEvent.PARTIAL_FILL,
                                    f"Partial fill: {fill_volume} at {fill_price}")
    
    def can_be_canceled(self) -> bool:
        """Check if order can be canceled in current state."""
        return self._state_machine.is_active_state(self.current_state)
    
    def can_be_modified(self) -> bool:
        """Check if order can be modified in current state."""
        return self.current_state == OrderState.OPEN
    
    def is_active(self) -> bool:
        """Check if order is currently active."""
        return self._state_machine.is_active_state(self.current_state)
    
    def is_terminal(self) -> bool:
        """Check if order is in terminal state."""
        return self._state_machine.is_terminal_state(self.current_state)
    
    def is_pending(self) -> bool:
        """Check if order is pending."""
        return self._state_machine.is_pending_state(self.current_state)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary."""
        return {
            'order_id': self.order_id,
            'current_state': self.current_state,
            'pair': self.pair,
            'side': self.type,
            'order_type': self.order_type,
            'volume': str(self.volume),
            'volume_executed': str(self.volume_executed),
            'volume_remaining': str(self.volume_remaining),
            'fill_percentage': self.fill_percentage,
            'fill_count': self.fill_count,
            'average_fill_price': str(self.average_fill_price) if self.average_fill_price else None,
            'total_fees': str(self.total_fees_paid),
            'created_at': self.created_at.isoformat(),
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'first_fill_at': self.first_fill_at.isoformat() if self.first_fill_at else None,
            'last_fill_at': self.last_fill_at.isoformat() if self.last_fill_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_active': self.is_active(),
            'is_terminal': self.is_terminal(),
            'state_transitions': len(self.state_history)
        }
    
    def get_state_timeline(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of state changes."""
        timeline = []
        for transition in self.state_history:
            timeline.append({
                'timestamp': transition.timestamp.isoformat(),
                'from_state': transition.from_state,
                'to_state': transition.to_state,
                'event': transition.event,
                'reason': transition.reason
            })
        return timeline
    
    @validator('current_state')
    def validate_state(cls, v):
        """Validate that state is a valid OrderState."""
        if isinstance(v, str):
            return OrderState(v)
        return v


class OrderCreationRequest(BaseModel):
    """Request model for creating new orders."""
    
    pair: str = Field(..., description="Trading pair (e.g., 'XBT/USD')")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type")
    volume: Decimal = Field(..., gt=0, description="Order volume")
    price: Optional[Decimal] = Field(None, gt=0, description="Order price (for limit orders)")
    
    # Optional parameters
    client_order_id: Optional[str] = Field(None, description="Client order ID")
    time_in_force: Optional[str] = Field("GTC", description="Time in force")
    post_only: bool = Field(False, description="Post-only flag")
    tags: List[str] = Field(default_factory=list, description="Order tags")
    
    @validator('volume', 'price', pre=True)
    def parse_decimal(cls, v):
        """Parse decimal values from strings."""
        if v is None:
            return v
        return Decimal(str(v))


def create_order_from_request(request: OrderCreationRequest) -> EnhancedKrakenOrder:
    """
    Create an EnhancedKrakenOrder from a creation request.
    
    Args:
        request: Order creation request
        
    Returns:
        New EnhancedKrakenOrder in PENDING_NEW state
    """
    order = EnhancedKrakenOrder(
        order_id="",  # Will be set when submitted to exchange
        pair=request.pair,
        status=OrderStatus.PENDING,  # For base class compatibility
        type=request.side,
        order_type=request.order_type,
        volume=request.volume,
        price=request.price,
        client_order_id=request.client_order_id,
        time_in_force=request.time_in_force,
        post_only=request.post_only,
        tags=request.tags,
        current_state=OrderState.PENDING_NEW
    )
    
    # Record initial state
    order.state_history.append(OrderStateTransition(
        from_state=OrderState.PENDING_NEW,
        to_state=OrderState.PENDING_NEW,
        event=OrderEvent.SUBMIT,  # Creation event
        reason="Order created locally"
    ))
    
    return order


# Export all classes for external use
__all__ = [
    'OrderState',
    'OrderEvent', 
    'OrderStateMachine',
    'OrderStateTransition',
    'EnhancedKrakenOrder',
    'OrderCreationRequest',
    'create_order_from_request'
]
