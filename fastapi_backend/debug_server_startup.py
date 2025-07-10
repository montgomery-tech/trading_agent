#!/usr/bin/env python3
"""
Debug Server Startup Script
Tests the actual FastAPI server startup to find where 500 errors originate
"""

import sys
import traceback
import logging
import asyncio
from datetime import datetime

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_main_py_imports():
    """Test all imports from main.py."""
    print("🔍 Testing main.py imports...")
    
    try:
        # Test all the imports from main.py exactly as they appear
        from fastapi import FastAPI, HTTPException, status, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from contextlib import asynccontextmanager
        from datetime import datetime
        
        from api.config import settings
        from api.database import DatabaseManager
        from api.routes import users, transactions, balances, currencies
        from api.auth_routes import router as auth_router
        
        from api.security import (
            create_security_middleware_stack,
            security_exception_handler,
            EnhancedErrorResponse
        )
        
        from api.security.redis_rate_limiting_backend import cleanup_redis_backend
        
        print("✅ All main.py imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

async def test_lifespan_execution():
    """Test the actual lifespan function execution."""
    print("\n🔍 Testing lifespan execution...")
    
    try:
        from api.config import settings
        from api.database import DatabaseManager
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        from api.security.redis_rate_limiting_backend import cleanup_redis_backend
        
        # Mock app state
        class MockApp:
            def __init__(self):
                self.state = type('State', (), {})()
        
        app = MockApp()
        
        print("  🔄 Starting lifespan sequence...")
        
        # Database initialization
        print("  📀 Initializing database...")
        db = DatabaseManager(settings.DATABASE_URL)
        db.connect()
        app.state.database = db
        print("  ✅ Database initialized")
        
        # Redis initialization
        print("  🔴 Initializing Redis...")
        await rate_limiting_service.initialize_redis()
        print("  ✅ Redis initialized")
        
        # Log production status
        print("  📊 Production status:")
        print(f"     Environment: {settings.ENVIRONMENT}")
        print(f"     Database: {getattr(settings, 'DATABASE_TYPE', 'Unknown')}")
        print(f"     Rate Limiting: {getattr(settings, 'RATE_LIMIT_ENABLED', 'Unknown')}")
        
        # Cleanup
        print("  🧹 Cleaning up...")
        await cleanup_redis_backend()
        if hasattr(app.state, 'database'):
            app.state.database.disconnect()
        
        print("✅ Lifespan execution completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Lifespan execution failed: {e}")
        traceback.print_exc()
        return False

def test_app_creation_with_routes():
    """Test creating the FastAPI app with all routes."""
    print("\n🔍 Testing app creation with routes...")
    
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from api.config import settings
        from api.routes import users, transactions, balances, currencies
        from api.auth_routes import router as auth_router
        from api.security import create_security_middleware_stack, security_exception_handler
        
        # Create app (without lifespan for now)
        app = FastAPI(
            title=settings.PROJECT_NAME,
            description="Test app with routes",
            version=settings.VERSION,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        print("  ✅ Basic app created")
        
        # Apply security middleware stack
        app = create_security_middleware_stack(app)
        print("  ✅ Security middleware applied")
        
        # Add CORS
        cors_origins = getattr(settings, 'CORS_ORIGINS', ["http://localhost:3000"])
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["*"],
        )
        print("  ✅ CORS middleware added")
        
        # Add exception handler
        from fastapi import HTTPException
        app.add_exception_handler(HTTPException, security_exception_handler)
        print("  ✅ Exception handler added")
        
        # Include routes
        app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
        app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
        app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
        app.include_router(balances.router, prefix="/api/v1/balances", tags=["Balances"])
        app.include_router(currencies.router, prefix="/api/v1/currencies", tags=["Currencies"])
        print("  ✅ All routes included")
        
        print("✅ App creation with routes completed")
        return True, app
        
    except Exception as e:
        print(f"❌ App creation with routes failed: {e}")
        traceback.print_exc()
        return False, None

def test_endpoint_definitions():
    """Test if endpoints are properly defined."""
    print("\n🔍 Testing endpoint definitions...")
    
    try:
        success, app = test_app_creation_with_routes()
        if not success:
            return False
        
        # Check if key endpoints exist
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append(f"{list(route.methods)[0] if route.methods else 'GET'} {route.path}")
        
        print("  📋 Available routes:")
        for route in sorted(routes):
            print(f"     {route}")
        
        # Check for key endpoints
        expected_endpoints = [
            "/health",
            "/api/rate-limit/metrics",
            "/api/redis/health"
        ]
        
        missing_endpoints = []
        for endpoint in expected_endpoints:
            found = any(endpoint in route for route in routes)
            if found:
                print(f"  ✅ {endpoint} found")
            else:
                print(f"  ❌ {endpoint} missing")
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"  ⚠️ Missing endpoints: {missing_endpoints}")
            print("  💡 This might be why you're getting 500 errors!")
            return False
        
        print("✅ All expected endpoints found")
        return True
        
    except Exception as e:
        print(f"❌ Endpoint definition test failed: {e}")
        traceback.print_exc()
        return False

