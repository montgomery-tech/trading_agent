#!/usr/bin/env python3
"""
Fix Balance Routes - Entity Access Control
Task 1: Update balance routes to enable entity-wide access for viewers and traders

SCRIPT: fix_balance_routes_entity_access.py

This script updates the balance routes to allow both viewers and traders 
to access balance data for any user within their assigned entity.
"""

import os
from pathlib import Path
from datetime import datetime

def create_backup(file_path):
    """Create backup of existing file"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        print(f"📁 Backup created: {backup_path}")
        return backup_path
    return None

def create_updated_balance_routes():
    """Create the updated balance routes with entity-wide access"""
    return '''"""
Balance management routes - With Entity-Wide Access Control
Updated to allow viewers and traders to access all balance data within their entity
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from api.dependencies import get_database
from api.database import DatabaseManager
from api.updated_auth_dependencies import (
    require_entity_any_access, 
    EntityAuthenticatedUser,
    get_user_accessible_entity_filter
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_balances(
    username: str,
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    currency: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get balances for a user within the current user's accessible entities.
    
    Both viewers and traders can access balance data for any user within their entity.
    Admins can access balance data for any user across all entities.
    """
    try:
        # First verify the target user exists and is active
        if db.db_type == 'postgresql':
            user_query = "SELECT id, entity_id FROM users WHERE username = %s AND is_active = %s"
            user_params = (username, True)
        else:
            user_query = "SELECT id, entity_id FROM users WHERE username = ? AND is_active = ?"
            user_params = (username, 1)

        user_results = db.execute_query(user_query, user_params)

        if not user_results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found or inactive"
            )

        target_user = user_results[0]
        user_id = target_user['id']
        target_entity_id = target_user.get('entity_id')

        # For non-admin users, verify the target user is within their accessible entities
        if current_user.role.value != 'admin':
            if not target_entity_id or not current_user.has_entity_access(target_entity_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. User '{username}' is not within your accessible entities"
                )

        # Build balances query with entity filtering
        if db.db_type == 'postgresql':
            query = """
                SELECT ub.id, ub.currency_code, ub.total_balance,
                       ub.available_balance, ub.locked_balance,
                       c.name as currency_name, c.symbol, c.is_fiat,
                       ub.created_at, ub.updated_at,
                       u.entity_id
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                JOIN users u ON ub.user_id = u.id
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
                       ub.created_at, ub.updated_at,
                       u.entity_id
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                JOIN users u ON ub.user_id = u.id
                WHERE ub.user_id = ?
            """
            params = [user_id]

            if currency:
                query += " AND ub.currency_code = ?"
                params.append(currency.upper())

        # Add entity filtering for non-admin users
        if current_user.role.value != 'admin':
            entity_filter, entity_params = await get_user_accessible_entity_filter(
                current_user, db, "u"
            )
            if entity_filter:
                query += f" AND {entity_filter}"
                params.extend(entity_params)

        query += " ORDER BY c.is_fiat DESC, ub.total_balance DESC"

        balances = db.execute_query(query, params)

        # Convert boolean fields for consistency
        for balance in balances:
            balance['is_fiat'] = bool(balance['is_fiat'])

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"accessed balances for user {username} in entity {target_entity_id}"
        )

        return {
            "success": True,
            "data": balances,
            "user": username,
            "entity_id": target_entity_id,
            "total_balances": len(balances),
            "access_info": {
                "viewer_role": current_user.role.value,
                "entity_access": "admin" if current_user.role.value == 'admin' else "entity_member"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balances for user {username}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving balances: {str(e)}"
        )


@router.get("/")
async def get_entity_balances_summary(
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    currency: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get balance summary for all users within the current user's accessible entities.
    
    This endpoint allows viewers and traders to see aggregate balance data 
    for their entire entity.
    """
    try:
        # Build entity-filtered summary query
        if db.db_type == 'postgresql':
            query = """
                SELECT 
                    u.username,
                    u.entity_id,
                    e.name as entity_name,
                    ub.currency_code,
                    c.name as currency_name,
                    c.symbol,
                    c.is_fiat,
                    ub.total_balance,
                    ub.available_balance,
                    ub.locked_balance,
                    ub.updated_at
                FROM user_balances ub
                JOIN users u ON ub.user_id = u.id
                JOIN entities e ON u.entity_id = e.id
                JOIN currencies c ON ub.currency_code = c.code
                WHERE u.is_active = %s
            """
            params = [True]

            if currency:
                query += " AND ub.currency_code = %s"
                params.append(currency.upper())
        else:
            # SQLite
            query = """
                SELECT 
                    u.username,
                    u.entity_id,
                    e.name as entity_name,
                    ub.currency_code,
                    c.name as currency_name,
                    c.symbol,
                    c.is_fiat,
                    ub.total_balance,
                    ub.available_balance,
                    ub.locked_balance,
                    ub.updated_at
                FROM user_balances ub
                JOIN users u ON ub.user_id = u.id
                JOIN entities e ON u.entity_id = e.id
                JOIN currencies c ON ub.currency_code = c.code
                WHERE u.is_active = ?
            """
            params = [1]

            if currency:
                query += " AND ub.currency_code = ?"
                params.append(currency.upper())

        # Add entity filtering for non-admin users
        if current_user.role.value != 'admin':
            entity_filter, entity_params = await get_user_accessible_entity_filter(
                current_user, db, "u"
            )
            if entity_filter:
                query += f" AND {entity_filter}"
                params.extend(entity_params)

        query += " ORDER BY e.name, u.username, c.is_fiat DESC, ub.total_balance DESC"

        balances = db.execute_query(query, params)

        # Convert boolean fields and group by entity
        entity_balances = {}
        for balance in balances:
            balance['is_fiat'] = bool(balance['is_fiat'])
            entity_id = balance['entity_id']
            
            if entity_id not in entity_balances:
                entity_balances[entity_id] = {
                    'entity_id': entity_id,
                    'entity_name': balance['entity_name'],
                    'users': {},
                    'total_users': 0,
                    'total_balances': 0
                }
            
            username = balance['username']
            if username not in entity_balances[entity_id]['users']:
                entity_balances[entity_id]['users'][username] = []
                entity_balances[entity_id]['total_users'] += 1
            
            entity_balances[entity_id]['users'][username].append({
                'currency_code': balance['currency_code'],
                'currency_name': balance['currency_name'],
                'symbol': balance['symbol'],
                'is_fiat': balance['is_fiat'],
                'total_balance': balance['total_balance'],
                'available_balance': balance['available_balance'],
                'locked_balance': balance['locked_balance'],
                'updated_at': balance['updated_at']
            })
            entity_balances[entity_id]['total_balances'] += 1

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"accessed entity balance summary"
        )

        return {
            "success": True,
            "data": list(entity_balances.values()),
            "total_entities": len(entity_balances),
            "access_info": {
                "viewer_role": current_user.role.value,
                "accessible_entities": current_user.accessible_entities,
                "entity_access": "admin" if current_user.role.value == 'admin' else "entity_member"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving entity balance summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving entity balance summary: {str(e)}"
        )


@router.get("/user/{username}/summary")
async def get_user_balance_summary(
    username: str,
    current_user: EntityAuthenticatedUser = Depends(require_entity_any_access()),
    db: DatabaseManager = Depends(get_database)
):
    """
    Get balance summary statistics for a specific user within accessible entities.
    
    Provides aggregate statistics like total currencies, fiat vs crypto breakdown, etc.
    """
    try:
        # First verify the target user exists and is within accessible entities
        if db.db_type == 'postgresql':
            user_query = "SELECT id, entity_id FROM users WHERE username = %s AND is_active = %s"
            user_params = (username, True)
        else:
            user_query = "SELECT id, entity_id FROM users WHERE username = ? AND is_active = ?"
            user_params = (username, 1)

        user_results = db.execute_query(user_query, user_params)

        if not user_results:
            raise HTTPException(
                status_code=404,
                detail=f"User '{username}' not found or inactive"
            )

        target_user = user_results[0]
        user_id = target_user['id']
        target_entity_id = target_user.get('entity_id')

        # Verify entity access for non-admin users
        if current_user.role.value != 'admin':
            if not target_entity_id or not current_user.has_entity_access(target_entity_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. User '{username}' is not within your accessible entities"
                )

        # Get balance summary statistics
        if db.db_type == 'postgresql':
            summary_query = """
                SELECT 
                    COUNT(DISTINCT ub.currency_code) as total_currencies,
                    COUNT(CASE WHEN ub.total_balance > 0 THEN 1 END) as currencies_with_balance,
                    COUNT(CASE WHEN c.is_fiat = true THEN 1 END) as fiat_currencies,
                    COUNT(CASE WHEN c.is_fiat = false THEN 1 END) as crypto_currencies,
                    COALESCE(SUM(CASE WHEN c.is_fiat = true THEN ub.total_balance ELSE 0 END), 0) as total_fiat_balance,
                    COALESCE(SUM(CASE WHEN c.is_fiat = false THEN ub.total_balance ELSE 0 END), 0) as total_crypto_balance
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = %s
            """
            params = (user_id,)
        else:
            summary_query = """
                SELECT 
                    COUNT(DISTINCT ub.currency_code) as total_currencies,
                    COUNT(CASE WHEN ub.total_balance > 0 THEN 1 END) as currencies_with_balance,
                    COUNT(CASE WHEN c.is_fiat = 1 THEN 1 END) as fiat_currencies,
                    COUNT(CASE WHEN c.is_fiat = 0 THEN 1 END) as crypto_currencies,
                    COALESCE(SUM(CASE WHEN c.is_fiat = 1 THEN ub.total_balance ELSE 0 END), 0) as total_fiat_balance,
                    COALESCE(SUM(CASE WHEN c.is_fiat = 0 THEN ub.total_balance ELSE 0 END), 0) as total_crypto_balance
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
            'crypto_currencies': 0,
            'total_fiat_balance': 0,
            'total_crypto_balance': 0
        }

        logger.info(
            f"User {current_user.username} (role: {current_user.role.value}) "
            f"accessed balance summary for user {username} in entity {target_entity_id}"
        )
        
        return {
            "success": True,
            "data": {
                "user": username,
                "entity_id": target_entity_id,
                "summary": summary,
                "access_info": {
                    "viewer_role": current_user.role.value,
                    "entity_access": "admin" if current_user.role.value == 'admin' else "entity_member"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balance summary for user {username}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving balance summary: {str(e)}"
        )
'''

def main():
    """Apply the balance routes entity access fix"""
    
    print("🚀 TASK 1: UPDATE BALANCE ROUTES - ENTITY-WIDE ACCESS")
    print("=" * 60)
    print()
    print("Updating balance routes to allow viewers and traders")
    print("to access balance data for any user within their entity.")
    print()
    
    # Ensure api/routes directory exists
    routes_dir = Path("api/routes")
    routes_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Ensured directory exists: {routes_dir}")
    
    # Target file path
    balance_routes_file = routes_dir / "balances.py"
    
    # Create backup if file exists
    if balance_routes_file.exists():
        backup_path = create_backup(str(balance_routes_file))
        print(f"✅ Existing file backed up")
    else:
        print("📝 Creating new balance routes file")
    
    # Write updated content
    updated_content = create_updated_balance_routes()
    
    with open(balance_routes_file, 'w') as f:
        f.write(updated_content)
    
    print(f"✅ Updated: {balance_routes_file}")
    print()
    print("🔍 KEY CHANGES MADE:")
    print("=" * 30)
    print("✅ Replaced require_resource_owner_or_admin with require_entity_any_access")
    print("✅ Added entity filtering for non-admin users")
    print("✅ Enhanced access logging with entity context")
    print("✅ Added entity balance summary endpoint")
    print("✅ Added user balance summary with entity verification")
    print("✅ Both viewers and traders can now access entity-wide balance data")
    print()
    print("🎯 EXPECTED BEHAVIOR:")
    print("=" * 25)
    print("• Viewers: READ access to all balance data within their entity")
    print("• Traders: READ access to all balance data within their entity")
    print("• Admins: READ access to all balance data across all entities")
    print("• Cross-entity access: BLOCKED for non-admin users")
    print()
    print("📋 NEXT STEPS:")
    print("=" * 20)
    print("1. Restart FastAPI server: python3 main.py")
    print("2. Test viewer access to entity balance data")
    print("3. Verify cross-entity access is blocked")
    print("4. Proceed to Task 2: Update Transaction Routes")
    print()
    print("🎉 TASK 1 COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
