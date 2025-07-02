#!/usr/bin/env python3
"""
Fix WebSocket OrderManager Initialization

This script fixes the WebSocket client to properly initialize OrderManager
during private connection, ensuring order management is available for live trading.

The issue: order_management_enabled=True but OrderManager is not initialized
The fix: Automatically initialize OrderManager during private connection
"""

import sys
from pathlib import Path


def fix_websocket_ordermanager_initialization():
    """Fix the WebSocket client to automatically initialize OrderManager."""
    
    print("🔧 FIXING WEBSOCKET ORDERMANAGER INITIALIZATION")
    print("=" * 60)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ WebSocket client file not found: {websocket_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Check if OrderManager initialization is already in connect_private
    if 'await self.initialize_order_manager()' in content:
        print("✅ OrderManager initialization already exists in connect_private")
        return True
    
    print("🔧 Adding OrderManager initialization to connect_private method...")
    
    # Find the connect_private method
    connect_private_start = content.find('async def connect_private(self)')
    if connect_private_start == -1:
        print("❌ connect_private method not found")
        return False
    
    # Find where to insert OrderManager initialization
    # Look for the account manager initialization section
    account_manager_section = content.find('if self.account_manager is None:', connect_private_start)
    if account_manager_section == -1:
        print("❌ Account manager initialization not found in connect_private")
        return False
    
    # Find the end of the account manager initialization block
    account_init_end = content.find('self.log_info("Account data manager initialized")', account_manager_section)
    if account_init_end == -1:
        print("❌ Account manager log statement not found")
        return False
    
    # Find the end of that line
    line_end = content.find('\n', account_init_end)
    
    # Insert OrderManager initialization after account manager
    ordermanager_init_code = '''

            # Initialize OrderManager integration if enabled
            if self._order_management_enabled:
                await self.initialize_order_manager()
                self.log_info("OrderManager integration initialized during private connection")'''
    
    new_content = content[:line_end] + ordermanager_init_code + content[line_end:]
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Added OrderManager initialization to connect_private method")
        return True
    except Exception as e:
        print(f"❌ Error writing WebSocket client: {e}")
        return False


def fix_live_order_placement_script():
    """Fix the live order placement script to ensure OrderManager is available."""
    
    print("\n🔧 FIXING LIVE ORDER PLACEMENT SCRIPT")
    print("=" * 60)
    
    live_order_path = Path("live_order_placement.py")
    
    try:
        with open(live_order_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Live order placement script not found: {live_order_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading live order placement script: {e}")
        return False
    
    # Check if explicit OrderManager initialization is already there
    if 'await self.websocket_client.initialize_order_manager()' in content:
        print("✅ OrderManager initialization already exists in live order script")
        return True
    
    print("🔧 Adding explicit OrderManager initialization to live order script...")
    
    # Find the connect_and_validate method where we establish the connection
    connect_validate_start = content.find('await self.websocket_client.connect_private()')
    if connect_validate_start == -1:
        print("❌ connect_private call not found in live order script")
        return False
    
    # Find the end of the connection success block
    success_check = content.find('print("✅ Connected to live Kraken account")', connect_validate_start)
    if success_check == -1:
        print("❌ Connection success message not found")
        return False
    
    # Find the end of that line
    line_end = content.find('\n', success_check)
    
    # Insert OrderManager initialization after successful connection
    ordermanager_init_code = '''
            
            # Ensure OrderManager is initialized for order placement
            if self.websocket_client._order_management_enabled:
                if not self.websocket_client.order_manager:
                    print("🔧 Initializing OrderManager for live orders...")
                    await self.websocket_client.initialize_order_manager()
                    print("✅ OrderManager initialized successfully")
                else:
                    print("✅ OrderManager already initialized")
            else:
                print("⚠️ Order management not enabled - enabling now...")
                self.websocket_client._order_management_enabled = True
                await self.websocket_client.initialize_order_manager()
                print("✅ OrderManager enabled and initialized")'''
    
    new_content = content[:line_end] + ordermanager_init_code + content[line_end:]
    
    try:
        with open(live_order_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Added OrderManager initialization to live order placement script")
        return True
    except Exception as e:
        print(f"❌ Error writing live order placement script: {e}")
        return False


def main():
    """Main execution function."""
    print("🚀 FIXING ORDERMANAGER INITIALIZATION ISSUE")
    print("=" * 70)
    print()
    print("This fix addresses the issue where:")
    print("• WebSocket client shows order_management_enabled=True")
    print("• But OrderManager is not actually initialized")
    print("• Causing live order placement to fail")
    print()
    
    success1 = fix_websocket_ordermanager_initialization()
    success2 = fix_live_order_placement_script()
    
    if success1 and success2:
        print("\n🎉 SUCCESS: OrderManager Initialization Fixed!")
        print("=" * 70)
        print("✅ WebSocket client will auto-initialize OrderManager on private connect")
        print("✅ Live order script will explicitly ensure OrderManager is ready")
        print("✅ Order management should now show as properly enabled")
        print()
        print("🚀 NEXT STEPS:")
        print("1. Test the fix by running: python3 live_order_placement.py")
        print("2. Verify order management shows as enabled")
        print("3. Confirm order placement proceeds past the management check")
        return True
    else:
        print("\n❌ SOME FIXES FAILED")
        print("Check the errors above and fix manually if needed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
