#!/usr/bin/env python3
"""
Task 3.3.A: Enhanced WebSocket Order Integration

This script completes the WebSocket client integration with OrderManager,
implementing the missing _sync_order_states method and enhancing real-time
order tracking capabilities.

File: complete_websocket_order_integration.py
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import re

def read_file_safely(file_path: Path) -> str:
    """Read file content safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return ""
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return ""

def write_file_safely(file_path: Path, content: str) -> bool:
    """Write file content safely."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Error writing file {file_path}: {e}")
        return False

def add_missing_websocket_methods():
    """Add missing WebSocket order integration methods."""
    
    print("🔧 Adding Missing WebSocket Order Integration Methods")
    print("=" * 60)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    content = read_file_safely(websocket_path)
    
    if not content:
        return False
    
    # Check if _sync_order_states method already exists
    if '_sync_order_states' in content:
        print("✅ _sync_order_states method already exists")
        return True
    
    print("📝 Adding _sync_order_states method...")
    
    # The complete _sync_order_states method implementation
    sync_order_states_method = '''
    async def _sync_order_states(self, order_data: List[Any]) -> None:
        """
        Sync order states from WebSocket openOrders feed with OrderManager.
        
        This method processes openOrders feed updates and synchronizes the order
        states in the OrderManager with the real-time data from Kraken.
        
        Args:
            order_data: OpenOrders feed data from WebSocket
        """
        if not self.order_manager or len(order_data) < 2:
            return
        
        try:
            orders_dict = order_data[1] if isinstance(order_data[1], dict) else {}
            
            for order_id, order_info in orders_dict.items():
                if isinstance(order_info, dict):
                    # Check if this is an order we're tracking
                    if self.order_manager.has_order(order_id):
                        await self.order_manager.sync_order_from_websocket(order_id, order_info)
                        
                        # Trigger order update event
                        await self._trigger_order_event_handlers(
                            "order_update",
                            {
                                "order_id": order_id,
                                "order_info": order_info,
                                "source": "openOrders"
                            }
                        )
                    else:
                        # Log unknown order (might be from other clients/sessions)
                        self.log_info(
                            "Received update for unknown order",
                            order_id=order_id,
                            status=order_info.get('status', 'unknown')
                        )
        
        except Exception as e:
            self.log_error("Error syncing order states from WebSocket", error=e)

    async def _trigger_order_event_handlers(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Trigger registered order event handlers.
        
        Args:
            event_type: Type of event (fill, order_update, state_change, etc.)
            event_data: Event data to pass to handlers
        """
        handlers = self._order_event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                self.log_error(
                    "Order event handler error",
                    event_type=event_type,
                    handler=getattr(handler, '__name__', 'unknown'),
                    error=e
                )

    def get_orders_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of all orders from OrderManager.
        
        Returns:
            Dictionary containing order statistics and summaries
        """
        if not self.order_manager:
            return {"enabled": False, "orders": [], "total_orders": 0}

        try:
            # Get statistics from OrderManager
            stats = self.order_manager.get_statistics()
            orders = self.order_manager.get_all_orders()

            # Build orders summary
            orders_data = []
            for order in orders:
                orders_data.append({
                    "order_id": order.order_id,
                    "client_order_id": order.client_order_id,
                    "state": order.current_state.value,
                    "pair": order.pair,
                    "side": order.side.value,
                    "order_type": order.order_type.value,
                    "volume": str(order.volume),
                    "volume_executed": str(order.volume_executed),
                    "volume_remaining": str(order.volume_remaining),
                    "fill_percentage": order.fill_percentage,
                    "price": str(order.price) if order.price else None,
                    "average_fill_price": str(order.average_fill_price) if order.average_fill_price else None,
                    "total_fees_paid": str(order.total_fees_paid),
                    "created_at": order.created_at.isoformat(),
                    "last_update": order.last_update.isoformat() if order.last_update else None,
                    "is_active": order.is_active(),
                    "can_be_canceled": order.can_be_canceled()
                })

            # Organize by state
            orders_by_state = {}
            for order in orders:
                state = order.current_state.value
                if state not in orders_by_state:
                    orders_by_state[state] = []
                orders_by_state[state].append(order.order_id)

            return {
                "enabled": True,
                "statistics": stats,
                "orders": orders_data,
                "total_orders": len(orders),
                "orders_by_state": orders_by_state,
                "active_orders": len([o for o in orders if o.is_active()]),
                "pending_orders": len([o for o in orders if o.is_pending()]),
                "terminal_orders": len([o for o in orders if o.is_terminal()])
            }
            
        except Exception as e:
            self.log_error("Error generating orders summary", error=e)
            return {
                "enabled": True, 
                "error": str(e), 
                "orders": [], 
                "total_orders": 0
            }

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a specific order.
        
        Args:
            order_id: The order ID to query
            
        Returns:
            Dictionary containing order status details
        """
        if not self.order_manager:
            return {"error": "OrderManager not initialized"}
        
        order = self.order_manager.get_order(order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}
        
        return {
            "order_id": order.order_id,
            "client_order_id": order.client_order_id,
            "current_state": order.current_state.value,
            "pair": order.pair,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "volume": str(order.volume),
            "volume_executed": str(order.volume_executed),
            "volume_remaining": str(order.volume_remaining),
            "fill_percentage": order.fill_percentage,
            "price": str(order.price) if order.price else None,
            "average_fill_price": str(order.average_fill_price) if order.average_fill_price else None,
            "total_fees_paid": str(order.total_fees_paid),
            "fill_count": order.fill_count,
            "created_at": order.created_at.isoformat(),
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "first_fill_at": order.first_fill_at.isoformat() if order.first_fill_at else None,
            "last_fill_at": order.last_fill_at.isoformat() if order.last_fill_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
            "last_update": order.last_update.isoformat() if order.last_update else None,
            "state_history": [
                {
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "event": transition.event.value,
                    "timestamp": transition.timestamp.isoformat(),
                    "reason": transition.reason
                }
                for transition in order.state_history
            ],
            "is_active": order.is_active(),
            "is_pending": order.is_pending(),
            "is_terminal": order.is_terminal(),
            "can_be_canceled": order.can_be_canceled(),
            "can_be_modified": order.can_be_modified()
        }
