#!/usr/bin/env python3
"""
Debug Middleware Issue Script
Tests each middleware component individually to find the failing one
"""

import sys
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_basic_imports():
    """Test basic imports that main.py uses."""
    print("🔍 Testing basic imports...")
    
    try:
        from api.config import settings
        print("✅ Settings imported")
    except Exception as e:
        print(f"❌ Settings import failed: {e}")
        return False
    
    try:
        from api.database import DatabaseManager
        print("✅ DatabaseManager imported")
    except Exception as e:
        print(f"❌ DatabaseManager import failed: {e}")
        return False
    
    try:
        from api.routes import users, transactions, balances, currencies
        print("✅ Routes imported")
    except Exception as e:
        print(f"❌ Routes import failed: {e}")
        return False
    
    try:
        from api.auth_routes import router as auth_router
        print("✅ Auth routes imported")
    except Exception as e:
        print(f"❌ Auth routes import failed: {e}")
        return False
    
    return True

def test_security_imports():
    """Test security module imports step by step."""
    print("\n🔍 Testing security imports...")
    
    # Test basic security import
    try:
        from api.security import create_security_middleware_stack
        print("✅ create_security_middleware_stack imported")
    except Exception as e:
        print(f"❌ create_security_middleware_stack import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        from api.security import security_exception_handler
        print("✅ security_exception_handler imported")
    except Exception as e:
        print(f"❌ security_exception_handler import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        from api.security import EnhancedErrorResponse
        print("✅ EnhancedErrorResponse imported")
    except Exception as e:
        print(f"❌ EnhancedErrorResponse import failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_redis_imports():
    """Test Redis-related imports."""
    print("\n🔍 Testing Redis imports...")
    
    try:
        from api.security.redis_rate_limiting_backend import cleanup_redis_backend
        print("✅ cleanup_redis_backend imported")
    except Exception as e:
        print(f"❌ cleanup_redis_backend import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        print("✅ rate_limiting_service imported")
    except Exception as e:
        print(f"❌ rate_limiting_service import failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_fastapi_app_creation():
    """Test FastAPI app creation without middleware."""
    print("\n🔍 Testing FastAPI app creation...")
    
    try:
        from fastapi import FastAPI
        from api.config import settings
        
        app = FastAPI(
            title=settings.PROJECT_NAME,
            description="Test app",
            version=settings.VERSION,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        print("✅ Basic FastAPI app created")
        return True, app
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
        traceback.print_exc()
        return False, None

def test_middleware_creation():
    """Test middleware stack creation."""
    print("\n🔍 Testing middleware stack creation...")
    
    try:
        from fastapi import FastAPI
        from api.config import settings
        from api.security import create_security_middleware_stack
        
        # Create basic app
        app = FastAPI(title="Test App", version="1.0.0")
        print("✅ Basic app created")
        
        # Try to apply middleware stack
        app = create_security_middleware_stack(app)
        print("✅ Security middleware stack applied")
        return True
        
    except Exception as e:
        print(f"❌ Middleware stack creation failed: {e}")
        traceback.print_exc()
        return False

def test_lifespan_context():
    """Test lifespan context manager functionality."""
    print("\n🔍 Testing lifespan context...")
    
    try:
        from contextlib import asynccontextmanager
        from api.database import DatabaseManager
        from api.config import settings
        
        @asynccontextmanager
        async def test_lifespan(app):
            print("  Starting lifespan...")
            
            # Test database initialization
            db = DatabaseManager(settings.DATABASE_URL)
            try:
                db.connect()
                print("  ✅ Database connected")
                app.state.database = db
            except Exception as e:
                print(f"  ❌ Database failed: {e}")
                raise
            
            # Test Redis initialization
            try:
                from api.security.enhanced_rate_limiting_service import rate_limiting_service
                await rate_limiting_service.initialize_redis()
                print("  ✅ Redis initialized")
            except Exception as e:
                print(f"  ⚠️ Redis failed (expected): {e}")
            
            yield
            
            # Cleanup
            print("  Cleaning up lifespan...")
            if hasattr(app.state, 'database'):
                app.state.database.disconnect()
        
        print("✅ Lifespan context manager created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Lifespan context failed: {e}")
        traceback.print_exc()
        return False

async def test_full_startup_sequence():
    """Test the full startup sequence."""
    print("\n🔍 Testing full startup sequence...")
    
    try:
        from fastapi import FastAPI
        from api.config import settings
        from api.security import create_security_middleware_stack
        from contextlib import asynccontextmanager
        from api.database import DatabaseManager
        
        @asynccontextmanager
        async def lifespan(app):
            # Database
            db = DatabaseManager(settings.DATABASE_URL)
            db.connect()
            app.state.database = db
            
            # Redis
            try:
                from api.security.enhanced_rate_limiting_service import rate_limiting_service
                await rate_limiting_service.initialize_redis()
            except Exception as e:
                print(f"  Redis initialization failed (continuing): {e}")
            
            yield
            
            # Cleanup
            if hasattr(app.state, 'database'):
                app.state.database.disconnect()
        
        # Create app with lifespan
        app = FastAPI(
            title=settings.PROJECT_NAME,
            description="Test app with full startup",
            version=settings.VERSION,
            lifespan=lifespan
        )
        
        # Apply middleware
        app = create_security_middleware_stack(app)
        
        print("✅ Full startup sequence completed")
        return True
        
    except Exception as e:
        print(f"❌ Full startup sequence failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests."""
    print("🔍 FastAPI Middleware Debug Diagnostic")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Security Imports", test_security_imports),
        ("Redis Imports", test_redis_imports),
        ("FastAPI App Creation", lambda: test_fastapi_app_creation()[0]),
        ("Middleware Creation", test_middleware_creation),
        ("Lifespan Context", test_lifespan_context),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Test async function
    print(f"\n{'=' * 20} Full Startup Sequence {'=' * 20}")
    try:
        import asyncio
        result = asyncio.run(test_full_startup_sequence())
        results.append(("Full Startup Sequence", result))
    except Exception as e:
        print(f"❌ Full startup sequence crashed: {e}")
        traceback.print_exc()
        results.append(("Full Startup Sequence", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 MIDDLEWARE DEBUG SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The server should start without middleware issues.")
    else:
        failed_tests = [name for name, result in results if not result]
        print(f"⚠️ Failed tests: {', '.join(failed_tests)}")
        print("\n💡 Focus on fixing the failed components first.")
    
    return passed == total

if __name__ == "__main__":
    main()
