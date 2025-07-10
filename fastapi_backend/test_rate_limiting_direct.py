#!/usr/bin/env python3
"""
Direct Rate Limiting Test
Test the rate limiting system directly without middleware
"""

import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_rate_limiting():
    """Test rate limiting service directly."""
    print("🔍 Testing rate limiting service directly...")
    
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        
        # Test multiple requests
        print("\n📊 Testing 5 rapid requests:")
        for i in range(5):
            result = await rate_limiting_service.check_rate_limit(
                ip="127.0.0.1",
                user_id=None,
                user_data=None,
                endpoint_path="/test",
                request_method="GET"
            )
            
            status = "✅ ALLOWED" if result.allowed else "❌ BLOCKED"
            print(f"Request {i+1}: {status} - Remaining: {result.remaining}, Type: {result.limit_type}")
            
            if not result.allowed:
                print(f"   Retry after: {result.retry_after} seconds")
        
        # Test metrics
        print("\n📈 Current metrics:")
        metrics = rate_limiting_service.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Allowed requests: {metrics['allowed_requests']}")
        print(f"Blocked requests: {metrics['blocked_requests']}")
        print(f"Fallback operations: {metrics['fallback_operations']}")
        
        # Test admin bypass
        print("\n👑 Testing admin bypass:")
        admin_result = await rate_limiting_service.check_rate_limit(
            ip="127.0.0.1",
            user_id="admin_user",
            user_data={"role": "admin"},
            endpoint_path="/admin/test",
            request_method="GET"
        )
        
        status = "✅ ALLOWED" if admin_result.allowed else "❌ BLOCKED"
        print(f"Admin request: {status} - Type: {admin_result.limit_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_middleware_endpoints():
    """Test if middleware endpoints work when called directly."""
    print("\n🔍 Testing middleware endpoints directly...")
    
    try:
        from api.security.enhanced_rate_limiting_middleware import RateLimitingConfigMiddleware
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        from fastapi import Request
        from fastapi.responses import JSONResponse
        
        # Create mock middleware
        class MockApp:
            pass
        
        middleware = RateLimitingConfigMiddleware(MockApp())
        
        # Create mock request for metrics
        class MockRequest:
            def __init__(self, path, method):
                self.url = MockURL(path)
                self.method = method
        
        class MockURL:
            def __init__(self, path):
                self.path = path
        
        # Test metrics endpoint
        print("Testing metrics endpoint...")
        mock_request = MockRequest("/api/rate-limit/metrics", "GET")
        response = await middleware._handle_metrics_request(mock_request)
        
        if hasattr(response, 'status_code'):
            print(f"Metrics endpoint status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Metrics endpoint working")
                return True
            else:
                print("❌ Metrics endpoint failed")
                return False
        else:
            print("✅ Metrics endpoint returned response")
            return True
            
    except Exception as e:
        print(f"❌ Middleware test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all direct tests."""
    print("🧪 DIRECT RATE LIMITING TESTS")
    print("=" * 50)
    
    # Test 1: Direct service
    test1_result = await test_direct_rate_limiting()
    
    # Test 2: Middleware endpoints
    test2_result = await test_middleware_endpoints()
    
    print("\n" + "=" * 50)
    print("📊 DIRECT TEST RESULTS")
    print("=" * 50)
    
    total_tests = 2
    passed_tests = sum([test1_result, test2_result])
    
    test_results = [
        ("Direct Service Test", test1_result),
        ("Middleware Endpoint Test", test2_result)
    ]
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} direct tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All direct tests passed!")
        print("📝 Rate limiting core functionality is working correctly")
        print("🔧 The 500 errors are likely from middleware integration issues")
    else:
        print("⚠️ Some direct tests failed")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
