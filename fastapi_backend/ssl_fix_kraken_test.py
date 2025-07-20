#!/usr/bin/env python3
"""
ssl_fix_kraken_test.py
Kraken connectivity test with SSL certificate handling for macOS
"""

import asyncio
import aiohttp
import ssl
import certifi
import json

async def test_kraken_public_api():
    """Test Kraken public API with proper SSL handling"""
    print("🔍 Testing Kraken public API connectivity...")
    
    try:
        url = "https://api.kraken.com/0/public/Time"
        
        # Create SSL context that uses system certificates
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        server_time = data['result']['unixtime']
                        print(f"✅ Kraken API accessible - Server time: {server_time}")
                        return True, ssl_context
                    else:
                        print(f"❌ Unexpected response: {data}")
                        return False, None
                else:
                    print(f"❌ HTTP {response.status}")
                    return False, None
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Trying alternative SSL approach...")
        
        # Try with less strict SSL verification
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            server_time = data['result']['unixtime']
                            print(f"⚠️  Kraken API accessible with relaxed SSL - Server time: {server_time}")
                            print("   Note: Using relaxed SSL verification")
                            return True, ssl_context
            
        except Exception as e2:
            print(f"❌ Alternative SSL approach also failed: {e2}")
        
        return False, None

async def test_kraken_ticker(ssl_context=None):
    """Test getting ticker data for BTC/USD"""
    print("🔍 Testing Kraken ticker data...")
    
    try:
        url = "https://api.kraken.com/0/public/Ticker"
        params = {"pair": "XBTUSD"}
        
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data and 'XXBTZUSD' in data['result']:
                        ticker = data['result']['XXBTZUSD']
                        last_price = float(ticker['c'][0])
                        bid = float(ticker['b'][0])
                        ask = float(ticker['a'][0])
                        
                        print(f"✅ BTC/USD Ticker:")
                        print(f"   Last: ${last_price:,.2f}")
                        print(f"   Bid:  ${bid:,.2f}")
                        print(f"   Ask:  ${ask:,.2f}")
                        return True
                    else:
                        print(f"❌ No ticker data found: {data}")
                        return False
                else:
                    print(f"❌ HTTP {response.status}")
                    return False
    
    except Exception as e:
        print(f"❌ Ticker request failed: {e}")
        return False

def fix_ssl_certificates():
    """Provide instructions for fixing SSL certificates on macOS"""
    print("🔧 SSL CERTIFICATE FIX INSTRUCTIONS:")
    print("=" * 50)
    print()
    print("If you're getting SSL certificate errors, try these fixes:")
    print()
    print("1️⃣ Install certificates (recommended):")
    print("   pip3 install --upgrade certifi")
    print("   # Then run this Python command:")
    print('   python3 -c "import certifi; print(certifi.where())"')
    print()
    print("2️⃣ macOS specific fix:")
    print("   /Applications/Python\\ 3.x/Install\\ Certificates.command")
    print("   (Replace 3.x with your Python version)")
    print()
    print("3️⃣ Alternative - use pip to install certificates:")
    print("   pip3 install --upgrade certifi")
    print("   pip3 install --upgrade requests[security]")
    print()
    print("4️⃣ If still having issues, we can configure the Kraken client")
    print("   to use relaxed SSL verification for development.")

async def main():
    print("🧪 KRAKEN CONNECTIVITY TEST (SSL-AWARE)")
    print("=" * 60)
    print()
    
    # Test basic connectivity
    api_ok, ssl_context = await test_kraken_public_api()
    print()
    
    if api_ok:
        # Test ticker data
        ticker_ok = await test_kraken_ticker(ssl_context)
        print()
        
        if ticker_ok:
            print("✅ ALL TESTS PASSED!")
            print()
            print("🎯 Your system can connect to Kraken API successfully.")
            print("   Ready to proceed with full integration testing.")
            print()
            print("📋 Next steps:")
            print("   1. Update your Kraken API client to use the working SSL context")
            print("   2. Test your FastAPI application: python3 main.py")
            print("   3. Try the endpoint: GET /api/v1/trades/kraken/status")
        else:
            print("⚠️  Ticker test failed but basic connectivity works.")
    else:
        print("❌ CONNECTIVITY FAILED!")
        print()
        fix_ssl_certificates()

if __name__ == "__main__":
    asyncio.run(main())
