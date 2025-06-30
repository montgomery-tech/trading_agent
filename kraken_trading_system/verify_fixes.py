#!/usr/bin/env python3
"""
Quick test to verify the fixes work
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.order_requests import (
        StopLossLimitOrderRequest,
        serialize_order_for_api,
        create_limit_order
    )
    from trading_systems.exchanges.kraken.account_models import OrderSide
    
    print("🧪 TESTING FIXES")
    print("=" * 40)
    
    # Test 1: Stop-loss-limit order with correct price relationship
    print("\n1️⃣ Testing stop-loss-limit order validation...")
    try:
        # For a SELL stop-loss-limit: stop price (48000) should be ABOVE limit price (47500)
        # This makes sense: if price drops to 48000, sell at limit 47500 or better
        stop_loss_limit = StopLossLimitOrderRequest(
            pair="XBTUSD",
            side=OrderSide.SELL,
            volume=Decimal("1.0"),
            price=Decimal("48000.00"),  # Stop price (higher)
            price2=Decimal("47500.00")  # Limit price (lower)
        )
        print("  ✅ Stop-loss-limit order created successfully")
    except Exception as e:
        print(f"  ❌ Stop-loss-limit order failed: {e}")
    
    # Test 2: API serialization
    print("\n2️⃣ Testing API serialization...")
    try:
        limit_order = create_limit_order("XBTUSD", OrderSide.BUY, "1.0", "50000.00")
        api_data = serialize_order_for_api(limit_order)
        
        assert "type" in api_data
        assert api_data["type"] == "buy"
        print("  ✅ API serialization works correctly")
        print(f"     API data: {api_data}")
    except Exception as e:
        print(f"  ❌ API serialization failed: {e}")
    
    print("\n✅ Fix verification complete!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
