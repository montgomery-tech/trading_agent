#!/usr/bin/env python3
"""Test with more details about errors"""

import requests
import json

base_url = "http://localhost:8000"

# Test BTCUSD which gave 500 error
url = f"{base_url}/api/v1/trading-pairs/spreads/BTCUSD"

print(f"Testing: {url}")
print("-" * 50)

response = requests.get(url)
print(f"Status: {response.status_code}")

if response.status_code == 500:
    print("\nError details:")
    try:
        error_data = response.json()
        print(json.dumps(error_data, indent=2))
    except:
        print(response.text[:500])
elif response.status_code == 200:
    data = response.json()
    print("✅ Success!")
    print(json.dumps(data, indent=2))

# Also test with slash
print("\n" + "="*50)
url2 = f"{base_url}/api/v1/trading-pairs/spreads/BTC/USD"
print(f"Testing: {url2}")
response2 = requests.get(url2)
print(f"Status: {response2.status_code}")
