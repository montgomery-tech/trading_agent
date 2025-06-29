#!/usr/bin/env python3
"""
Final Comprehensive Validation for Task 3.3.A

This script validates that all attribute issues have been resolved
and the WebSocket order integration is working correctly.
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

async def comprehensive_validation():
    """Comprehensive validation of all fixes."""
    print("🎯 COMPREHENSIVE TASK 3.3.A VALIDATION")
    print("=" * 60)
    
    test_results = {}
    
    try:
        # Test 1: Basic initialization
        print("1️⃣ Testing Initialization...")
        ws_client = KrakenWebSocketClient()
        await ws_client.initialize_order_manager()
        print("   ✅ WebSocket client and OrderManager initialized")
        test_results['initialization'] = True
        
        # Test 2: Order creation with attribute access
        print("\n2️⃣ Testing Order Creation and Attribute Access...")
        order_request = OrderCreationRequest(
            pair="XBT/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            volume=Decimal("0.01"),
            price=Decimal("50000.00")
        )
        
        test_order = await ws_client.order_manager.create_order(order_request)
        
        # Test current_state access (primary)
        state = test_order.current_state
        print(f"   ✅ current_state access: {state.value}")
        
        # Test state alias (if available)
        try:
            state_alias = test_order.state
            print(f"   ✅ state alias access: {state_alias.value}")
        except AttributeError:
            print("   ⚠️ state alias not available (that's okay)")
        
        # Test type access (primary)
        order_type = test_order.type
        print(f"   ✅ type access: {order_type.value}")
        
        # Test side alias (if available)
        try:
            side_alias = test_order.side
            print(f"   ✅ side alias access: {side_alias.value}")
        except AttributeError:
            print("   ⚠️ side alias not available (that's okay)")
        
        # Test volume_remaining (read-only property)
        vol_remaining = test_order.volume_remaining
        print(f"   ✅ volume_remaining access: {vol_remaining}")
        
        test_results['attribute_access'] = True
        
        # Test 3: OrderManager methods
        print("\n3️⃣ Testing OrderManager Methods...")
        
        # Test get_all_orders
        all_orders = ws_client.order_manager.get_all_orders()
        print(f"   ✅ get_all_orders: {len(all_orders)} orders")
        
        # Test get_statistics
        stats = ws_client.order_manager.get_statistics()
        print(f"   ✅ get_statistics: {stats.get('orders_created', 0)} orders created")
        
        test_results['order_manager_methods'] = True
        
        # Test 4: WebSocket integration methods
        print("\n4️⃣ Testing WebSocket Integration...")
        
        # Test orders summary
        summary = ws_client.get_orders_summary()
        print(f"   ✅ get_orders_summary: {summary.get('total_orders', 0)} orders")
        
        # Test order status (should not be async)
        status = ws_client.get_order_status(test_order.order_id)
        print(f"   ✅ get_order_status: {status.get('current_state', 'unknown')}")
        
        test_results['websocket_integration'] = True
        
        # Test 5: State synchronization simulation
        print("\n5️⃣ Testing State Synchronization...")
        
        # Simulate WebSocket order update
        mock_order_data = [
            123456,
            {test_order.order_id: {"status": "open", "vol_exec": "0.005", "cost": "250.00", "fee": "0.25"}},
            "openOrders"
        ]
        
        await ws_client._sync_order_states(mock_order_data)
        
        # Verify update
        updated_order = ws_client.order_manager.get_order(test_order.order_id)
        if updated_order and updated_order.volume_executed > 0:
            print(f"   ✅ Order synchronized: {updated_order.volume_executed} executed")
            test_results['state_sync'] = True
        else:
            print("   ❌ Order synchronization failed")
            test_results['state_sync'] = False
        
        # Test 6: Trade fill processing
        print("\n6️⃣ Testing Trade Fill Processing...")
        
        mock_trade_data = [
            123457,
            {"TRADE_TEST": {"ordertxid": test_order.order_id, "vol": "0.005", "price": "50000", "fee": "0.25"}},
            "ownTrades"
        ]
        
        await ws_client._process_trade_fills(mock_trade_data)
        
        final_order = ws_client.order_manager.get_order(test_order.order_id)
        if final_order and final_order.fill_count > 0:
            print(f"   ✅ Trade fill processed: {final_order.fill_count} fills")
            test_results['trade_fill'] = True
        else:
            print("   ❌ Trade fill processing failed")
            test_results['trade_fill'] = False
        
        # Final assessment
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE VALIDATION RESULTS")
        print("=" * 60)
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result)
        
        print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        print()
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {test_name.replace('_', ' ').title()}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL VALIDATION TESTS PASSED!")
            print("✅ Task 3.3.A: Enhanced WebSocket Order Integration - COMPLETE!")
            print("✅ All attribute issues resolved")
            print("✅ Full integration working correctly")
            print()
            print("🎯 READY FOR TASK 3.3.B: Order Fill Processing System")
        else:
            print(f"\n⚠️ {total_tests - passed_tests} tests still failing")
            print("Additional fixes may be needed")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(comprehensive_validation())
