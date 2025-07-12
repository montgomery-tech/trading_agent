#!/bin/bash

echo "🚀 Adding Server Startup Code to main.py"
echo "========================================"

# Check if startup code already exists
if grep -q "__main__" main.py; then
    echo "✅ Startup code already exists"
    exit 0
fi

echo "📝 Adding missing server startup code..."

# Add the missing startup code to main.py
cat >> main.py << 'EOF'

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

# Root endpoints
@app.get("/")
async def root():
    """API root endpoint with authentication and security info"""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication": "JWT Bearer Token",
        "security": {
            "input_validation": "enabled",
            "rate_limiting": "enabled" if getattr(settings, 'RATE_LIMIT_ENABLED', True) else "disabled",
            "security_headers": "enabled",
            "request_size_limit": f"{getattr(settings, 'MAX_REQUEST_SIZE', 10485760) / 1024 / 1024:.1f}MB"
        },
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "authentication": f"{settings.API_V1_PREFIX}/auth",
            "admin": f"{settings.API_V1_PREFIX}/admin",
            "users": f"{settings.API_V1_PREFIX}/users",
            "balances": f"{settings.API_V1_PREFIX}/balances",
            "transactions": f"{settings.API_V1_PREFIX}/transactions",
            "currencies": f"{settings.API_V1_PREFIX}/currencies"
        },
        "auth_endpoints": {
            "register": f"{settings.API_V1_PREFIX}/auth/register",
            "login": f"{settings.API_V1_PREFIX}/auth/login",
            "refresh": f"{settings.API_V1_PREFIX}/auth/refresh",
            "logout": f"{settings.API_V1_PREFIX}/auth/logout",
            "profile": f"{settings.API_V1_PREFIX}/auth/me",
            "change_password": f"{settings.API_V1_PREFIX}/auth/change-password"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION
    }

# Server startup
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Balance Tracking API...")
    logger.info(f"   • Environment: {settings.ENVIRONMENT}")
    logger.info(f"   • Debug mode: {settings.DEBUG}")
    logger.info(f"   • Database: {settings.DATABASE_TYPE}")
    logger.info(f"   • JWT Authentication: {'Enabled' if hasattr(settings, 'SECRET_KEY') else 'Disabled'}")
    logger.info(f"   • Rate Limiting: {'Enabled' if getattr(settings, 'RATE_LIMIT_ENABLED', True) else 'Disabled'}")
    logger.info(f"   • Security headers: Enabled")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
EOF

echo "✅ Added server startup code to main.py"
echo ""
echo "🚀 Now you can start the server:"
echo "   python3 main.py"
