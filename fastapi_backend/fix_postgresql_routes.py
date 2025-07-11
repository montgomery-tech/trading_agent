#!/usr/bin/env python3
"""
PostgreSQL Compatible API Routes Fix
Updates the user routes to work with both SQLite and PostgreSQL
"""

import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_users_route():
    """Fix the users route to work with PostgreSQL"""
    
    users_route_content = '''"""
User management routes - PostgreSQL Compatible
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{username}")
async def get_user(
    username: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get user by username - PostgreSQL compatible"""
    try:
        # Use parameterized query compatible with both SQLite and PostgreSQL
        query = """
            SELECT id, username, email, first_name, last_name, 
                   is_active, is_verified, created_at, updated_at, last_login
            FROM users 
            WHERE username = %s AND is_active = %s
        """
        
        # PostgreSQL uses %s for parameters
        if db.db_type == 'postgresql':
            params = (username, True)
        else:
            # SQLite uses ? for parameters
            query = query.replace('%s', '?')
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
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "is_active": bool(user["is_active"]),
                "is_verified": bool(user["is_verified"]),
                "created_at": user["created_at"],
                "updated_at": user["updated_at"],
                "last_login": user["last_login"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving user: {str(e)}"
        )


@router.get("/")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = True,
    db: DatabaseManager = Depends(get_database)
):
    """List users with pagination - PostgreSQL compatible"""
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        offset = (page - 1) * page_size
        
        # Build query based on database type
        if db.db_type == 'postgresql':
            query = """
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at, updated_at
                FROM users
            """
            count_query = "SELECT COUNT(*) as total FROM users"
            params = []
            count_params = []
            
            if active_only:
                query += " WHERE is_active = %s"
                count_query += " WHERE is_active = %s"
                params.append(True)
                count_params.append(True)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            
        else:
            # SQLite
            query = """
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at, updated_at
                FROM users
            """
            count_query = "SELECT COUNT(*) as total FROM users"
            params = []
            count_params = []
            
            if active_only:
                query += " WHERE is_active = ?"
                count_query += " WHERE is_active = ?"
                params.append(1)
                count_params.append(1)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, offset])
        
        # Get users
        users = db.execute_query(query, params)
        
        # Get total count
        count_result = db.execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0
        
        # Convert boolean fields for consistency
        for user in users:
            user['is_active'] = bool(user['is_active'])
            user['is_verified'] = bool(user['is_verified'])
        
        return {
            "success": True,
            "data": users,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error listing users: {str(e)}"
        )
'''
    
    # Write the fixed users route
    users_file = Path("api/routes/users.py")
    users_file.write_text(users_route_content)
    logger.info("✅ Fixed users route for PostgreSQL compatibility")


def fix_balances_route():
    """Fix the balances route to work with PostgreSQL"""
    
    balances_route_content = '''"""
Balance management routes - PostgreSQL Compatible
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_balances(
    username: str,
    currency: str = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get balances for a user - PostgreSQL compatible"""
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


@router.get("/summary/{username}")
async def get_balance_summary(
    username: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get balance summary for a user - PostgreSQL compatible"""
    try:
        # Verify user exists
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
        
        # Get balance summary
        if db.db_type == 'postgresql':
            summary_query = """
                SELECT 
                    COUNT(*) as total_currencies,
                    COUNT(CASE WHEN ub.total_balance > 0 THEN 1 END) as currencies_with_balance,
                    COUNT(CASE WHEN c.is_fiat = true THEN 1 END) as fiat_currencies,
                    COUNT(CASE WHEN c.is_fiat = false THEN 1 END) as crypto_currencies
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = %s
            """
            params = (user_id,)
        else:
            summary_query = """
                SELECT 
                    COUNT(*) as total_currencies,
                    COUNT(CASE WHEN ub.total_balance > 0 THEN 1 END) as currencies_with_balance,
                    COUNT(CASE WHEN c.is_fiat = 1 THEN 1 END) as fiat_currencies,
                    COUNT(CASE WHEN c.is_fiat = 0 THEN 1 END) as crypto_currencies
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = ?
            """
            params = (user_id,)
        
        summary_result = db.execute_query(summary_query, params)
        summary = summary_result[0] if summary_result else {
            'total_currencies': 0,
            'currencies_with_balance': 0,
            'fiat_currencies': 0,
            'crypto_currencies': 0
        }
        
        return {
            "success": True,
            "data": {
                "user": username,
                "summary": summary
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balance summary: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving balance summary: {str(e)}"
        )
'''
    
    # Write the fixed balances route
    balances_file = Path("api/routes/balances.py")
    balances_file.write_text(balances_route_content)
    logger.info("✅ Fixed balances route for PostgreSQL compatibility")


