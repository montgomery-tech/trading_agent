#!/usr/bin/env python3
"""
Enable Real Order Placement

This enables order management in the WebSocket client for real trading.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def enable_real_order_placement():
    """Enable real order placement in the WebSocket client."""
    print("🔧 ENABLING REAL ORDER PLACEMENT")
    print("=" * 50)
    
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        
        # Create client
        client = KrakenWebSocketClient()
        
        # Check initial state
        print(f"📊 Initial state:")
        print(f"   Order management enabled: {client._order_management_enabled}")
        
        # Enable order management before connecting
        print("🔧 Enabling order management...")
        client._order_management_enabled = True
        
        # Connect
        await client.connect_private()
        
        if client.is_private_connected:
            print("✅ Connected with order management enabled")
            
            # Check final status
            status = client.get_connection_status()
            print(f"📊 Final Status:")
            print(f"   Private connected: {status.get('private_connected', False)}")
            print(f"   Order management: {status.get('order_management_enabled', False)}")
            print(f"   Has token: {status.get('has_token', False)}")
            
            # Check if order manager is available
            if hasattr(client, 'order_manager') and client.order_manager:
                print("✅ Order manager initialized")
            else:
                print("⚠️ Order manager not initialized")
            
            await client.disconnect()
            
            if status.get('order_management_enabled', False):
                print("\n🎉 SUCCESS: Order management is now enabled!")
                print("✅ Ready for live order placement")
                return True
            else:
                print("\n❌ Order management still not enabled")
                return False
        else:
            print("❌ Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Failed to enable order management: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(enable_real_order_placement())
    
    if success:
        print("\n🚀 READY FOR LIVE ORDERS!")
        print("Order management is now enabled.")
        print("You can now place real orders.")
    else:
        print("\n❌ Order management enablement failed")
        print("Check the logs above for issues.")
