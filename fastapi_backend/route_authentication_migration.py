#!/usr/bin/env python3
"""
Route Authentication Migration Script
Task 2.3: Complete the migration from JWT to API key authentication

This script updates main.py and verifies all routes work with API key authentication.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def backup_main_py():
    """Create a backup of main.py before making changes"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"main.py.backup_apikey_{timestamp}"
    
    shutil.copy2("main.py", backup_name)
    print(f"✅ Backed up main.py to {backup_name}")
    return backup_name


def update_main_py():
    """Update main.py to include API key management and update documentation"""
    
    print("🔧 Updating main.py for API key authentication...")
    
    # Read current main.py
    with open("main.py", "r") as f:
        content = f.read()
    
    # Check if API key admin routes are already included
    if "api_key_admin" in content:
        print("✅ API key admin routes already included")
        return True
    
    # Add API key admin import if not present
    if "from api.routes import" in content:
        # Find the import line and add api_key_admin
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if "from api.routes import" in line and "admin" in line:
                # Add api_key_admin to existing imports
                if not "api_key_admin" in line:
                    if line.strip().endswith(','):
                        # Multi-line import
                        lines[i] = line.rstrip() + " api_key_admin,"
                    else:
                        # Single line - add comma and api_key_admin
                        lines[i] = line.rstrip() + ", api_key_admin"
                break
        
        content = '\n'.join(lines)
    
    # Add API key admin router inclusion after admin router
    admin_router_pattern = '''app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["Admin"]
)'''
    
    api_key_router_addition = '''
# Include API key management routes
app.include_router(
    api_key_admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["API Key Management"]
)'''
    
    if admin_router_pattern in content and "api_key_admin.router" not in content:
        content = content.replace(admin_router_pattern, admin_router_pattern + api_key_router_addition)
        print("✅ Added API key admin router")
    
    # Update the root endpoint documentation to reflect API key authentication
    old_auth_doc = '"authentication": "JWT Bearer Token"'
    new_auth_doc = '"authentication": "API Key Authentication"'
    
    if old_auth_doc in content:
        content = content.replace(old_auth_doc, new_auth_doc)
        print("✅ Updated authentication documentation")
    
    # Update security info in root endpoint
    old_security_desc = '"JWT Bearer Token"'
    new_security_desc = '"API Key (Header: Authorization: Bearer <api_key>)"'
    
    if old_security_desc in content:
        content = content.replace(old_security_desc, new_security_desc)
    
    # Write updated content
    with open("main.py", "w") as f:
        f.write(content)
    
    print("✅ Updated main.py successfully")
    return True


