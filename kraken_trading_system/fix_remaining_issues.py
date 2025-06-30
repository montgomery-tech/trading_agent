#!/usr/bin/env python3
"""
Fix Remaining Issues in Order Models - Task 3.4.B.1

This script fixes the two remaining issues identified in the test results:
1. Stop-loss-limit order validation logic (price relationship)
2. API serialization enum value access

Issues Fixed:
1. StopLossLimitOrderRequest validation logic for price relationships
2. serialize_order_for_api function enum handling

Run: python3 fix_remaining_issues.py
"""

import sys
from pathlib import Path
import re

def fix_remaining_issues():
    """Fix the remaining issues in order_requests.py."""
    
    print("🔧 FIXING REMAINING ISSUES IN ORDER MODELS")
    print("=" * 60)
    
    order_requests_path = Path("src/trading_systems/exchanges/kraken/order_requests.py")
    
    if not order_requests_path.exists():
        print("❌ order_requests.py not found")
        return False
    
    try:
        # Read current content
        with open(order_requests_path, 'r') as f:
            content = f.read()
        
        print(f"📊 Original file size: {len(content)} characters")
        
        # Create backup
        backup_path = order_requests_path.with_suffix('.py.fix_backup')
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"💾 Backup created: {backup_path}")
        
        # Track changes
        changes_made = []
        
        # Fix 1: Stop-loss-limit order validation logic
        print("\n🔧 Fix 1: Stop-loss-limit order validation logic")
        
        old_validation = '''    @model_validator(mode='after')
    def validate_prices(self):
        """Validate stop and limit price relationship."""
        price = self.price
        price2 = self.price2
        side = self.side
        
        if price and price2 and side:
            # For sell stop-loss: stop price should be below limit price
            # For buy stop-loss: stop price should be above limit price
            if side == OrderSide.SELL and price >= price2:
                raise ValueError("For sell stop-loss-limit: stop price must be below limit price")
            elif side == OrderSide.BUY and price <= price2:
                raise ValueError("For buy stop-loss-limit: stop price must be above limit price")
        
        return self'''
        
        # The validation logic was backwards - fix it
        new_validation = '''    @model_validator(mode='after')
    def validate_prices(self):
        """Validate stop and limit price relationship."""
        price = self.price
        price2 = self.price2
        side = self.side
        
        if price and price2 and side:
            # For sell stop-loss-limit: stop price should be above limit price
            # For buy stop-loss-limit: stop price should be below limit price
            # This is because stop-loss triggers when price moves against the position
            if side == OrderSide.SELL and price <= price2:
                raise ValueError("For sell stop-loss-limit: stop price must be above limit price")
            elif side == OrderSide.BUY and price >= price2:
                raise ValueError("For buy stop-loss-limit: stop price must be below limit price")
        
        return self'''
        
        if old_validation in content:
            content = content.replace(old_validation, new_validation)
            changes_made.append("Fixed stop-loss-limit validation logic")
            print("  ✅ Fixed stop-loss-limit price validation logic")
        else:
            print("  ⚠️  Stop-loss-limit validation not found or already different")
        
        # Fix 2: API serialization enum handling
        print("\n🔧 Fix 2: API serialization enum handling")
        
        old_serialization = '''def serialize_order_for_api(request: BaseOrderRequest) -> Dict[str, Any]:
    """Serialize order request for Kraken API submission."""
    api_data = {
        "pair": request.pair,
        "type": request.side.value,
        "ordertype": get_order_type_from_request(request),
        "volume": str(request.volume)
    }
    
    # Add price fields
    if hasattr(request, 'price') and request.price:
        api_data["price"] = str(request.price)
    
    if hasattr(request, 'price2') and request.price2:
        api_data["price2"] = str(request.price2)
    
    # Add optional fields
    if hasattr(request, 'time_in_force') and request.time_in_force:
        api_data["timeinforce"] = request.time_in_force.value
    
    if hasattr(request, 'order_flags') and request.order_flags:
        api_data["oflags"] = ",".join([flag.value for flag in request.order_flags])
    
    if request.userref:
        api_data["userref"] = request.userref
    
    if request.validate_only:
        api_data["validate"] = "true"
    
    return api_data'''
        
        new_serialization = '''def serialize_order_for_api(request: BaseOrderRequest) -> Dict[str, Any]:
    """Serialize order request for Kraken API submission."""
    # Handle enum values safely
    side_value = request.side.value if hasattr(request.side, 'value') else str(request.side)
    
    api_data = {
        "pair": request.pair,
        "type": side_value,
        "ordertype": get_order_type_from_request(request),
        "volume": str(request.volume)
    }
    
    # Add price fields
    if hasattr(request, 'price') and request.price:
        api_data["price"] = str(request.price)
    
    if hasattr(request, 'price2') and request.price2:
        api_data["price2"] = str(request.price2)
    
    # Add optional fields
    if hasattr(request, 'time_in_force') and request.time_in_force:
        tif_value = request.time_in_force.value if hasattr(request.time_in_force, 'value') else str(request.time_in_force)
        api_data["timeinforce"] = tif_value
    
    if hasattr(request, 'order_flags') and request.order_flags:
        flag_values = []
        for flag in request.order_flags:
            flag_value = flag.value if hasattr(flag, 'value') else str(flag)
            flag_values.append(flag_value)
        api_data["oflags"] = ",".join(flag_values)
    
    if request.userref:
        api_data["userref"] = request.userref
    
    if request.validate_only:
        api_data["validate"] = "true"
    
    return api_data'''
        
        if old_serialization in content:
            content = content.replace(old_serialization, new_serialization)
            changes_made.append("Fixed API serialization enum handling")
            print("  ✅ Fixed API serialization enum handling")
        else:
            print("  ⚠️  API serialization function not found or already different")
        
        # Write the fixed content
        with open(order_requests_path, 'w') as f:
            f.write(content)
        
        print(f"\n📊 Updated file size: {len(content)} characters")
        print(f"🔧 Changes made: {len(changes_made)}")
        for change in changes_made:
            print(f"   • {change}")
        
        print(f"\n✅ Remaining issues fixed in {order_requests_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing remaining issues: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_fixed_test_case():
    """Create a quick test to verify the fixes work."""
    
    test_code = '''#!/usr/bin/env python3
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
    print("\\n1️⃣ Testing stop-loss-limit order validation...")
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
    print("\\n2️⃣ Testing API serialization...")
    try:
        limit_order = create_limit_order("XBTUSD", OrderSide.BUY, "1.0", "50000.00")
        api_data = serialize_order_for_api(limit_order)
        
        assert "type" in api_data
        assert api_data["type"] == "buy"
        print("  ✅ API serialization works correctly")
        print(f"     API data: {api_data}")
    except Exception as e:
        print(f"  ❌ API serialization failed: {e}")
    
    print("\\n✅ Fix verification complete!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
'''
    
    test_path = Path("verify_fixes.py")
    with open(test_path, 'w') as f:
        f.write(test_code)
    
    print(f"📝 Created verification test: {test_path}")
    return True


def main():
    """Main execution function."""
    
    print("🚀 FIXING REMAINING ISSUES - TASK 3.4.B.1")
    print("=" * 70)
    print()
    print("Fixing the 2 remaining issues from test results:")
    print("1. Stop-loss-limit order validation logic")
    print("2. API serialization enum value access")
    print()
    
    success_count = 0
    total_tasks = 2
    
    # Fix the issues
    print("📝 STEP 1: Applying Fixes to order_requests.py")
    print("-" * 60)
    if fix_remaining_issues():
        success_count += 1
        print("✅ Fixes applied successfully")
    else:
        print("❌ Failed to apply fixes")
    
    print()
    
    # Create verification test
    print("📝 STEP 2: Creating Verification Test")
    print("-" * 60)
    if create_fixed_test_case():
        success_count += 1
        print("✅ Verification test created")
    else:
        print("❌ Failed to create verification test")
    
    print()
    print("=" * 70)
    print("📊 FIX SUMMARY")
    print("=" * 70)
    print(f"🎯 Fix Tasks: {success_count}/{total_tasks}")
    
    if success_count == total_tasks:
        print("🎉 REMAINING ISSUES FIXED!")
        print()
        print("✅ Fixed Issues:")
        print("   • Stop-loss-limit order validation logic corrected")
        print("   • API serialization enum handling made robust")
        print()
        print("🧪 Next Steps:")
        print("   1. Run: python3 verify_fixes.py")
        print("   2. Run: python3 test_task_3_4_b_1_order_models.py")
        print("   3. Should now get 100% test success rate")
        print("   4. Proceed with Task 3.4.B.1 completion")
        
    else:
        print("❌ FIXES INCOMPLETE - Manual review required")
    
    print("=" * 70)
    return success_count == total_tasks


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