'''
    
    # Find the location to insert these methods
    # Look for the _process_trade_fills method and insert after it
    if '_process_trade_fills' in content:
        # Find the end of _process_trade_fills method
        start_pos = content.find('async def _process_trade_fills')
        if start_pos != -1:
            # Find the next method definition
            next_method_pos = content.find('\n    async def ', start_pos + 1)
            if next_method_pos == -1:
                next_method_pos = content.find('\n    def ', start_pos + 1)
            
            if next_method_pos != -1:
                # Insert before the next method
                new_content = content[:next_method_pos] + sync_order_states_method + content[next_method_pos:]
            else:
                # Insert at the end of the class
                class_end = content.rfind('\n\n# ')
                if class_end != -1:
                    new_content = content[:class_end] + sync_order_states_method + content[class_end:]
                else:
                    new_content = content + sync_order_states_method
        else:
            print("❌ Could not find _process_trade_fills method")
            return False
    else:
        print("❌ _process_trade_fills method not found")
        return False
    
    # Write the updated content
    if write_file_safely(websocket_path, new_content):
        print("✅ Added missing WebSocket order integration methods:")
        print("   • _sync_order_states")
        print("   • _trigger_order_event_handlers") 
        print("   • get_orders_summary (enhanced)")
        print("   • get_order_status")
        return True
    else:
        return False

def enhance_order_manager_websocket_methods():
    """Enhance OrderManager with missing WebSocket integration methods."""
    
    print("\n🔧 Enhancing OrderManager WebSocket Integration")
    print("=" * 60)
    
    order_manager_path = Path("src/trading_systems/exchanges/kraken/order_manager.py")
    content = read_file_safely(order_manager_path)
    
    if not content:
        return False
    
    # Check if sync_order_from_websocket method exists
    if 'sync_order_from_websocket' in content:
        print("✅ sync_order_from_websocket method already exists")
        return True
    
    print("📝 Adding enhanced WebSocket integration methods...")
    
    # Enhanced WebSocket integration methods for OrderManager
    websocket_methods = '''
    # ENHANCED WEBSOCKET INTEGRATION METHODS

    async def sync_order_from_websocket(self, order_id: str, order_info: Dict[str, Any]) -> None:
        """
        Sync order state from WebSocket openOrders feed.
        
        This method updates order state based on real-time data from Kraken's
        openOrders WebSocket feed, ensuring local order state matches exchange state.
        
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
            old_state = order.current_state

            # Parse WebSocket order status and execution info
            ws_status = order_info.get('status', 'unknown')
            ws_vol_exec = Decimal(str(order_info.get('vol_exec', '0')))
            ws_cost = Decimal(str(order_info.get('cost', '0')))
            ws_fee = Decimal(str(order_info.get('fee', '0')))

            # Update executed volume and related fields
            if ws_vol_exec != order.volume_executed:
                order.volume_executed = ws_vol_exec
                order.volume_remaining = order.volume - ws_vol_exec

                # Update cost and fees
                if ws_cost > 0:
                    order.cost = ws_cost
                if ws_fee > 0:
                    order.total_fees_paid = ws_fee

                # Update fill percentage
                if order.volume > 0:
                    order.fill_percentage = float((order.volume_executed / order.volume) * 100)

            # Map WebSocket status to internal state
            new_state = self._map_websocket_status_to_state(ws_status, order.volume_executed, order.volume)

            # Transition to new state if changed
            if new_state != old_state:
                success = order.transition_to(
                    new_state,
                    self._get_event_for_transition(old_state, new_state),
                    f"WebSocket sync: {ws_status}",
                    order_info
                )
                
                if success:
                    self._update_order_indices(order, old_state, new_state)
                    
                    # Trigger state change handlers
                    for handler in self._state_change_handlers:
                        try:
                            handler(order, old_state, new_state)
                        except Exception as e:
                            self.log_error("State change handler error", error=e)

            # Update last update timestamp
            order.last_update = datetime.now()

            self.log_info(
                "Order synced from WebSocket",
                order_id=order_id,
                ws_status=ws_status,
                vol_executed=str(ws_vol_exec),
                old_state=old_state.value,
                new_state=order.current_state.value
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
        
        This method processes trade fills and updates the corresponding order
        state and execution information.
        
        Args:
            trade_id: The trade ID
            trade_info: Trade information from WebSocket
        """
        try:
            order_id = trade_info.get('ordertxid')
            if not order_id or order_id not in self._orders:
                self.log_debug(f"Fill for unknown order: {order_id}")
                return

            order = self._orders[order_id]

            # Extract trade information
            fill_volume = Decimal(str(trade_info.get('vol', '0')))
            fill_price = Decimal(str(trade_info.get('price', '0')))
            fill_fee = Decimal(str(trade_info.get('fee', '0')))
            fill_cost = Decimal(str(trade_info.get('cost', '0')))

            # Process the fill
            success = await self.handle_fill(order_id, fill_volume, fill_price, fill_fee, trade_id)
            
            if success:
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
                "Error processing fill update from WebSocket",
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
        status_mapping = {
            'open': OrderState.OPEN,
            'closed': OrderState.FILLED,
            'canceled': OrderState.CANCELED,
            'expired': OrderState.EXPIRED
        }
        
        # Handle execution-based states for open orders
        if ws_status == 'open':
            if vol_executed == 0:
                return OrderState.OPEN
            elif vol_executed < total_volume:
                return OrderState.PARTIALLY_FILLED
            else:
                return OrderState.FILLED
        
        return status_mapping.get(ws_status, OrderState.OPEN)

    def _get_event_for_transition(self, old_state: OrderState, new_state: OrderState) -> OrderEvent:
        """Get appropriate event for state transition."""
        if new_state == OrderState.OPEN and old_state == OrderState.PENDING_SUBMIT:
            return OrderEvent.CONFIRM
        elif new_state == OrderState.PARTIALLY_FILLED:
            return OrderEvent.PARTIAL_FILL
        elif new_state == OrderState.FILLED:
            return OrderEvent.FULL_FILL
        elif new_state == OrderState.CANCELED:
            return OrderEvent.CANCEL_CONFIRM
        elif new_state == OrderState.EXPIRED:
            return OrderEvent.EXPIRE
        else:
            return OrderEvent.RESET

    def has_order(self, order_id: str) -> bool:
        """
        Check if an order exists in the manager.
        
        Args:
            order_id: The order ID to check
            
        Returns:
            True if the order exists, False otherwise
        """
        return order_id in self._orders

    def get_all_orders(self) -> List[EnhancedKrakenOrder]:
        """
        Get all orders managed by this OrderManager.
        
        Returns:
            List of all orders
        """
        return list(self._orders.values())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive OrderManager statistics.
        
        Returns:
            Dictionary containing various statistics
        """
        return self._stats.copy()
'''
    
    # Find a good location to insert the methods
    if '# INTEGRATION WITH ACCOUNT DATA MANAGER' in content:
        insert_pos = content.find('# INTEGRATION WITH ACCOUNT DATA MANAGER')
        new_content = content[:insert_pos] + websocket_methods + '\n    ' + content[insert_pos:]
    elif '__all__ = [' in content:
        insert_pos = content.find('__all__ = [')
        new_content = content[:insert_pos] + websocket_methods + '\n\n' + content[insert_pos:]
    else:
        # Insert near the end of the class
        class_end = content.rfind('    def ')
        if class_end != -1:
            # Find the end of the last method
            next_line = content.find('\n\n', class_end)
            if next_line != -1:
                new_content = content[:next_line] + websocket_methods + content[next_line:]
            else:
                new_content = content + websocket_methods
        else:
            new_content = content + websocket_methods
    
    # Write the updated content
    if write_file_safely(order_manager_path, new_content):
        print("✅ Enhanced OrderManager with WebSocket integration methods:")
        print("   • sync_order_from_websocket")
        print("   • process_fill_update")
        print("   • _map_websocket_status_to_state")
        print("   • _get_event_for_transition")
        print("   • has_order")
        print("   • get_all_orders")
        print("   • get_statistics")
        return True
    else:
        return False

def create_integration_test_script():
    """Create a test script for the enhanced WebSocket integration."""
    
    print("\n🧪 Creating Integration Test Script")
    print("=" * 60)
    
    test_script = '''#!/usr/bin/env python3
"""
Test Script for Task 3.3.A: Enhanced WebSocket Order Integration

