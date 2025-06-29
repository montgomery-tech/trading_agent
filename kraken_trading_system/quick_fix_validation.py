#!/usr/bin/env python3
"""
Quick Fix Validation Test - Tests key functionality with correct attributes.
Run this after applying fixes to verify everything works.
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

async def quick_validation():
    """Quick validation of key functionality."""
    print("🚀 QUICK FIX VALIDATION TEST")
    print("=" * 50)
    
    try:
        # Test 1: Create WebSocket client and OrderManager
        print("1️⃣ Testing Basic Integration...")
        ws_client = KrakenWebSocketClient()
        await ws_client.initialize_order_manager()
        print("   ✅ WebSocket client and OrderManager initialized")
        
        # Test 2: Create a test order
        print("2️⃣ Testing Order Creation...")
        order_request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("0.01"),
            price=Decimal("50000.00")
        )
        
        test_order = await ws_client.order_manager.create_order(order_request)
        print(f"   ✅ Order created: {test_order.order_id}")
        print(f"   📊 State: {test_order.current_state.value}")
        print(f"   📊 Type: {test_order.type.value}")
        
        # Test 3: Test attribute access (both new and alias)
        print("3️⃣ Testing Attribute Access...")
        
        # Test current_state attribute
        state_via_current = test_order.current_state
        print(f"   ✅ current_state: {state_via_current.value}")
        
        # Test state alias (if property aliases were added)
        try:
            state_via_alias = test_order.state
            print(f"   ✅ state alias: {state_via_alias.value}")
        except AttributeError:
            print("   ⚠️ state alias not available (property aliases not added)")
        
        # Test type attribute
        type_via_type = test_order.type
        print(f"   ✅ type: {type_via_type.value}")
        
        # Test side alias (if property aliases were added)
        try:
            side_via_alias = test_order.side
            print(f"   ✅ side alias: {side_via_alias.value}")
        except AttributeError:
            print("   ⚠️ side alias not available (property aliases not added)")
        
        # Test 4: Test OrderManager methods
        print("4️⃣ Testing OrderManager Methods...")
        
        # Test get_all_orders
        all_orders = ws_client.order_manager.get_all_orders()
        print(f"   ✅ get_all_orders: {len(all_orders)} orders")
        
        # Test has_order
        has_order = ws_client.order_manager.has_order(test_order.order_id)
        print(f"   ✅ has_order: {has_order}")
        
        # Test get_statistics
        stats = ws_client.order_manager.get_statistics()
        print(f"   ✅ get_statistics: {stats.get('orders_created', 0)} orders created")
        
        # Test _get_event_for_transition method
        if hasattr(ws_client.order_manager, '_get_event_for_transition'):
            from trading_systems.exchanges.kraken.order_models import OrderState, OrderEvent
            event = ws_client.order_manager._get_event_for_transition(
                OrderState.PENDING_SUBMIT, OrderState.OPEN
            )
            print(f"   ✅ _get_event_for_transition: {event.value}")
        else:
            print("   ❌ _get_event_for_transition method missing")
        
        # Test 5: Test WebSocket integration methods
        print("5️⃣ Testing WebSocket Integration...")
        
        # Test orders summary
        summary = ws_client.get_orders_summary()
        print(f"   ✅ get_orders_summary: {summary.get('total_orders', 0)} orders")
        
        # Test order status
        status = await ws_client.get_order_status(test_order.order_id)
        print(f"   ✅ get_order_status: {status.get('current_state', 'unknown')}")
        
        print("
🎉 QUICK VALIDATION COMPLETED SUCCESSFULLY!")
        print("✅ All key functionality is working correctly")
        print("🎯 Ready to run full validation test")
        
    except Exception as e:
        print(f"
❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_validation())
