#!/usr/bin/env python3
"""
Conservative Production Testing

Test live account data and minimal trading with $10 limit
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_account_data():
    """Test reading real account data (safe)."""
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        
        print("💰 TESTING LIVE ACCOUNT DATA")
        print("=" * 40)
        
        client = KrakenWebSocketClient()
        await client.connect_private()
        
        if client.is_private_connected:
            print("✅ Connected to live account")
            
            # Try to get account snapshot if available
            if hasattr(client, 'get_account_snapshot'):
                snapshot = await client.get_account_snapshot()
                if snapshot:
                    print("📊 Account data retrieved:")
                    print(f"   Account snapshot available: ✅")
                else:
                    print("📊 Account snapshot: None (may need subscription)")
            
            # Check connection status
            status = client.get_connection_status()
            print(f"📊 Account features:")
            print(f"   Account data enabled: {status.get('account_data_enabled', False)}")
            print(f"   Order management enabled: {status.get('order_management_enabled', False)}")
            
            await client.disconnect()
            print("✅ Test completed safely")
            return True
        else:
            print("❌ Connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🧪 CONSERVATIVE PRODUCTION TESTING")
    print("Safe read-only testing with live credentials")
    print("=" * 50)
    
    success = await test_account_data()
    
    if success:
        print("\n🎉 SUCCESS! Ready for minimal trading tests")
        print("💡 Next: Test minimal orders (max $10)")
    else:
        print("\n❌ Account data test failed")

if __name__ == "__main__":
    asyncio.run(main())
