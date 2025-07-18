#!/usr/bin/env python3
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
