"""
Order Manager for Kraken Trading System - FIXED IMPORTS

This module provides comprehensive order lifecycle management, integrating with the
AccountDataManager and providing order persistence, validation, and real-time updates.

File Location: src/trading_system/exchanges/kraken/order_manager.py
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Callable
from collections import defaultdict, deque
from decimal import Decimal

# FIXED IMPORTS - Try both possible import paths
try:
    # Try trading_system (singular) first
    from ...utils.logger import LoggerMixin
    from ...utils.exceptions import (
        OrderError,
        InvalidOrderError,
        RiskManagementError,
        WebSocketError
    )
    from .order_models import (
        OrderState,
        OrderEvent,
        OrderStateMachine,
        EnhancedKrakenOrder,
        OrderCreationRequest,
        create_order_from_request
    )
    from .account_models import OrderSide, OrderType, OrderStatus
    from .account_data_manager import AccountDataManager
except ImportError:
    # Fallback to absolute imports if relative imports fail
    import sys
    from pathlib import Path

    # Add src to path
    src_path = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(src_path))

    try:
        from trading_system.utils.logger import LoggerMixin
        from trading_system.utils.exceptions import (
            OrderError,
            InvalidOrderError,
            RiskManagementError,
            WebSocketError
        )
        from trading_system.exchanges.kraken.order_models import (
            OrderState,
            OrderEvent,
            OrderStateMachine,
            EnhancedKrakenOrder,
            OrderCreationRequest,
            create_order_from_request
        )
        from trading_system.exchanges.kraken.account_models import OrderSide, OrderType, OrderStatus
        from trading_system.exchanges.kraken.account_data_manager import AccountDataManager
    except ImportError:
        try:
            from trading_systems.utils.logger import LoggerMixin
            from trading_systems.utils.exceptions import (
                OrderError,
                InvalidOrderError,
                RiskManagementError,
                WebSocketError
            )
            from trading_systems.exchanges.kraken.order_models import (
                OrderState,
                OrderEvent,
                OrderStateMachine,
                EnhancedKrakenOrder,
                OrderCreationRequest,
                create_order_from_request
            )
            from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType, OrderStatus
            from trading_systems.exchanges.kraken.account_data_manager import AccountDataManager
        except ImportError as e:
            raise ImportError(f"Could not import required modules. Check your project structure: {e}")


class OrderManager(LoggerMixin):
    """
    Comprehensive order lifecycle management system.

    This class manages the complete order lifecycle from creation to completion,
    integrating with AccountDataManager for real-time state synchronization
    and providing order persistence, validation, and event handling.
    """

    def __init__(self, account_manager: Optional[AccountDataManager] = None):
        super().__init__()

        # Core dependencies
        self.account_manager = account_manager or AccountDataManager()

        # Order storage and tracking
        self._orders: Dict[str, EnhancedKrakenOrder] = {}  # order_id -> order
        self._client_orders: Dict[str, str] = {}  # client_order_id -> order_id
        self._orders_by_pair: Dict[str, Set[str]] = defaultdict(set)
        self._orders_by_state: Dict[OrderState, Set[str]] = defaultdict(set)

        # Order validation and risk management
        self._validators: List[Callable[[OrderCreationRequest], bool]] = []
        self._risk_checks: List[Callable[[EnhancedKrakenOrder], bool]] = []

        # Event handling
        self._event_handlers: Dict[OrderEvent, List[Callable]] = defaultdict(list)
        self._state_change_handlers: List[Callable[[EnhancedKrakenOrder, OrderState, OrderState], None]] = []

        # Order recovery and persistence
        self._recovery_queue: deque = deque(maxlen=1000)
        self._persistence_enabled = True

        # Statistics and monitoring
        self._stats = {
            'orders_created': 0,
            'orders_submitted': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'validation_failures': 0,
            'risk_check_failures': 0,
            'last_order_time': None,
            'last_fill_time': None
        }

        self.log_info("OrderManager initialized",
                     has_account_manager=self.account_manager is not None)

    # ORDER CREATION AND SUBMISSION

    async def create_order(self, request: OrderCreationRequest) -> EnhancedKrakenOrder:
        """
        Create a new order from a creation request.

        Args:
            request: Order creation request with validated parameters

        Returns:
            New order in PENDING_NEW state

        Raises:
            InvalidOrderError: If order validation fails
            RiskManagementError: If risk checks fail
        """
        try:
            # Validate order request
            if not self._validate_order_request(request):
                raise InvalidOrderError("Order request validation failed")

            # Create order from request
            order = create_order_from_request(request)

            # Generate internal order ID if not provided
            if not order.order_id:
                order.order_id = self._generate_order_id()

            # Run pre-creation risk checks
            if not self._run_risk_checks(order):
                raise RiskManagementError("Order failed risk management checks")

            # Store order
            self._add_order(order)

            # Update statistics
            self._stats['orders_created'] += 1
            self._stats['last_order_time'] = datetime.now()

            # Trigger event handlers
            await self._trigger_event_handlers(OrderEvent.SUBMIT, order)

            self.log_info(
                "Order created",
                order_id=order.order_id,
                client_order_id=order.client_order_id,
                pair=order.pair,
                side=order.type,
                volume=str(order.volume),
                price=str(order.price) if order.price else None
            )

            return order

        except Exception as e:
            self._stats['validation_failures'] += 1
            self.log_error("Order creation failed", error=e)
            raise

    async def submit_order(self, order_id: str) -> bool:
        """
        Submit an order to the exchange (transition to PENDING_SUBMIT).

        Args:
            order_id: ID of order to submit

        Returns:
            True if submission successful

        Raises:
            OrderError: If order not found or cannot be submitted
        """
        order = self._get_order(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")

        if order.current_state != OrderState.PENDING_NEW:
            raise OrderError(f"Order {order_id} cannot be submitted from state {order.current_state}")

        # Transition to pending submit
        success = order.transition_to(
            OrderState.PENDING_SUBMIT,
            OrderEvent.SUBMIT,
            "Order submitted to exchange"
        )

        if success:
            self._update_order_indices(order, OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT)
            self._stats['orders_submitted'] += 1

            # Trigger event handlers
            await self._trigger_event_handlers(OrderEvent.SUBMIT, order)

            self.log_info("Order submitted", order_id=order_id)

        return success

    # ORDER LIFECYCLE MANAGEMENT

    async def confirm_order(self, order_id: str, exchange_order_id: str,
                          exchange_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Confirm order acceptance by exchange.

        Args:
            order_id: Internal order ID
            exchange_order_id: Exchange-assigned order ID
            exchange_data: Additional data from exchange

        Returns:
            True if confirmation successful
        """
        order = self._get_order(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")

        # Update exchange order ID
        if exchange_order_id:
            order.order_id = exchange_order_id
            # Update internal mapping
            if order_id != exchange_order_id:
                self._orders[exchange_order_id] = self._orders.pop(order_id)

        # Transition to open state
        success = order.transition_to(
            OrderState.OPEN,
            OrderEvent.CONFIRM,
            "Order confirmed by exchange",
            exchange_data
        )

        if success:
            self._update_order_indices(order, OrderState.PENDING_SUBMIT, OrderState.OPEN)

            # Trigger event handlers
            await self._trigger_event_handlers(OrderEvent.CONFIRM, order)

            self.log_info(
                "Order confirmed",
                order_id=order.order_id,
                exchange_order_id=exchange_order_id
            )

        return success

    async def reject_order(self, order_id: str, reason: str,
                         exchange_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark order as rejected by exchange.

        Args:
            order_id: Order ID
            reason: Rejection reason
            exchange_data: Exchange error data

        Returns:
            True if rejection processed successfully
        """
        order = self._get_order(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")

        old_state = order.current_state
        success = order.transition_to(
            OrderState.REJECTED,
            OrderEvent.REJECT,
            f"Order rejected: {reason}",
            exchange_data
        )

        if success:
            self._update_order_indices(order, old_state, OrderState.REJECTED)
            self._stats['orders_rejected'] += 1

            # Trigger event handlers
            await self._trigger_event_handlers(OrderEvent.REJECT, order)

            self.log_error(
                "Order rejected",
                order_id=order_id,
                reason=reason,
                exchange_data=exchange_data
            )

        return success

    async def handle_fill(self, order_id: str, fill_volume: Decimal,
                        fill_price: Decimal, fill_fee: Decimal = Decimal('0'),
                        trade_id: Optional[str] = None) -> bool:
        """
        Process order fill event.

        Args:
            order_id: Order ID
            fill_volume: Volume filled
            fill_price: Fill price
            fill_fee: Fill fee
            trade_id: Trade ID from exchange

        Returns:
            True if fill processed successfully
        """
        order = self._get_order(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")

        # Process fill in order model
        old_state = order.current_state
        success = order.handle_fill(fill_volume, fill_price, fill_fee)

        if success:
            new_state = order.current_state
            self._update_order_indices(order, old_state, new_state)

            # Update statistics
            if new_state == OrderState.FILLED:
                self._stats['orders_filled'] += 1
            self._stats['last_fill_time'] = datetime.now()

            # Determine event type
            event = OrderEvent.FULL_FILL if new_state == OrderState.FILLED else OrderEvent.PARTIAL_FILL

            # Trigger event handlers
            await self._trigger_event_handlers(event, order)

            self.log_info(
                "Order fill processed",
                order_id=order_id,
                fill_volume=str(fill_volume),
                fill_price=str(fill_price),
                total_filled=str(order.volume_executed),
                fill_percentage=f"{order.fill_percentage:.2f}%",
                new_state=new_state,
                trade_id=trade_id
            )

        return success

    async def cancel_order(self, order_id: str, reason: str = "User requested") -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason

        Returns:
            True if cancellation processed successfully
        """
        order = self._get_order(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")

        if not order.can_be_canceled():
            raise OrderError(f"Order {order_id} cannot be canceled from state {order.current_state}")

        old_state = order.current_state
        success = order.transition_to(
            OrderState.CANCELED,
            OrderEvent.CANCEL_CONFIRM,
            f"Order canceled: {reason}"
        )

        if success:
            self._update_order_indices(order, old_state, OrderState.CANCELED)
            self._stats['orders_canceled'] += 1

            # Trigger event handlers
            await self._trigger_event_handlers(OrderEvent.CANCEL_CONFIRM, order)

            self.log_info(
                "Order canceled",
                order_id=order_id,
                reason=reason,
                volume_executed=str(order.volume_executed),
                volume_remaining=str(order.volume_remaining)
            )

        return success

    # ORDER QUERIES AND ACCESS

    def get_order(self, order_id: str) -> Optional[EnhancedKrakenOrder]:
        """Get order by ID."""
        return self._orders.get(order_id)

    def get_order_by_client_id(self, client_order_id: str) -> Optional[EnhancedKrakenOrder]:
        """Get order by client order ID."""
        order_id = self._client_orders.get(client_order_id)
        return self._orders.get(order_id) if order_id else None

    def get_orders_by_pair(self, pair: str) -> List[EnhancedKrakenOrder]:
        """Get all orders for a trading pair."""
        order_ids = self._orders_by_pair.get(pair, set())
        return [self._orders[oid] for oid in order_ids if oid in self._orders]

    def get_orders_by_state(self, state: OrderState) -> List[EnhancedKrakenOrder]:
        """Get all orders in a specific state."""
        order_ids = self._orders_by_state.get(state, set())
        return [self._orders[oid] for oid in order_ids if oid in self._orders]

    def get_active_orders(self) -> List[EnhancedKrakenOrder]:
        """Get all active orders (OPEN and PARTIALLY_FILLED)."""
        active_orders = []
        for state in [OrderState.OPEN, OrderState.PARTIALLY_FILLED]:
            active_orders.extend(self.get_orders_by_state(state))
        return active_orders

    def get_pending_orders(self) -> List[EnhancedKrakenOrder]:
        """Get all pending orders."""
        pending_orders = []
        for state in [OrderState.PENDING_NEW, OrderState.PENDING_SUBMIT]:
            pending_orders.extend(self.get_orders_by_state(state))
        return pending_orders

    # ORDER VALIDATION AND RISK MANAGEMENT

    def add_validator(self, validator: Callable[[OrderCreationRequest], bool]) -> None:
        """Add order validation function."""
        self._validators.append(validator)
        self.log_info("Order validator added", total_validators=len(self._validators))

    def add_risk_check(self, risk_check: Callable[[EnhancedKrakenOrder], bool]) -> None:
        """Add risk management check function."""
        self._risk_checks.append(risk_check)
        self.log_info("Risk check added", total_risk_checks=len(self._risk_checks))

    def _validate_order_request(self, request: OrderCreationRequest) -> bool:
        """Run all validation checks on order request."""
        for validator in self._validators:
            try:
                if not validator(request):
                    self.log_warning("Order validation failed", validator=validator.__name__)
                    return False
            except Exception as e:
                self.log_error("Validator error", validator=validator.__name__, error=e)
                return False
        return True

    def _run_risk_checks(self, order: EnhancedKrakenOrder) -> bool:
        """Run all risk management checks on order."""
        for risk_check in self._risk_checks:
            try:
                if not risk_check(order):
                    self.log_warning("Risk check failed", risk_check=risk_check.__name__)
                    self._stats['risk_check_failures'] += 1
                    return False
            except Exception as e:
                self.log_error("Risk check error", risk_check=risk_check.__name__, error=e)
                return False
        return True

    # EVENT HANDLING

    def add_event_handler(self, event: OrderEvent, handler: Callable) -> None:
        """Add event handler for specific order events."""
        self._event_handlers[event].append(handler)
        self.log_info("Event handler added", event=event, handler=handler.__name__)

    def add_state_change_handler(self, handler: Callable[[EnhancedKrakenOrder, OrderState, OrderState], None]) -> None:
        """Add handler for order state changes."""
        self._state_change_handlers.append(handler)
        self.log_info("State change handler added", handler=handler.__name__)

    async def _trigger_event_handlers(self, event: OrderEvent, order: EnhancedKrakenOrder) -> None:
        """Trigger all handlers for an event."""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(order)
                else:
                    handler(order)
            except Exception as e:
                self.log_error("Event handler error", event=event, handler=handler.__name__, error=e)

    # INTEGRATION WITH ACCOUNT DATA MANAGER

    async def sync_with_account_manager(self) -> None:
        """Synchronize order states with account manager data."""
        if not self.account_manager:
            return

        # Get orders from account manager
        account_orders = self.account_manager.get_open_orders()
        account_trades = self.account_manager.get_recent_trades(100)

        # Sync order states
        for account_order in account_orders.values():
            internal_order = self.get_order(account_order.order_id)
            if internal_order:
                await self._sync_order_state(internal_order, account_order)

        # Process recent trades for fills
        for trade in account_trades:
            await self._process_trade_for_fills(trade)

    async def _sync_order_state(self, internal_order: EnhancedKrakenOrder, account_order) -> None:
        """Sync internal order with account manager order."""
        # Check for execution updates
        if account_order.volume_executed != internal_order.volume_executed:
            fill_volume = account_order.volume_executed - internal_order.volume_executed
            if fill_volume > 0:
                # Estimate fill price (would be better to get from trades)
                fill_price = account_order.price or internal_order.price or Decimal('0')
                await self.handle_fill(internal_order.order_id, fill_volume, fill_price)

        # Check for status changes
        if account_order.status != internal_order.status:
            await self._handle_status_change(internal_order, account_order.status)

    async def _process_trade_for_fills(self, trade) -> None:
        """Process trade data to update order fills."""
        if trade.order_id in self._orders:
            await self.handle_fill(
                trade.order_id,
                trade.volume,
                trade.price,
                trade.fee
            )

    # UTILITY METHODS

    def _add_order(self, order: EnhancedKrakenOrder) -> None:
        """Add order to internal storage and indices."""
        self._orders[order.order_id] = order

        if order.client_order_id:
            self._client_orders[order.client_order_id] = order.order_id

        self._orders_by_pair[order.pair].add(order.order_id)
        self._orders_by_state[order.current_state].add(order.order_id)

    def _get_order(self, order_id: str) -> Optional[EnhancedKrakenOrder]:
        """Get order with error handling."""
        return self._orders.get(order_id)

    def _update_order_indices(self, order: EnhancedKrakenOrder, old_state: OrderState, new_state: OrderState) -> None:
        """Update order indices when state changes."""
        self._orders_by_state[old_state].discard(order.order_id)
        self._orders_by_state[new_state].add(order.order_id)

        # Trigger state change handlers
        for handler in self._state_change_handlers:
            try:
                handler(order, old_state, new_state)
            except Exception as e:
                self.log_error("State change handler error", handler=handler.__name__, error=e)

    def _generate_order_id(self) -> str:
        """Generate unique internal order ID."""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"ORDER_{timestamp}_{len(self._orders)}"

    # STATISTICS AND MONITORING

    def get_statistics(self) -> Dict[str, Any]:
        """Get order manager statistics."""
        active_orders = len(self.get_active_orders())
        pending_orders = len(self.get_pending_orders())

        return {
            **self._stats,
            'total_orders': len(self._orders),
            'active_orders': active_orders,
            'pending_orders': pending_orders,
            'orders_by_state': {
                state.value: len(order_ids)
                for state, order_ids in self._orders_by_state.items()
            },
            'orders_by_pair': {
                pair: len(order_ids)
                for pair, order_ids in self._orders_by_pair.items()
            }
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on order manager."""
        active_orders = self.get_active_orders()
        pending_orders = self.get_pending_orders()

        # Check for stale orders
        now = datetime.now()
        stale_orders = []
        for order in pending_orders:
            if order.created_at and (now - order.created_at).total_seconds() > 300:  # 5 minutes
                stale_orders.append(order.order_id)

        health_status = "healthy"
        if len(stale_orders) > 0:
            health_status = "warning"
        if len(stale_orders) > 5:
            health_status = "critical"

        return {
            'status': health_status,
            'total_orders': len(self._orders),
            'active_orders': len(active_orders),
            'pending_orders': len(pending_orders),
            'stale_orders': len(stale_orders),
            'stale_order_ids': stale_orders,
            'validation_failures': self._stats['validation_failures'],
            'risk_check_failures': self._stats['risk_check_failures'],
            'last_order_time': self._stats['last_order_time'].isoformat() if self._stats['last_order_time'] else None,
            'last_fill_time': self._stats['last_fill_time'].isoformat() if self._stats['last_fill_time'] else None
        }

    # RECOVERY AND PERSISTENCE

    async def recover_orders(self) -> int:
        """
        Recover orders from account manager state.

        Returns:
            Number of orders recovered
        """
        if not self.account_manager:
            return 0

        recovered_count = 0

        try:
            # Get current orders from account manager
            account_orders = self.account_manager.get_open_orders()

            for order_id, account_order in account_orders.items():
                if order_id not in self._orders:
                    # Create order from account data
                    recovered_order = self._create_order_from_account_data(account_order)
                    self._add_order(recovered_order)
                    recovered_count += 1

                    self.log_info(
                        "Order recovered from account data",
                        order_id=order_id,
                        pair=account_order.pair,
                        state=recovered_order.current_state
                    )

            self.log_info("Order recovery completed", recovered_orders=recovered_count)
            return recovered_count

        except Exception as e:
            self.log_error("Order recovery failed", error=e)
            return 0

    def _create_order_from_account_data(self, account_order) -> EnhancedKrakenOrder:
        """Create enhanced order from account manager order data."""
        # Map account order status to our state
        state_mapping = {
            OrderStatus.OPEN: OrderState.OPEN,
            OrderStatus.CLOSED: OrderState.FILLED,
            OrderStatus.CANCELED: OrderState.CANCELED,
            OrderStatus.PENDING: OrderState.PENDING_SUBMIT
        }

        current_state = state_mapping.get(account_order.status, OrderState.UNKNOWN)

        enhanced_order = EnhancedKrakenOrder(
            order_id=account_order.order_id,
            pair=account_order.pair,
            status=account_order.status,
            type=account_order.type,
            order_type=account_order.order_type,
            volume=account_order.volume,
            volume_executed=account_order.volume_executed,
            price=account_order.price,
            current_state=current_state,
            created_at=datetime.now(),  # Approximate
            submitted_at=datetime.now() if current_state != OrderState.PENDING_NEW else None
        )

        return enhanced_order

    # CLEANUP AND MAINTENANCE

    async def cleanup_terminal_orders(self, older_than_hours: int = 24) -> int:
        """
        Clean up terminal orders older than specified time.

        Args:
            older_than_hours: Remove orders older than this many hours

        Returns:
            Number of orders cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        cleaned_count = 0

        terminal_states = {OrderState.FILLED, OrderState.CANCELED, OrderState.REJECTED, OrderState.EXPIRED}
        orders_to_remove = []

        for order_id, order in self._orders.items():
            if (order.current_state in terminal_states and
                order.completed_at and
                order.completed_at < cutoff_time):
                orders_to_remove.append(order_id)

        for order_id in orders_to_remove:
            order = self._orders[order_id]
            self._remove_order(order)
            cleaned_count += 1

            self.log_info(
                "Terminal order cleaned up",
                order_id=order_id,
                state=order.current_state,
                completed_at=order.completed_at.isoformat()
            )

        if cleaned_count > 0:
            self.log_info("Order cleanup completed", cleaned_orders=cleaned_count)

        return cleaned_count

    def _remove_order(self, order: EnhancedKrakenOrder) -> None:
        """Remove order from all indices and storage."""
        order_id = order.order_id

        # Remove from main storage
        self._orders.pop(order_id, None)

        # Remove from client ID mapping
        if order.client_order_id:
            self._client_orders.pop(order.client_order_id, None)

        # Remove from indices
        self._orders_by_pair[order.pair].discard(order_id)
        self._orders_by_state[order.current_state].discard(order_id)

    # BULK OPERATIONS

    async def cancel_all_orders(self, pair: Optional[str] = None,
                              reason: str = "Bulk cancellation") -> List[str]:
        """
        Cancel all active orders, optionally filtered by pair.

        Args:
            pair: Trading pair to filter by (None for all pairs)
            reason: Cancellation reason

        Returns:
            List of canceled order IDs
        """
        active_orders = self.get_active_orders()

        if pair:
            active_orders = [order for order in active_orders if order.pair == pair]

        canceled_orders = []

        for order in active_orders:
            try:
                success = await self.cancel_order(order.order_id, reason)
                if success:
                    canceled_orders.append(order.order_id)
            except Exception as e:
                self.log_error(
                    "Failed to cancel order in bulk operation",
                    order_id=order.order_id,
                    error=e
                )

        self.log_info(
            "Bulk cancellation completed",
            pair=pair or "ALL",
            canceled_count=len(canceled_orders),
            attempted_count=len(active_orders)
        )

        return canceled_orders

    async def get_order_summary(self, pair: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive order summary.

        Args:
            pair: Trading pair to filter by (None for all pairs)

        Returns:
            Order summary dictionary
        """
        orders = list(self._orders.values())

        if pair:
            orders = [order for order in orders if order.pair == pair]

        # Calculate summary statistics
        total_orders = len(orders)
        active_orders = [order for order in orders if order.is_active()]
        pending_orders = [order for order in orders if order.is_pending()]
        terminal_orders = [order for order in orders if order.is_terminal()]

        # Volume statistics
        total_volume = sum(order.volume for order in orders)
        executed_volume = sum(order.volume_executed for order in orders)

        # State breakdown
        state_counts = {}
        for state in OrderState:
            state_counts[state.value] = len([order for order in orders if order.current_state == state])

        # Side breakdown
        buy_orders = [order for order in orders if order.type == OrderSide.BUY]
        sell_orders = [order for order in orders if order.type == OrderSide.SELL]

        return {
            'pair': pair or 'ALL',
            'total_orders': total_orders,
            'active_orders': len(active_orders),
            'pending_orders': len(pending_orders),
            'terminal_orders': len(terminal_orders),
            'total_volume': str(total_volume),
            'executed_volume': str(executed_volume),
            'execution_rate': float(executed_volume / total_volume * 100) if total_volume > 0 else 0.0,
            'state_breakdown': state_counts,
            'buy_orders': len(buy_orders),
            'sell_orders': len(sell_orders),
            'order_types': {
                order_type.value: len([order for order in orders if order.order_type == order_type])
                for order_type in OrderType
            }
        }

    def has_order(self, order_id: str) -> bool:
        """
        Check if an order exists in the manager.

        Args:
            order_id: The order ID to check

        Returns:
            True if the order exists, False otherwise
        """
        return order_id in self._orders

    def get_order(self, order_id: str) -> Optional[EnhancedKrakenOrder]:
        """
        Get an order by its ID.

        Args:
            order_id: The order ID to retrieve

        Returns:
            The order if found, None otherwise
        """
        return self._orders.get(order_id)

    def get_all_orders(self) -> List[EnhancedKrakenOrder]:
        """
        Get all orders managed by this OrderManager.

        Returns:
            List of all orders
        """
        return list(self._orders.values())

    def get_active_orders(self) -> List[EnhancedKrakenOrder]:
        """
        Get all active orders (not filled, canceled, or rejected).

        Returns:
            List of active orders
        """
        active_states = {
            OrderState.PENDING_NEW,
            OrderState.PENDING_SUBMIT,
            OrderState.OPEN,
            OrderState.PARTIALLY_FILLED
        }

        return [
            order for order in self._orders.values()
            if order.state in active_states
        ]

    def get_pending_orders(self) -> List[EnhancedKrakenOrder]:
        """
        Get all pending orders (not yet submitted).

        Returns:
            List of pending orders
        """
        pending_states = {
            OrderState.PENDING_NEW,
            OrderState.PENDING_SUBMIT
        }

        return [
            order for order in self._orders.values()
            if order.state in pending_states
        ]

    async def sync_order_from_websocket(self, order_id: str, order_info: Dict[str, Any]) -> None:
        """
        Sync order state from WebSocket openOrders feed.

        Args:
            order_id: The order ID to sync
            order_info: Order information from WebSocket
        """
        try:
            order = self._orders.get(order_id)
            if not order:
                self.log_warning(f"Received WebSocket update for unknown order: {order_id}")
                return

            # Update order fields from WebSocket data
            old_state = order.state

            # Parse WebSocket order status
            ws_status = order_info.get('status', 'unknown')
            ws_vol_exec = Decimal(str(order_info.get('vol_exec', '0')))
            ws_cost = Decimal(str(order_info.get('cost', '0')))
            ws_fee = Decimal(str(order_info.get('fee', '0')))

            # Update executed volume
            if ws_vol_exec != order.volume_executed:
                order.volume_executed = ws_vol_exec
                order.volume_remaining = order.volume - ws_vol_exec

                # Update cost and fees
                if ws_cost > 0:
                    order.cost = ws_cost
                if ws_fee > 0:
                    order.fee = ws_fee

                # Update fill percentage
                if order.volume > 0:
                    order.fill_percentage = float((order.volume_executed / order.volume) * 100)

            # Update order state based on WebSocket status
            new_state = self._map_websocket_status_to_state(ws_status, order.volume_executed, order.volume)

            if new_state != old_state:
                await self._transition_order_state(order, new_state)

            order.last_update = datetime.now()

            self.log_info(
                "Order synced from WebSocket",
                order_id=order_id,
                status=ws_status,
                vol_exec=str(ws_vol_exec),
                old_state=old_state.value,
                new_state=order.state.value
            )

        except Exception as e:
            self.log_error(
                "Error syncing order from WebSocket",
                order_id=order_id,
                error=e
            )

    async def process_fill_update(self, trade_id: str, trade_info: Dict[str, Any]) -> None:
        """
        Process a fill update from WebSocket ownTrades feed.

        Args:
            trade_id: The trade ID
            trade_info: Trade information from WebSocket
        """
        try:
            order_id = trade_info.get('ordertxid')
            if not order_id or order_id not in self._orders:
                return

            order = self._orders[order_id]

            # Extract trade information
            fill_volume = Decimal(str(trade_info.get('vol', '0')))
            fill_price = Decimal(str(trade_info.get('price', '0')))
            fill_fee = Decimal(str(trade_info.get('fee', '0')))
            fill_cost = Decimal(str(trade_info.get('cost', '0')))

            # Update order with fill information
            await self.handle_fill(order_id, fill_volume, fill_price, fill_fee)

            self.log_info(
                "Fill processed from WebSocket",
                trade_id=trade_id,
                order_id=order_id,
                volume=str(fill_volume),
                price=str(fill_price),
                fee=str(fill_fee)
            )

        except Exception as e:
            self.log_error(
                "Error processing fill update",
                trade_id=trade_id,
                error=e
            )

    def _map_websocket_status_to_state(self, ws_status: str, vol_executed: Decimal, total_volume: Decimal) -> OrderState:
        """
        Map WebSocket order status to internal OrderState.

        Args:
            ws_status: WebSocket order status
            vol_executed: Volume executed
            total_volume: Total order volume

        Returns:
            Corresponding OrderState
        """
        if ws_status == 'open':
            if vol_executed == 0:
                return OrderState.OPEN
            elif vol_executed < total_volume:
                return OrderState.PARTIALLY_FILLED
            else:
                return OrderState.FILLED
        elif ws_status == 'closed':
            return OrderState.FILLED
        elif ws_status == 'canceled':
            return OrderState.CANCELED
        elif ws_status == 'expired':
            return OrderState.EXPIRED
        else:
            return OrderState.OPEN  # Default fallback

    async def _transition_order_state(self, order: EnhancedKrakenOrder, new_state: OrderState) -> None:
        """
        Transition order to new state with proper validation and event handling.

        Args:
            order: The order to transition
            new_state: The new state to transition to
        """
        old_state = order.state

        # Validate transition
        if not OrderStateMachine.is_valid_transition(old_state, new_state):
            self.log_warning(
                "Invalid state transition attempted",
                order_id=order.order_id,
                old_state=old_state.value,
                new_state=new_state.value
            )
            return

        # Update order state
        order.state = new_state
        order.last_update = datetime.now()

        # Update indices
        self._update_order_indices(order, old_state, new_state)

        # Update statistics
        self._update_statistics_for_state_change(old_state, new_state)

        self.log_info(
            "Order state transitioned",
            order_id=order.order_id,
            old_state=old_state.value,
            new_state=new_state.value
        )

    def _update_statistics_for_state_change(self, old_state: OrderState, new_state: OrderState) -> None:
        """Update statistics when order state changes."""
        if new_state == OrderState.FILLED:
            self._stats['orders_filled'] += 1
            self._stats['last_fill_time'] = datetime.now()
        elif new_state == OrderState.CANCELED:
            self._stats['orders_canceled'] += 1
        elif new_state == OrderState.REJECTED:
            self._stats['orders_rejected'] += 1
        elif new_state == OrderState.OPEN and old_state == OrderState.PENDING_SUBMIT:
            self._stats['orders_submitted'] += 1


    # ALSO ADD THIS TO FIX THE get_connection_status METHOD:

    def get_orders_summary(self) -> Dict[str, Any]:
        """
        Get summary of all orders from OrderManager.

        Returns:
            Dictionary with order summary information
        """
        if not self.order_manager:
            return {"enabled": False, "orders": []}

        stats = self.order_manager.get_statistics()
        orders = self.order_manager.get_all_orders()

        orders_data = []
        for order in orders:
            orders_data.append({
                "order_id": order.order_id,
                "state": order.state.value,
                "pair": order.pair,
                "type": order.type,
                "volume": str(order.volume),
                "volume_executed": str(order.volume_executed),
                "price": str(order.price) if order.price else None,
                "last_update": order.last_update.isoformat()
            })

        return {
            "enabled": True,
            "statistics": stats,
            "orders": orders_data,
            "total_orders": len(orders)
        }

    # ALSO ADD TO FIX THE EVENT HANDLER COUNT ISSUE:

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status including OrderManager integration."""
        base_status = {
            "public_connected": self.is_public_connected,
            "private_connected": self.is_private_connected,
            "public_subscriptions": list(self.public_subscriptions),
            "private_subscriptions": list(self.private_subscriptions),
            "has_token": self.current_token is not None,
            "token_manager_initialized": self.token_manager is not None,
            "last_heartbeat": self.last_heartbeat,
            "reconnect_attempts": self.reconnect_attempts,
            "ssl_verify_mode": self.ssl_context.verify_mode.name if hasattr(self.ssl_context.verify_mode, 'name') else str(self.ssl_context.verify_mode),
            "ssl_check_hostname": self.ssl_context.check_hostname
        }

        # Add account data status
        if self.account_manager:
            account_stats = self.account_manager.get_statistics()
            base_status.update({
                "account_data_enabled": self._account_data_enabled,
                "account_data_stats": account_stats
            })
        else:
            base_status.update({
                "account_data_enabled": False,
                "account_data_stats": None
            })

        # Add OrderManager status - FIX THE EVENT HANDLER COUNT ISSUE
        if self.order_manager:
            order_stats = self.order_manager.get_statistics()
            base_status.update({
                "order_management_enabled": self._order_management_enabled,
                "order_manager_stats": order_stats,
                "order_event_handlers": {
                    event_type: len(handlers) if isinstance(handlers, list) else 1
                    for event_type, handlers in self._order_event_handlers.items()
                }
            })
        else:
            base_status.update({
                "order_management_enabled": False,
                "order_manager_stats": None,
                "order_event_handlers": {}
            })

        return base_status

# UTILITY FUNCTIONS FOR ORDER MANAGER

def create_basic_validators() -> List[Callable[[OrderCreationRequest], bool]]:
    """Create basic order validation functions."""

    def validate_volume(request: OrderCreationRequest) -> bool:
        """Validate order volume is positive."""
        return request.volume > 0

    def validate_price(request: OrderCreationRequest) -> bool:
        """Validate limit order has positive price."""
        if request.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
            return request.price is not None and request.price > 0
        return True

    def validate_pair_format(request: OrderCreationRequest) -> bool:
        """Validate pair format."""
        return '/' in request.pair and len(request.pair.split('/')) == 2

    return [validate_volume, validate_price, validate_pair_format]


def create_basic_risk_checks() -> List[Callable[[EnhancedKrakenOrder], bool]]:
    """Create basic risk management checks."""

    def check_order_size_limit(order: EnhancedKrakenOrder) -> bool:
        """Check order size doesn't exceed limits."""
        # Example: max 10 BTC per order
        if 'BTC' in order.pair or 'XBT' in order.pair:
            return order.volume <= Decimal('10.0')
        return True

    def check_order_value_limit(order: EnhancedKrakenOrder) -> bool:
        """Check order value doesn't exceed limits."""
        if order.price:
            order_value = order.volume * order.price
            # Example: max $100k per order
            return order_value <= Decimal('100000')
        return True

    return [check_order_size_limit, check_order_value_limit]


# INTEGRATION HELPER FUNCTIONS

async def integrate_order_manager_with_websocket(websocket_client, order_manager: OrderManager) -> None:
    """
    Integrate OrderManager with WebSocket client for real-time updates.

    Args:
        websocket_client: WebSocket client instance
        order_manager: OrderManager instance
    """
    # Add order manager to websocket client
    websocket_client.order_manager = order_manager

    # Set up event handlers for real-time updates
    async def handle_order_update(order_data):
        """Handle order updates from WebSocket."""
        if isinstance(order_data, list) and len(order_data) >= 3:
            channel_name = order_data[2]

            if channel_name == "openOrders":
                await order_manager.sync_with_account_manager()

    # Add handler to websocket client (implementation depends on client structure)
    if hasattr(websocket_client, 'add_private_message_handler'):
        websocket_client.add_private_message_handler(handle_order_update)


# Export main classes and functions
__all__ = [
    'OrderManager',
    'create_basic_validators',
    'create_basic_risk_checks',
    'integrate_order_manager_with_websocket'
]
