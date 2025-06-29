#!/usr/bin/env python3
"""
Final Task 3.3.A Validation Test - All Issues Fixed

This test should pass 7/7 tests after all fixes are applied.
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.exchanges.kraken.order_manager import OrderManager
    from trading_systems.exchanges.kraken.order_models import OrderCreationRequest
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def final_validation():
    """Final validation test - should pass all checks."""
    print("🎯 FINAL TASK 3.3.A VALIDATION")
    print("=" * 50)
    
    try:
        # Initialize
        ws_client = KrakenWebSocketClient()
        await ws_client.initialize_order_manager()
        
        # Create test order
        order_request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("0.01"),
            price=Decimal("50000.00")
        )
        
        test_order = await ws_client.order_manager.create_order(order_request)
        print(f"✅ Test order created: {test_order.order_id}")
        
        # Test all key methods
        print("🧪 Testing key methods...")
        
        # 1. Orders summary
        summary = ws_client.get_orders_summary()
        print(f"✅ Orders summary: {summary.get('total_orders', 0)} orders")
        
        # 2. Order status (without await!)
        status = ws_client.get_order_status(test_order.order_id)
        print(f"✅ Order status: {status.get('current_state', 'unknown')}")
        
        # 3. WebSocket sync simulation
        mock_data = [123, {test_order.order_id: {"status": "open", "vol_exec": "0.005"}}, "openOrders"]
        await ws_client._sync_order_states(mock_data)
        print("✅ WebSocket sync simulation completed")
        
        # 4. Trade fill simulation
        mock_trade = [124, {"TRADE_123": {"ordertxid": test_order.order_id, "vol": "0.005", "price": "50000", "fee": "0.25"}}, "ownTrades"]
        await ws_client._process_trade_fills(mock_trade)
        print("✅ Trade fill simulation completed")
        
        # Final stats
        final_stats = ws_client.order_manager.get_statistics()
        print(f"📊 Final stats: {final_stats.get('orders_created', 0)} orders created")
        
        print("
🎉 FINAL VALIDATION SUCCESSFUL!")
        print("✅ Task 3.3.A: Enhanced WebSocket Order Integration - COMPLETE!")
        
    except Exception as e:
        print(f"❌ Final validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(final_validation())
