#!/usr/bin/env python3
"""
Debug script to check what routes are registered in your FastAPI app
"""

import requests
import json

def check_routes():
    """Check all available routes in the FastAPI application"""
    print("🔍 Checking Available Routes")
    print("=" * 50)
    
    # Get OpenAPI schema which lists all routes
    response = requests.get("http://localhost:8000/openapi.json")
    
    if response.status_code == 200:
        openapi = response.json()
        paths = openapi.get("paths", {})
        
        print(f"\n📋 Found {len(paths)} routes:\n")
        
        # Group routes by prefix
        trading_routes = []
        spread_routes = []
        other_routes = []
        
        for path, methods in paths.items():
            if "/trading-pairs" in path:
                if "spread" in path:
                    spread_routes.append(path)
                else:
                    trading_routes.append(path)
            else:
                other_routes.append(path)
        
        if spread_routes:
            print("✅ Spread Management Routes:")
            for route in sorted(spread_routes):
                print(f"   {route}")
        else:
            print("❌ No spread routes found!")
        
        print(f"\n📊 Trading Pair Routes:")
        for route in sorted(trading_routes):
            print(f"   {route}")
        
        print(f"\n🔗 Other Routes (first 10):")
        for route in sorted(other_routes)[:10]:
            print(f"   {route}")
            
    else:
        print(f"❌ Failed to get routes: {response.status_code}")
        print("Make sure FastAPI is running on http://localhost:8000")


def check_specific_endpoints():
    """Test specific endpoints we expect to exist"""
    print("\n\n🧪 Testing Specific Endpoints")
    print("=" * 50)
    
    endpoints = [
        "/api/v1/trading-pairs/",
        "/api/v1/trading-pairs/spreads",
        "/api/v1/trading-pairs/spreads/BTC/USD",
        "/api/v1/trades/simulate",
    ]
    
    for endpoint in endpoints:
        url = f"http://localhost:8000{endpoint}"
        try:
            response = requests.get(url)
            print(f"\n{endpoint}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 404:
                print(f"   ❌ Not Found")
            elif response.status_code == 200:
                print(f"   ✅ Working")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def check_main_py():
    """Check if main.py has the spread routes included"""
    print("\n\n📄 Checking main.py Configuration")
    print("=" * 50)
    
    try:
        with open("main.py", "r") as f:
            content = f.read()
            
        # Check for spread management import
        if "spread_management" in content:
            print("✅ spread_management is imported")
        else:
            print("❌ spread_management is NOT imported")
            
        # Check for router inclusion
        if "spread_management.router" in content:
            print("✅ spread_management.router is included")
            
            # Find the exact line
            for line in content.split('\n'):
                if "spread_management.router" in line:
                    print(f"   Found: {line.strip()}")
        else:
            print("❌ spread_management.router is NOT included")
            
        # Check trading pairs router
        if "trading_pairs.router" in content:
            print("✅ trading_pairs.router is included")
            for line in content.split('\n'):
                if "trading_pairs.router" in line and "include_router" in line:
                    print(f"   Found: {line.strip()}")
                    
    except FileNotFoundError:
        print("❌ main.py not found!")


if __name__ == "__main__":
    print("🔧 FastAPI Routes Debug Tool")
    print("=" * 50)
    
    check_main_py()
    check_routes()
    check_specific_endpoints()
    
    print("\n\n💡 Troubleshooting Tips:")
    print("1. Make sure FastAPI is running: python3 main.py")
    print("2. Check that spread_management is properly imported in main.py")
    print("3. Verify the router prefix matches what the test expects")
    print("4. Look at http://localhost:8000/docs for all available endpoints")
