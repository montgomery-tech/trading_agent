#!/usr/bin/env python3
"""
Automatic Fix Script for Order Request Models

This script automatically applies the necessary fixes to resolve:
1. Stop order field mapping (stop_price -> price)
2. Data sanitization enum handling
3. Pydantic V2 compatibility

Save as: auto_fix_order_models.py
Run with: python3 auto_fix_order_models.py
"""

import sys
from pathlib import Path
import re

def auto_fix_order_models():
    """Automatically fix the order models file."""
    
    print("🔧 AUTOMATIC FIX - ORDER REQUEST MODELS")
    print("=" * 60)
    
    order_models_path = Path("src/trading_systems/exchanges/kraken/order_requests.py")
    
    if not order_models_path.exists():
        print("❌ order_requests.py file not found")
        return False
    
    try:
        # Read current content
        with open(order_models_path, 'r') as f:
            content = f.read()
        
        print(f"📊 Original file size: {len(content)} characters")
        
        # Create backup
        backup_path = order_models_path.with_suffix('.py.auto_backup')
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"💾 Backup created: {backup_path}")
        
        # Track changes
        changes_made = []
        
        # Fix 1: Update Config class
        if 'allow_population_by_field_name' in content:
            content = content.replace(
                'allow_population_by_field_name = True',
                'validate_by_name = True'
            )
            changes_made.append("Updated Pydantic Config")
            print("  ✅ Fixed Pydantic V2 Config")
        
        # Fix 2: Fix StopLossOrderRequest class
        stop_loss_pattern = r'class StopLossOrderRequest\(BaseOrderRequest\):.*?@validator\(\'order_type\'\)'
        stop_loss_replacement = '''class StopLossOrderRequest(BaseOrderRequest):
    """Stop-loss order request model."""
    
    order_type: OrderType = Field(OrderType.STOP_LOSS, description="Order type (stop-loss)")
    price: Decimal = Field(..., gt=0, description="Stop price")
    
    # Stop-loss specific fields
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    
    @validator('order_type')'''
        
        if re.search(stop_loss_pattern, content, re.DOTALL):
            content = re.sub(stop_loss_pattern, stop_loss_replacement, content, flags=re.DOTALL)
            changes_made.append("Fixed StopLossOrderRequest")
            print("  ✅ Fixed StopLossOrderRequest class")
        
        # Fix 3: Fix TakeProfitOrderRequest class
        take_profit_pattern = r'class TakeProfitOrderRequest\(BaseOrderRequest\):.*?@validator\(\'order_type\'\)'
        take_profit_replacement = '''class TakeProfitOrderRequest(BaseOrderRequest):
    """Take-profit order request model."""
    
    order_type: OrderType = Field(OrderType.TAKE_PROFIT, description="Order type (take-profit)")
    price: Decimal = Field(..., gt=0, description="Take profit price")
    
    # Take-profit specific fields  
    trigger: Optional[TriggerType] = Field(TriggerType.LAST, description="Trigger type")
    order_flags: Optional[List[OrderFlags]] = Field(None, description="Order flags")
    
    @validator('order_type')'''
        
        if re.search(take_profit_pattern, content, re.DOTALL):
            content = re.sub(take_profit_pattern, take_profit_replacement, content, flags=re.DOTALL)
            changes_made.append("Fixed TakeProfitOrderRequest")
            print("  ✅ Fixed TakeProfitOrderRequest class")
        
        # Fix 4: Enhanced sanitize_order_data function
        sanitize_pattern = r'def sanitize_order_data\(data: Dict\[str, Any\]\) -> Dict\[str, Any\]:.*?return sanitized'
        sanitize_replacement = '''def sanitize_order_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize order data for API submission.
    
    Args:
        data: Raw order data
        
    Returns:
        Sanitized order data
    """
    sanitized = {}
    
    # Map common field names
    field_mapping = {
        'side': 'type',
        'order_type': 'ordertype',
        'stop_price': 'price',
        'limit_price': 'price2',
        'client_order_id': 'cl_ord_id'
    }
    
    for key, value in data.items():
        if value is not None:
            # Use mapped field name if available
            api_key = field_mapping.get(key, key)
            
            # Convert Decimal to string
            if isinstance(value, Decimal):
                sanitized[api_key] = str(value)
            # Convert enums to values - Enhanced handling
            elif hasattr(value, 'value'):
                sanitized[api_key] = value.value
            elif hasattr(value, 'name') and hasattr(value, '__class__'):
                # Handle enum instances
                sanitized[api_key] = str(value.value if hasattr(value, 'value') else value)
            # Convert lists to comma-separated strings - Enhanced handling
            elif isinstance(value, list):
                if value:  # Only process non-empty lists
                    string_items = []
                    for item in value:
                        if hasattr(item, 'value'):
                            string_items.append(item.value)
                        elif hasattr(item, 'name'):
                            string_items.append(item.name.lower())
                        else:
                            string_items.append(str(item))
                    sanitized[api_key] = ','.join(string_items)
            else:
                sanitized[api_key] = str(value)
    
    return sanitized'''
        
        if re.search(sanitize_pattern, content, re.DOTALL):
            content = re.sub(sanitize_pattern, sanitize_replacement, content, flags=re.DOTALL)
            changes_made.append("Enhanced sanitize_order_data function")
            print("  ✅ Enhanced sanitize_order_data function")
        
        # Fix 5: Update validate_order_request function to use model_dump
        if 'request.dict()' in content:
            content = content.replace('request.dict()', 'request.model_dump()')
            changes_made.append("Updated to model_dump")
            print("  ✅ Updated to use model_dump()")
        
        # Write the updated content
        if changes_made:
            with open(order_models_path, 'w') as f:
                f.write(content)
            
            print(f"\n✅ Successfully applied fixes to order_requests.py")
            print(f"📊 Updated file size: {len(content)} characters")
            print("\n🔧 Changes applied:")
            for change in changes_made:
                print(f"   • {change}")
            
            return True
        else:
            print("\n⚠️ No changes were needed or patterns not found")
            return False
            
    except Exception as e:
        print(f"\n❌ Error applying fixes: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_simple_test():
    """Create a simple test to verify the fixes."""
    
    test_content = '''#!/usr/bin/env python3
"""
Simple test to verify Order Request Models fixes.
"""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.order_requests import (
        StopLossOrderRequest,
        sanitize_order_data,
        OrderFlags
    )
    from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType
    
    print("✅ All imports successful")
    
    # Test 1: Stop order creation
    try:
        stop_order = StopLossOrderRequest(
            pair="XBTUSD",
            side=OrderSide.SELL,
            volume=Decimal("1.0"),
            price=Decimal("45000.00")  # This should work now
        )
        print("✅ Stop order creation working")
    except Exception as e:
        print(f"❌ Stop order creation failed: {e}")
        sys.exit(1)
    
    # Test 2: Data sanitization
    try:
        test_data = {
            'side': OrderSide.BUY,
            'order_flags': [OrderFlags.POST_ONLY]
        }
        sanitized = sanitize_order_data(test_data)
        if 'post' in sanitized.get('order_flags', ''):
            print("✅ Data sanitization working")
        else:
            print(f"❌ Data sanitization issue: {sanitized}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Data sanitization failed: {e}")
        sys.exit(1)
    
    print("🎉 ALL SIMPLE TESTS PASSED!")
    print("Ready to run full test suite")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
'''
    
    with open('simple_test_fixes.py', 'w') as f:
        f.write(test_content)
    
    print("📝 Created simple_test_fixes.py")

def main():
    """Main fix application function."""
    print("🚀 Starting automatic fix process...")
    
    success = auto_fix_order_models()
    
    if success:
        create_simple_test()
        
        print("\n" + "=" * 60)
        print("🎉 AUTOMATIC FIXES COMPLETED!")
        print("✅ Order Request Models have been fixed")
        print("\n📋 Next steps:")
        print("   1. Run: python3 simple_test_fixes.py")
        print("   2. If simple test passes, run: python3 test_order_models_fixed.py")
        print("   3. Should achieve 10/10 tests passing")
    else:
        print("\n" + "=" * 60)
        print("❌ AUTOMATIC FIXES FAILED")
        print("⚠️ Manual intervention may be required")
    
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Fix process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
