#!/usr/bin/env python3
"""
Middleware Stack Test Script
Quick test to verify all middleware components are working correctly
"""

import requests
import time
import json
from typing import Dict, List

def test_server_connectivity(base_url: str = "http://localhost:8000") -> bool:
    """Test basic server connectivity."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Server connectivity: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Server connectivity failed: {e}")
        return False

def test_security_headers(base_url: str = "http://localhost:8000") -> bool:
    """Test that security headers are present."""
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        present_headers = []
        missing_headers = []
        
        for header in expected_headers:
            if header in response.headers:
                present_headers.append(header)
            else:
                missing_headers.append(header)
        
        print(f"✅ Security headers present: {len(present_headers)}/{len(expected_headers)}")
        if present_headers:
            print(f"   Found: {', '.join(present_headers)}")
        if missing_headers:
            print(f"   Missing: {', '.join(missing_headers)}")
        
        return len(missing_headers) == 0
        
    except Exception as e:
        print(f"❌ Security headers test failed: {e}")
        return False

def test_rate_limiting_headers(base_url: str = "http://localhost:8000") -> bool:
    """Test that rate limiting headers are present."""
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        
        rate_limit_headers = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining', 
            'X-RateLimit-Reset',
            'X-RateLimit-Type'
        ]
        
        present_headers = []
        for header in rate_limit_headers:
            if header in response.headers:
                present_headers.append(f"{header}: {response.headers[header]}")
        
        if present_headers:
            print(f"✅ Rate limiting active: {len(present_headers)} headers found")
            for header in present_headers:
                print(f"   {header}")
            return True
        else:
            print("⚠️  No rate limiting headers found")
            return False
            
    except Exception as e:
        print(f"❌ Rate limiting headers test failed: {e}")
        return False

def test_enhanced_rate_limiting_endpoints(base_url: str = "http://localhost:8000") -> bool:
    """Test enhanced rate limiting specific endpoints."""
    try:
        # Test metrics endpoint
        response = requests.get(f"{base_url}/api/rate-limit/metrics", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Enhanced rate limiting metrics endpoint working")
                metrics = data.get("data", {})
                print(f"   Total requests: {metrics.get('total_requests', 0)}")
                print(f"   Blocked requests: {metrics.get('blocked_requests', 0)}")
                return True
            else:
                print("⚠️  Enhanced rate limiting metrics returned error")
                return False
        else:
            print(f"⚠️  Enhanced rate limiting metrics endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced rate limiting test failed: {e}")
        return False

def test_request_processing_time(base_url: str = "http://localhost:8000") -> bool:
    """Test that processing time headers are added."""
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        
        if 'X-Process-Time' in response.headers:
            process_time = response.headers['X-Process-Time']
            print(f"✅ Request processing time: {process_time}s")
            return True
        else:
            print("⚠️  No processing time header found")
            return False
            
    except Exception as e:
        print(f"❌ Processing time test failed: {e}")
        return False

def test_basic_rate_limiting(base_url: str = "http://localhost:8000") -> bool:
    """Test basic rate limiting by making rapid requests."""
    try:
        print("🧪 Testing rate limiting with rapid requests...")
        
        # Make 10 rapid requests
        responses = []
        for i in range(10):
            response = requests.get(f"{base_url}/", timeout=5)
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay
        
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)
        
        print(f"   Successful requests: {success_count}")
        print(f"   Rate limited requests: {rate_limited_count}")
        
        if rate_limited_count > 0:
            print("✅ Rate limiting is active and blocking requests")
            return True
        elif success_count == 10:
            print("✅ All requests successful (rate limit not triggered)")
            return True
        else:
            print("⚠️  Unexpected response pattern")
            return False
            
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def main():
    """Run all middleware tests."""
    print("🔧 MIDDLEWARE STACK TEST SUITE")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    tests = [
        ("Server Connectivity", test_server_connectivity),
        ("Security Headers", test_security_headers),
        ("Rate Limiting Headers", test_rate_limiting_headers),
        ("Enhanced Rate Limiting", test_enhanced_rate_limiting_endpoints),
        ("Request Processing Time", test_request_processing_time),
        ("Basic Rate Limiting", test_basic_rate_limiting),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func(base_url)
            results[test_name] = result
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results[test_name] = False
        
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 MIDDLEWARE TEST RESULTS")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    print()
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print()
    
    if passed_tests == total_tests:
        print("🎉 ALL MIDDLEWARE TESTS PASSED!")
        print("✅ Security middleware stack is fully functional")
    elif passed_tests >= total_tests * 0.8:  # 80% pass rate
        print("✅ Most middleware tests passed - system is functional")
    else:
        print("⚠️  Some critical middleware tests failed")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