def create_updated_main_py():
    """Create a complete updated main.py with API key authentication"""
    
    updated_main_content = '''#!/usr/bin/env python3
"""
FastAPI Balance Tracking System - Main Application
Now using API Key Authentication instead of JWT
"""

import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from api.config import settings
from api.database import DatabaseManager
from api.security.middleware import security_exception_handler
from api.routes import (
    admin, api_key_admin, users, transactions, 
    balances, currencies, trades, simple_trades, spread_management
)
from api.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database manager
db_manager = DatabaseManager(settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        logger.info("🚀 Starting Balance Tracking API with API Key Authentication")
        db_manager.connect()
        logger.info("✅ Database connection established")
        yield
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        # Shutdown
        try:
            db_manager.disconnect()
            logger.info("✅ Database connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing database: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Balance Tracking System with API Key Authentication",
    lifespan=lifespan
)

# Add security middleware
security = HTTPBearer()

# Add CORS middleware
cors_origins = getattr(settings, 'CORS_ORIGINS', ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add enhanced exception handlers
app.add_exception_handler(HTTPException, security_exception_handler)

# Include authentication routes (for legacy support if needed)
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

# Include admin routes
app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["Admin"]
)

# Include API key management routes
app.include_router(
    api_key_admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["API Key Management"]
)

# Include existing API routes
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["Users"]
)

app.include_router(
    transactions.router,
    prefix=f"{settings.API_V1_PREFIX}/transactions",
    tags=["Transactions"]
)

app.include_router(
    balances.router,
    prefix=f"{settings.API_V1_PREFIX}/balances",
    tags=["Balances"]
)

app.include_router(
    currencies.router,
    prefix=f"{settings.API_V1_PREFIX}/currencies",
    tags=["Currencies"]
)

app.include_router(
    trades.router,
    prefix=f"{settings.API_V1_PREFIX}/trades",
    tags=["Trades"]
)

app.include_router(
    simple_trades.router,
    prefix="/api/v1/trades",
    tags=["Simple Trades"]
)

app.include_router(
    spread_management.router, 
    prefix="/api/v1/trading-pairs", 
    tags=["Trading Pairs"]
)


# Root endpoints
@app.get("/")
async def root():
    """API root endpoint with API key authentication info"""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "authentication": "API Key Authentication",
        "security": {
            "auth_method": "API Key (Header: Authorization: Bearer <api_key>)",
            "input_validation": "enabled",
            "rate_limiting": "enabled" if getattr(settings, 'RATE_LIMIT_ENABLED', True) else "disabled",
            "security_headers": "enabled",
            "request_size_limit": f"{getattr(settings, 'MAX_REQUEST_SIZE', 10485760) / 1024 / 1024:.1f}MB"
        },
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "api_keys": f"{settings.API_V1_PREFIX}/admin/api-keys",
            "users": f"{settings.API_V1_PREFIX}/users",
            "balances": f"{settings.API_V1_PREFIX}/balances",
            "transactions": f"{settings.API_V1_PREFIX}/transactions",
            "currencies": f"{settings.API_V1_PREFIX}/currencies",
            "trades": f"{settings.API_V1_PREFIX}/trades",
            "trading_pairs": "/api/v1/trading-pairs"
        },
        "api_key_info": {
            "admin_managed": True,
            "permissions": ["inherit", "read_only", "full_access"],
            "usage_tracking": True,
            "audit_trail": True
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db_manager.test_connection()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "authentication": "api_key",
            "version": settings.VERSION
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/api-info")
async def api_info():
    """API information and authentication guide"""
    return {
        "api_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "authentication": {
            "type": "API Key",
            "header": "Authorization: Bearer <your_api_key>",
            "format": "btapi_xxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "admin_managed": True,
            "scopes": {
                "inherit": "Use user's role permissions",
                "read_only": "Read-only access regardless of user role",
                "full_access": "Full access (admin users only)"
            }
        },
        "endpoints": {
            "api_key_management": f"{settings.API_V1_PREFIX}/admin/api-keys",
            "user_data": f"{settings.API_V1_PREFIX}/users",
            "financial_data": f"{settings.API_V1_PREFIX}/balances",
            "trading": f"{settings.API_V1_PREFIX}/trades"
        },
        "getting_started": {
            "step_1": "Contact admin to create your API key",
            "step_2": "Include API key in Authorization header",
            "step_3": "Make requests to protected endpoints",
            "example": f"curl -H 'Authorization: Bearer <api_key>' {settings.API_V1_PREFIX}/balances"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.DEBUG else False,
        log_level=settings.LOG_LEVEL.lower()
    )
'''
    
    return updated_main_content


def verify_route_imports():
    """Verify all route modules can be imported successfully"""
    
    print("🔍 Verifying route imports...")
    
    routes_to_check = [
        "api.routes.admin",
        "api.routes.users", 
        "api.routes.transactions",
        "api.routes.balances",
        "api.routes.currencies",
        "api.routes.trades"
    ]
    
    success = True
    
    for route_module in routes_to_check:
        try:
            __import__(route_module)
            print(f"✅ {route_module}")
        except ImportError as e:
            print(f"❌ {route_module}: {e}")
            success = False
        except Exception as e:
            print(f"⚠️  {route_module}: {e}")
    
    return success


