#!/usr/bin/env python3
"""
Task 3.3.A Validation Test - Enhanced WebSocket Order Integration

This test validates that all WebSocket order integration functionality is working correctly.
Run this test to verify Task 3.3.A completion before proceeding to Task 3.3.B.

Usage: python3 validate_task_3_3_a.py
"""

import asyncio
import sys
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.exchanges.kraken.order_manager import OrderManager
    from trading_systems.exchanges.kraken.order_models import OrderCreationRequest, OrderState, OrderEvent
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType
    from trading_systems.utils.logger import get_logger
    print("✅ All required modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)


class Task33AValidationTest:
    """Comprehensive validation test for Task 3.3.A."""

    def __init__(self):
        self.logger = get_logger("Task33AValidationTest")
        self.ws_client = KrakenWebSocketClient()
        self.test_results = {}
        self.event_log = []
        self.start_time = time.time()

    async def run_validation(self):
        """Run the complete validation test suite."""
        print("🎯 TASK 3.3.A VALIDATION TEST SUITE")
        print("=" * 70)
        print("Testing Enhanced WebSocket Order Integration functionality")
        print()

        try:
            # Core validation tests
            await self._test_websocket_client_methods()
            await self._test_order_manager_methods()  
            await self._test_integration_initialization()
            await self._test_order_event_system()
            await self._test_order_state_synchronization()
            await self._test_trade_fill_processing()
            await self._test_order_queries_and_summary()
            
            # Generate final validation report
            self._generate_validation_report()
            
        except Exception as e:
            self.logger.error("Validation test failed", error=str(e), exc_info=True)
            print(f"❌ CRITICAL ERROR: {e}")

    async def _test_websocket_client_methods(self):
        """Test 1: Validate WebSocket client has required methods."""
        print("1️⃣ Testing WebSocket Client Methods")
        print("-" * 50)
        
        required_methods = [
            '_sync_order_states',
            '_trigger_order_event_handlers', 
            '_process_trade_fills',
            'get_orders_summary',
            'get_order_status',
            'initialize_order_manager',
            'add_order_event_handler',
            'remove_order_event_handler'
        ]
        
        missing_methods = []
        for method in required_methods:
            if hasattr(self.ws_client, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - MISSING")
                missing_methods.append(method)
        
        success = len(missing_methods) == 0
        self.test_results['websocket_client_methods'] = success
        
        if success:
            print("✅ All WebSocket client methods available")
        else:
            print(f"❌ Missing methods: {missing_methods}")
        
        print()

    async def _test_order_manager_methods(self):
        """Test 2: Validate OrderManager has required methods."""
        print("2️⃣ Testing OrderManager Methods")
        print("-" * 50)
        
        order_manager = OrderManager()
        
        required_methods = [
            'sync_order_from_websocket',
            'process_fill_update',
            'has_order',
            'get_all_orders',
            'get_statistics',
            '_map_websocket_status_to_state',
            '_get_event_for_transition'
        ]
        
        missing_methods = []
        for method in required_methods:
            if hasattr(order_manager, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - MISSING")
                missing_methods.append(method)
        
        success = len(missing_methods) == 0
        self.test_results['order_manager_methods'] = success
        
        if success:
            print("✅ All OrderManager methods available")
        else:
            print(f"❌ Missing methods: {missing_methods}")
        
        print()

    async def _test_integration_initialization(self):
        """Test 3: Test OrderManager integration initialization."""
        print("3️⃣ Testing Integration Initialization")
        print("-" * 50)
        
        try:
            # Initialize OrderManager integration
            await self.ws_client.initialize_order_manager()
            
            # Verify integration state
            has_order_manager = hasattr(self.ws_client, 'order_manager') and self.ws_client.order_manager is not None
            
            if has_order_manager:
                print("   ✅ OrderManager integrated with WebSocket client")
                
                # Check connection status
                status = self.ws_client.get_connection_status()
                order_mgmt_enabled = status.get('order_management_enabled', False)
                
                if order_mgmt_enabled:
                    print("   ✅ Order management enabled in WebSocket client")
                    self.test_results['integration_init'] = True
                else:
                    print("   ❌ Order management not enabled")
                    self.test_results['integration_init'] = False
            else:
                print("   ❌ OrderManager not integrated")
                self.test_results['integration_init'] = False
                
        except Exception as e:
            print(f"   ❌ Integration initialization failed: {e}")
            self.test_results['integration_init'] = False
        
        print()

    async def _test_order_event_system(self):
        """Test 4: Test order event handling system."""
        print("4️⃣ Testing Order Event System")
        print("-" * 50)
        
        try:
            events_received = []
            
            # Define test event handlers
            def test_handler(event_data):
                events_received.append({
                    'type': event_data.get('type', 'unknown'),
                    'timestamp': datetime.now(),
                    'data': event_data
                })
                print(f"   📨 Event received: {event_data.get('type', 'unknown')}")
            
            # Register event handlers
            self.ws_client.add_order_event_handler("test_event", test_handler)
            self.ws_client.add_order_event_handler("state_change", test_handler)
            
            # Test triggering events
            test_events = [
                {"type": "test_event", "order_id": "TEST_123", "message": "test"},
                {"type": "state_change", "order_id": "TEST_456", "old_state": "open", "new_state": "filled"}
            ]
            
            for event in test_events:
                await self.ws_client._trigger_order_event_handlers(event["type"], event)
            
            # Verify events were received
            if len(events_received) >= len(test_events):
                print("   ✅ Event system working correctly")
                self.test_results['event_system'] = True
            else:
                print(f"   ❌ Expected {len(test_events)} events, got {len(events_received)}")
                self.test_results['event_system'] = False
                
        except Exception as e:
            print(f"   ❌ Event system test failed: {e}")
            self.test_results['event_system'] = False
        
        print()

    async def _test_order_state_synchronization(self):
        """Test 5: Test order state synchronization from WebSocket."""
        print("5️⃣ Testing Order State Synchronization")
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
            initial_state = test_order.current_state
            initial_vol_exec = test_order.volume_executed
            
            print(f"   📝 Created test order: {test_order.order_id}")
            print(f"   📊 Initial state: {initial_state.value}")
            print(f"   📊 Initial volume executed: {initial_vol_exec}")
            
            # Simulate WebSocket openOrders update with partial fill
            mock_order_data = [
                123456,  # sequence number
                {
                    test_order.order_id: {
                        "status": "open",
                        "vol": "0.01",
                        "vol_exec": "0.005",
                        "cost": "250.00",
                        "fee": "0.25",
                        "price": "50000.00",
                        "stopprice": "0.00000",
                        "limitprice": "0.00000",
                        "misc": "",
                        "oflags": "fciq"
                    }
                },
                "openOrders"
            ]
            
            # Process the sync
            await self.ws_client._sync_order_states(mock_order_data)
            
            # Verify order was updated
            updated_order = self.ws_client.order_manager.get_order(test_order.order_id)
            
            if updated_order:
                new_vol_exec = updated_order.volume_executed
                new_state = updated_order.current_state
                
                print(f"   📊 Updated volume executed: {new_vol_exec}")
                print(f"   📊 Updated state: {new_state.value}")
                
                # Check if synchronization worked
                if new_vol_exec == Decimal("0.005") and new_vol_exec != initial_vol_exec:
                    print("   ✅ Order state synchronized successfully")
                    self.test_results['order_sync'] = True
                else:
                    print("   ❌ Order state sync failed")
                    self.test_results['order_sync'] = False
            else:
                print("   ❌ Updated order not found")
                self.test_results['order_sync'] = False
                
        except Exception as e:
            print(f"   ❌ Order sync test failed: {e}")
            self.test_results['order_sync'] = False
        
        print()

    async def _test_trade_fill_processing(self):
        """Test 6: Test trade fill processing from WebSocket."""
        print("6️⃣ Testing Trade Fill Processing")
        print("-" * 50)
        
        try:
            # Get existing test order
            orders = self.ws_client.order_manager.get_all_orders()
            if not orders:
                print("   ⚠️ No test orders available, creating new one")
                # Create a simple test order
                order_request = OrderCreationRequest(
                    pair="ETH/USD",
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    volume=Decimal("0.1"),
                    price=Decimal("3000.00")
                )
                test_order = await self.ws_client.order_manager.create_order(order_request)
            else:
                test_order = orders[0]
            
            initial_fill_count = test_order.fill_count
            initial_fees = test_order.total_fees_paid
            
            print(f"   📝 Using test order: {test_order.order_id}")
            print(f"   📊 Initial fill count: {initial_fill_count}")
            print(f"   📊 Initial fees: {initial_fees}")
            
            # Simulate ownTrades update with a new fill
            mock_trade_data = [
                123457,  # sequence number
                {
                    "TRADE_TEST_789": {
                        "ordertxid": test_order.order_id,
                        "pair": test_order.pair,
                        "time": 1640995200.0,
                        "type": test_order.side.value,
                        "ordertype": test_order.order_type.value,
                        "price": "50000.00",
                        "vol": "0.005",
                        "fee": "0.25",
                        "cost": "250.00",
                        "margin": "0.00000"
                    }
                },
                "ownTrades"
            ]
            
            # Process the trade fill
            await self.ws_client._process_trade_fills(mock_trade_data)
            
            # Verify fill was processed
            updated_order = self.ws_client.order_manager.get_order(test_order.order_id)
            
            if updated_order:
                new_fill_count = updated_order.fill_count
                new_fees = updated_order.total_fees_paid
                
                print(f"   📊 Updated fill count: {new_fill_count}")
                print(f"   📊 Updated fees: {new_fees}")
                
                # Check if fill was processed
                if new_fill_count > initial_fill_count or new_fees > initial_fees:
                    print("   ✅ Trade fill processed successfully")
                    self.test_results['trade_fill_processing'] = True
                else:
                    print("   ❌ Trade fill processing failed")
                    self.test_results['trade_fill_processing'] = False
            else:
                print("   ❌ Updated order not found")
                self.test_results['trade_fill_processing'] = False
                
        except Exception as e:
            print(f"   ❌ Trade fill processing test failed: {e}")
            self.test_results['trade_fill_processing'] = False
        
        print()

    async def _test_order_queries_and_summary(self):
        """Test 7: Test order queries and summary functionality."""
        print("7️⃣ Testing Order Queries and Summary")
        print("-" * 50)
        
        try:
            # Test orders summary
            summary = self.ws_client.get_orders_summary()
            
            print(f"   📊 Orders summary enabled: {summary.get('enabled', False)}")
            print(f"   📊 Total orders: {summary.get('total_orders', 0)}")
            print(f"   📊 Active orders: {summary.get('active_orders', 0)}")
            
            # Check summary structure
            required_summary_fields = ['enabled', 'orders', 'total_orders']
            summary_valid = all(field in summary for field in required_summary_fields)
            
            if summary_valid and summary.get('enabled', False):
                print("   ✅ Orders summary working correctly")
                summary_success = True
            else:
                print("   ❌ Orders summary validation failed")
                summary_success = False
            
            # Test individual order status query
            orders = self.ws_client.order_manager.get_all_orders()
            if orders:
                test_order = orders[0]
                status = await self.ws_client.get_order_status(test_order.order_id)
                
                print(f"   📊 Order status query for: {test_order.order_id}")
                print(f"   📊 Current state: {status.get('current_state', 'unknown')}")
                print(f"   📊 Fill percentage: {status.get('fill_percentage', 0):.2f}%")
                
                # Check status structure
                required_status_fields = ['order_id', 'current_state', 'pair', 'side']
                status_valid = all(field in status for field in required_status_fields)
                
                if status_valid:
                    print("   ✅ Order status query working correctly")
                    status_success = True
                else:
                    print("   ❌ Order status query validation failed")
                    status_success = False
            else:
                print("   ⚠️ No orders available for status query test")
                status_success = True  # Not a failure if no orders exist
            
            self.test_results['queries_and_summary'] = summary_success and status_success
            
        except Exception as e:
            print(f"   ❌ Queries and summary test failed: {e}")
            self.test_results['queries_and_summary'] = False
        
        print()

    def _generate_validation_report(self):
        """Generate comprehensive validation report."""
        print("=" * 70)
        print("📊 TASK 3.3.A VALIDATION REPORT")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        runtime = time.time() - self.start_time
        
        print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        print(f"⏱️ Total Runtime: {runtime:.1f} seconds")
        print()
        
        print("📋 Detailed Test Results:")
        test_descriptions = {
            'websocket_client_methods': 'WebSocket Client Methods Availability',
            'order_manager_methods': 'OrderManager Methods Availability',
            'integration_init': 'OrderManager Integration Initialization',
            'event_system': 'Order Event Handling System',
            'order_sync': 'Order State Synchronization',
            'trade_fill_processing': 'Trade Fill Processing',
            'queries_and_summary': 'Order Queries and Summary'
        }
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            description = test_descriptions.get(test_name, test_name.replace('_', ' ').title())
            print(f"  {status} - {description}")
        
        print()
        print("📊 Integration Statistics:")
        if hasattr(self.ws_client, 'order_manager') and self.ws_client.order_manager:
            stats = self.ws_client.order_manager.get_statistics()
            print(f"   Orders created: {stats.get('orders_created', 0)}")
            print(f"   Orders filled: {stats.get('orders_filled', 0)}")
            print(f"   Total events logged: {len(self.event_log)}")
        
        print()
        
        # Final assessment
        if passed_tests == total_tests:
            print("🎉 ALL VALIDATION TESTS PASSED!")
            print("✅ Task 3.3.A: Enhanced WebSocket Order Integration - VERIFIED!")
            print()
            print("🚀 Validated Features:")
            print("   • Real-time order state synchronization")
            print("   • Trade fill processing from WebSocket feeds")
            print("   • Order event handling system")
            print("   • Comprehensive order status queries")
            print("   • Order summary and statistics")
            print()
            print("🎯 READY TO PROCEED TO TASK 3.3.B: Order Fill Processing System")
            
        elif passed_tests >= total_tests * 0.9:
            print("⚠️ MOSTLY VALIDATED - Minor issues detected")
            print("Core functionality working, some features may need attention")
            
        elif passed_tests >= total_tests * 0.7:
            print("⚠️ MAJOR FUNCTIONALITY WORKING")
            print("Core integration working, but several issues need resolution")
            
        else:
            print("❌ SIGNIFICANT ISSUES DETECTED")
            print("WebSocket integration needs substantial work before proceeding")
        
        print("=" * 70)
        
        return passed_tests == total_tests


async def main():
    """Main validation execution."""
    try:
        validator = Task33AValidationTest()
        await validator.run_validation()
    except KeyboardInterrupt:
        print("\n\n👋 Validation interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected validation error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