async def test_server_response_simulation():
    """Simulate server responses to identify the 500 error source."""
    print("\n🔍 Testing server response simulation...")
    
    try:
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from api.config import settings
        from api.database import DatabaseManager
        from contextlib import asynccontextmanager
        
        # Create the exact lifespan from main.py
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("🚀 Starting Balance Tracking API...")

            # Initialize database
            db = DatabaseManager(settings.DATABASE_URL)
            try:
                db.connect()
                app.state.database = db
                logger.info("✅ Database initialized")
            except Exception as e:
                logger.error(f"❌ Database initialization failed: {e}")
                raise

            # Initialize Redis backend for rate limiting
            try:
                from api.security.enhanced_rate_limiting_service import rate_limiting_service
                await rate_limiting_service.initialize_redis()
                logger.info("✅ Redis rate limiting backend initialized")
            except Exception as e:
                logger.warning(f"⚠️ Redis initialization failed, using fallback: {e}")

            yield

            # Cleanup
            logger.info("🛑 Shutting down...")
            try:
                from api.security.redis_rate_limiting_backend import cleanup_redis_backend
                await cleanup_redis_backend()
                logger.info("✅ Redis backend cleaned up")
            except Exception as e:
                logger.warning(f"⚠️ Redis cleanup warning: {e}")

            if hasattr(app.state, 'database'):
                app.state.database.disconnect()
                logger.info("✅ Database disconnected")
        
        # Create app with exact configuration from main.py
        app = FastAPI(
            title=settings.PROJECT_NAME,
            description="REST API for managing user balances, transactions, and trading",
            version=settings.VERSION,
            lifespan=lifespan,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add basic endpoints that are causing 500 errors
        @app.get("/")
        async def root():
            return {
                "message": f"Welcome to {settings.PROJECT_NAME}",
                "version": settings.VERSION,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }

        @app.get("/health")
        async def health_check():
            try:
                db = app.state.database
                db.test_connection()
                stats = db.get_stats()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "database": {
                        "status": "connected",
                        "type": getattr(settings, 'DATABASE_TYPE', 'sqlite'),
                        "stats": stats
                    },
                    "version": settings.VERSION
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e)
                }

        print("  ✅ Test app created with lifespan")
        
        # Test with TestClient
        with TestClient(app) as client:
            print("  🔄 Testing endpoints...")
            
            # Test root endpoint
            try:
                response = client.get("/")
                print(f"    GET / -> {response.status_code}")
                if response.status_code != 200:
                    print(f"      Response: {response.text}")
            except Exception as e:
                print(f"    GET / -> ERROR: {e}")
            
            # Test health endpoint
            try:
                response = client.get("/health")
                print(f"    GET /health -> {response.status_code}")
                if response.status_code != 200:
                    print(f"      Response: {response.text}")
            except Exception as e:
                print(f"    GET /health -> ERROR: {e}")
        
        print("✅ Server response simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Server response simulation failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all diagnostic tests."""
    print("🔍 FastAPI Server Startup Debug")
    print("=" * 50)
    
    tests = [
        ("Main.py Imports", test_main_py_imports),
        ("Lifespan Execution", lambda: asyncio.run(test_lifespan_execution())),
        ("App Creation with Routes", lambda: test_app_creation_with_routes()[0]),
        ("Endpoint Definitions", test_endpoint_definitions),
        ("Server Response Simulation", lambda: asyncio.run(test_server_response_simulation())),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SERVER STARTUP DEBUG SUMMARY")
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
        print("🎉 All startup tests passed!")
        print("💡 The issue might be in the specific endpoints missing from main.py")
        print("   Check if /api/rate-limit/metrics and /api/redis/health are defined")
    else:
        failed_tests = [name for name, result in results if not result]
        print(f"⚠️ Failed tests: {', '.join(failed_tests)}")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
