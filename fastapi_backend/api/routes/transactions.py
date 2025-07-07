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
from typing import Optional
from api.models import (
    DepositRequest, WithdrawalRequest, TransactionResponse,
    DataResponse, ListResponse
)
from api.dependencies import get_database, validate_user_exists, validate_currency_exists
from api.database import DatabaseManager
from typing import Optional
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

    def create_balance_snapshot(self, user_id: str, currency_code: str,
                              balance_data: dict, transaction_id: str):
        """Create balance snapshot for audit trail"""
        snapshot_id = str(uuid.uuid4())

        command = """
            INSERT INTO balance_snapshots (
                id, user_id, currency_code, total_balance, available_balance,
                locked_balance, snapshot_type, triggered_by_transaction_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db.execute_command(command, (
            snapshot_id, user_id, currency_code,
            str(balance_data['total']), str(balance_data['available']),
            str(balance_data['locked']), 'transaction', transaction_id
        ))

    def update_user_balance(self, user_id: str, currency_code: str, new_balance: dict) -> bool:
        """Update or create user balance"""
        # Check if balance exists
        check_query = "SELECT id FROM user_balances WHERE user_id = ? AND currency_code = ?"
        existing = self.db.execute_query(check_query, (user_id, currency_code))

        if existing:
            # Update existing balance
            command = """
                UPDATE user_balances
                SET total_balance = ?, available_balance = ?, locked_balance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND currency_code = ?
            """
            params = (
                str(new_balance['total']), str(new_balance['available']),
                str(new_balance['locked']), user_id, currency_code
            )
        else:
            # Create new balance
            balance_id = str(uuid.uuid4())
            command = """
                INSERT INTO user_balances (id, user_id, currency_code, total_balance,
                                         available_balance, locked_balance)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                balance_id, user_id, currency_code,
                str(new_balance['total']), str(new_balance['available']),
                str(new_balance['locked'])
            )

        self.db.execute_command(command, params)
        return True

    def create_transaction_record(self, transaction_data: dict) -> str:
        """Create transaction record"""
        command = """
            INSERT INTO transactions (
                id, user_id, transaction_type, status, amount, currency_code,
                balance_before, balance_after, description, external_reference,
                fee_amount, fee_currency_code, created_at, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """

        self.db.execute_command(command, (
            transaction_data['id'],
            transaction_data['user_id'],
            transaction_data['transaction_type'],
            transaction_data['status'],
            str(transaction_data['amount']),
            transaction_data['currency_code'],
            str(transaction_data['balance_before']),
            str(transaction_data['balance_after']),
            transaction_data.get('description'),
            transaction_data.get('external_reference'),
            str(transaction_data.get('fee_amount', Decimal('0'))),
            transaction_data.get('fee_currency_code')
        ))

        return transaction_data['id']

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

            # 5. Prepare transaction data
            transaction_data = {
                'id': transaction_id,
                'user_id': user['id'],
                'transaction_type': 'deposit',
                'status': 'completed',
                'amount': request.amount,
                'currency_code': request.currency_code,
                'balance_before': current_balance['total'],
                'balance_after': new_balance['total'],
                'description': request.description,
                'external_reference': request.external_reference,
                'fee_amount': Decimal('0'),  # No fees on deposits
                'fee_currency_code': None
            }

            # 6. Execute atomic transaction
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

            # Add balance snapshot
            snapshot_id = str(uuid.uuid4())
            commands.append((
                """INSERT INTO balance_snapshots (
                    id, user_id, currency_code, total_balance, available_balance,
                    locked_balance, snapshot_type, triggered_by_transaction_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (snapshot_id, user['id'], request.currency_code, str(new_balance['total']),
                 str(new_balance['available']), str(new_balance['locked']),
                 'transaction', transaction_id)
            ))

            # Execute all commands atomically
            self.db.execute_transaction(commands)

            logger.info(f"Deposit completed: {transaction_id}")

            # 7. Return success response
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
            # Re-raise HTTP exceptions (validation errors)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in deposit processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the deposit"
            )

    def process_withdrawal(self, request: WithdrawalRequest) -> TransactionResponse:
        """Process withdrawal transaction with comprehensive validation"""
        logger.info(f"Processing withdrawal: {request.amount} {request.currency_code} for {request.username}")

        try:
            # 1. Validate user and currency
            user = self.validate_user(request.username)
            currency = self.validate_currency(request.currency_code)

            # 2. Get current balance
            current_balance = self.get_user_balance(user['id'], request.currency_code)

            # 3. Check sufficient funds
            if current_balance['available'] < request.amount:
                # Create failed transaction record for audit
                failed_transaction_id = str(uuid.uuid4())
                failed_transaction_data = {
                    'id': failed_transaction_id,
                    'user_id': user['id'],
                    'transaction_type': 'withdrawal',
                    'status': 'failed',
                    'amount': request.amount,
                    'currency_code': request.currency_code,
                    'balance_before': current_balance['total'],
                    'balance_after': current_balance['total'],  # No change on failure
                    'description': f"FAILED: {request.description or 'Withdrawal'} (Insufficient funds)",
                    'external_reference': request.external_reference,
                    'fee_amount': Decimal('0'),
                    'fee_currency_code': None
                }

                self.create_transaction_record(failed_transaction_data)

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Insufficient funds",
                        "available_balance": str(current_balance['available']),
                        "requested_amount": str(request.amount),
                        "currency": request.currency_code,
                        "failed_transaction_id": failed_transaction_id
                    }
                )

            # 4. Calculate new balance
            new_balance = {
                'total': current_balance['total'] - request.amount,
                'available': current_balance['available'] - request.amount,
                'locked': current_balance['locked']  # Locked balance unchanged
            }

            # 5. Create transaction ID
            transaction_id = str(uuid.uuid4())

            # 6. Execute atomic transaction
            commands = [
                # Create transaction record
                ("""INSERT INTO transactions (
                    id, user_id, transaction_type, status, amount, currency_code,
                    balance_before, balance_after, description, external_reference,
                    fee_amount, created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (transaction_id, user['id'], 'withdrawal', 'completed', str(request.amount),
                 request.currency_code, str(current_balance['total']), str(new_balance['total']),
                 request.description, request.external_reference, '0')),

                # Update balance
                ("""UPDATE user_balances
                   SET total_balance = ?, available_balance = ?, locked_balance = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND currency_code = ?""",
                (str(new_balance['total']), str(new_balance['available']),
                 str(new_balance['locked']), user['id'], request.currency_code))
            ]

            # Add balance snapshot
            snapshot_id = str(uuid.uuid4())
            commands.append((
                """INSERT INTO balance_snapshots (
                    id, user_id, currency_code, total_balance, available_balance,
                    locked_balance, snapshot_type, triggered_by_transaction_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (snapshot_id, user['id'], request.currency_code, str(new_balance['total']),
                 str(new_balance['available']), str(new_balance['locked']),
                 'transaction', transaction_id)
            ))

            # Execute all commands atomically
            self.db.execute_transaction(commands)

            logger.info(f"Withdrawal completed: {transaction_id}")

            # 8. Return success response
            return TransactionResponse(
                success=True,
                message=f"Withdrawal of {request.amount} {request.currency_code} completed successfully",
                transaction_id=transaction_id,
                transaction_type='withdrawal',
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
            # Re-raise HTTP exceptions (validation errors)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in withdrawal processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the withdrawal"
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


@router.post("/withdraw", response_model=TransactionResponse)
async def create_withdrawal(
    request: WithdrawalRequest,
    db: DatabaseManager = Depends(get_database)
):
    """Enhanced withdrawal processing with comprehensive validation"""
    processor = TransactionProcessor(db)
    return processor.process_withdrawal(request)


@router.get("/user/{username}", response_model=ListResponse)
async def get_user_transactions(
    username: str,
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get user transaction history with filtering"""
    try:
        # Validate parameters
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 10
        if offset < 0:
            offset = 0

        # Get user ID
        user_query = "SELECT id FROM users WHERE username = ? AND is_active = 1"
        user_results = db.execute_query(user_query, (username,))

        if not user_results:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")

        user_id = user_results[0]['id']

        # Build query with filters
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
        params.extend([limit, offset])

        transactions = db.execute_query(query, params)

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = ?"
        count_params = [user_id]

        if transaction_type:
            count_query += " AND transaction_type = ?"
            count_params.append(transaction_type)

        if status:
            count_query += " AND status = ?"
            count_params.append(status)

        count_results = db.execute_query(count_query, count_params)
        total_count = count_results[0]['total'] if count_results else 0

        return ListResponse(
            message=f"Retrieved {len(transactions)} transactions for {username}",
            data=transactions,
            pagination={
                "limit": limit,
                "offset": offset,
                "count": len(transactions),
                "total": total_count,
                "has_more": offset + len(transactions) < total_count
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving transactions: {str(e)}")


@router.get("/{transaction_id}", response_model=DataResponse)
async def get_transaction_details(
    transaction_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get details of a specific transaction"""
    try:
        query = """
            SELECT t.id, t.transaction_type, t.status, t.amount, t.currency_code,
                   t.balance_before, t.balance_after, t.description, t.external_reference,
                   t.fee_amount, t.fee_currency_code, t.created_at, t.processed_at,
                   u.username, u.email, c.name as currency_name, c.symbol as currency_symbol
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN currencies c ON t.currency_code = c.code
            WHERE t.id = ?
        """

        results = db.execute_query(query, (transaction_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return DataResponse(
            message="Transaction details retrieved successfully",
            data=results[0]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving transaction: {str(e)}")


@router.get("/", response_model=ListResponse)
async def get_all_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    currency_code: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """Get all transactions with filtering (admin endpoint)"""
    try:
        # Validate parameters
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 10
        if offset < 0:
            offset = 0

        # Build query with filters
        query = """
            SELECT t.id, t.transaction_type, t.status, t.amount, t.currency_code,
                   t.balance_before, t.balance_after, t.description, t.external_reference,
                   t.fee_amount, t.created_at, t.processed_at, u.username
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            WHERE 1=1
        """
        params = []

        if transaction_type:
            query += " AND t.transaction_type = ?"
            params.append(transaction_type)

        if status:
            query += " AND t.status = ?"
            params.append(status)

        if currency_code:
            query += " AND t.currency_code = ?"
            params.append(currency_code.upper())

        query += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        transactions = db.execute_query(query, params)

        return ListResponse(
            message=f"Retrieved {len(transactions)} transactions",
            data=transactions,
            pagination={
                "limit": limit,
                "offset": offset,
                "count": len(transactions)
            }
        )

    except Exception as e:
        logger.error(f"Error retrieving all transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving transactions: {str(e)}")
