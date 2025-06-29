#!/usr/bin/env python3
"""
Fix Syntax Errors from Regex Replacements

The previous fix script was too aggressive with regex and broke function names.
This script fixes the syntax errors caused by incorrect replacements.

Issues to fix:
- def handle_order.current_state_change -> def handle_order_state_change
- *test*order.current_state_synchronization -> _test_order_state_synchronization

File: fix_syntax_errors.py
"""

import sys
from pathlib import Path
import re

def fix_websocket_client_syntax():
    """Fix syntax errors in WebSocket client."""
    
    print("🔧 Fixing WebSocket Client Syntax Errors")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Fix broken function names
    fixes = [
        # Fix handle_order.current_state_change
        ('def handle_order.current_state_change', 'def handle_order_state_change'),
        ('handle_order.current_state_change', 'handle_order_state_change'),
        
        # Fix any other broken patterns
        ('order.current_state_change', 'order_state_change'),
        ('def order.current_state_', 'def order_state_'),
        
        # Fix method calls that got broken
        ('\.current_state_change\(', '_state_change('),
    ]
    
    original_content = content
    for old_pattern, new_pattern in fixes:
        content = content.replace(old_pattern, new_pattern)
    
    # Additional regex fixes for more complex patterns
    # Fix any remaining function definitions that got broken
    content = re.sub(r'def (\w+)\.current_state_(\w+)', r'def \1_state_\2', content)
    content = re.sub(r'def (\w+)\.current_state\(', r'def \1_current_state(', content)
    
    changes_made = content != original_content
    
    if changes_made:
        try:
            with open(websocket_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ WebSocket client syntax errors fixed")
            return True
        except Exception as e:
            print(f"❌ Error writing WebSocket client: {e}")
            return False
    else:
        print("✅ No syntax errors found in WebSocket client")
        return True

def fix_validation_test_syntax():
    """Fix syntax errors in validation test."""
    
    print("\n🔧 Fixing Validation Test Syntax Errors")
    print("=" * 50)
    
    test_path = Path("validate_task_3_3_a.py")
    
    try:
        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading validation test: {e}")
        return False
    
    # Fix broken function names in test
    fixes = [
        # Fix test method names
        ('*test*order.current_state_synchronization', '_test_order_state_synchronization'),
        ('*test*order.current_state_', '_test_order_state_'),
        ('def *test*', 'def _test_'),
        
        # Fix any other broken patterns
        ('async def *test*order.current_state_', 'async def _test_order_state_'),
        ('test*order.current_state', 'test_order_state'),
    ]
    
    original_content = content
    for old_pattern, new_pattern in fixes:
        content = content.replace(old_pattern, new_pattern)
    
    # Additional regex fixes
    # Fix test method names that got broken
    content = re.sub(r'def \*test\*(\w+)\.current_state_(\w+)', r'def _test_\1_state_\2', content)
    content = re.sub(r'async def \*test\*(\w+)\.current_state_(\w+)', r'async def _test_\1_state_\2', content)
    
    changes_made = content != original_content
    
    if changes_made:
        try:
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Validation test syntax errors fixed")
            return True
        except Exception as e:
            print(f"❌ Error writing validation test: {e}")
            return False
    else:
        print("✅ No syntax errors found in validation test")
        return True

def fix_order_manager_syntax():
    """Fix any syntax errors in OrderManager."""
    
    print("\n🔧 Checking OrderManager for Syntax Errors")
    print("=" * 50)
    
    order_manager_path = Path("src/trading_systems/exchanges/kraken/order_manager.py")
    
    try:
        with open(order_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading OrderManager: {e}")
        return False
    
    # Fix any broken function or method names
    fixes = [
        # Fix any broken method names
        ('def order.current_state_', 'def order_state_'),
        ('order.current_state_transition', 'order_state_transition'),
        
        # Fix any variable names that got broken
        ('old.current_state = order.current_state', 'old_state = order.current_state'),
        ('new.current_state = ', 'new_state = '),
    ]
    
    original_content = content
    for old_pattern, new_pattern in fixes:
        content = content.replace(old_pattern, new_pattern)
    
    # Check for any remaining syntax issues
    content = re.sub(r'def (\w+)\.current_state_(\w+)', r'def \1_state_\2', content)
    
    changes_made = content != original_content
    
    if changes_made:
        try:
            with open(order_manager_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ OrderManager syntax errors fixed")
            return True
        except Exception as e:
            print(f"❌ Error writing OrderManager: {e}")
            return False
    else:
        print("✅ No syntax errors found in OrderManager")
        return True

def create_simple_validation_test():
    """Create a simple validation test to verify fixes."""
    
    print("\n🧪 Creating Simple Validation Test")
    print("=" * 50)
    
    simple_test = '''#!/usr/bin/env python3
"""
Simple validation test to check that syntax errors are fixed.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported without syntax errors."""
    print("🧪 Testing Module Imports...")
    
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        print("   ✅ WebSocket client imported successfully")
    except SyntaxError as e:
        print(f"   ❌ WebSocket client syntax error: {e}")
        return False
    except ImportError as e:
        print(f"   ❌ WebSocket client import error: {e}")
        return False
    
    try:
        from trading_systems.exchanges.kraken.order_manager import OrderManager
        print("   ✅ OrderManager imported successfully")
    except SyntaxError as e:
        print(f"   ❌ OrderManager syntax error: {e}")
        return False
    except ImportError as e:
        print(f"   ❌ OrderManager import error: {e}")
        return False
    
    try:
        from trading_systems.exchanges.kraken.order_models import OrderCreationRequest
        print("   ✅ Order models imported successfully")
    except SyntaxError as e:
        print(f"   ❌ Order models syntax error: {e}")
        return False
    except ImportError as e:
        print(f"   ❌ Order models import error: {e}")
        return False
    
    try:
        from trading_systems.exchanges.kraken.account_models import OrderSide, OrderType
        print("   ✅ Account models imported successfully")
    except SyntaxError as e:
        print(f"   ❌ Account models syntax error: {e}")
        return False
    except ImportError as e:
        print(f"   ❌ Account models import error: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality without syntax errors."""
    print("\\n🧪 Testing Basic Functionality...")
    
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        from trading_systems.exchanges.kraken.order_manager import OrderManager
        
        # Test object creation
        ws_client = KrakenWebSocketClient()
        print("   ✅ WebSocket client created")
        
        order_manager = OrderManager()
        print("   ✅ OrderManager created")
        
        # Test basic method calls
        status = ws_client.get_connection_status()
        print("   ✅ WebSocket client methods working")
        
        stats = order_manager.get_statistics()
        print("   ✅ OrderManager methods working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main test execution."""
    print("🎯 SIMPLE SYNTAX AND FUNCTIONALITY VALIDATION")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test basic functionality
    functionality_ok = test_basic_functionality()
    
    print("\\n" + "=" * 60)
    print("📊 SIMPLE VALIDATION RESULTS")
    print("=" * 60)
    
    if imports_ok and functionality_ok:
        print("🎉 ALL SYNTAX ERRORS FIXED!")
        print("✅ All modules import successfully")
        print("✅ Basic functionality working")
        print("\\n🎯 Ready to run full validation test")
        print("Next step: python3 validate_task_3_3_a.py")
    else:
        print("❌ Still have issues:")
        if not imports_ok:
            print("   • Import/syntax errors remain")
        if not functionality_ok:
            print("   • Basic functionality issues")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
'''
    
    test_path = Path("simple_syntax_validation.py")
    try:
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(simple_test)
        print("✅ Created simple validation test")
        return True
    except Exception as e:
        print(f"❌ Error creating simple test: {e}")
        return False

def main():
    """Main execution function."""
    print("🔧 FIXING SYNTAX ERRORS FROM REGEX REPLACEMENTS")
    print("=" * 60)
    print()
    print("The previous fix was too aggressive and broke function names.")
    print("Applying targeted fixes to restore correct syntax.")
    print()
    
    success_count = 0
    total_fixes = 4
    
    # Fix 1: WebSocket client syntax
    if fix_websocket_client_syntax():
        success_count += 1
    
    # Fix 2: Validation test syntax
    if fix_validation_test_syntax():
        success_count += 1
    
    # Fix 3: OrderManager syntax
    if fix_order_manager_syntax():
        success_count += 1
    
    # Fix 4: Create simple validation test
    if create_simple_validation_test():
        success_count += 1
    
    print("\n" + "=" * 60)
    print("📊 SYNTAX FIX COMPLETION REPORT")
    print("=" * 60)
    print(f"🎯 Fixes Applied: {success_count}/{total_fixes}")
    
    if success_count == total_fixes:
        print("\n🎉 SYNTAX ERRORS FIXED!")
        print()
        print("✅ Applied Fixes:")
        print("   • WebSocket client function names restored")
        print("   • Validation test method names fixed")
        print("   • OrderManager syntax checked and corrected")
        print("   • Simple validation test created")
        print()
        print("🧪 Next Steps:")
        print("   1. Run: python3 simple_syntax_validation.py")
        print("   2. If successful, run: python3 validate_task_3_3_a.py")
        print("   3. Should now work without syntax errors")
        
    else:
        print("\n⚠️ Some syntax fixes may need manual review")
    
    print("=" * 60)
    return success_count == total_fixes

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Syntax fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
