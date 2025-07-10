#!/usr/bin/env python3
"""Debug rate limiting setup"""

import requests
import time

def test_rate_limiting():
    base_url = "http://localhost:8000"
    
    print("🔍 Debugging Rate Limiting Setup")
    print("=" * 50)
    
    # Test 1: Check what headers we get
    print("1. Checking response headers...")
    response = requests.get(f"{base_url}/")
    print(f"Status: {response.status_code}")
    print("Headers:")
    for header, value in response.headers.items():
        if 'rate' in header.lower() or 'limit' in header.lower():
            print(f"  {header}: {value}")
    
    print(f"\nAll headers: {dict(response.headers)}")
    
    # Test 2: Rapid requests to trigger rate limiting
    print("\n2. Testing with rapid requests...")
    for i in range(8):
        response = requests.get(f"{base_url}/")
        print(f"Request {i+1}: Status {response.status_code}")
        if response.status_code == 429:
            print("✅ Rate limiting triggered!")
            print(f"Response: {response.json()}")
            break
        time.sleep(0.1)
    else:
        print("❌ Rate limiting not triggered after 8 requests")

if __name__ == "__main__":
    test_rate_limiting()
