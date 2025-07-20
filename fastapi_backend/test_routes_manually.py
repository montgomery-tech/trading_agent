#!/usr/bin/env python3
"""
test_routes_manually.py
Test the routes manually to see what's actually registered
"""

import sys
from pathlib import Path
import requests
import json

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_endpoint(url, method="GET", data=None):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=5)
        
        print(f"  {method} {url}")
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"    ✅ Success: {result}")
            except:
                print(f"    ✅ Success: {response.text[:100]}")
        elif response.status_code == 404:
            print(f"    ❌ Not Found")
        elif response.status_code == 500:
            try:
                error = response.json()
                print(f"    ❌ Server Error: {error.get('detail', 'Unknown error')}")
            except:
                print(f"    ❌ Server Error: {response.text[:100]}")
        else:
            print(f"    ⚠️  Status {response.status_code}: {response.text[:100]}")
        
        print()
        return response.status_code
        
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Connection failed - is FastAPI running on http://localhost:8000?")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def test_all_trades_endpoints():
    """Test all the trades endpoints we expect to exist"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 TESTING TRADES ENDPOINTS")
    print("=" * 50)
    
    # Test basic FastAPI endpoints first
    print("📋 Basic endpoints:")
    test_endpoint(f"{base_url}/")
    test_endpoint(f"{base_url}/health")
    test_endpoint(f"{base_url}/docs")
    
    # Test trades endpoints
    print("📋 Trades endpoints:")
    
    # The endpoints we found in the debug
    endpoints_to_test = [
        ("GET", "/api/v1/trades/kraken/status"),
        ("GET", "/api/v1/trades/pricing/BTC/USD"),
        ("GET", "/api/v1/trades/user/demo_user"),
        ("POST", "/api/v1/trades/execute"),
        ("POST", "/api/v1/trades/simulate"),
    ]
    
    for method, path in endpoints_to_test:
        url = f"{base_url}{path}"
        
        if method == "POST":
            # Test data for POST endpoints
            if "simulate" in path:
                test_data = {
                    "username": "demo_user",
                    "symbol": "BTC/USD",
                    "side": "buy",
                    "amount": "0.001",
                    "order_type": "market"
                }
            elif "execute" in path:
                test_data = {
                    "username": "demo_user", 
                    "symbol": "BTC/USD",
                    "side": "buy",
                    "amount": "0.001",
                    "order_type": "market"
                }
            else:
                test_data = {}
            
            status = test_endpoint(url, method, test_data)
        else:
            status = test_endpoint(url, method)

def check_app_running():
    """Check if the FastAPI app is running"""
    try:
        response = requests.get("http://localhost:8000/", timeout=2)
        if response.status_code == 200:
            print("✅ FastAPI app is running")
            return True
    except:
        pass
    
    print("❌ FastAPI app is NOT running")
    print("   Start it with: python3 main.py")
    return False

def get_openapi_schema():
    """Get the OpenAPI schema to see all registered routes"""
    try:
        response = requests.get("http://localhost:8000/openapi.json", timeout=5)
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})
            
            print("📋 All registered routes from OpenAPI:")
            trades_paths = {}
            other_paths = {}
            
            for path, methods in paths.items():
                if "/trades/" in path:
                    trades_paths[path] = list(methods.keys())
                else:
                    other_paths[path] = list(methods.keys())
            
            print("\n🔧 Trades routes:")
            for path, methods in sorted(trades_paths.items()):
                for method in methods:
                    if method.upper() not in ['HEAD', 'OPTIONS']:
                        print(f"  {method.upper():<6} {path}")
            
            print(f"\n📊 Total routes: {len(paths)}")
            print(f"📊 Trades routes: {len(trades_paths)}")
            
            return trades_paths
        else:
            print(f"❌ Failed to get OpenAPI schema: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting OpenAPI schema: {e}")
        return None

def main():
    print("🚀 MANUAL ROUTE TESTING")
    print("=" * 60)
    
    # Check if app is running
    if not check_app_running():
        return
    
    print()
    
    # Get actual registered routes
    trades_routes = get_openapi_schema()
    
    print()
    
    # Test the endpoints
    test_all_trades_endpoints()
    
    print("🎯 SUMMARY:")
    print("- If you see 404 errors, the routes aren't properly registered")
    print("- If you see 500 errors, the routes exist but have implementation issues")
    print("- If you see 200 responses, the integration is working!")

if __name__ == "__main__":
    main()
