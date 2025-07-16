#!/bin/bash
# Fix Auth Dependencies SQL Syntax Error
# This is the REAL cause of the authentication failures

echo "🔧 FIXING AUTH DEPENDENCIES SQL SYNTAX ERROR"
echo "============================================"

echo "🎯 Root Cause Found:"
echo "   auth_dependencies.py line 88: SQL syntax error"
echo "   Using SQLite syntax (WHERE id = ?) with PostgreSQL database"
echo "   Need PostgreSQL syntax (WHERE id = %s)"
echo ""

# Step 1: Backup current auth_dependencies.py
echo "📁 Step 1: Creating backup..."
if [[ -f "api/auth_dependencies.py" ]]; then
    cp "api/auth_dependencies.py" "api/auth_dependencies.py.broken.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup created"
else
    echo "⚠️  No existing auth_dependencies.py found"
fi

# Step 2: Deploy the fixed auth_dependencies.py
echo "🛠️  Step 2: Deploying fixed auth_dependencies.py..."

cat > api/auth_dependencies.py << 'EOF'
"""
Authentication dependencies for the Balance Tracking API
Role-based access control and authentication middleware
FIXED: PostgreSQL SQL syntax corrected
"""

import logging
from typing import List, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth_models import AuthenticatedUser, UserRole, TokenType
from api.dependencies import get_database
from api.database import DatabaseManager
from api.jwt_service import jwt_service

logger = logging.getLogger(__name__)
security = HTTPBearer()


# =============================================================================
# Core Authentication Dependencies
# =============================================================================

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DatabaseManager = Depends(get_database)
) -> AuthenticatedUser:
    """
    Extract and validate current user from JWT token.

    This is the base authentication dependency used by all protected routes.
    """
    token = credentials.credentials

    try:
        # Validate access token
        token_data = jwt_service.validate_token(token, expected_type=TokenType.ACCESS)

        # Get user from database to ensure they still exist and are active
        # FIXED: Use proper PostgreSQL parameter syntax
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, created_at, updated_at, last_login, role
                FROM users
                WHERE id = %s
            """
        else:
            query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, created_at, updated_at, last_login, role
                FROM users
                WHERE id = ?
            """
        
        results = db.execute_query(query, (token_data.user_id,))

        if not results:
            logger.warning(f"Token valid but user not found: {token_data.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        user = results[0]

        # Check if user account is active
        if not user['is_active']:
            logger.warning(f"Inactive user attempted access: {user['username']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )

        # Create authenticated user object
        authenticated_user = AuthenticatedUser(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=token_data.role,
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            created_at=user['created_at'],
            last_login=user['last_login']
        )

        logger.debug(f"Authenticated user: {user['username']} ({token_data.role.value})")
        return authenticated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# =============================================================================
# Role-Based Access Control Dependencies
# =============================================================================

def require_roles(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of roles that can access the endpoint

    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user_from_token)
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.username} "
                f"(role: {current_user.role.value}, required: {[r.value for r in allowed_roles]})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


def require_admin():
    """Dependency to require admin role."""
    return require_roles([UserRole.ADMIN])


def require_trader_or_admin():
    """Dependency to require trader or admin role."""
    return require_roles([UserRole.TRADER, UserRole.ADMIN])


def require_verified_user():
    """
    Dependency to require email-verified user account.
    """
    async def verified_checker(
        current_user: AuthenticatedUser = Depends(get_current_user_from_token)
    ) -> AuthenticatedUser:
        if not current_user.is_verified:
            logger.warning(f"Unverified user attempted access: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required. Please verify your email address."
            )
        return current_user

    return verified_checker


def require_verified_trader():
    """Dependency to require verified trader or admin."""
    async def verified_trader_checker(
        current_user: AuthenticatedUser = Depends(require_trader_or_admin())
    ) -> AuthenticatedUser:
        if not current_user.is_verified:
            logger.warning(f"Unverified trader attempted access: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required for trading operations"
            )
        return current_user

    return verified_trader_checker


# =============================================================================
# Optional Authentication Dependencies
# =============================================================================

async def get_current_user_optional(
    request: Request,
    db: DatabaseManager = Depends(get_database)
) -> Optional[AuthenticatedUser]:
    """
    Get current user if authenticated, otherwise return None.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None

        token = authorization.split(" ")[1]

        # Validate token
        token_data = jwt_service.validate_token(token, expected_type=TokenType.ACCESS)

        # Get user from database - FIXED: Use proper PostgreSQL syntax
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, created_at, updated_at, last_login, role
                FROM users
                WHERE id = %s
            """
        else:
            query = """
                SELECT id, username, email, first_name, last_name,
                       is_active, is_verified, created_at, updated_at, last_login, role
                FROM users
                WHERE id = ?
            """
        
        results = db.execute_query(query, (token_data.user_id,))

        if not results or not results[0]['is_active']:
            return None

        user = results[0]
        return AuthenticatedUser(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=token_data.role,
            is_active=user['is_active'],
            is_verified=user['is_verified'],
            created_at=user['created_at'],
            last_login=user['last_login']
        )

    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


# =============================================================================
# Resource Owner Validation Dependencies
# =============================================================================

def require_resource_owner_or_admin(resource_user_field: str = "username"):
    """
    Dependency factory to ensure user can only access their own resources.

    Args:
        resource_user_field: Name of the path parameter containing the resource owner identifier

    Returns:
        Dependency function that validates resource ownership
    """
    async def ownership_checker(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user_from_token)
    ) -> AuthenticatedUser:
        # Admin users can access any resource
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Get the resource owner from path parameters
        path_params = request.path_params
        resource_owner = path_params.get(resource_user_field)

        if not resource_owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {resource_user_field} parameter"
            )

        # Check if current user owns the resource
        if current_user.username != resource_owner:
            logger.warning(
                f"User {current_user.username} attempted to access resource owned by {resource_owner}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own resources."
            )

        return current_user

    return ownership_checker


