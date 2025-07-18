#!/usr/bin/env python3
"""
Check if trade routes exist and are properly configured
"""

import os

def check_trade_routes():
    """Check if trades.py has the simulate endpoint"""
    
    trades_file = "api/routes/trades.py"
    
    print(f"🔍 Checking {trades_file}...")
    
    if not os.path.exists(trades_file):
        print(f"❌ {trades_file} not found!")
        return False
    
    with open(trades_file, "r") as f:
        content = f.read()
    
    # Check for key components
    checks = {
        "simulate endpoint": '/simulate"' in content or '/simulate\'' in content,
        "EnhancedTradeService": "EnhancedTradeService" in content,
        "simulate_trade method": "simulate_trade" in content,
        "TradeSimulationRequest": "TradeSimulationRequest" in content,
    }
    
    print("\n📋 Trade routes status:")
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check}")
    
    # Check if using the base or enhanced service
    if "return TradeService(db)" in content:
        print("\n⚠️  Still using base TradeService, not EnhancedTradeService!")
    elif "return EnhancedTradeService(db)" in content:
        print("\n✅ Using EnhancedTradeService")
    
    return all(checks.values())

def check_main_routes():
    """Check if trades router is included in main.py"""
    
    print("\n🔍 Checking main.py for trades router...")
    
    with open("main.py", "r") as f:
        content = f.read()
    
    if "trades" in content and "trades.router" in content:
        print("✅ trades router is included in main.py")
        
        # Find the exact line
        for line in content.split('\n'):
            if "trades.router" in line and "include_router" in line:
                print(f"   Found: {line.strip()}")
                return True
    else:
        print("❌ trades router NOT found in main.py")
        return False

def suggest_fix():
    """Suggest how to add the missing routes"""
    
    print("\n💡 If trade routes are missing:")
    print("-" * 50)
    print("1. Make sure trades.py is imported in main.py:")
    print("   from api.routes import ..., trades")
    print("\n2. Include the trades router:")
    print("   app.include_router(trades.router, prefix=\"/api/v1/trades\", tags=[\"trades\"])")
    print("\n3. Ensure EnhancedTradeService is being used")
    print("\n4. Check that trades.py has the simulate endpoint")

if __name__ == "__main__":
    print("🚀 Checking Trade Routes Configuration")
    print("=" * 50)
    
    trades_exist = check_trade_routes()
    main_includes = check_main_routes()
    
    if not trades_exist or not main_includes:
        suggest_fix()
    else:
        print("\n✅ Trade routes appear to be configured")
        print("\n📋 If still getting 404:")
        print("1. Check the exact URL in the API docs: http://localhost:8000/docs")
        print("2. Ensure the EnhancedTradeService is being used")
        print("3. Restart the FastAPI application")
