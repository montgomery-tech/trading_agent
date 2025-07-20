#!/usr/bin/env python3
"""
test_live_config.py
Test your live trading configuration before going live
"""

import os
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_kraken_credentials():
    """Test that Kraken credentials work"""
    
    print("🔑 Testing Kraken API Credentials...")
    
    api_key = os.getenv("KRAKEN_API_KEY")
    api_secret = os.getenv("KRAKEN_API_SECRET")
    
    if not api_key or api_key == "your_actual_api_key_here":
        print("❌ KRAKEN_API_KEY not set or still placeholder")
        return False
    
    if not api_secret or api_secret == "your_actual_api_secret_here":
        print("❌ KRAKEN_API_SECRET not set or still placeholder")
        return False
    
    print("✅ API credentials are configured")
    
    try:
        from api.services.kraken_api_client import get_kraken_client
        
        client = await get_kraken_client()
        
        # Test connection
        is_valid = await client.validate_connection()
        
        if is_valid:
            print("✅ Kraken API connection successful!")
            
            # Test getting account balance
            try:
                balance = await client.get_account_balance()
                print("✅ Account balance retrieved:")
                for currency, amount in balance.items():
                    if float(amount) > 0:
                        print(f"   {currency}: {amount}")
            except Exception as e:
                print(f"⚠️  Could not get balance: {e}")
            
            return True
        else:
            print("❌ Kraken API connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Kraken API test failed: {e}")
        return False

async def test_trading_settings():
    """Test trading configuration"""
    
    print("\n⚙️  Testing Trading Settings...")
    
    live_trading = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
    max_order = os.getenv("MAX_ORDER_SIZE_USD", "100.00")
    
    print(f"Live Trading Enabled: {live_trading}")
    print(f"Max Order Size: ${max_order}")
    
    if live_trading:
        print("⚠️  WARNING: Live trading is ENABLED!")
        print("   Real trades will be executed on Kraken")
    else:
        print("✅ Live trading is disabled (sandbox mode)")
    
    return True

async def test_price_feed():
    """Test that price feeds work"""
    
    print("\n📈 Testing Price Feed...")
    
    try:
        from api.services.kraken_api_client import get_kraken_client
        
        client = await get_kraken_client()
        price = await client.get_current_price("BTC-USD")
        
        print(f"✅ BTC-USD current price: ${price}")
        return True
        
    except Exception as e:
        print(f"❌ Price feed test failed: {e}")
        return False

async def main():
    """Run all configuration tests"""
    
    print("🧪 TESTING LIVE TRADING CONFIGURATION")
    print("=" * 60)
    
    # Test credentials
    creds_ok = await test_kraken_credentials()
    
    # Test settings
    settings_ok = await test_trading_settings()
    
    # Test price feed
    price_ok = await test_price_feed()
    
    print("\n📊 TEST RESULTS:")
    print("=" * 30)
    print(f"Kraken Credentials: {'✅ PASS' if creds_ok else '❌ FAIL'}")
    print(f"Trading Settings: {'✅ PASS' if settings_ok else '❌ FAIL'}")  
    print(f"Price Feed: {'✅ PASS' if price_ok else '❌ FAIL'}")
    
    if creds_ok and settings_ok and price_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("You're ready to enable live trading!")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Fix the issues above before going live.")

if __name__ == "__main__":
    asyncio.run(main())
