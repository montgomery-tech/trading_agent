#!/bin/bash

# Complete Modular FastAPI Setup Script
# This script creates all the files needed for the modular FastAPI structure

set -e

echo "🚀 Setting up Modular FastAPI Structure..."

# Create the structure script first
cat > create_structure.py << 'EOF'
import os
from pathlib import Path

def create_files():
    # Get the current directory
    base_dir = Path(".")
    
    # Ensure directories exist
    (base_dir / "api" / "routes").mkdir(parents=True, exist_ok=True)
    
    print("✅ Created directory structure")

if __name__ == "__main__":
    create_files()
EOF

python3 create_structure.py
rm create_structure.py

# Create api/routes/transactions.py
cat > api/routes/transactions.py << 'EOF'
#!/usr/bin/env python3
"""
api/routes/transactions.py
Enhanced transaction processing routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime
import uuid
import logging

from api.models import (
    DepositRequest, WithdrawalRequest, TransactionResponse,
    DataResponse, ListResponse
)
from api.dependencies import get_database, validate_user_exists, validate_currency_exists
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()


class TransactionProcessor:
    """Enhanced transaction processing engine"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        
    def validate_user(self, username: str) -> dict:
        """Validate user exists and is active"""
        query = """
            SELECT id, username, email, is_active, is_verified
            FROM users WHERE username = ?
        """
        results = self.db.execute_query(query, (username,))
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        
        user = results[0]
        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{username}' is not active"
            )
        
        return user
    
    def validate_currency(self, currency_code: str) -> dict:
        """Validate currency exists and is active"""
        query = """
            SELECT code, name, symbol, decimal_places, is_active, is_fiat
            FROM currencies WHERE code = ?
        """
        results = self.db.execute_query(query, (currency_code,))
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Currency '{currency_code}' not found"
            )
        
        currency = results[0]
        if not currency['is_active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Currency '{currency_code}' is not active"
            )
        
        return currency
    
    def get_user_balance(self, user_id: str, currency_code: str) -> dict:
        """Get current user balance for currency"""
        query = """
            SELECT total_balance, available_balance, locked_balance
            FROM user_balances 
            WHERE user_id = ? AND currency_code = ?
        """
        results = self.db.execute_query(query, (user_id, currency_code))
        
        if results:
            balance = results[0]
            return {
                'total': Decimal(str(balance['total_balance'])),
                'available': Decimal(str(balance['available_balance'])),
                'locked': Decimal(str(balance['locked_balance']))
            }
        else:
            return {
                'total': Decimal('0'),
                'available': Decimal('0'),
                'locked': Decimal('0')
            }
    
    def process_deposit(self, request: DepositRequest) -> TransactionResponse:
        """Process deposit transaction with full validation and audit trail"""
        logger.info(f"Processing deposit: {request.amount} {request.currency_code} for {request.username}")
        
        try:
            # 1. Validate user and currency
            user = self.validate_user(request.username)
            currency = self.validate_currency(request.currency_code)
            
            # 2. Get current balance
            current_balance = self.get_user_balance(user['id'], request.currency_code)
            
            # 3. Calculate new balance
            new_balance = {
                'total': current_balance['total'] + request.amount,
                'available': current_balance['available'] + request.amount,  # All deposits are available
                'locked': current_balance['locked']  # Locked balance unchanged
            }
            
            # 4. Create transaction ID
            transaction_id = str(uuid.uuid4())
            
            # 5. Execute atomic transaction
            commands = [
                # Create transaction record
                ("""INSERT INTO transactions (
                    id, user_id, transaction_type, status, amount, currency_code,
                    balance_before, balance_after, description, external_reference,
                    fee_amount, created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (transaction_id, user['id'], 'deposit', 'completed', str(request.amount),
                 request.currency_code, str(current_balance['total']), str(new_balance['total']),
                 request.description, request.external_reference, '0'))
            ]
            
            # Add balance update/create command
            check_balance = self.db.execute_query(
                "SELECT id FROM user_balances WHERE user_id = ? AND currency_code = ?",
                (user['id'], request.currency_code)
            )
            
            if check_balance:
                commands.append((
                    """UPDATE user_balances 
                       SET total_balance = ?, available_balance = ?, locked_balance = ?, 
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ? AND currency_code = ?""",
                    (str(new_balance['total']), str(new_balance['available']), 
                     str(new_balance['locked']), user['id'], request.currency_code)
                ))
            else:
                balance_id = str(uuid.uuid4())
                commands.append((
                    """INSERT INTO user_balances (id, user_id, currency_code, total_balance, 
                                                available_balance, locked_balance)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (balance_id, user['id'], request.currency_code,
                     str(new_balance['total']), str(new_balance['available']), 
                     str(new_balance['locked']))
                ))
            
            # Execute all commands atomically
            self.db.execute_transaction(commands)
            
            logger.info(f"Deposit completed: {transaction_id}")
            
            # Return success response
            return TransactionResponse(
                success=True,
                message=f"Deposit of {request.amount} {request.currency_code} completed successfully",
                transaction_id=transaction_id,
                transaction_type='deposit',
                status='completed',
                amount=request.amount,
                currency_code=request.currency_code,
                balance_before=current_balance['total'],
                balance_after=new_balance['total'],
                description=request.description,
                external_reference=request.external_reference,
                created_at=datetime.utcnow(),
                processed_at=datetime.utcnow()
            )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in deposit processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the deposit"
            )


