#!/usr/bin/env python3
"""
WebSocket SSL Context Investigation

The WebSocket client already has SSL verification disabled, but we're still getting
certificate errors. This script investigates what's happening.
"""

import asyncio
import ssl
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    import websockets
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_direct_websocket_with_no_ssl():
    """Test WebSocket connection with SSL verification explicitly disabled."""
    print("🔧 TESTING DIRECT WEBSOCKET WITH SSL DISABLED")
    print("-" * 50)
    
    try:
        # Create SSL context that definitely doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        print(f"SSL context settings:")
        print(f"  check_hostname: {ssl_context.check_hostname}")
        print(f"  verify_mode: {ssl_context.verify_mode}")
        
        async with websockets.connect(
            "wss://ws.kraken.com",
            ssl=ssl_context,
            ping_interval=None,
            ping_timeout=None
        ) as websocket:
            
            print("✅ Direct WebSocket connection successful")
            
            # Wait for system status message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"📨 Received: {data.get('event', 'unknown')} - {data.get('status', 'unknown')}")
            
            return True
            
    except Exception as e:
        print(f"❌ Direct WebSocket failed: {e}")
        return False


async def test_kraken_websocket_client():
    """Test the actual KrakenWebSocketClient class."""
    print("\n🔧 TESTING KRAKEN WEBSOCKET CLIENT")
    print("-" * 50)
    
    try:
        client = KrakenWebSocketClient()
        
        # Check the SSL context
        print(f"SSL context settings:")
        print(f"  check_hostname: {client.ssl_context.check_hostname}")
        print(f"  verify_mode: {client.ssl_context.verify_mode}")
        
        # Try to connect to public WebSocket
        try:
            client.public_ws = await websockets.connect(
                client.public_url,
                ssl=client.ssl_context,
                ping_interval=None,
                ping_timeout=None
            )
            
            client.is_public_connected = True
            print("✅ KrakenWebSocketClient public connection successful")
            
            # Wait for a message
            message = await asyncio.wait_for(client.public_ws.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"📨 Received: {data.get('event', 'unknown')} - {data.get('status', 'unknown')}")
            
            await client.public_ws.close()
            return True
            
        except Exception as e:
            print(f"❌ KrakenWebSocketClient connection failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ KrakenWebSocketClient creation failed: {e}")
        return False


