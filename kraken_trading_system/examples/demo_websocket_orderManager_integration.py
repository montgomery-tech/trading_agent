#!/usr/bin/env python3
"""
Demonstration script for Task 3.1.C: OrderManager WebSocket Integration

This script demonstrates the complete OrderManager integration with the WebSocket client,
showing real-time order state updates and event handling.

File Location: examples/demo_websocket_orderManager_integration.py
"""

import asyncio
import sys
import signal
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.exchanges.kraken.order_manager import OrderManager
    from trading_systems.exchanges.kraken.order_models import OrderCreationRequest
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType
    from trading_systems.utils.logger import get_logger
    print("✅ Successfully imported all required modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required modules are available")
    sys.exit(1)


class WebSocketOrderManagerDemo:
    """Demonstration of WebSocket OrderManager integration."""

    def __init__(self):
        self.logger = get_logger("WebSocketOrderManagerDemo")
        self.ws_client = KrakenWebSocketClient()
        self.running = True
        self.order_events = []

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info("Shutdown signal received", signal=signum)
        self.running = False

    async def run_demonstration(self):
        """Run the complete OrderManager WebSocket integration demonstration."""
        try:
            print("🚀 WEBSOCKET ORDERMASTER INTEGRATION DEMONSTRATION")
            print("=" * 70)
            print()
            print("This demo shows Task 3.1.C implementation:")
            print("• OrderManager integration into WebSocket client")
            print("• Real-time order state updates")
            print("• Order event propagation")
            print("• Event handling system")
            print()

            # Step 1: Initialize WebSocket client
            await self._step1_initialize_websocket_client()

            # Step 2: Set up order event handlers
            await self._step2_setup_event_handlers()

            # Step 3: Initialize OrderManager integration
            await self._step3_initialize_order_manager()

            # Step 4: Demonstrate order creation and tracking
            await self._step4_demonstrate_order_tracking()

            # Step 5: Simulate real-time order updates
            await self._step5_simulate_realtime_updates()

            # Step 6: Show integration status and statistics
            await self._step6_show_integration_status()

            print("\n🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
            print("Task 3.1.C: OrderManager WebSocket Integration is working correctly")

        except KeyboardInterrupt:
            self.logger.info("Demonstration interrupted by user")
        except Exception as e:
            self.logger.error("Demonstration failed", error=str(e), exc_info=True)
        finally:
            await self._cleanup()

    async def _step1_initialize_websocket_client(self):
        """Step 1: Initialize WebSocket client."""
        print("1️⃣ STEP 1: Initialize WebSocket Client")
        print("-" * 50)

        # Show initial state
        status = self.ws_client.get_connection_status()
        print(f"📊 Initial OrderManager enabled: {status.get('order_management_enabled', False)}")
        print(f"📊 Initial order event handlers: {len(status.get('order_event_handlers', {}))}")
        
        print("✅ WebSocket client initialized successfully")
        print()

    async def _step2_setup_event_handlers(self):
        """Step 2: Set up order event handlers."""
        print("2️⃣ STEP 2: Set up Order Event Handlers")
        print("-" * 50)

        # Define event handlers
        def order_state_change_handler(event_data):
            """Handle order state changes."""
            order = event_data.get('order')
            old_state = event_data.get('old_state')
            new_state = event_data.get('new_state')
            
            self.order_events.append({
                'type': 'state_change',
                'timestamp': datetime.now(),
                'order_id': order.order_id if order else 'unknown',
                'old_state': old_state.value if old_state else 'unknown',
                'new_state': new_state.value if new_state else 'unknown'
            })
            
            print(f"    📈 Order State Change: {order.order_id if order else 'N/A'}")
            print(f"       {old_state.value if old_state else 'N/A'} → {new_state.value if new_state else 'N/A'}")

        def order_fill_handler(event_data):
            """Handle order fills."""
            trade_id = event_data.get('trade_id')
            order_id = event_data.get('order_id')
            
            self.order_events.append({
                'type': 'fill',
                'timestamp': datetime.now(),
                'trade_id': trade_id,
                'order_id': order_id
            })
            
            print(f"    💰 Order Fill: Trade {trade_id} for Order {order_id}")

        def order_update_handler(event_data):
            """Handle order updates from WebSocket."""
            order_id = event_data.get('order_id')
            source = event_data.get('source', 'unknown')
            
            self.order_events.append({
                'type': 'update',
                'timestamp': datetime.now(),
                'order_id': order_id,
                'source': source
            })
            
            print(f"    🔄 Order Update: {order_id} from {source}")

        # Register handlers (before OrderManager initialization)
        self.ws_client.add_order_event_handler("state_change", order_state_change_handler)
        self.ws_client.add_order_event_handler("fill", order_fill_handler)
        self.ws_client.add_order_event_handler("order_update", order_update_handler)

        print("✅ Event handlers registered:")
        print("   • Order state change handler")
        print("   • Order fill handler") 
        print("   • Order update handler")
        print()

    async def _step3_initialize_order_manager(self):
        """Step 3: Initialize OrderManager integration."""
        print("3️⃣ STEP 3: Initialize OrderManager Integration")
        print("-" * 50)

        # Initialize OrderManager integration
        await self.ws_client.initialize_order_manager()
        
        # Verify integration
        status = self.ws_client.get_connection_status()
        print(f"📊 OrderManager enabled: {status['order_management_enabled']}")
        print(f"📊 Event handlers registered: {sum(len(handlers) for handlers in status['order_event_handlers'].values())}")
        
        # Show OrderManager statistics
        if status.get('order_manager_stats'):
            stats = status['order_manager_stats']
            print(f"📊 Orders created: {stats.get('orders_created', 0)}")
            print(f"📊 Orders submitted: {stats.get('orders_submitted', 0)}")
        
        print("✅ OrderManager integration initialized successfully")
        print()

    async def _step4_demonstrate_order_tracking(self):
        """Step 4: Demonstrate order creation and tracking."""
        print("4️⃣ STEP 4: Demonstrate Order Creation and Tracking")
        print("-" * 50)

        # Create test orders
        test_orders = []
        
        for i in range(3):
            order_request = OrderCreationRequest(
                pair="XBT/USD" if i % 2 == 0 else "ETH/USD",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.LIMIT,
                volume=Decimal("0.1") * (i + 1),
                price=Decimal("50000.00") if i % 2 == 0 else Decimal("3000.00")
            )
            
            order = await self.ws_client.order_manager.create_order(order_request)
            test_orders.append(order)
            
            print(f"📝 Created Order {i+1}:")
            print(f"   ID: {order.order_id}")
            print(f"   Pair: {order.pair}")
            print(f"   Type: {order.type} {order.order_type}")
            print(f"   Volume: {order.volume}")
            print(f"   State: {order.state.value}")
            
            # Small delay to simulate real order creation
            await asyncio.sleep(0.1)

        print(f"✅ Created {len(test_orders)} test orders")
        
        # Show orders summary
        orders_summary = self.ws_client.get_orders_summary()
        print(f"📊 Total orders tracked: {orders_summary['total_orders']}")
        print()

        return test_orders

    async def _step5_simulate_realtime_updates(self):
        """Step 5: Simulate real-time order updates."""
        print("5️⃣ STEP 5: Simulate Real-time Order Updates")
        print("-" * 50)

        # Get a test order to update
        orders_summary = self.ws_client.get_orders_summary()
        if not orders_summary['orders']:
            print("⚠️ No orders available for simulation")
            return

        test_order_id = orders_summary['orders'][0]['order_id']
        print(f"🎯 Simulating updates for order: {test_order_id}")
        print()

        # Simulate openOrders feed update
        print("📡 Simulating openOrders WebSocket update...")
        mock_order_update = [
            123456,  # sequence number
            {
                test_order_id: {
                    "status": "open",
                    "vol": "0.1",
                    "vol_exec": "0.05",
                    "cost": "2500.00",
                    "fee": "1.25",
                    "price": "50000.00",
                    "stopprice": "0.00000",
                    "limitprice": "0.00000",
                    "misc": "",
                    "oflags": "fciq"
                }
            },
            "openOrders"
        ]

        await self.ws_client._sync_order_states(mock_order_update)
        print("✅ Order state sync completed")

        # Simulate ownTrades feed update
        print("\n📡 Simulating ownTrades WebSocket update...")
        mock_trade_update = [
            123457,  # sequence number
            {
                "TRADE_DEMO_123": {
                    "ordertxid": test_order_id,
                    "pair": "XBT/USD",
                    "time": 1640995200.0,
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "50000.00",
                    "vol": "0.05",
                    "fee": "1.25",
                    "cost": "2500.00",
                    "margin": "0.00000"
                }
            },
            "ownTrades"
        ]

        await self.ws_client._process_trade_fills(mock_trade_update)
        print("✅ Trade fill processing completed")
        print()

    async def _step6_show_integration_status(self):
        """Step 6: Show integration status and statistics."""
        print("6️⃣ STEP 6: Integration Status and Statistics")
        print("-" * 50)

        # Get comprehensive status
        status = self.ws_client.get_connection_status()
        
        print("📊 WebSocket Client Status:")
        print(f"   • OrderManager enabled: {status['order_management_enabled']}")
        print(f"   • Account data enabled: {status['account_data_enabled']}")
        
        if status.get('order_manager_stats'):
            stats = status['order_manager_stats']
            print("\n📊 OrderManager Statistics:")
            print(f"   • Orders created: {stats.get('orders_created', 0)}")
            print(f"   • Orders submitted: {stats.get('orders_submitted', 0)}")
            print(f"   • Orders filled: {stats.get('orders_filled', 0)}")
            print(f"   • Orders canceled: {stats.get('orders_canceled', 0)}")
        
        print("\n📊 Event Handler Statistics:")
        event_handlers = status.get('order_event_handlers', {})
        for event_type, count in event_handlers.items():
            print(f"   • {event_type}: {count} handlers")
        
        print(f"\n📊 Events Captured During Demo: {len(self.order_events)}")
        for event in self.order_events[-5:]:  # Show last 5 events
            timestamp = event['timestamp'].strftime("%H:%M:%S")
            print(f"   • {timestamp} - {event['type']}: {event.get('order_id', 'N/A')}")
        
        print("\n✅ Integration status verification complete")
        print()

    async def _cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self.ws_client, 'disconnect'):
                await self.ws_client.disconnect()
            print("🧹 Cleanup completed")
        except Exception as e:
            self.logger.error("Error during cleanup", error=e)


async def main():
    """Main demonstration function."""
    print("🎬 Starting WebSocket OrderManager Integration Demonstration")
    print()
    
    demo = WebSocketOrderManagerDemo()
    await demo.run_demonstration()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demonstration interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
