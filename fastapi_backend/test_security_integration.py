#!/usr/bin/env python3
"""Test security framework integration."""

import requests
import json

def test_security_integration():
    """Test the integrated security framework."""
    base_url = "http://localhost:8000"
    
    print("🔐 Testing Security Framework Integration")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testing health check...")
    response = requests.get(f"{base_url}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test 2: Security headers
    print("\n2. Testing security headers...")
    response = requests.get(f"{base_url}/")
    headers = response.headers
    security_headers = [
        'X-XSS-Protection',
        'X-Content-Type-Options', 
        'X-Frame-Options',
        'Content-Security-Policy'
    ]
    
    for header in security_headers:
        if header in headers:
            print(f"   ✅ {header}: {headers[header]}")
        else:
            print(f"   ❌ {header}: Missing")
    
    # Test 3: Rate limiting headers
    print("\n3. Testing rate limiting...")
    response = requests.get(f"{base_url}/")
    rate_headers = [
        'X-RateLimit-Limit',
        'X-RateLimit-Remaining'
    ]
    
    for header in rate_headers:
        if header in headers:
            print(f"   ✅ {header}: {headers[header]}")
    
    # Test 4: Input validation
    print("\n4. Testing input validation...")
    malicious_data = {
        "username": "<script>alert('xss')</script>",
        "amount": "'; DROP TABLE users; --",
        "currency_code": "USD"
    }
    
    response = requests.post(
        f"{base_url}/transactions/deposit",
        json=malicious_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Malicious request status: {response.status_code}")
    if response.status_code == 422:
        print("   ✅ Input validation blocked malicious input")
    else:
        print("   ⚠️ Input validation may need review")
    
    print("\n✅ Security framework integration test complete!")

if __name__ == "__main__":
    test_security_integration()
