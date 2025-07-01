#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_server():
    print("🧪 Testing MCP Server Components...")
    
    try:
        # Test basic imports
        from trading_systems.mcp_server.config import MCPServerConfig
        from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter
        print("✅ MCP server components import successfully")
        
        # Test adapter
        config = MCPServerConfig()
        adapter = TradingSystemAdapter(config)
        await adapter.initialize()
        print("✅ Trading adapter initializes successfully")
        
        # Test methods
        status = adapter.get_status()
        print(f"✅ Status check: {status}")
        
        balance = await adapter.get_account_balance()
        print(f"✅ Balance check: {balance}")
        
        await adapter.shutdown()
        print("✅ All tests passed! Your MCP server is working!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_server())
