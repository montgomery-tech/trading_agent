#!/usr/bin/env python3
"""
Debug Kraken API Response

Let's see what Kraken actually returns for ETH price data.
"""

import asyncio
import json

async def debug_kraken_api():
    """Debug what Kraken API actually returns."""
    print("🔍 DEBUGGING KRAKEN API RESPONSE")
    print("=" * 50)
    
    try:
        import aiohttp
        
        # Test different endpoints and pairs
        test_urls = [
            ("ETH/USD ticker", "https://api.kraken.com/0/public/Ticker?pair=ETHUSD"\),
            ("ETH/USD alt", "https://api.kraken.com/0/public/Ticker?pair=XETHZUSD"\),
            ("All asset pairs", "https://api.kraken.com/0/public/AssetPairs"\),
            ("Simple ticker", "https://api.kraken.com/0/public/Ticker"\)
        ]
        
        async with aiohttp.ClientSession() as session:
            for name, url in test_urls:
                print(f"\n📡 Testing: {name}")
                print(f"URL: {url}")
                
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            print(f"✅ Response received")
                            print(f"📊 Response keys: {list(data.keys())}")
                            
                            if 'result' in data:
                                result = data['result']
                                if isinstance(result, dict):
                                    print(f"📊 Result keys: {list(result.keys())}")
                                    
                                    # Look for ETH-related keys
                                    eth_keys = [k for k in result.keys() if 'ETH' in k.upper()]
                                    if eth_keys:
                                        print(f"🎯 ETH-related keys found: {eth_keys}")
                                        
                                        # Show first ETH entry
                                        first_eth_key = eth_keys[0]
                                        eth_data = result[first_eth_key]
                                        print(f"📊 Sample ETH data ({first_eth_key}):")
                                        print(json.dumps(eth_data, indent=2)[:500] + "...")
                                else:
                                    print(f"📊 Result type: {type(result)}")
                            
                            if 'error' in data and data['error']:
                                print(f"❌ API errors: {data['error']}")
                                
                        else:
                            print(f"❌ HTTP error: {response.status}")
                            
                except Exception as e:
                    print(f"❌ Request failed: {e}")
                
                print("-" * 30)
        
        print("\n💡 If we found ETH data above, we can use the correct key!")
        
    except ImportError:
        print("❌ aiohttp not installed. Install with: pip install aiohttp")
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_kraken_api())
