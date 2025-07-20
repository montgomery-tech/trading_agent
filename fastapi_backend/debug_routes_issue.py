#!/usr/bin/env python3
"""
debug_routes_issue.py
Debug why the trades routes are returning 404
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_main_py_import():
    """Check if main.py properly imports trades"""
    
    print("🔍 Checking main.py imports...")
    
    with open("main.py", "r") as f:
        content = f.read()
    
    # Check imports
    if "from api.routes import" in content:
        import_lines = [line for line in content.split('\n') if "from api.routes import" in line]
        for line in import_lines:
            print(f"Import line: {line.strip()}")
            if "trades" in line:
                print("✅ trades is imported")
            else:
                print("❌ trades is NOT imported")
    
    # Check router includes
    if "trades.router" in content:
        router_lines = [line for line in content.split('\n') if "trades.router" in line]
        for line in router_lines:
            print(f"Router line: {line.strip()}")
        print("✅ trades.router is included")
    else:
        print("❌ trades.router is NOT included")

def check_trades_py():
    """Check if trades.py is properly structured"""
    
    print("\n🔍 Checking api/routes/trades.py...")
    
    trades_path = "api/routes/trades.py"
    
    if not Path(trades_path).exists():
        print(f"❌ {trades_path} does not exist!")
        return False
    
    with open(trades_path, "r") as f:
        content = f.read()
    
    # Check key components
    checks = {
        "router = APIRouter()": "router = APIRouter()" in content,
        "@router.get('/status')": "@router.get(\"/status\")" in content or "@router.get('/status')" in content,
        "@router.post('/simulate')": "@router.post(\"/simulate\")" in content or "@router.post('/simulate')" in content,
        "@router.get('/pricing/{symbol}')": "pricing/{symbol}" in content,
    }
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    return all(checks.values())

def test_direct_import():
    """Test importing the trades router directly"""
    
    print("\n🔍 Testing direct import of trades router...")
    
    try:
        from api.routes.trades import router as trades_router
        print("✅ Can import trades router directly")
        
        # Check routes on the router
        routes = []
        if hasattr(trades_router, 'routes'):
            for route in trades_router.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    methods = [m for m in route.methods if m not in ['HEAD', 'OPTIONS']]
                    for method in methods:
                        routes.append(f"{method} {route.path}")
        
        print(f"Routes found in trades router:")
        for route in routes:
            print(f"  {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cannot import trades router: {e}")
        return False

def test_app_routes():
    """Test importing the main app and checking its routes"""
    
    print("\n🔍 Testing main app routes...")
    
    try:
        from main import app
        print("✅ Can import main app")
        
        # Get all routes from the app
        all_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = [m for m in route.methods if m not in ['HEAD', 'OPTIONS']]
                for method in methods:
                    all_routes.append(f"{method} {route.path}")
        
        print(f"\nAll routes in main app:")
        trades_routes = []
        for route in sorted(all_routes):
            print(f"  {route}")
            if "/trades/" in route:
                trades_routes.append(route)
        
        if trades_routes:
            print(f"\n✅ Found {len(trades_routes)} trades routes:")
            for route in trades_routes:
                print(f"  {route}")
        else:
            print("\n❌ No trades routes found in main app!")
        
        return len(trades_routes) > 0
        
    except Exception as e:
        print(f"❌ Cannot import main app: {e}")
        print(f"Error details: {type(e).__name__}: {str(e)}")
        return False

def suggest_fixes():
    """Suggest fixes based on what we found"""
    
    print("\n💡 SUGGESTED FIXES:")
    print("=" * 50)
    
    print("\n1️⃣ If trades is not imported in main.py:")
    print("   Add: from api.routes import ..., trades")
    
    print("\n2️⃣ If trades.router is not included:")
    print("   Add this after other router includes:")
    print("""   app.include_router(
       trades.router,
       prefix="/api/v1/trades",
       tags=["Trades"]
   )""")
    
    print("\n3️⃣ If trades.py has issues:")
    print("   Make sure it has:")
    print("   - router = APIRouter()")
    print("   - @router.get('/status')")
    print("   - @router.post('/simulate')")
    print("   - @router.get('/pricing/{symbol}')")
    
    print("\n4️⃣ If import errors:")
    print("   Check for missing dependencies or syntax errors")
    print("   Run: python3 -m py_compile api/routes/trades.py")

def main():
    print("🚀 DEBUGGING TRADES ROUTES 404 ISSUE")
    print("=" * 60)
    
    # Run all checks
    check_main_py_import()
    trades_ok = check_trades_py()
    import_ok = test_direct_import()
    app_ok = test_app_routes()
    
    print(f"\n📊 SUMMARY:")
    print(f"trades.py structure: {'✅' if trades_ok else '❌'}")
    print(f"Direct import works: {'✅' if import_ok else '❌'}")
    print(f"App includes trades: {'✅' if app_ok else '❌'}")
    
    if not (trades_ok and import_ok and app_ok):
        suggest_fixes()
    else:
        print("\n✅ Everything looks good - this might be a restart issue")
        print("Try restarting your FastAPI application")

if __name__ == "__main__":
    main()
