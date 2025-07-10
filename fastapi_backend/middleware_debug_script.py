#!/usr/bin/env python3
"""
Middleware Debug Script
Test middleware integration step by step
"""

import asyncio
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_middleware_imports():
    """Test if middleware imports correctly."""
    print("🔍 Testing middleware imports...")
    
    try:
        from api.security.enhanced_rate_limiting_middleware import (
            EnhancedRateLimitingMiddleware,
            RateLimitingConfigMiddleware,
            create_enhanced_rate_limiting_middleware
        )
        print("✅ Middleware classes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Middleware import failed: {e}")
        traceback.print_exc()
        return False

def test_fastapi_integration():
    """Test FastAPI app creation with middleware."""
    print("\n🔍 Testing FastAPI integration...")
    
    try:
        from fastapi import FastAPI
        from api.security.enhanced_rate_limiting_middleware import create_enhanced_rate_limiting_middleware
        
        # Create test app
        app = FastAPI(title="Test App")
        
        # Add middleware
        app = create_enhanced_rate_limiting_middleware(app)
        
        print("✅ FastAPI app created with rate limiting middleware")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI integration failed: {e}")
        traceback.print_exc()
        return False

def test_request_simulation():
    """Test simulated request processing."""
    print("\n🔍 Testing request simulation...")
    
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from api.security.enhanced_rate_limiting_middleware import EnhancedRateLimitingMiddleware
        
        # Create middleware instance
        class MockApp:
            pass
        
        middleware = EnhancedRateLimitingMiddleware(MockApp())
        
        # Create mock request
        class MockClient:
            host = "127.0.0.1"
        
        class MockURL:
            path = "/test"
        
        class MockHeaders:
            def get(self, key, default=None):
                return default
            
            def __contains__(self, key):
                return False
        
        class MockRequest:
            def __init__(self):
                self.client = MockClient()
                self.url = MockURL()
                self.headers = MockHeaders()
                self.method = "GET"
        
        mock_request = MockRequest()
        
        # Test IP extraction
        ip = middleware._get_client_ip(mock_request)
        print(f"✅ IP extraction works: {ip}")
        
        return True
        
    except Exception as e:
        print(f"❌ Request simulation failed: {e}")
        traceback.print_exc()
        return False

async def test_async_rate_check():
    """Test async rate limiting check."""
    print("\n🔍 Testing async rate limiting check...")
    
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        
        # Simple rate check
        result = await rate_limiting_service.check_rate_limit(
            ip="127.0.0.1",
            endpoint_path="/test"
        )
        
        print(f"✅ Async rate check works: allowed={result.allowed}")
        return True
        
    except Exception as e:
        print(f"❌ Async rate check failed: {e}")
        traceback.print_exc()
        return False

def test_main_app_structure():
    """Test if main.py structure is correct."""
    print("\n🔍 Testing main.py structure...")
    
    try:
        # Try to import main components
        from main import app
        print("✅ Main app imported successfully")
        
        # Check if middleware is registered
        middleware_names = [type(m).__name__ for m in app.middleware_stack]
        print(f"📋 Registered middleware: {middleware_names}")
        
        # Look for rate limiting middleware
        has_rate_limiting = any("RateLimit" in name for name in middleware_names)
        if has_rate_limiting:
            print("✅ Rate limiting middleware found in app")
        else:
            print("⚠️ Rate limiting middleware not found in app")
        
        return True
        
    except Exception as e:
        print(f"❌ Main app test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all middleware debug tests."""
    print("🔧 MIDDLEWARE DEBUG TESTS")
    print("=" * 50)
    
    tests = [
        ("Middleware Imports", test_middleware_imports),
        ("FastAPI Integration", test_fastapi_integration),
        ("Request Simulation", test_request_simulation),
        ("Main App Structure", test_main_app_structure),
    ]
    
    # Run sync tests
    results = {}
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Run async test
    print(f"\n🧪 Running: Async Rate Check")
    try:
        async_result = asyncio.run(test_async_rate_check())
        results["Async Rate Check"] = async_result
    except Exception as e:
        print(f"❌ Async test crashed: {e}")
        results["Async Rate Check"] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 MIDDLEWARE DEBUG RESULTS")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All middleware tests passed!")
        print("🔧 The 500 errors might be from other middleware or routes")
    else:
        print("⚠️ Some middleware tests failed - this explains the 500 errors")
    
    print("\n💡 Next steps:")
    print("1. Check your FastAPI server logs for detailed error traces")
    print("2. Try accessing a simple endpoint like http://localhost:8000/docs")
    print("3. Temporarily disable rate limiting middleware to isolate the issue")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    main()