async def test_private_websocket_connection():
    """Test private WebSocket connection process."""
    print("\n🔧 TESTING PRIVATE WEBSOCKET CONNECTION PROCESS")
    print("-" * 50)
    
    try:
        client = KrakenWebSocketClient()
        
        # Try the private connection process
        print("🔑 Testing private connection...")
        await client.connect_private()
        
        if client.is_private_connected:
            print("✅ Private WebSocket connection successful")
            await client.disconnect()
            return True
        else:
            print("❌ Private WebSocket connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Private connection error: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check if it's specifically an SSL error
        if "SSL" in str(e) or "certificate" in str(e):
            print("🔍 This is an SSL certificate error")
            
            # Check where the error is coming from
            if "token" in str(e).lower():
                print("💡 Error appears to be from token request, not WebSocket connection")
            else:
                print("💡 Error appears to be from WebSocket connection itself")
        
        return False


async def investigate_token_manager():
    """Investigate if the token manager is causing SSL issues."""
    print("\n🔧 INVESTIGATING TOKEN MANAGER SSL")
    print("-" * 50)
    
    try:
        from trading_systems.exchanges.kraken.token_manager import KrakenTokenManager
        
        token_manager = KrakenTokenManager()
        await token_manager._ensure_http_client()
        
        print("🔍 Token manager HTTP client settings:")
        if hasattr(token_manager._http_client, '_transport'):
            transport = token_manager._http_client._transport
            print(f"  HTTP client transport: {type(transport).__name__}")
        
        # Try to get a token
        print("🔑 Attempting token request...")
        try:
            token = await token_manager.get_websocket_token()
            print("✅ Token request successful")
            return True
        except Exception as e:
            print(f"❌ Token request failed: {e}")
            
            # This is likely where the SSL error is coming from
            if "SSL" in str(e) or "certificate" in str(e):
                print("🎯 SSL error is from token request, not WebSocket connection!")
                print("💡 The token manager needs SSL context fix, not the WebSocket client")
            
            return False
            
    except Exception as e:
        print(f"❌ Token manager investigation failed: {e}")
        return False


def create_fixed_ssl_context():
    """Create a properly configured SSL context."""
    ssl_context = ssl.create_default_context()
    
    # Set proper TLS version support
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Try to load certificates properly
    try:
        # Load default certificates
        ssl_context.load_default_certs()
        
        # Try loading macOS system certificates
        try:
            ssl_context.load_verify_locations('/System/Library/OpenSSL/certs/cert.pem')
        except:
            pass
            
        try:
            ssl_context.load_verify_locations('/etc/ssl/certs/ca-certificates.crt')
        except:
            pass
            
        # Enable hostname and certificate verification
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        print("✅ Created SSL context with certificate verification")
        return ssl_context, True
        
    except Exception as e:
        print(f"⚠️ Certificate loading failed: {e}")
        
        # Fallback to no verification
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        print("⚠️ Created SSL context without certificate verification")
        return ssl_context, False


async def test_token_request_with_fixed_ssl():
    """Test token request with properly configured SSL."""
    print("\n🔧 TESTING TOKEN REQUEST WITH FIXED SSL")
    print("-" * 50)
    
    try:
        import httpx
        from trading_systems.config.settings import settings
        import base64
        import hashlib
        import hmac
        import time
        
        # Get credentials
        api_key, api_secret = settings.get_api_credentials()
        
        # Create signature
        nonce = str(int(time.time() * 1000))
        post_data = f"nonce={nonce}"
        api_path = "/0/private/GetWebSocketsToken"
        
        api_secret_decoded = base64.b64decode(api_secret)
        sha256_hash = hashlib.sha256((nonce + post_data).encode('utf-8'))
        hmac_signature = hmac.new(
            api_secret_decoded,
            api_path.encode('utf-8') + sha256_hash.digest(),
            hashlib.sha512
        )
        signature = base64.b64encode(hmac_signature.digest()).decode('utf-8')
        
        headers = {
            "API-Key": api_key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"nonce": nonce}
        url = f"https://api.kraken.com{api_path}"
        
        # Test with different SSL configurations
        ssl_context, has_verification = create_fixed_ssl_context()
        
        print(f"🔒 Testing with SSL verification: {has_verification}")
        
        async with httpx.AsyncClient(verify=ssl_context, timeout=30.0) as client:
            response = await client.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "token" in result["result"]:
                    print("✅ Token request with fixed SSL successful")
                    return True
                else:
                    print(f"❌ Token request API error: {result.get('error', 'Unknown')}")
            else:
                print(f"❌ Token request HTTP error: {response.status_code}")
            
            return False
            
    except Exception as e:
        print(f"❌ Fixed SSL token request failed: {e}")
        return False


async def main():
    """Run all SSL investigations."""
    print("🔍 WEBSOCKET SSL CONTEXT INVESTIGATION")
    print("=" * 70)
    print("Investigating why SSL certificate errors persist despite disabled verification")
    print("=" * 70)
    
    # Test direct WebSocket connection
    direct_ws_ok = await test_direct_websocket_with_no_ssl()
    
    # Test KrakenWebSocketClient
    client_ws_ok = await test_kraken_websocket_client()
    
    # Test token manager (likely source of SSL error)
    token_mgr_ok = await investigate_token_manager()
    
    # Test private connection process
    private_ok = await test_private_websocket_connection()
    
    # Test token request with fixed SSL
    fixed_ssl_ok = await test_token_request_with_fixed_ssl()
    
    # Summary
    print("\n📊 INVESTIGATION SUMMARY")
    print("=" * 50)
    print(f"✅ Direct WebSocket (SSL disabled): {direct_ws_ok}")
    print(f"✅ KrakenWebSocketClient: {client_ws_ok}")
    print(f"✅ Token Manager: {token_mgr_ok}")
    print(f"✅ Private Connection: {private_ok}")
    print(f"✅ Fixed SSL Token Request: {fixed_ssl_ok}")
    
    print("\n💡 CONCLUSIONS")
    print("-" * 30)
    
    if direct_ws_ok and client_ws_ok and not token_mgr_ok:
        print("🎯 ISSUE IDENTIFIED: Token Manager SSL Configuration")
        print("   • WebSocket connections work fine")
        print("   • Token request is failing with SSL certificate verification")
        print("   • Need to fix token manager HTTP client SSL context")
    elif not direct_ws_ok:
        print("🎯 ISSUE: Basic WebSocket SSL verification problem")
        print("   • Even disabled SSL verification isn't working")
        print("   • May need system-level SSL fixes")
    elif fixed_ssl_ok:
        print("🎯 SOLUTION: Fixed SSL context works")
        print("   • Need to apply fixed SSL context to token manager")
    else:
        print("🎯 COMPLEX ISSUE: Multiple SSL problems")
        print("   • May need system certificate updates")
    
    return any([direct_ws_ok, client_ws_ok, fixed_ssl_ok])


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
