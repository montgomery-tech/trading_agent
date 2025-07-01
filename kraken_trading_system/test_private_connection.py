#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_private_connection():
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        from trading_systems.config.settings import settings
        
        print("🧪 TESTING PRIVATE WEBSOCKET CONNECTION")
        print("=" * 50)
        
        # Check credentials first
        if not settings.has_api_credentials():
            print("❌ No credentials available")
            return
            
        print("✅ Credentials available")
        
        # Create client and test private connection
        client = KrakenWebSocketClient()
        print("✅ WebSocket client created")
        
        print("🔗 Attempting private connection...")
        await client.connect_private()
        
        if client.is_private_connected:
            print("🎉 SUCCESS! Private WebSocket connected!")
            
            # Get connection status
            status = client.get_connection_status()
            print(f"📊 Connection Status:")
            print(f"   Private Connected: {status.get('private_connected', False)}")
            print(f"   Has Token: {status.get('has_token', False)}")
            
            # Cleanup
            await client.disconnect()
            print("✅ Disconnected successfully")
            
            return True
        else:
            print("❌ Private connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_private_connection())
    if success:
        print("\n🎉 LIVE CONNECTION ESTABLISHED!")
        print("Ready for production mode testing!")
    else:
        print("\n❌ Connection failed - need to debug further")