def fix_transactions_route():
    """Fix the transactions route to work with PostgreSQL"""
    
    transactions_route_content = '''"""
Transaction management routes - PostgreSQL Compatible
"""

from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_transactions(
    username: str,
    transaction_type: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: DatabaseManager = Depends(get_database)
):
    """Get transactions for a user - PostgreSQL compatible"""
    try:
        # Validate pagination
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        # Verify user exists
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
        
        # Build transactions query
        if db.db_type == 'postgresql':
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       fee_amount, created_at, processed_at
                FROM transactions
                WHERE user_id = %s
            """
            params = [user_id]
            
            if transaction_type:
                query += " AND transaction_type = %s"
                params.append(transaction_type)
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, (page - 1) * page_size])
            
        else:
            # SQLite
            query = """
                SELECT id, transaction_type, status, amount, currency_code,
                       balance_before, balance_after, description, external_reference,
                       fee_amount, created_at, processed_at
                FROM transactions
                WHERE user_id = ?
            """
            params = [user_id]
            
            if transaction_type:
                query += " AND transaction_type = ?"
                params.append(transaction_type)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])
        
        transactions = db.execute_query(query, params)
        
        # Get total count for pagination
        if db.db_type == 'postgresql':
            count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = %s"
            count_params = [user_id]
            
            if transaction_type:
                count_query += " AND transaction_type = %s"
                count_params.append(transaction_type)
            
            if status:
                count_query += " AND status = %s"
                count_params.append(status)
                
        else:
            count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = ?"
            count_params = [user_id]
            
            if transaction_type:
                count_query += " AND transaction_type = ?"
                count_params.append(transaction_type)
            
            if status:
                count_query += " AND status = ?"
                count_params.append(status)
        
        count_result = db.execute_query(count_query, count_params)
        total = count_result[0]['total'] if count_result else 0
        
        return {
            "success": True,
            "data": transactions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
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
    
    # Write the fixed transactions route
    transactions_file = Path("api/routes/transactions.py")
    if transactions_file.exists():
        # Backup existing file
        backup_file = Path("api/routes/transactions.py.backup")
        import shutil
        shutil.copy(transactions_file, backup_file)
        logger.info(f"✅ Backed up existing transactions route to {backup_file}")
    
    transactions_file.write_text(transactions_route_content)
    logger.info("✅ Fixed transactions route for PostgreSQL compatibility")


def main():
    """Fix all API routes for PostgreSQL compatibility"""
    print("🔧 Fixing API Routes for PostgreSQL Compatibility")
    print("=" * 50)
    
    try:
        # Check if we're in the right directory
        if not Path("api/routes").exists():
            print("❌ Error: api/routes directory not found")
            print("Make sure you're in the fastapi_backend directory")
            return False
        
        # Fix all routes
        fix_users_route()
        fix_balances_route()
        fix_transactions_route()
        
        print("\n🎉 All API routes fixed for PostgreSQL compatibility!")
        print("\n📋 Changes made:")
        print("✅ Users route: Fixed parameter placeholders and boolean handling")
        print("✅ Balances route: Fixed SQL syntax for PostgreSQL")
        print("✅ Transactions route: Fixed parameter binding")
        print("\n🚀 Test your application:")
        print("1. python3 main.py")
        print("2. curl http://localhost:8000/api/v1/users/agent_1")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing routes: {e}")
        return False


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
