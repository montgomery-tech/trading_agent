#!/usr/bin/env python3
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
    print("\n🧪 Testing Basic Functionality...")
    
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
    
    print("\n" + "=" * 60)
    print("📊 SIMPLE VALIDATION RESULTS")
    print("=" * 60)
    
    if imports_ok and functionality_ok:
        print("🎉 ALL SYNTAX ERRORS FIXED!")
        print("✅ All modules import successfully")
        print("✅ Basic functionality working")
        print("\n🎯 Ready to run full validation test")
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
