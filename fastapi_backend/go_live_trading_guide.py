#!/usr/bin/env python3
"""
go_live_trading_guide.py
Complete guide and script to enable live trading with Kraken
"""

import os
from pathlib import Path

def print_live_trading_checklist():
    """Print the complete checklist for going live"""
    
    print("🚀 GOING LIVE WITH KRAKEN TRADING")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This involves REAL MONEY and REAL TRADES!")
    print("   Please read everything carefully before proceeding.")
    print()
    
    print("📋 PRE-FLIGHT CHECKLIST:")
    print("-" * 30)
    print("✅ 1. Get Kraken Account & API Credentials")
    print("✅ 2. Configure Environment Variables")
    print("✅ 3. Test with Small Amounts First")
    print("✅ 4. Set Up Proper Risk Controls")
    print("✅ 5. Enable Live Trading Mode")
    print("✅ 6. Monitor and Scale Gradually")
    print()

def step1_kraken_account_setup():
    """Guide for setting up Kraken account and API"""
    
    print("1️⃣ KRAKEN ACCOUNT & API SETUP")
    print("=" * 40)
    print()
    print("📝 Steps to get Kraken API credentials:")
    print()
    print("1. Create a Kraken account:")
    print("   - Go to https://kraken.com")
    print("   - Complete account verification (required for API)")
    print("   - Fund your account with USD/crypto")
    print()
    print("2. Generate API keys:")
    print("   - Log into Kraken")
    print("   - Go to Settings > API")
    print("   - Click 'Generate New Key'")
    print("   - Set permissions:")
    print("     ✅ Query Funds")
    print("     ✅ Query Open Orders") 
    print("     ✅ Query Closed Orders")
    print("     ✅ Query Trades History")
    print("     ✅ Create & Modify Orders")
    print("     ✅ Cancel Orders")
    print("     ❌ Withdraw Funds (NOT recommended)")
    print("   - Save your API Key and Private Key securely!")
    print()
    print("💡 SECURITY TIP: Never share your API keys!")
    print()

def step2_configure_environment():
    """Create the environment configuration"""
    
    print("2️⃣ ENVIRONMENT CONFIGURATION")
    print("=" * 40)
    print()
    
    # Check current .env file
    env_file = ".env"
    env_example = ".env.example"
    
    if os.path.exists(env_file):
        print(f"✅ Found existing {env_file}")
        with open(env_file, "r") as f:
            content = f.read()
        
        # Check what's already configured
        has_kraken_key = "KRAKEN_API_KEY=" in content
        has_kraken_secret = "KRAKEN_API_SECRET=" in content
        has_live_trading = "ENABLE_LIVE_TRADING=" in content
        
        print("Current configuration:")
        print(f"  - Kraken API Key: {'✅ Set' if has_kraken_key else '❌ Missing'}")
        print(f"  - Kraken Secret: {'✅ Set' if has_kraken_secret else '❌ Missing'}")  
        print(f"  - Live Trading: {'✅ Set' if has_live_trading else '❌ Missing'}")
        print()
    else:
        print(f"❌ No {env_file} found")
        if os.path.exists(env_example):
            print(f"✅ Found {env_example} - copying to {env_file}")
            with open(env_example, "r") as f:
                content = f.read()
            with open(env_file, "w") as f:
                f.write(content)
        else:
            print("❌ No .env.example found either")
            return False
    
    # Create the live trading configuration
    live_config = """
# =============================================================================
# LIVE TRADING CONFIGURATION
# =============================================================================
# ⚠️  WARNING: These settings enable REAL trading with REAL money!

# Kraken API Credentials (KEEP THESE SECRET!)
KRAKEN_API_KEY=your_actual_api_key_here
KRAKEN_API_SECRET=your_actual_api_secret_here

# Live Trading Control
ENABLE_LIVE_TRADING=false  # Change to 'true' when ready to go live

# Risk Management
MAX_ORDER_SIZE_USD=100.00  # Start small! Maximum order size
DEFAULT_TRADING_FEE_PERCENTAGE=0.26  # Kraken's standard fee

# Trading Configuration
MARKET_ORDER_SLIPPAGE_TOLERANCE=0.01  # 1% slippage tolerance
PRICE_STALENESS_THRESHOLD_SECONDS=30  # Price freshness

# Logging (Important for live trading!)
LOG_KRAKEN_REQUESTS=true
LOG_KRAKEN_RESPONSES=true
LOG_LEVEL=INFO

# Development vs Production
KRAKEN_SANDBOX_MODE=false  # No real sandbox, this is just for internal logic
"""
    
    print("📝 Add this to your .env file:")
    print("=" * 50)
    print(live_config)
    print("=" * 50)
    print()
    print("🔑 IMPORTANT: Replace 'your_actual_api_key_here' with your real credentials!")
    print()