# Route endpoints
@router.post("/deposit", response_model=TransactionResponse)
async def create_deposit(
    request: DepositRequest,
    db: DatabaseManager = Depends(get_database)
):
    """Enhanced deposit processing with comprehensive validation"""
    processor = TransactionProcessor(db)
    return processor.process_deposit(request)


@router.get("/user/{username}")
async def get_user_transactions(
    username: str,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseManager = Depends(get_database)
):
    """Get user transaction history"""
    try:
        # Get user ID
        user_query = "SELECT id FROM users WHERE username = ? AND is_active = 1"
        user_results = db.execute_query(user_query, (username,))
        
        if not user_results:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        user_id = user_results[0]['id']
        
        # Get transactions
        query = """
            SELECT id, transaction_type, status, amount, currency_code,
                   balance_before, balance_after, description, external_reference,
                   created_at, processed_at
            FROM transactions 
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """
        
        transactions = db.execute_query(query, (user_id, limit, offset))
        
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
        raise HTTPException(status_code=500, detail=f"Error retrieving transactions: {str(e)}")
EOF

# Create api/routes/balances.py
cat > api/routes/balances.py << 'EOF'
"""
Balance management routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from api.dependencies import get_database
from api.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{username}")
async def get_user_balances(
    username: str,
    currency: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get balances for a specific user"""
    try:
        # Get user ID
        user_query = "SELECT id FROM users WHERE username = ? AND is_active = 1"
        user_results = db.execute_query(user_query, (username,))
        
        if not user_results:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        user_id = user_results[0]['id']
        
        # Build balance query
        query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, 
                   ub.locked_balance, ub.updated_at, c.name, c.symbol, c.is_fiat
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
        
        return {
            "success": True,
            "data": balances
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving balances: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving balances: {str(e)}")
EOF

# Create api/routes/users.py
cat > api/routes/users.py << 'EOF'
"""
User management routes
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
    """Get user by username"""
    try:
        query = """
            SELECT id, username, email, first_name, last_name, 
                   is_active, is_verified, created_at, updated_at, last_login
            FROM users 
            WHERE username = ?
        """
        
        results = db.execute_query(query, (username,))
        
        if not results:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        return {
            "success": True,
            "data": results[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user: {str(e)}")
EOF

# Create api/routes/currencies.py
cat > api/routes/currencies.py << 'EOF'
"""
Currency management routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from api.dependencies import get_database
from api.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_currencies(
    active_only: bool = True,
    db: DatabaseManager = Depends(get_database)
):
    """Get list of available currencies"""
    try:
        query = "SELECT code, name, symbol, decimal_places, is_fiat, is_active FROM currencies"
        params = []
        
        if active_only:
            query += " WHERE is_active = 1"
        
        query += " ORDER BY is_fiat DESC, code"
        
        currencies = db.execute_query(query, params)
        
        return {
            "success": True,
            "data": currencies
        }
        
    except Exception as e:
        logger.error(f"Error retrieving currencies: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving currencies: {str(e)}")
EOF

echo "✅ Created all route files"

# Copy the artifacts content to actual files (you'll need to copy these manually)
echo ""
echo "📋 MANUAL STEPS NEEDED:"
echo "Copy the following artifact contents to these files:"
echo ""
echo "1. Copy 'modular_fastapi_structure' artifact content to:"
echo "   - api/config.py"
echo "   - api/models.py" 
echo "   - api/database.py"
echo "   - api/dependencies.py"
echo "   - new_main.py"
echo ""
echo "2. Files already created by this script:"
echo "   - ✅ api/routes/transactions.py"
echo "   - ✅ api/routes/balances.py"
echo "   - ✅ api/routes/users.py"
echo "   - ✅ api/routes/currencies.py"
echo ""
echo "🚀 After copying, run:"
echo "   python3 new_main.py"
echo ""
echo "📚 Your current working main.py is preserved"
echo "   The new modular version is in new_main.py"
