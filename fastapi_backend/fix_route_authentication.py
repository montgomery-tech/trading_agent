#!/usr/bin/env python3
"""
Fix Route Authentication Script
Adds proper API key authentication to route endpoints

This script updates the route files to include proper authentication dependencies.
"""

import os
from pathlib import Path


def fix_users_route():
    """Fix users.py route to include authentication"""
    users_content = '''"""
User management routes - With API Key Authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{username}")
async def get_user(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    db: DatabaseManager = Depends(get_database)
):
    """Get user by username - Requires authentication"""
    try:
        # Check if user exists and is active
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at, updated_at, last_login
                FROM users 
                WHERE username = %s AND is_active = %s
            """
            params = (username, True)
        else:
            query = """
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at, updated_at, last_login
                FROM users 
                WHERE username = ? AND is_active = ?
            """
            params = (username, 1)
        
        results = db.execute_query(query, params)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found or inactive"
            )
        
        user = results[0]
        
        return {
            "success": True,
            "data": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "first_name": user['first_name'],
                "last_name": user['last_name'],
                "is_active": user['is_active'],
                "is_verified": user['is_verified'],
                "created_at": user['created_at'],
                "updated_at": user['updated_at'],
                "last_login": user['last_login']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {username}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user: {str(e)}"
        )
'''
    return users_content


def fix_balances_route():
    """Fix balances.py route to include authentication"""
    balances_content = '''"""
Balance management routes - With API Key Authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_balances(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    currency: str = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get balances for a user - Requires authentication"""
    try:
        # First verify user exists and is active
        if db.db_type == 'postgresql':
            user_query = "SELECT id FROM users WHERE username = %s AND is_active = %s"
            user_params = (username, True)
        else:
            user_query = "SELECT id FROM users WHERE username = ? AND is_active = ?"
            user_params = (username, 1)

        user_results = db.execute_query(user_query, user_params)

        if not user_results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found or inactive"
            )

        user_id = user_results[0]['id']

        # Build balances query
        if db.db_type == 'postgresql':
            query = """
                SELECT ub.id, ub.currency_code, ub.total_balance,
                       ub.available_balance, ub.locked_balance,
                       c.name as currency_name, c.symbol, c.is_fiat,
                       ub.created_at, ub.updated_at
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = %s
            """
            params = [user_id]

            if currency:
                query += " AND ub.currency_code = %s"
                params.append(currency.upper())

        else:
            # SQLite
            query = """
                SELECT ub.id, ub.currency_code, ub.total_balance,
                       ub.available_balance, ub.locked_balance,
                       c.name as currency_name, c.symbol, c.is_fiat,
                       ub.created_at, ub.updated_at
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = ?
            """
            params = [user_id]

            if currency:
                query += " AND ub.currency_code = ?"
                params.append(currency.upper())

        query += " ORDER BY c.is_fiat DESC, ub.total_balance DESC"

        balances = db.execute_query(query, params)

        # Convert boolean fields for consistency
        for balance in balances:
            balance['is_fiat'] = bool(balance['is_fiat'])

        return {
            "success": True,
            "data": balances,
            "user": username,
            "total_balances": len(balances)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balances: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving balances: {str(e)}"
        )
'''
    return balances_content


def fix_transactions_route():
    """Fix transactions.py route to include authentication"""
    transactions_content = '''"""
Transaction management routes - With API Key Authentication
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from api.auth_dependencies import require_resource_owner_or_admin, AuthenticatedUser
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_transactions(
    username: str,
    current_user: AuthenticatedUser = Depends(require_resource_owner_or_admin("username")),
    limit: int = 50,
    offset: int = 0,
    db: DatabaseManager = Depends(get_database)
):
    """Get transactions for a user - Requires authentication"""
    try:
        # Verify user exists and is active
        if db.db_type == 'postgresql':
            user_query = "SELECT id FROM users WHERE username = %s AND is_active = %s"
            user_params = (username, True)
        else:
            user_query = "SELECT id FROM users WHERE username = ? AND is_active = ?"
            user_params = (username, 1)
        
        user_results = db.execute_query(user_query, user_params)
        
        if not user_results:
            raise HTTPException(
                status_code=404, 
                detail=f"User '{username}' not found"
            )
        
        user_id = user_results[0]['id']
        
        # Get transactions
        if db.db_type == 'postgresql':
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       created_at, processed_at
                FROM transactions 
                WHERE user_id = %s
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            params = (user_id, limit, offset)
        else:
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       created_at, processed_at
                FROM transactions 
                WHERE user_id = ?
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            params = (user_id, limit, offset)
        
        transactions = db.execute_query(query, params)
        
        return {
            "success": True,
            "data": transactions,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(transactions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving transactions: {str(e)}"
        )
'''
    return transactions_content


def main():
    """Update route files with authentication"""
    
    print("🔧 Fixing Route Authentication")
    print("=" * 40)
    
    # Update users.py
    users_file = Path("api/routes/users.py")
    if users_file.exists():
        with open(users_file, 'w') as f:
            f.write(fix_users_route())
        print("✅ Updated api/routes/users.py")
    else:
        print("❌ api/routes/users.py not found")
    
    # Update balances.py  
    balances_file = Path("api/routes/balances.py")
    if balances_file.exists():
        with open(balances_file, 'w') as f:
            f.write(fix_balances_route())
        print("✅ Updated api/routes/balances.py")
    else:
        print("❌ api/routes/balances.py not found")
    
    # Update transactions.py
    transactions_file = Path("api/routes/transactions.py")
    if transactions_file.exists():
        with open(transactions_file, 'w') as f:
            f.write(fix_transactions_route())
        print("✅ Updated api/routes/transactions.py")
    else:
        print("❌ api/routes/transactions.py not found")
    
    print("\n🚀 Authentication Fix Complete!")
    print("Please restart your FastAPI server: python3 main.py")


if __name__ == "__main__":
    main()
