#!/usr/bin/env python3
"""
Debug Server - Find the Issue

This simplified server will help us identify why the enhanced server exits.

Usage: python3 debug_server.py --http
"""

import asyncio
import sys
import traceback
from pathlib import Path

print("🔍 DEBUG SERVER STARTING")
print("=" * 50)

try:
    print("1️⃣ Testing basic imports...")
    from mcp.server.fastmcp import FastMCP
    print("   ✅ FastMCP imported")
    
    import uvicorn
    print("   ✅ uvicorn imported")
    
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    print("   ✅ Starlette components imported")
    
    print("2️⃣ Creating basic MCP server...")
    mcp = FastMCP("Debug Server")
    print("   ✅ MCP server created")
    
    @mcp.tool()
    def debug_ping() -> str:
        """Debug ping tool."""
        return "🏓 Debug pong!"
    
    print("   ✅ Tool registered")
    
    print("3️⃣ Testing async function...")
    
    async def debug_main():
        """Debug main function."""
        print("   🔄 Inside debug_main()")
        
        try:
            print("   📡 Creating health check...")
            async def health_check(request):
                return JSONResponse({
                    "status": "healthy",
                    "server": "Debug Server",
                    "message": "Debug server is working!"
                })
            
            print("   🔧 Creating routes...")
            routes = [Route("/health", health_check, methods=["GET"])]
            
            print("   📦 Creating Starlette app...")
            app = Starlette(routes=routes)
            
            print("   🚀 Starting uvicorn server...")
            print("   📍 Server will run on http://localhost:8000")
            print("   🛑 Press Ctrl+C to stop")
            print("   " + "="*40)
            
            config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            print(f"   ❌ Error in debug_main: {e}")
            traceback.print_exc()
    
    print("4️⃣ Running main function...")
    
    if "--http" in sys.argv:
        print("   🌐 HTTP mode requested")
        asyncio.run(debug_main())
    else:
        print("   📱 Stdio mode (use --http for HTTP)")
        asyncio.run(mcp.run_stdio_async())
        
except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
    print("📍 Full traceback:")
    traceback.print_exc()
finally:
    print("\n🏁 Debug server finished")
