#!/usr/bin/env python3
"""
Check what endpoints are actually working in your FastAPI app
"""

import requests

print("🔍 Checking FastAPI Endpoints")
print("=" * 50)

# Common endpoint patterns to test
test_urls = [
    "http://localhost:8000/",
    "http://localhost:8000/health",
    "http://localhost:8000/docs",
    "http://localhost:8000/redoc",
    "http://localhost:8000/openapi.json",
    "http://localhost:8000/api/docs",
    "http://localhost:8000/api/openapi.json",
    "http://localhost:8000/api/v1/",
    "http://localhost:8000/api/v1/health",
    "http://localhost:8000/api/v1/users",
    "http://localhost:8000/api/v1/trades",
    "http://localhost:8000/api/v1/trading-pairs",
    "http://localhost:8000/api/v1/balances",
    "http://localhost:8000/api/v1/currencies",
]

working_endpoints = []

for url in test_urls:
    try:
        response = requests.get(url, timeout=2)
        if response.status_code != 404:
            working_endpoints.append((url, response.status_code))
            print(f"✅ {url} -> {response.status_code}")
    except Exception as e:
        print(f"❌ {url} -> Error: {str(e)[:50]}")

print("\n📊 Summary:")
print(f"Found {len(working_endpoints)} working endpoints")

if working_endpoints:
    print("\n🔗 Working endpoints:")
    for url, status in working_endpoints:
        print(f"  {url} (Status: {status})")
else:
    print("\n❌ No working endpoints found!")
    print("Is the FastAPI app running on http://localhost:8000?")

# Try to find the docs
for url, status in working_endpoints:
    if "docs" in url or "openapi" in url:
        print(f"\n📚 API Documentation available at: {url}")
        break
