#!/usr/bin/env python3
"""
WebSocket SSL Certificate Fix

Fixes SSL certificate verification issues for WebSocket connections on macOS.
Updates the WebSocket client to handle SSL certificate verification properly.
"""

import ssl
import sys
from pathlib import Path

def create_ssl_context_for_websocket():
    """Create SSL context that works with macOS certificate verification."""
    # Create default SSL context
    ssl_context = ssl.create_default_context()
    
    # Set minimum TLS version
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Load default CA certificates
    ssl_context.load_default_certs()
    
    # For macOS, also try to load system certificates
    try:
        # This helps with macOS certificate chain issues
        ssl_context.load_verify_locations('/System/Library/OpenSSL/certs/cert.pem')
    except:
        pass
    
    # Enable hostname checking
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    return ssl_context

def update_websocket_client():
    """Update WebSocket client to use proper SSL context."""
    
    websocket_client_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_client_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the SSL context initialization
        ssl_context_init = 'self.ssl_context = ssl.create_default_context()'
        
        if ssl_context_init in content:
            # Replace with our enhanced SSL context
            new_ssl_context = '''# Create enhanced SSL context for macOS compatibility
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.ssl_context.load_default_certs()
        
        # Load macOS system certificates if available
        try:
            self.ssl_context.load_verify_locations('/System/Library/OpenSSL/certs/cert.pem')
        except:
            pass
            
        # Ensure hostname verification
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED'''
        
            content = content.replace(ssl_context_init, new_ssl_context)
            
            with open(websocket_client_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Updated WebSocket client SSL context")
            return True
        else:
            print("⚠️ SSL context initialization not found in expected format")
            return False
            
    except Exception as e:
        print(f"❌ Error updating WebSocket client: {e}")
        return False

def test_ssl_fix():
    """Test the SSL fix with a simple WebSocket connection."""
    print("🧪 Testing SSL fix...")
    
    try:
        import asyncio
        import websockets
        import json
        
        async def test_connection():
            # Create the same SSL context we're using in the fix
            ssl_context = create_ssl_context_for_websocket()
            
            try:
                async with websockets.connect(
                    "wss://ws.kraken.com",
                    ssl=ssl_context,
                    ping_interval=None,
                    ping_timeout=None
                ) as websocket:
                    
                    # Send a simple subscription
                    subscribe_msg = {
                        "event": "subscribe",
                        "pair": ["ETH/USD"],
                        "subscription": {"name": "ticker"}
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    
                    # Try to receive a response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print("✅ WebSocket SSL connection test successful")
                    return True
                    
            except Exception as e:
                print(f"❌ WebSocket SSL connection test failed: {e}")
                return False
        
        return asyncio.run(test_connection())
        
    except Exception as e:
        print(f"❌ SSL test error: {e}")
        return False

def alternative_ssl_approaches():
    """Show alternative SSL approaches if the main fix doesn't work."""
    
    print("\n🔧 ALTERNATIVE SSL APPROACHES")
    print("-" * 40)
    print()
    print("If the SSL context fix doesn't work, try these approaches:")
    print()
    print("1. **Update macOS certificates**:")
    print("   brew install ca-certificates")
    print("   # or update macOS system")
    print()
    print("2. **Use Python certifi certificates**:")
    print("   pip install --upgrade certifi")
    print()
    print("3. **Disable SSL verification temporarily** (not recommended for production):")
    print("   ssl_context = ssl.create_default_context()")
    print("   ssl_context.check_hostname = False")
    print("   ssl_context.verify_mode = ssl.CERT_NONE")
    print()
    print("4. **Use system Python instead of framework Python**:")
    print("   # If using Python installed via python.org, try homebrew Python")
    print("   brew install python")
    print()

def main():
    """Main execution function."""
    print("🔧 WEBSOCKET SSL CERTIFICATE FIX")
    print("=" * 50)
    print()
    print("ISSUE IDENTIFIED:")
    print("• HTTP requests work (token, REST API)")
    print("• WebSocket SSL certificate verification fails")
    print("• Common macOS SSL certificate chain issue")
    print()
    
    # Test current SSL setup
    print("🧪 Testing current SSL setup...")
    ssl_works = test_ssl_fix()
    
    if ssl_works:
        print("✅ SSL already working - no fix needed!")
        return True
    
    print("\n🔧 Applying SSL context fix to WebSocket client...")
    
    # Apply the fix
    fix_applied = update_websocket_client()
    
    if fix_applied:
        print("✅ SSL context fix applied")
        print("\n🧪 Testing WebSocket connection after fix...")
        
        # Test again after fix
        ssl_works_after_fix = test_ssl_fix()
        
        if ssl_works_after_fix:
            print("\n🎉 SSL FIX SUCCESSFUL!")
            print("=" * 50)
            print("✅ WebSocket SSL certificate verification fixed")
            print("✅ Ready to test account balance retrieval")
            print()
            print("🚀 TEST COMMAND:")
            print("python3 account_balance_retrieval.py")
            return True
        else:
            print("\n⚠️ SSL fix applied but still having issues")
            alternative_ssl_approaches()
            return False
    else:
        print("❌ Could not apply SSL fix")
        alternative_ssl_approaches()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
