#!/usr/bin/env python3
"""
Fix the URL routing issue for individual spread endpoint
"""

import os

def fix_spread_routes():
    """Fix the route ordering in spread_management.py"""
    
    spread_file = "api/routes/spread_management.py"
    
    print(f"🔧 Fixing route ordering in {spread_file}...")
    
    # Read the file
    with open(spread_file, "r") as f:
        content = f.read()
    
    # The issue is likely that the routes are in the wrong order
    # FastAPI matches routes in order, so /spreads/{symbol} must come before /spreads
    # Let's check the current order
    
    lines = content.split('\n')
    
    # Find route decorators
    route_lines = []
    for i, line in enumerate(lines):
        if "@router.get" in line or "@router.put" in line or "@router.post" in line:
            route_lines.append((i, line.strip()))
    
    print("\n📋 Current route order:")
    for i, (line_num, route) in enumerate(route_lines):
        print(f"   {i+1}. Line {line_num}: {route}")
    
    # Check if URL encoding might be an issue
    if '"/spreads/{symbol}"' in content:
        print("\n✅ Route pattern looks correct")
    else:
        print("\n❌ Route pattern might be incorrect")
    
    return True

def create_test_specific_endpoint():
    """Create a simple test script to check specific endpoint"""
    
    test_code = '''#!/usr/bin/env python3
"""Test specific spread endpoint"""

import requests

base_url = "http://localhost:8000"

# Test different URL patterns
urls_to_test = [
    "/api/v1/trading-pairs/spreads/BTC/USD",
    "/api/v1/trading-pairs/spreads/BTCUSD",
    "/api/v1/trading-pairs/spreads/BTC%2FUSD",  # URL encoded
    "/api/v1/trading-pairs/BTC/USD/spreads",
    "/api/v1/trading-pairs/BTC/USD",
]

print("Testing different URL patterns...")
print("-" * 50)

for url in urls_to_test:
    try:
        response = requests.get(base_url + url)
        print(f"{url}")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "spread_percentage" in data["data"]:
                spread = data["data"]["spread_percentage"] * 100
                print(f"  ✅ Spread: {spread:.2f}%")
        elif response.status_code == 404:
            print(f"  ❌ Not Found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()
'''
    
    with open("test_spread_endpoint.py", "w") as f:
        f.write(test_code)
    
    print("✅ Created test_spread_endpoint.py")

def check_fastapi_routes():
    """Create script to list all registered routes"""
    
    check_code = '''#!/usr/bin/env python3
"""Check all registered FastAPI routes"""

import requests

try:
    # Get OpenAPI schema
    response = requests.get("http://localhost:8000/openapi.json")
    if response.status_code == 200:
        openapi = response.json()
        paths = openapi.get("paths", {})
        
        print("🔍 Registered API Routes:")
        print("-" * 50)
        
        # Filter for trading-pairs routes
        trading_routes = [(path, list(methods.keys())) for path, methods in paths.items() if "trading-pairs" in path]
        
        if trading_routes:
            print("\\nTrading Pairs Routes:")
            for path, methods in sorted(trading_routes):
                print(f"  {path} [{', '.join(methods).upper()}]")
        else:
            print("No trading-pairs routes found!")
            
        # Show all routes if no trading routes
        if not trading_routes:
            print("\\nAll Routes:")
            for path in sorted(paths.keys())[:20]:
                print(f"  {path}")
                
    else:
        print("Could not get OpenAPI schema")
except Exception as e:
    print(f"Error: {e}")
    print("\\nTrying alternate method...")
    
    # Just check if docs are available
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ API docs available at: http://localhost:8000/docs")
            print("   Check there for all available routes")
    except:
        pass
'''
    
    with open("check_routes.py", "w") as f:
        f.write(check_code)
    
    print("✅ Created check_routes.py")

if __name__ == "__main__":
    print("🚀 Debugging Spread Route Issue")
    print("=" * 50)
    
    # Check current routes
    fix_spread_routes()
    
    # Create test scripts
    create_test_specific_endpoint()
    check_fastapi_routes()
    
    print("\n📋 Next steps:")
    print("1. Run: python3 check_routes.py")
    print("   This will show all registered routes")
    print("\n2. Run: python3 test_spread_endpoint.py")
    print("   This will test different URL patterns")
    print("\n3. Check http://localhost:8000/docs")
    print("   Look for the exact URL pattern for spread endpoints")
    
    print("\n💡 The issue is likely:")
    print("- The {symbol} parameter might need URL encoding")
    print("- The route might be registered differently")
    print("- FastAPI might be interpreting / in BTC/USD as a path separator")
