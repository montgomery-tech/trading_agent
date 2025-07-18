#!/usr/bin/env python3
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
            print("\nTrading Pairs Routes:")
            for path, methods in sorted(trading_routes):
                print(f"  {path} [{', '.join(methods).upper()}]")
        else:
            print("No trading-pairs routes found!")
            
        # Show all routes if no trading routes
        if not trading_routes:
            print("\nAll Routes:")
            for path in sorted(paths.keys())[:20]:
                print(f"  {path}")
                
    else:
        print("Could not get OpenAPI schema")
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying alternate method...")
    
    # Just check if docs are available
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ API docs available at: http://localhost:8000/docs")
            print("   Check there for all available routes")
    except:
        pass
