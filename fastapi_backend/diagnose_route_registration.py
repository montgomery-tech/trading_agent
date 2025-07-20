#!/usr/bin/env python3
"""
diagnose_route_registration.py
Diagnose why some routes work and others don't
"""

import sys
from pathlib import Path
import requests

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_openapi_endpoints():
    """Check different OpenAPI endpoint variations"""
    
    base_url = "http://localhost:8000"
    openapi_urls = [
        f"{base_url}/openapi.json",
        f"{base_url}/api/v1/openapi.json", 
        f"{base_url}/docs/openapi.json",
        f"{base_url}/redoc",
        f"{base_url}/docs"
    ]
    
    print("🔍 Checking OpenAPI endpoints...")
    
    for url in openapi_urls:
        try:
            response = requests.get(url, timeout=3)
            print(f"  {url}: Status {response.status_code}")
            
            if response.status_code == 200 and "openapi.json" in url:
                try:
                    schema = response.json()
                    paths = schema.get("paths", {})
                    trades_paths = [p for p in paths.keys() if "/trades/" in p]
                    print(f"    ✅ Found {len(trades_paths)} trades paths in schema")
                    for path in sorted(trades_paths):
                        methods = list(paths[path].keys())
                        print(f"      {path}: {methods}")
                    return schema
                except:
                    print(f"    ❌ Not valid JSON")
            
        except Exception as e:
            print(f"  {url}: ❌ Failed - {e}")
    
    return None

def check_route_patterns():
    """Test different route patterns to see what works"""
    
    base_url = "http://localhost:8000"
    
    # Routes we know work
    working_routes = [
        "/api/v1/trades/kraken/status",
        "/api/v1/trades/simulate"
    ]
    
    # Routes that don't work
    broken_routes = [
        "/api/v1/trades/pricing/BTC/USD",
        "/api/v1/trades/user/demo_user"
    ]
    
    # Alternative patterns to test
    alternative_routes = [
        "/api/v1/trades/pricing/BTC-USD",
        "/api/v1/trades/pricing/BTCUSD", 
        "/trades/pricing/BTC/USD",
        "/trades/pricing/BTC-USD",
        "/api/v1/trade/pricing/BTC/USD",  # singular
        "/api/v1/trades/price/BTC/USD",   # different word
    ]
    
    print("\n🧪 Testing route patterns...")
    
    print("\n✅ Working routes:")
    for route in working_routes:
        url = f"{base_url}{route}"
        try:
            response = requests.get(url, timeout=3)
            print(f"  {route}: {response.status_code}")
        except Exception as e:
            print(f"  {route}: Error - {e}")
    
    print("\n❌ Broken routes:")
    for route in broken_routes:
        url = f"{base_url}{route}"
        try:
            response = requests.get(url, timeout=3)
            print(f"  {route}: {response.status_code}")
        except Exception as e:
            print(f"  {route}: Error - {e}")
    
    print("\n🔍 Testing alternatives:")
    for route in alternative_routes:
        url = f"{base_url}{route}"
        try:
            response = requests.get(url, timeout=3)
            if response.status_code != 404:
                print(f"  {route}: {response.status_code} ⭐")
            else:
                print(f"  {route}: 404")
        except Exception as e:
            print(f"  {route}: Error - {e}")

def check_trades_router_directly():
    """Import and check the trades router directly"""
    
    print("\n🔍 Checking trades router directly...")
    
    try:
        from api.routes.trades import router as trades_router
        
        print(f"✅ Trades router imported successfully")
        print(f"Router type: {type(trades_router)}")
        
        if hasattr(trades_router, 'routes'):
            print(f"Number of routes: {len(trades_router.routes)}")
            
            for i, route in enumerate(trades_router.routes):
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    methods = [m for m in route.methods if m not in ['HEAD', 'OPTIONS']]
                    print(f"  Route {i}: {methods} {route.path}")
                    
                    # Check if this is the pricing route
                    if "pricing" in route.path:
                        print(f"    🎯 Found pricing route: {route.path}")
                        print(f"    Route details: {route}")
                        
                        # Check path parameters
                        if hasattr(route, 'path_regex'):
                            print(f"    Path regex: {route.path_regex.pattern}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import trades router: {e}")
        return False

def check_main_app_registration():
    """Check how the trades router is registered in main app"""
    
    print("\n🔍 Checking main app registration...")
    
    try:
        from main import app
        
        print("✅ Main app imported successfully")
        
        # Look at the app's router
        if hasattr(app, 'router'):
            print(f"App router type: {type(app.router)}")
            
            # Check if trades routes are in the main router
            all_routes = []
            for route in app.router.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    methods = [m for m in route.methods if m not in ['HEAD', 'OPTIONS']]
                    for method in methods:
                        route_str = f"{method} {route.path}"
                        all_routes.append(route_str)
                        
                        if "/trades/" in route.path and "pricing" in route.path:
                            print(f"🎯 Found pricing route in main app: {route_str}")
                            print(f"   Route object: {route}")
            
            # Count trades routes
            trades_routes = [r for r in all_routes if "/trades/" in r]
            print(f"\nTotal routes in app: {len(all_routes)}")
            print(f"Trades routes in app: {len(trades_routes)}")
            
            if trades_routes:
                print("Trades routes found:")
                for route in sorted(trades_routes):
                    print(f"  {route}")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to check main app: {e}")
        return False

def main():
    print("🚀 DIAGNOSING ROUTE REGISTRATION ISSUES")
    print("=" * 60)
    
    # Check OpenAPI schema
    schema = check_openapi_endpoints()
    
    # Test route patterns
    check_route_patterns()
    
    # Check router directly
    router_ok = check_trades_router_directly()
    
    # Check main app
    app_ok = check_main_app_registration()
    
    print(f"\n📊 DIAGNOSTIC SUMMARY:")
    print(f"OpenAPI schema accessible: {'✅' if schema else '❌'}")
    print(f"Trades router imports: {'✅' if router_ok else '❌'}")
    print(f"Main app registration: {'✅' if app_ok else '❌'}")
    
    print(f"\n🎯 FINDINGS:")
    print("- Trade simulation works perfectly (real Kraken prices!)")
    print("- Kraken status endpoint works")
    print("- Some routes work, others return 404")
    print("- This suggests a path parameter or routing configuration issue")
    
    print(f"\n💡 LIKELY CAUSES:")
    print("1. Path parameter format issue (BTC/USD vs BTC-USD)")
    print("2. Route registration order")
    print("3. FastAPI app reload didn't pick up all routes")
    print("4. Path parameter validation failing")

if __name__ == "__main__":
    main()