This script validates the completed WebSocket order integration functionality.
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.exchanges.kraken.order_manager import OrderManager
    from trading_systems.exchanges.kraken.order_models import OrderCreationRequest
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType
    from trading_systems.utils.logger import get_logger
    print("✅ All required modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class WebSocketOrderIntegrationTest:
    """Test suite for WebSocket order integration."""

    def __init__(self):
        self.logger = get_logger("WebSocketOrderIntegrationTest")
        self.ws_client = KrakenWebSocketClient()
        self.test_results = {}
        self.event_log = []

    async def run_integration_tests(self):
        """Run the complete integration test suite."""
        print("🚀 TASK 3.3.A: WEBSOCKET ORDER INTEGRATION TESTS")
        print("=" * 70)
        
        try:
            # Test 1: Verify method availability
            await self._test_method_availability()
            
            # Test 2: Initialize OrderManager integration
            await self._test_order_manager_initialization()
            
            # Test 3: Test order event handlers
            await self._test_order_event_handlers()
            
            # Test 4: Test order state synchronization
            await self._test_order_state_sync()
            
            # Test 5: Test trade fill processing
            await self._test_trade_fill_processing()
            
            # Test 6: Test orders summary functionality
            await self._test_orders_summary()
            
            # Test 7: Test order status queries
            await self._test_order_status_queries()
            
            # Generate final report
            self._generate_test_report()
            
        except Exception as e:
            self.logger.error("Integration test failed", error=str(e), exc_info=True)
            self.test_results['overall'] = False

    async def _test_method_availability(self):
        """Test 1: Verify all required methods are available."""
        print("1️⃣ Testing Method Availability")
        print("-" * 50)
        
        # WebSocket client methods
        ws_methods = [
            '_sync_order_states',
            '_trigger_order_event_handlers',
            'get_orders_summary',
            'get_order_status',
            'initialize_order_manager'
        ]
        
        missing_ws_methods = []
        for method in ws_methods:
            if hasattr(self.ws_client, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method}")
                missing_ws_methods.append(method)
        
        # OrderManager methods
        order_manager = OrderManager()
        om_methods = [
            'sync_order_from_websocket',
            'process_fill_update',
            'has_order',
            'get_all_orders',
            'get_statistics'
        ]
        
        missing_om_methods = []
        for method in om_methods:
            if hasattr(order_manager, method):
                print(f"   ✅ OrderManager.{method}")
            else:
                print(f"   ❌ OrderManager.{method}")
                missing_om_methods.append(method)
        
        success = len(missing_ws_methods) == 0 and len(missing_om_methods) == 0
        self.test_results['method_availability'] = success
        
        if success:
            print("✅ All required methods are available")
        else:
            print(f"❌ Missing methods: WS={missing_ws_methods}, OM={missing_om_methods}")
        
        print()

    async def _test_order_manager_initialization(self):
        """Test 2: Test OrderManager initialization."""
        print("2️⃣ Testing OrderManager Initialization")
        print("-" * 50)
        
        try:
            await self.ws_client.initialize_order_manager()
            
            # Verify initialization
            if hasattr(self.ws_client, 'order_manager') and self.ws_client.order_manager:
                print("   ✅ OrderManager initialized")
                
                status = self.ws_client.get_connection_status()
                if status.get('order_management_enabled', False):
                    print("   ✅ Order management enabled")
                    self.test_results['order_manager_init'] = True
                else:
                    print("   ❌ Order management not enabled")
                    self.test_results['order_manager_init'] = False
            else:
                print("   ❌ OrderManager not initialized")
                self.test_results['order_manager_init'] = False
                
        except Exception as e:
            print(f"   ❌ Initialization failed: {e}")
            self.test_results['order_manager_init'] = False
        
        print()

    async def _test_order_event_handlers(self):
        """Test 3: Test order event handlers."""
        print("3️⃣ Testing Order Event Handlers")
        print("-" * 50)
        
        try:
            # Define test event handlers
            def state_change_handler(event_data):
                self.event_log.append({
                    'type': 'state_change',
                    'timestamp': datetime.now(),
                    'data': event_data
                })
                print(f"   📈 State change event received: {event_data}")
            
            def fill_handler(event_data):
                self.event_log.append({
                    'type': 'fill',
                    'timestamp': datetime.now(), 
                    'data': event_data
                })
                print(f"   💰 Fill event received: {event_data}")
            
            # Register handlers
            self.ws_client.add_order_event_handler("state_change", state_change_handler)
            self.ws_client.add_order_event_handler("fill", fill_handler)
            
            # Test triggering events
            test_event_data = {
                'order_id': 'TEST_ORDER_123',
                'test': True
            }
            
            await self.ws_client._trigger_order_event_handlers("state_change", test_event_data)
            await self.ws_client._trigger_order_event_handlers("fill", test_event_data)
            
            # Verify events were received
            if len(self.event_log) >= 2:
                print("   ✅ Event handlers working correctly")
                self.test_results['event_handlers'] = True
            else:
                print("   ❌ Event handlers not triggered")
                self.test_results['event_handlers'] = False
                
        except Exception as e:
            print(f"   ❌ Event handler test failed: {e}")
            self.test_results['event_handlers'] = False
        
        print()

    async def _test_order_state_sync(self):
        """Test 4: Test order state synchronization."""
        print("4️⃣ Testing Order State Synchronization")
        print("-" * 50)
        
        try:
            # Create a test order
            order_request = OrderCreationRequest(
                pair="XBT/USD",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                volume=Decimal("0.01"),
                price=Decimal("50000.00")
            )
            
            test_order = await self.ws_client.order_manager.create_order(order_request)
            print(f"   📝 Created test order: {test_order.order_id}")
            
            # Simulate WebSocket order update
            mock_order_data = [
                123456,  # sequence number
                {
                    test_order.order_id: {
                        "status": "open",
                        "vol": "0.01",
                        "vol_exec": "0.005",
                        "cost": "250.00",
                        "fee": "0.25",
                        "price": "50000.00"
                    }
                },
                "openOrders"
            ]
            
            # Test sync
            await self.ws_client._sync_order_states(mock_order_data)
            
            # Verify order was updated
            updated_order = self.ws_client.order_manager.get_order(test_order.order_id)
            if updated_order and updated_order.volume_executed == Decimal("0.005"):
                print("   ✅ Order state synchronized from WebSocket")
                self.test_results['order_state_sync'] = True
            else:
                print("   ❌ Order state sync failed")
                self.test_results['order_state_sync'] = False
                
        except Exception as e:
            print(f"   ❌ Order state sync test failed: {e}")
            self.test_results['order_state_sync'] = False
        
        print()

    async def _test_trade_fill_processing(self):
        """Test 5: Test trade fill processing."""
        print("5️⃣ Testing Trade Fill Processing")
        print("-" * 50)
        
        try:
            # Get test order from previous test
            orders = self.ws_client.order_manager.get_all_orders()
            if not orders:
                print("   ⚠️ No test orders available")
                self.test_results['trade_fill_processing'] = False
                return
            
            test_order = orders[0]
            
            # Simulate trade fill
            mock_trade_data = [
                123457,  # sequence number
                {
                    "TRADE_TEST_456": {
                        "ordertxid": test_order.order_id,
                        "pair": "XBT/USD",
                        "time": 1640995200.0,
                        "type": "buy",
                        "ordertype": "limit",
                        "price": "50000.00",
                        "vol": "0.005",
                        "fee": "0.25",
                        "cost": "250.00"
                    }
                },
                "ownTrades"
            ]
            
            # Process trade fill
            await self.ws_client._process_trade_fills(mock_trade_data)
            
            # Verify fill was processed
            updated_order = self.ws_client.order_manager.get_order(test_order.order_id)
            if updated_order and updated_order.fill_count > 0:
                print("   ✅ Trade fill processed successfully")
                self.test_results['trade_fill_processing'] = True
            else:
                print("   ❌ Trade fill processing failed")
                self.test_results['trade_fill_processing'] = False
                
        except Exception as e:
            print(f"   ❌ Trade fill processing test failed: {e}")
            self.test_results['trade_fill_processing'] = False
        
        print()

    async def _test_orders_summary(self):
        """Test 6: Test orders summary functionality."""
        print("6️⃣ Testing Orders Summary")
        print("-" * 50)
        
        try:
            summary = self.ws_client.get_orders_summary()
            
            # Verify summary structure
            required_fields = ['enabled', 'orders', 'total_orders']
            missing_fields = [field for field in required_fields if field not in summary]
            
            if not missing_fields and summary.get('enabled', False):
                print(f"   ✅ Orders summary generated: {summary['total_orders']} orders")
                print(f"   📊 Active orders: {summary.get('active_orders', 0)}")
                print(f"   📊 Terminal orders: {summary.get('terminal_orders', 0)}")
                self.test_results['orders_summary'] = True
            else:
                print(f"   ❌ Orders summary invalid: missing {missing_fields}")
                self.test_results['orders_summary'] = False
                
        except Exception as e:
            print(f"   ❌ Orders summary test failed: {e}")
            self.test_results['orders_summary'] = False
        
        print()

    async def _test_order_status_queries(self):
        """Test 7: Test order status queries."""
        print("7️⃣ Testing Order Status Queries")
        print("-" * 50)
        
        try:
            orders = self.ws_client.order_manager.get_all_orders()
            if not orders:
                print("   ⚠️ No orders available for status query test")
                self.test_results['order_status_queries'] = False
                return
            
            test_order = orders[0]
            status = await self.ws_client.get_order_status(test_order.order_id)
            
            # Verify status structure
            required_fields = ['order_id', 'current_state', 'pair', 'side', 'order_type']
            missing_fields = [field for field in required_fields if field not in status]
            
            if not missing_fields:
                print(f"   ✅ Order status query successful")
                print(f"   📊 Order ID: {status['order_id']}")
                print(f"   📊 State: {status['current_state']}")
                print(f"   📊 Fill %: {status.get('fill_percentage', 0):.2f}%")
                self.test_results['order_status_queries'] = True
            else:
                print(f"   ❌ Order status query failed: missing {missing_fields}")
                self.test_results['order_status_queries'] = False
                
        except Exception as e:
            print(f"   ❌ Order status query test failed: {e}")
            self.test_results['order_status_queries'] = False
        
        print()

    def _generate_test_report(self):
        """Generate comprehensive test report."""
        print("=" * 70)
        print("📊 TASK 3.3.A INTEGRATION TEST REPORT")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        print()
        
        print("📋 Detailed Test Results:")
        test_descriptions = {
            'method_availability': 'Method Availability Check',
            'order_manager_init': 'OrderManager Initialization',
            'event_handlers': 'Order Event Handlers',
            'order_state_sync': 'Order State Synchronization',
            'trade_fill_processing': 'Trade Fill Processing',
            'orders_summary': 'Orders Summary Generation',
            'order_status_queries': 'Order Status Queries'
        }
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            description = test_descriptions.get(test_name, test_name.replace('_', ' ').title())
            print(f"  {status} - {description}")
        
        print()
        print(f"📊 Event Log Entries: {len(self.event_log)}")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Task 3.3.A: Enhanced WebSocket Order Integration - COMPLETE!")
            print()
            print("🚀 Implemented Features:")
            print("   • Real-time order state synchronization")
            print("   • Trade fill processing from WebSocket feeds")
            print("   • Order event handling system")
            print("   • Comprehensive order status queries")
            print("   • Order summary and statistics")
            print()
            print("🎯 READY FOR TASK 3.3.B: Order Fill Processing System")
            
        elif passed_tests >= total_tests * 0.8:
            print("⚠️ MOSTLY PASSED - Minor issues detected")
            print("Core functionality working, some features need attention")
            
        else:
            print("❌ SIGNIFICANT ISSUES DETECTED")
            print("WebSocket integration needs additional work")
        
        print("=" * 70)


async def main():
    """Main test execution."""
    try:
        test_suite = WebSocketOrderIntegrationTest()
        await test_suite.run_integration_tests()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    test_path = Path("test_websocket_order_integration.py")
    if write_file_safely(test_path, test_script):
        print("✅ Created integration test script: test_websocket_order_integration.py")
        return True
    else:
        return False

def main():
    """Main execution function."""
    print("🚀 TASK 3.3.A: ENHANCED WEBSOCKET ORDER INTEGRATION")
    print("=" * 70)
    print()
    print("This script completes the WebSocket integration with OrderManager")
    print("by implementing missing methods and enhancing real-time capabilities.")
    print()
    
    success_count = 0
    total_tasks = 3
    
    # Task 1: Add missing WebSocket methods
    if add_missing_websocket_methods():
        success_count += 1
    
    # Task 2: Enhance OrderManager integration
    if enhance_order_manager_websocket_methods():
        success_count += 1
    
    # Task 3: Create integration test
    if create_integration_test_script():
        success_count += 1
    
    print("\n" + "=" * 70)
    print("📊 TASK 3.3.A COMPLETION REPORT")
    print("=" * 70)
    print(f"🎯 Tasks Completed: {success_count}/{total_tasks}")
    
    if success_count == total_tasks:
        print("🎉 TASK 3.3.A SUCCESSFULLY COMPLETED!")
        print()
        print("✅ Enhanced WebSocket Order Integration:")
        print("   • Real-time order state synchronization")
        print("   • Trade fill processing from ownTrades feed")
        print("   • Order event handling system")
        print("   • Comprehensive order status queries")
        print("   • Enhanced OrderManager WebSocket methods")
        print()
        print("🧪 Next Steps:")
        print("   1. Run: python3 test_websocket_order_integration.py")
        print("   2. Verify all integration tests pass")
        print("   3. Proceed to Task 3.3.B: Order Fill Processing System")
        
    elif success_count >= 2:
        print("⚠️ MOSTLY COMPLETED - Some tasks may need manual review")
        
    else:
        print("❌ SIGNIFICANT ISSUES - Manual intervention required")
    
    print("=" * 70)
    return success_count == total_tasks


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Task interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