def step3_test_configuration():
    """Create a test script for the live configuration"""
    
    print("3️⃣ TESTING CONFIGURATION")
    print("=" * 40)
    print()
    
    test_script = '''#!/usr/bin/env python3
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
    
    print("\\n⚙️  Testing Trading Settings...")
    
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
    
    print("\\n📈 Testing Price Feed...")
    
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
    
    print("\\n📊 TEST RESULTS:")
    print("=" * 30)
    print(f"Kraken Credentials: {'✅ PASS' if creds_ok else '❌ FAIL'}")
    print(f"Trading Settings: {'✅ PASS' if settings_ok else '❌ FAIL'}")  
    print(f"Price Feed: {'✅ PASS' if price_ok else '❌ FAIL'}")
    
    if creds_ok and settings_ok and price_ok:
        print("\\n🎉 ALL TESTS PASSED!")
        print("You're ready to enable live trading!")
    else:
        print("\\n❌ SOME TESTS FAILED")
        print("Fix the issues above before going live.")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open("test_live_config.py", "w") as f:
        f.write(test_script)
    
    print("✅ Created test_live_config.py")
    print()
    print("📋 To test your configuration:")
    print("   python3 test_live_config.py")
    print()

def step4_risk_management():
    """Explain risk management for live trading"""
    
    print("4️⃣ RISK MANAGEMENT")
    print("=" * 40)
    print()
    print("🛡️  CRITICAL SAFETY MEASURES:")
    print()
    print("1. Start with TINY amounts:")
    print("   - Set MAX_ORDER_SIZE_USD=10.00 initially")
    print("   - Test with $10 trades first")
    print("   - Gradually increase limits")
    print()
    print("2. Monitor everything:")
    print("   - Watch logs carefully")
    print("   - Check Kraken account regularly")
    print("   - Verify all trades match expectations")
    print()
    print("3. Set strict limits:")
    print("   - Daily trading limits")
    print("   - Maximum position sizes")
    print("   - Stop-loss mechanisms")
    print()
    print("4. Have emergency procedures:")
    print("   - Know how to stop the system quickly")
    print("   - Have manual Kraken access ready")
    print("   - Keep some funds liquid")
    print()

def step5_go_live_procedure():
    """The actual procedure to go live"""
    
    print("5️⃣ GO LIVE PROCEDURE")
    print("=" * 40)
    print()
    print("🚨 FINAL CHECKLIST BEFORE GOING LIVE:")
    print()
    print("□ Kraken account verified and funded")
    print("□ API credentials tested and working")
    print("□ Small order limits set (MAX_ORDER_SIZE_USD=10.00)")
    print("□ All tests passing")
    print("□ Monitoring systems ready")
    print("□ Emergency procedures understood")
    print()
    print("🚦 TO ENABLE LIVE TRADING:")
    print()
    print("1. Edit your .env file:")
    print("   ENABLE_LIVE_TRADING=true")
    print()
    print("2. Restart your FastAPI application:")
    print("   python3 main.py")
    print()
    print("3. Test with a tiny order:")
    print('   curl -X POST "http://localhost:8000/api/v1/trades/execute-simple" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"username":"demo_user","symbol":"BTC-USD","side":"buy","amount":"0.00001"}\'')
    print()
    print("4. Verify the trade on Kraken:")
    print("   - Log into Kraken")
    print("   - Check your orders and trades")
    print("   - Confirm everything matches")
    print()
    print("⚠️  START WITH AMOUNTS YOU CAN AFFORD TO LOSE!")
    print()

def create_live_trading_script():
    """Create a script to toggle live trading on/off"""
    
    toggle_script = '''#!/usr/bin/env python3
"""
toggle_live_trading.py
Safely toggle live trading on/off
"""

import os

def toggle_live_trading():
    """Toggle live trading setting"""
    
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ .env file not found")
        return
    
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    found = False
    for i, line in enumerate(lines):
        if line.startswith("ENABLE_LIVE_TRADING="):
            current_value = line.strip().split("=")[1].lower()
            
            if current_value == "true":
                lines[i] = "ENABLE_LIVE_TRADING=false\\n"
                print("🔴 Live trading DISABLED")
                print("   System is now in sandbox mode")
            else:
                print("⚠️  ENABLING LIVE TRADING!")
                confirm = input("Are you sure? This will execute REAL trades! (yes/no): ")
                if confirm.lower() == "yes":
                    lines[i] = "ENABLE_LIVE_TRADING=true\\n"
                    print("🟢 Live trading ENABLED")
                    print("   ⚠️  REAL trades will now be executed!")
                else:
                    print("❌ Live trading remains disabled")
                    return
            
            found = True
            break
    
    if not found:
        print("❌ ENABLE_LIVE_TRADING setting not found in .env")
        return
    
    with open(env_file, "w") as f:
        f.writelines(lines)
    
    print("\\n📋 Remember to restart your FastAPI application:")
    print("   python3 main.py")

if __name__ == "__main__":
    toggle_live_trading()
'''
    
    with open("toggle_live_trading.py", "w") as f:
        f.write(toggle_script)
    
    os.chmod("toggle_live_trading.py", 0o755)
    print("✅ Created toggle_live_trading.py")

def main():
    """Main guide function"""
    
    print_live_trading_checklist()
    print()
    
    step1_kraken_account_setup()
    print()
    
    step2_configure_environment()
    print()
    
    step3_test_configuration()
    print()
    
    step4_risk_management()
    print()
    
    step5_go_live_procedure()
    print()
    
    create_live_trading_script()
    print()
    
    print("🎯 SUMMARY")
    print("=" * 20)
    print("Your trading system is ready for live deployment!")
    print()
    print("📋 Files created:")
    print("  - test_live_config.py (test your setup)")
    print("  - toggle_live_trading.py (enable/disable live trading)")
    print()
    print("🚨 REMEMBER:")
    print("  - Start with tiny amounts ($10 orders)")
    print("  - Monitor everything closely")
    print("  - You can always disable live trading quickly")
    print()
    print("🚀 Good luck with your trading platform!")

if __name__ == "__main__":
    main()
