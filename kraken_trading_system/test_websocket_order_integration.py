#!/usr/bin/env python3
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
        print("

👋 Test interrupted by user")
    except Exception as e:
        print(f"
❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
