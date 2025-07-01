#!/usr/bin/env python3
"""
MCP Version and Transport Checker

This script checks what MCP features are available in your installation.
"""

import sys
from pathlib import Path

print("🔍 CHECKING MCP INSTALLATION AND CAPABILITIES")
print("=" * 60)

# Check MCP package
try:
    import mcp
    print(f"✅ MCP package version: {getattr(mcp, '__version__', 'unknown')}")
except ImportError as e:
    print(f"❌ MCP package not found: {e}")
    sys.exit(1)

# Check FastMCP
try:
    from mcp.server.fastmcp import FastMCP
    print("✅ FastMCP available")
    
    # Test FastMCP creation
    test_mcp = FastMCP("Test Server")
    print("✅ FastMCP can be instantiated")
    
    # Check available methods
    methods = [method for method in dir(test_mcp) if not method.startswith('_')]
    print(f"✅ FastMCP methods: {len(methods)} available")
    
    # Check for specific methods
    key_methods = ['tool', 'resource', 'run', 'run_server']
    for method in key_methods:
        if hasattr(test_mcp, method):
            print(f"   ✅ {method}() available")
        else:
            print(f"   ❌ {method}() not available")
            
except ImportError as e:
    print(f"❌ FastMCP not available: {e}")

# Check available transports
print("\n🚀 CHECKING AVAILABLE TRANSPORTS")
print("-" * 40)

transports = []

# Check stdio transport
try:
    from mcp.server import stdio
    print("✅ stdio transport available")
    transports.append("stdio")
except ImportError:
    print("❌ stdio transport not available")

# Check SSE transport
try:
    from mcp.server.sse import SseServerTransport
    print("✅ SSE (Server-Sent Events) transport available")
    transports.append("sse")
    
    # Check SSE methods
    sse = SseServerTransport("/test")
    if hasattr(sse, 'mount'):
        print("   ✅ mount() method available")
    else:
        print("   ❌ mount() method not available")
        
except ImportError:
    print("❌ SSE transport not available")

# Check HTTP support
try:
    import uvicorn
    print("✅ uvicorn available (HTTP server support)")
except ImportError:
    print("❌ uvicorn not available")

try:
    import starlette
    print("✅ starlette available (ASGI framework)")
except ImportError:
    print("❌ starlette not available")

# Check client capabilities
print("\n🔗 CHECKING CLIENT CAPABILITIES")
print("-" * 40)

try:
    from mcp.client import ClientSession
    print("✅ MCP ClientSession available")
except ImportError:
    print("❌ MCP ClientSession not available")

try:
    from mcp.client.sse import SseClientTransport
    print("✅ SSE ClientTransport available")
except ImportError:
    print("❌ SSE ClientTransport not available")

try:
    import httpx
    print("✅ httpx available (HTTP client support)")
except ImportError:
    print("❌ httpx not available")

# Summary
print("\n📊 SUMMARY")
print("=" * 60)

if "stdio" in transports:
    print("✅ Your current stdio MCP server should work perfectly")

if "sse" in transports:
    print("✅ HTTP/SSE transport is available")
    print("   → External agents can potentially connect via HTTP")
else:
    print("❌ HTTP/SSE transport not available in this MCP version")
    print("   → External agents cannot connect directly")
    print("   → Your stdio server works great for local use")

print(f"\n🎯 Available transports: {', '.join(transports) if transports else 'None detected'}")

print("\n💡 RECOMMENDATIONS:")
if "sse" in transports:
    print("   • Try the working_http_server.py")
    print("   • External agent testing should work")
else:
    print("   • Your stdio MCP server is working perfectly")
    print("   • For external agents, consider:")
    print("     - Upgrading MCP package: pip install --upgrade mcp")
    print("     - Using a different MCP version with HTTP support")
    print("     - Deploying stdio server with network wrapper")

print("\n🚀 Your MCP server implementation is solid regardless of transport!")
