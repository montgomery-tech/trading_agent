#!/usr/bin/env python3
"""
Debug MCP Client

Simple test client to debug the MCP server connection issues.
"""

import asyncio
import json
import httpx

async def test_server():
    """Test the MCP server endpoints."""
    server_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        print("🔍 DEBUGGING MCP SERVER CONNECTION")
        print("=" * 50)
        
        # Test 1: Health check
        print("1. Testing health endpoint...")
        try:
            response = await client.get(f"{server_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
        
        # Test 2: Root endpoint
        print("2. Testing root endpoint...")
        try:
            response = await client.get(f"{server_url}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
        
        # Test 3: SSE endpoint with GET
        print("3. Testing SSE endpoint with GET...")
        try:
            response = await client.get(f"{server_url}/sse")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
        
        # Test 4: SSE endpoint with POST (MCP style)
        print("4. Testing SSE endpoint with MCP POST...")
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "ping",
                    "arguments": {}
                }
            }
            
            response = await client.post(
                f"{server_url}/sse",
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   JSON Response: {json.dumps(result, indent=2)}")
                except:
                    print(f"   Text Response: {response.text}")
            else:
                print(f"   Error Response: {response.text}")
                
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
        
        # Test 5: Try direct function call (if server supports it)
        print("5. Testing direct tool call...")
        try:
            response = await client.post(
                f"{server_url}/tools/ping",
                json={},
                headers={"Content-Type": "application/json"}
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_server())