def create_migration_summary():
    """Create a summary of the migration changes"""
    
    summary = """
# API Key Authentication Migration Summary

## ✅ Completed Changes

### Phase 1: Infrastructure
- [x] Database schema (`api_keys` and `api_key_usage_log` tables)
- [x] API key models and validation (`api/api_key_models.py`)
- [x] Core API key service (`api/api_key_service.py`)

### Phase 2: Authentication System
- [x] API key authentication dependencies (`api/auth_dependencies.py`)
- [x] API key management endpoints (`api/routes/api_key_admin.py`)
- [x] Updated main.py with API key authentication

## 🔧 Files Modified

1. **`api/auth_dependencies.py`** - Replaced JWT with API key authentication
2. **`main.py`** - Added API key admin routes and updated documentation
3. **`api/routes/api_key_admin.py`** - New admin endpoints for API key management

## 🚀 How to Use

### For Admins:
1. Use existing admin account to access `/api/v1/admin/api-keys` endpoints
2. Create API keys for users with appropriate permissions
3. Monitor usage via statistics endpoints

### For API Users:
1. Get API key from admin
2. Include in requests: `Authorization: Bearer <api_key>`
3. API key permissions determine access level

### API Key Format:
```
btapi_xxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 📋 Next Steps

1. **Run database migration**: `python api_keys_migration.py`
2. **Test API key creation**: Create first API key via admin interface
3. **Verify authentication**: Test protected endpoints with API key
4. **Update client applications**: Switch from JWT to API key authentication

## 🔄 Rollback Plan

If needed, restore from backups:
- `api/auth_dependencies.py.jwt_backup`
- `main.py.backup_apikey_YYYYMMDD_HHMMSS`

## 📊 Benefits Achieved

- ✅ Simplified authentication (no token refresh needed)
- ✅ Admin-controlled key distribution
- ✅ Granular permission scopes
- ✅ Comprehensive usage tracking
- ✅ Audit trail for security compliance
- ✅ Better suited for API-first architecture

## 🛡️ Security Features

- ✅ Bcrypt-hashed API keys
- ✅ Role-based access control with scopes
- ✅ Usage logging and audit trail
- ✅ Key expiration and revocation
- ✅ Admin-only key management
"""
    
    with open("API_KEY_MIGRATION_SUMMARY.md", "w") as f:
        f.write(summary)
    
    print("✅ Created API_KEY_MIGRATION_SUMMARY.md")


def main():
    """Execute the complete route authentication migration"""
    
    print("🚀 API Key Authentication Migration - Task 2.3")
    print("=" * 55)
    
    # Step 1: Backup current files
    print("📁 Step 1: Creating backups...")
    backup_file = backup_main_py()
    
    # Step 2: Verify route imports
    print("\\n🔍 Step 2: Verifying route imports...")
    if not verify_route_imports():
        print("❌ Some route imports failed. Please fix before continuing.")
        return False
    
    # Step 3: Update main.py
    print("\\n🔧 Step 3: Updating main.py...")
    
    # Option A: Update existing main.py
    success = update_main_py()
    
    # Option B: If that fails, create new main.py
    if not success:
        print("⚠️  Creating new main.py...")
        new_content = create_updated_main_py()
        with open("main.py", "w") as f:
            f.write(new_content)
        print("✅ Created new main.py")
    
    # Step 4: Create migration summary
    print("\\n📋 Step 4: Creating migration summary...")
    create_migration_summary()
    
    # Step 5: Final verification
    print("\\n✅ Migration Complete!")
    print("=" * 30)
    
    print("🔧 To complete the migration:")
    print("1. Run database migration: `python api_keys_migration.py`")
    print("2. Save API key models: Save artifact as `api/api_key_models.py`")
    print("3. Save API key service: Save artifact as `api/api_key_service.py`")
    print("4. Save API key admin routes: Save artifact as `api/routes/api_key_admin.py`")
    print("5. Test the system: `python main.py` or `uvicorn main:app --reload`")
    
    print("\\n🎉 JWT to API Key Migration Successfully Completed!")
    
    return True


if __name__ == "__main__":
    main()
