"""
Unit tests for enhanced order models with state machine logic.

These tests validate:
- Order state machine transitions
- Order lifecycle management
- Fill processing
- State validation
- Error handling

File Location: tests/unit/test_order_models.py
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from trading_systems.exchanges.kraken.order_models import (
    OrderState,
    OrderEvent,
    OrderStateMachine,
    OrderStateTransition,
    EnhancedKrakenOrder,
    OrderCreationRequest,
    create_order_from_request
)
from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType, OrderStatus


class TestOrderStateMachine:
    """Test cases for OrderStateMachine class."""

    def test_valid_transitions_defined(self):
        """Test that valid transitions are properly defined."""
        # Check that all states have defined transitions
        for state in OrderState:
            assert state in OrderStateMachine.VALID_TRANSITIONS

        # Check specific important transitions
        assert OrderState.OPEN in OrderStateMachine.VALID_TRANSITIONS[OrderState.PENDING_SUBMIT]
        assert OrderState.FILLED in OrderStateMachine.VALID_TRANSITIONS[OrderState.OPEN]
        assert OrderState.PARTIALLY_FILLED in OrderStateMachine.VALID_TRANSITIONS[OrderState.OPEN]

    def test_is_valid_transition(self):
        """Test state transition validation."""
        # Valid transitions
        assert OrderStateMachine.is_valid_transition(OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT)
        assert OrderStateMachine.is_valid_transition(OrderState.PENDING_SUBMIT, OrderState.OPEN)
        assert OrderStateMachine.is_valid_transition(OrderState.OPEN, OrderState.FILLED)
        assert OrderStateMachine.is_valid_transition(OrderState.OPEN, OrderState.PARTIALLY_FILLED)
        assert OrderStateMachine.is_valid_transition(OrderState.PARTIALLY_FILLED, OrderState.FILLED)

        # Invalid transitions
        assert not OrderStateMachine.is_valid_transition(OrderState.FILLED, OrderState.OPEN)
        assert not OrderStateMachine.is_valid_transition(OrderState.CANCELED, OrderState.OPEN)
        assert not OrderStateMachine.is_valid_transition(OrderState.REJECTED, OrderState.FILLED)

    def test_get_next_state(self):
        """Test event-driven state transitions."""
        # Test submit event
        next_state = OrderStateMachine.get_next_state(OrderState.PENDING_NEW, OrderEvent.SUBMIT)
        assert next_state == OrderState.PENDING_SUBMIT

        # Test confirm event
        next_state = OrderStateMachine.get_next_state(OrderState.PENDING_SUBMIT, OrderEvent.CONFIRM)
        assert next_state == OrderState.OPEN

        # Test fill events
        next_state = OrderStateMachine.get_next_state(OrderState.OPEN, OrderEvent.PARTIAL_FILL)
        assert next_state == OrderState.PARTIALLY_FILLED

        next_state = OrderStateMachine.get_next_state(OrderState.OPEN, OrderEvent.FULL_FILL)
        assert next_state == OrderState.FILLED

        # Test invalid event
        next_state = OrderStateMachine.get_next_state(OrderState.FILLED, OrderEvent.SUBMIT)
        assert next_state is None

    def test_terminal_states(self):
        """Test terminal state identification."""
        terminal_states = {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED,
                          OrderState.EXPIRED, OrderState.FAILED}

        for state in terminal_states:
            assert OrderStateMachine.is_terminal_state(state)

        non_terminal_states = {OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT,
                              OrderState.OPEN, OrderState.PARTIALLY_FILLED}

        for state in non_terminal_states:
            assert not OrderStateMachine.is_terminal_state(state)

    def test_active_states(self):
        """Test active state identification."""
        active_states = {OrderState.OPEN, OrderState.PARTIALLY_FILLED}

        for state in active_states:
            assert OrderStateMachine.is_active_state(state)

        inactive_states = {OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT,
                          OrderState.FILLED, OrderState.CANCELED}

        for state in inactive_states:
            assert not OrderStateMachine.is_active_state(state)

    def test_pending_states(self):
        """Test pending state identification."""
        pending_states = {OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT}

        for state in pending_states:
            assert OrderStateMachine.is_pending_state(state)

        non_pending_states = {OrderState.OPEN, OrderState.FILLED, OrderState.CANCELED}

        for state in non_pending_states:
            assert not OrderStateMachine.is_pending_state(state)


class TestOrderStateTransition:
    """Test cases for OrderStateTransition class."""

    def test_transition_creation(self):
        """Test state transition record creation."""
        transition = OrderStateTransition(
            from_state=OrderState.PENDING_NEW,
            to_state=OrderState.PENDING_SUBMIT,
            event=OrderEvent.SUBMIT,
            reason="Order submitted to exchange"
        )

        assert transition.from_state == OrderState.PENDING_NEW
        assert transition.to_state == OrderState.PENDING_SUBMIT
        assert transition.event == OrderEvent.SUBMIT
        assert transition.reason == "Order submitted to exchange"
        assert isinstance(transition.timestamp, datetime)

    def test_transition_with_exchange_data(self):
        """Test transition with exchange data."""
        exchange_data = {"kraken_order_id": "ORDER123", "status": "open"}

        transition = OrderStateTransition(
            from_state=OrderState.PENDING_SUBMIT,
            to_state=OrderState.OPEN,
            event=OrderEvent.CONFIRM,
            exchange_data=exchange_data
        )

        assert transition.exchange_data == exchange_data


class TestEnhancedKrakenOrder:
    """Test cases for EnhancedKrakenOrder class."""

    @pytest.fixture
    def sample_order(self):
        """Create a sample order for testing."""
        return EnhancedKrakenOrder(
            order_id="ORDER_123",
            pair="XBT/USD",
            status=OrderStatus.OPEN,
            type=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("1.0"),
            price=Decimal("50000.00"),
            client_order_id="CLIENT_123"
        )

    def test_order_creation(self, sample_order):
        """Test enhanced order creation."""
        assert sample_order.order_id == "ORDER_123"
        assert sample_order.pair == "XBT/USD"
        assert sample_order.current_state == OrderState.PENDING_NEW
        assert len(sample_order.state_history) == 0
        assert sample_order.fill_count == 0
        assert sample_order.total_fees_paid == Decimal('0')

    def test_state_transition(self, sample_order):
        """Test order state transitions."""
        # Test valid transition
        success = sample_order.transition_to(
            OrderState.PENDING_SUBMIT,
            OrderEvent.SUBMIT,
            "Order submitted to exchange"
        )

        assert success
        assert sample_order.current_state == OrderState.PENDING_SUBMIT
        assert len(sample_order.state_history) == 1
        assert sample_order.state_history[0].from_state == OrderState.PENDING_NEW
        assert sample_order.state_history[0].to_state == OrderState.PENDING_SUBMIT
        assert sample_order.submitted_at is not None

    def test_invalid_state_transition(self, sample_order):
        """Test invalid state transition rejection."""
        # Try to transition directly to FILLED from PENDING_NEW (invalid)
        success = sample_order.transition_to(
            OrderState.FILLED,
            OrderEvent.FULL_FILL,
            "Invalid transition"
        )

        assert not success
        assert sample_order.current_state == OrderState.PENDING_NEW
        assert len(sample_order.state_history) == 0

    def test_fill_processing(self, sample_order):
        """Test order fill processing."""
        # Set up order in OPEN state
        sample_order.current_state = OrderState.OPEN

        # Process partial fill
        fill_success = sample_order.handle_fill(
            fill_volume=Decimal("0.3"),
            fill_price=Decimal("50100.00"),
            fill_fee=Decimal("5.01")
        )

        assert fill_success
        assert sample_order.current_state == OrderState.PARTIALLY_FILLED
        assert sample_order.volume_executed == Decimal("0.3")
        assert sample_order.fill_count == 1
        assert sample_order.average_fill_price == Decimal("50100.00")
        assert sample_order.total_fees_paid == Decimal("5.01")
        assert sample_order.first_fill_at is not None
        assert sample_order.last_fill_at is not None

    def test_complete_fill(self, sample_order):
        """Test complete order fill."""
        # Set up order in OPEN state
        sample_order.current_state = OrderState.OPEN

        # Process complete fill
        fill_success = sample_order.handle_fill(
            fill_volume=Decimal("1.0"),
            fill_price=Decimal("50000.00"),
            fill_fee=Decimal("10.00")
        )

        assert fill_success
        assert sample_order.current_state == OrderState.FILLED
        assert sample_order.volume_executed == Decimal("1.0")
        assert sample_order.fill_percentage == 100.0
        assert sample_order.is_fully_filled
        assert sample_order.completed_at is not None

    def test_multiple_fills(self, sample_order):
        """Test multiple partial fills leading to complete fill."""
        # Set up order in OPEN state
        sample_order.current_state = OrderState.OPEN

        # First partial fill
        sample_order.handle_fill(
            fill_volume=Decimal("0.4"),
            fill_price=Decimal("50000.00"),
            fill_fee=Decimal("4.00")
        )

        assert sample_order.current_state == OrderState.PARTIALLY_FILLED
        assert sample_order.volume_executed == Decimal("0.4")
        assert sample_order.fill_count == 1

        # Second partial fill
        sample_order.handle_fill(
            fill_volume=Decimal("0.3"),
            fill_price=Decimal("50200.00"),
            fill_fee=Decimal("3.01")
        )

        assert sample_order.current_state == OrderState.PARTIALLY_FILLED
        assert sample_order.volume_executed == Decimal("0.7")
        assert sample_order.fill_count == 2

        # Calculate expected average price: (0.4 * 50000 + 0.3 * 50200) / 0.7
        expected_avg = (Decimal("0.4") * Decimal("50000.00") + Decimal("0.3") * Decimal("50200.00")) / Decimal("0.7")
        assert abs(sample_order.average_fill_price - expected_avg) < Decimal("0.01")

        # Final fill to complete order
        sample_order.handle_fill(
            fill_volume=Decimal("0.3"),
            fill_price=Decimal("50100.00"),
            fill_fee=Decimal("3.00")
        )

        assert sample_order.current_state == OrderState.FILLED
        assert sample_order.volume_executed == Decimal("1.0")
        assert sample_order.fill_count == 3
        assert sample_order.total_fees_paid == Decimal("10.01")

    def test_order_capabilities(self, sample_order):
        """Test order capability checks."""
        # Test pending order
        assert not sample_order.can_be_canceled()
        assert not sample_order.can_be_modified()
        assert not sample_order.is_active()
        assert sample_order.is_pending()
        assert not sample_order.is_terminal()

        # Transition to OPEN state
        sample_order.current_state = OrderState.OPEN

        assert sample_order.can_be_canceled()
        assert sample_order.can_be_modified()
        assert sample_order.is_active()
        assert not sample_order.is_pending()
        assert not sample_order.is_terminal()

        # Transition to FILLED state
        sample_order.current_state = OrderState.FILLED

        assert not sample_order.can_be_canceled()
        assert not sample_order.can_be_modified()
        assert not sample_order.is_active()
        assert not sample_order.is_pending()
        assert sample_order.is_terminal()

    def test_execution_summary(self, sample_order):
        """Test execution summary generation."""
        # Set up order with some execution
        sample_order.current_state = OrderState.PARTIALLY_FILLED
        sample_order.volume_executed = Decimal("0.5")
        sample_order.fill_count = 2
        sample_order.average_fill_price = Decimal("50050.00")
        sample_order.total_fees_paid = Decimal("5.00")

        summary = sample_order.get_execution_summary()

        assert summary['order_id'] == "ORDER_123"
        assert summary['current_state'] == OrderState.PARTIALLY_FILLED
        assert summary['pair'] == "XBT/USD"
        assert summary['side'] == OrderSide.BUY
        assert summary['volume'] == "1.0"
        assert summary['volume_executed'] == "0.5"
        assert summary['fill_percentage'] == 50.0
        assert summary['fill_count'] == 2
        assert summary['average_fill_price'] == "50050.00"
        assert summary['total_fees'] == "5.00"
        assert summary['is_active'] == True
        assert summary['is_terminal'] == False

    def test_state_timeline(self, sample_order):
        """Test state timeline generation."""
        # Add some state transitions
        sample_order.transition_to(OrderState.PENDING_SUBMIT, OrderEvent.SUBMIT, "Submitted")
        sample_order.transition_to(OrderState.OPEN, OrderEvent.CONFIRM, "Confirmed")
        sample_order.transition_to(OrderState.PARTIALLY_FILLED, OrderEvent.PARTIAL_FILL, "First fill")

        timeline = sample_order.get_state_timeline()

        assert len(timeline) == 3
        assert timeline[0]['to_state'] == OrderState.PENDING_SUBMIT
        assert timeline[0]['event'] == OrderEvent.SUBMIT
        assert timeline[1]['to_state'] == OrderState.OPEN
        assert timeline[2]['to_state'] == OrderState.PARTIALLY_FILLED

    def test_lifecycle_timestamps(self, sample_order):
        """Test lifecycle timestamp updates."""
        start_time = datetime.now()

        # Test submission timestamp
        sample_order.transition_to(OrderState.PENDING_SUBMIT, OrderEvent.SUBMIT)
        assert sample_order.submitted_at is not None
        assert sample_order.submitted_at >= start_time

        # Test first fill timestamp
        sample_order.transition_to(OrderState.OPEN, OrderEvent.CONFIRM)
        sample_order.handle_fill(Decimal("0.3"), Decimal("50000.00"))

        assert sample_order.first_fill_at is not None
        assert sample_order.last_fill_at is not None
        assert sample_order.first_fill_at == sample_order.last_fill_at

        # Test completion timestamp
        sample_order.handle_fill(Decimal("0.7"), Decimal("50100.00"))

        assert sample_order.completed_at is not None
        assert sample_order.last_fill_at >= sample_order.first_fill_at


class TestOrderCreationRequest:
    """Test cases for OrderCreationRequest class."""

    def test_valid_order_request(self):
        """Test valid order creation request."""
        request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("1.0"),
            price=Decimal("50000.00"),
            client_order_id="CLIENT_123",
            tags=["test", "automated"]
        )

        assert request.pair == "XBT/USD"
        assert request.side == OrderSide.BUY
        assert request.order_type == OrderType.LIMIT
        assert request.volume == Decimal("1.0")
        assert request.price == Decimal("50000.00")
        assert request.client_order_id == "CLIENT_123"
        assert request.tags == ["test", "automated"]

    def test_market_order_request(self):
        """Test market order request (no price)."""
        request = OrderCreationRequest(
            pair="ETH/USD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            volume=Decimal("2.5")
        )

        assert request.pair == "ETH/USD"
        assert request.side == OrderSide.SELL
        assert request.order_type == OrderType.MARKET
        assert request.volume == Decimal("2.5")
        assert request.price is None

    def test_invalid_volume(self):
        """Test validation of invalid volume."""
        with pytest.raises(ValueError):
            OrderCreationRequest(
                pair="XBT/USD",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                volume=Decimal("0"),  # Invalid: must be > 0
                price=Decimal("50000.00")
            )

    def test_decimal_string_parsing(self):
        """Test decimal parsing from strings."""
        request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume="1.5",  # String input
            price="50000.00"  # String input
        )

        assert request.volume == Decimal("1.5")
        assert request.price == Decimal("50000.00")


class TestOrderCreationFunction:
    """Test cases for create_order_from_request function."""

    def test_create_order_from_request(self):
        """Test order creation from request."""
        request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("1.0"),
            price=Decimal("50000.00"),
            client_order_id="CLIENT_123",
            time_in_force="GTC",
            post_only=True,
            tags=["test"]
        )

        order = create_order_from_request(request)

        assert isinstance(order, EnhancedKrakenOrder)
        assert order.pair == "XBT/USD"
        assert order.type == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.volume == Decimal("1.0")
        assert order.price == Decimal("50000.00")
        assert order.client_order_id == "CLIENT_123"
        assert order.time_in_force == "GTC"
        assert order.post_only == True
        assert order.tags == ["test"]
        assert order.current_state == OrderState.PENDING_NEW
        assert len(order.state_history) == 1

    def test_market_order_creation(self):
        """Test market order creation."""
        request = OrderCreationRequest(
            pair="ETH/USD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            volume=Decimal("2.0")
        )

        order = create_order_from_request(request)

        assert order.order_type == OrderType.MARKET
        assert order.price is None
        assert order.current_state == OrderState.PENDING_NEW


class TestIntegration:
    """Integration tests for order state machine workflow."""

    def test_complete_order_lifecycle(self):
        """Test complete order lifecycle from creation to fill."""
        # Create order request
        request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("1.0"),
            price=Decimal("50000.00")
        )

        # Create order
        order = create_order_from_request(request)
        assert order.current_state == OrderState.PENDING_NEW

        # Submit order
        assert order.transition_to(OrderState.PENDING_SUBMIT, OrderEvent.SUBMIT)
        assert order.submitted_at is not None

        # Exchange confirms order
        assert order.transition_to(OrderState.OPEN, OrderEvent.CONFIRM)
        assert order.is_active()

        # Partial fill
        assert order.handle_fill(Decimal("0.3"), Decimal("50100.00"), Decimal("3.01"))
        assert order.current_state == OrderState.PARTIALLY_FILLED
        assert order.volume_executed == Decimal("0.3")

        # Complete fill
        assert order.handle_fill(Decimal("0.7"), Decimal("49900.00"), Decimal("6.99"))
        assert order.current_state == OrderState.FILLED
        assert order.is_terminal()
        assert order.completed_at is not None

        # Verify execution summary
        summary = order.get_execution_summary()
        assert summary['fill_count'] == 2
        assert summary['total_fees'] == "10.00"
        assert summary['is_terminal'] == True

    def test_order_cancellation_workflow(self):
        """Test order cancellation workflow."""
        request = OrderCreationRequest(
            pair="ETH/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            volume=Decimal("2.0"),
            price=Decimal("3000.00")
        )

        order = create_order_from_request(request)

        # Submit and confirm order
        order.transition_to(OrderState.PENDING_SUBMIT, OrderEvent.SUBMIT)
        order.transition_to(OrderState.OPEN, OrderEvent.CONFIRM)

        assert order.can_be_canceled()

        # Cancel order
        assert order.transition_to(OrderState.CANCELED, OrderEvent.CANCEL_CONFIRM)
        assert order.current_state == OrderState.CANCELED
        assert order.is_terminal()
        assert not order.can_be_canceled()
        assert order.completed_at is not None

    def test_order_rejection_workflow(self):
        """Test order rejection workflow."""
        request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("100.0"),  # Large order that might be rejected
            price=Decimal("1000.00")   # Low price that might be rejected
        )

        order = create_order_from_request(request)

        # Submit order
        order.transition_to(OrderState.PENDING_SUBMIT, OrderEvent.SUBMIT)

        # Exchange rejects order
        assert order.transition_to(OrderState.REJECTED, OrderEvent.REJECT,
                                 "Insufficient funds",
                                 {"error_code": "INSUFFICIENT_FUNDS"})

        assert order.current_state == OrderState.REJECTED
        assert order.is_terminal()
        assert not order.is_active()

        # Check rejection was recorded
        timeline = order.get_state_timeline()
        rejection_event = timeline[-1]
        assert rejection_event['to_state'] == OrderState.REJECTED
        assert rejection_event['reason'] == "Insufficient funds"


# Test configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
