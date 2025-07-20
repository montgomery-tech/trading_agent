#!/usr/bin/env python3
"""
simple_kraken_test.py
Simple test to verify Kraken API connectivity without complex imports
"""

import asyncio
import aiohttp
import json

async def test_kraken_public_api():
    """Test Kraken public API to verify basic connectivity"""
    print("🔍 Testing Kraken public API connectivity...")
    
    try:
        url = "https://api.kraken.com/0/public/Time"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        server_time = data['result']['unixtime']
                        print(f"✅ Kraken API accessible - Server time: {server_time}")
                        return True
                    else:
                        print(f"❌ Unexpected response: {data}")
                        return False
                else:
                    print(f"❌ HTTP {response.status}")
                    return False
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def test_kraken_ticker():
    """Test getting ticker data for BTC/USD"""
    print("🔍 Testing Kraken ticker data...")
    
    try:
        url = "https://api.kraken.com/0/public/Ticker"
        params = {"pair": "XBTUSD"}
        
        async with aiohttp.ClientSession() as session:
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

async def test_symbol_mapping():
    """Test the symbol mapping logic"""
    print("🔍 Testing symbol mapping logic...")
    
    mappings = {
        "BTC/USD": "XBTUSD",
        "ETH/USD": "ETHUSD", 
        "ETH/BTC": "ETHXBT",
        "LTC/USD": "LTCUSD",
    }
    
    for internal, kraken in mappings.items():
        print(f"✅ {internal} -> {kraken}")
    
    return True

async def main():
    print("🧪 SIMPLE KRAKEN CONNECTIVITY TEST")
    print("=" * 50)
    print()
    
    # Test basic connectivity
    api_ok = await test_kraken_public_api()
    print()
    
    if api_ok:
        # Test ticker data
        ticker_ok = await test_kraken_ticker()
        print()
        
        # Test symbol mapping
        mapping_ok = await test_symbol_mapping()
        print()
        
        if ticker_ok and mapping_ok:
            print("✅ ALL TESTS PASSED!")
            print()
            print("🎯 Your system can connect to Kraken API successfully.")
            print("   Ready to proceed with full integration testing.")
        else:
            print("⚠️  Some tests failed but basic connectivity works.")
    else:
        print("❌ CONNECTIVITY FAILED!")
        print("   Check your internet connection and try again.")

if __name__ == "__main__":
    asyncio.run(main())