# =============================================================================
# Convenience Aliases
# =============================================================================

# Common authentication dependencies with descriptive names
get_current_user = get_current_user_from_token
require_authentication = get_current_user_from_token
require_admin_access = require_admin()
require_trader_access = require_trader_or_admin()
require_verified_access = require_verified_user()
require_verified_trader_access = require_verified_trader()

# Resource ownership dependencies
require_own_resource = require_resource_owner_or_admin()
require_own_user_resource = require_resource_owner_or_admin("username")
require_own_id_resource = require_resource_owner_or_admin("user_id")
EOF

echo "✅ Fixed auth_dependencies.py deployed"

# Step 3: Test the fix
echo ""
echo "🧪 Step 3: Testing import..."
python3 -c "
try:
    from api.auth_dependencies import require_admin, AuthenticatedUser
    print('✅ Auth dependencies import successful')
    
    admin_dep = require_admin()
    print('✅ require_admin() callable')
except Exception as e:
    print(f'❌ Import test failed: {e}')
"

echo ""
echo "🔄 Step 4: Server restart required"
echo "=================================="
echo ""
echo "🔥 CRITICAL: The server MUST be restarted for the fix to take effect!"
echo ""
echo "🛑 1. Stop your current server (Ctrl+C)"
echo "🚀 2. Start server: python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info"
echo "🧪 3. Test: ./test_admin_auth.sh"
echo ""
echo "🎯 What was fixed:"
echo "   ❌ Before: WHERE id = ? (SQLite syntax causing PostgreSQL errors)"
echo "   ✅ After:  WHERE id = %s (Proper PostgreSQL syntax)"
echo ""
echo "📋 Expected results after restart:"
echo "   ✅ No more 'syntax error at end of input' errors"
echo "   ✅ Admin endpoints return real data with valid tokens"
echo "   ✅ Authentication protection working correctly"
echo ""
echo "🎉 AUTH DEPENDENCIES FIX COMPLETE!"
