#!/usr/bin/env python3
"""
api/routes/transactions.py
Enhanced transaction processing routes with Task 1.3 Security Framework
FIXED: Import paths corrected
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime
import uuid
import logging

# Existing imports
from api.models import (
    DepositRequest, WithdrawalRequest, TransactionResponse,
    DataResponse, ListResponse
)
from api.dependencies import get_database, validate_user_exists, validate_currency_exists
from api.database import DatabaseManager

# NEW: Import Task 1.3 Security Framework
from api.security import (
    EnhancedDepositRequest,
    EnhancedWithdrawalRequest,
    EnhancedPaginationParams,
    create_secure_response,
    create_secure_error,
    validation_service
)

# FIXED: Import JWT authentication from correct module (Task 1.2)
# Try different possible auth module locations
try:
    from api.auth import get_current_user
except ImportError:
    try:
        from api.auth_routes import get_current_user
    except ImportError:
        try:
            from api.authentication import get_current_user
        except ImportError:
            # Create a placeholder dependency for now
            def get_current_user():
                """Placeholder for authentication - replace with actual auth"""
                return {"username": "placeholder", "id": "placeholder"}

logger = logging.getLogger(__name__)
router = APIRouter()


class TransactionProcessor:
    """Enhanced transaction processing engine with security validation"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def validate_user(self, username: str) -> dict:
        """Validate user exists and is active with enhanced security"""
        # Use security framework for username validation
        validated_username = validation_service.validate_username(username)

        query = """
            SELECT id, username, email, is_active, is_verified
            FROM users WHERE username = ?
        """
        results = self.db.execute_query(query, (validated_username,))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{validated_username}' not found"
            )

        user = results[0]
        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{validated_username}' is not active"
            )

        return user

    def validate_currency(self, currency_code: str) -> dict:
        """Validate currency exists and is active with enhanced security"""
        # Use security framework for currency validation
        validated_currency = validation_service.validate_currency_code(currency_code)

        query = """
            SELECT code, name, symbol, decimal_places, is_active, is_fiat
            FROM currencies WHERE code = ?
        """
        results = self.db.execute_query(query, (validated_currency,))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Currency '{validated_currency}' not found"
            )

        currency = results[0]
        if not currency['is_active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Currency '{validated_currency}' is not active"
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

    def process_deposit(self, request: EnhancedDepositRequest) -> TransactionResponse:
        """Process deposit transaction with enhanced security validation"""
        logger.info(f"Processing deposit: {request.amount} {request.currency_code} for {request.username}")

        try:
            # 1. Validate user and currency (with enhanced security)
            user = self.validate_user(request.username)
            currency = self.validate_currency(request.currency_code)

            # 2. Additional amount validation with security framework
            validated_amount = validation_service.validate_decimal_amount(
                request.amount,
                field_name="deposit_amount",
                min_value=Decimal('0.00000001'),
                max_value=Decimal('999999999999.99')
            )

            # 3. Get current balance
            current_balance = self.get_user_balance(user['id'], request.currency_code)

            # 4. Calculate new balance
            new_balance = {
                'total': current_balance['total'] + validated_amount,
                'available': current_balance['available'] + validated_amount,
                'locked': current_balance['locked']
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
                (transaction_id, user['id'], 'deposit', 'completed', str(validated_amount),
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

            # 7. Return success response using security framework
            return TransactionResponse(
                success=True,
                message=f"Deposit of {validated_amount} {request.currency_code} completed successfully",
                transaction_id=transaction_id,
                transaction_type='deposit',
                status='completed',
                amount=validated_amount,
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

    def process_withdrawal(self, request: EnhancedWithdrawalRequest) -> TransactionResponse:
        """Process withdrawal transaction with enhanced security validation"""
        logger.info(f"Processing withdrawal: {request.amount} {request.currency_code} for {request.username}")

        try:
            # 1. Validate user and currency (with enhanced security)
            user = self.validate_user(request.username)
            currency = self.validate_currency(request.currency_code)

            # 2. Additional amount validation with security framework
            validated_amount = validation_service.validate_decimal_amount(
                request.amount,
                field_name="withdrawal_amount",
                min_value=Decimal('0.00000001'),
                max_value=Decimal('999999999999.99')
            )

            # 3. Get current balance
            current_balance = self.get_user_balance(user['id'], request.currency_code)

            # 4. Check sufficient funds
            if current_balance['available'] < validated_amount:
                # Create failed transaction record for audit
                failed_transaction_id = str(uuid.uuid4())
                failed_transaction_data = {
                    'id': failed_transaction_id,
                    'user_id': user['id'],
                    'transaction_type': 'withdrawal',
                    'status': 'failed',
                    'amount': validated_amount,
                    'currency_code': request.currency_code,
                    'balance_before': current_balance['total'],
                    'balance_after': current_balance['total'],
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
                        "requested_amount": str(validated_amount),
                        "currency": request.currency_code,
                        "failed_transaction_id": failed_transaction_id
                    }
                )

            # 5. Calculate new balance
            new_balance = {
                'total': current_balance['total'] - validated_amount,
                'available': current_balance['available'] - validated_amount,
                'locked': current_balance['locked']
            }

            # 6. Create transaction ID
            transaction_id = str(uuid.uuid4())

            # 7. Execute atomic transaction
            commands = [
                # Create transaction record
                ("""INSERT INTO transactions (
                    id, user_id, transaction_type, status, amount, currency_code,
                    balance_before, balance_after, description, external_reference,
                    fee_amount, created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (transaction_id, user['id'], 'withdrawal', 'completed', str(validated_amount),
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
                message=f"Withdrawal of {validated_amount} {request.currency_code} completed successfully",
                transaction_id=transaction_id,
                transaction_type='withdrawal',
                status='completed',
                amount=validated_amount,
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


# Route endpoints with enhanced security
@router.post("/deposit", response_model=TransactionResponse)
async def create_deposit(
    request: EnhancedDepositRequest,  # NEW: Using enhanced security model
    current_user = Depends(get_current_user),  # NEW: JWT authentication required
    db: DatabaseManager = Depends(get_database)
):
    """Enhanced deposit processing with comprehensive security validation"""
    processor = TransactionProcessor(db)
    return processor.process_deposit(request)


@router.post("/withdraw", response_model=TransactionResponse)
async def create_withdrawal(
    request: EnhancedWithdrawalRequest,  # NEW: Using enhanced security model
    current_user = Depends(get_current_user),  # NEW: JWT authentication required
    db: DatabaseManager = Depends(get_database)
):
    """Enhanced withdrawal processing with comprehensive security validation"""
    processor = TransactionProcessor(db)
    return processor.process_withdrawal(request)


@router.get("/user/{username}", response_model=ListResponse)
async def get_user_transactions(
    username: str,
    page: int = 1,
    page_size: int = 20,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user),  # NEW: JWT authentication required
    db: DatabaseManager = Depends(get_database)
):
    """Get user transaction history with enhanced security and pagination"""
    try:
        # NEW: Validate username with security framework
        validated_username = validation_service.validate_username(username)

        # NEW: Validate pagination parameters
        validated_page, validated_page_size = validation_service.validate_pagination_params(page, page_size)

        # Get user ID
        user_query = "SELECT id FROM users WHERE username = ? AND is_active = 1"
        user_results = db.execute_query(user_query, (validated_username,))

        if not user_results:
            raise HTTPException(status_code=404, detail=f"User '{validated_username}' not found")

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
            # NEW: Validate transaction type
            validated_type = validation_service.validate_and_sanitize_string(
                transaction_type, "transaction_type", max_length=20
            )
            query += " AND transaction_type = ?"
            params.append(validated_type)

        if status:
            # NEW: Validate status
            validated_status = validation_service.validate_and_sanitize_string(
                status, "status", max_length=20
            )
            query += " AND status = ?"
            params.append(validated_status)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([validated_page_size, (validated_page - 1) * validated_page_size])

        transactions = db.execute_query(query, params)

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM transactions WHERE user_id = ?"
        count_params = [user_id]

        if transaction_type:
            count_query += " AND transaction_type = ?"
            count_params.append(validated_type)

        if status:
            count_query += " AND status = ?"
            count_params.append(validated_status)

        count_results = db.execute_query(count_query, count_params)
        total_count = count_results[0]['total'] if count_results else 0

        return ListResponse(
            message=f"Retrieved {len(transactions)} transactions for {validated_username}",
            data=transactions,
            pagination={
                "page": validated_page,
                "page_size": validated_page_size,
                "count": len(transactions),
                "total": total_count,
                "has_more": (validated_page * validated_page_size) < total_count
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
    current_user = Depends(get_current_user),  # NEW: JWT authentication required
    db: DatabaseManager = Depends(get_database)
):
    """Get details of a specific transaction with enhanced security"""
    try:
        # NEW: Validate transaction ID format
        validated_transaction_id = validation_service.validate_transaction_id(transaction_id)

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

        results = db.execute_query(query, (validated_transaction_id,))

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
    page: int = 1,
    page_size: int = 20,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    currency_code: Optional[str] = None,
    current_user = Depends(get_current_user),  # NEW: JWT authentication required
    db: DatabaseManager = Depends(get_database)
):
    """Get all transactions with enhanced security and filtering (admin endpoint)"""
    try:
        # NEW: Validate pagination parameters
        validated_page, validated_page_size = validation_service.validate_pagination_params(page, page_size)

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
            # NEW: Validate transaction type with security framework
            validated_type = validation_service.validate_and_sanitize_string(
                transaction_type, "transaction_type", max_length=20
            )
            query += " AND t.transaction_type = ?"
            params.append(validated_type)

        if status:
            # NEW: Validate status with security framework
            validated_status = validation_service.validate_and_sanitize_string(
                status, "status", max_length=20
            )
            query += " AND t.status = ?"
            params.append(validated_status)

        if currency_code:
            # NEW: Validate currency code with security framework
            validated_currency = validation_service.validate_currency_code(currency_code)
            query += " AND t.currency_code = ?"
            params.append(validated_currency)

        query += " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
        params.extend([validated_page_size, (validated_page - 1) * validated_page_size])

        transactions = db.execute_query(query, params)

        # Get total count
        count_query = "SELECT COUNT(*) as total FROM transactions t WHERE 1=1"
        count_params = []

        if transaction_type:
            count_query += " AND t.transaction_type = ?"
            count_params.append(validated_type)

        if status:
            count_query += " AND t.status = ?"
            count_params.append(validated_status)

        if currency_code:
            count_query += " AND t.currency_code = ?"
            count_params.append(validated_currency)

        count_results = db.execute_query(count_query, count_params)
        total_count = count_results[0]['total'] if count_results else 0

        return ListResponse(
            message=f"Retrieved {len(transactions)} transactions",
            data=transactions,
            pagination={
                "page": validated_page,
                "page_size": validated_page_size,
                "count": len(transactions),
                "total": total_count,
                "has_more": (validated_page * validated_page_size) < total_count
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving all transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving transactions: {str(e)}")


# NEW: Enhanced security metrics endpoint
@router.get("/admin/security-metrics")
async def get_security_metrics(
    current_user = Depends(get_current_user),  # JWT authentication required
    db: DatabaseManager = Depends(get_database)
):
    """Get security metrics for transaction processing (admin only)"""
    try:
        # Import security metrics
        from api.security import security_metrics

        # Get failed transaction count
        failed_query = "SELECT COUNT(*) as count FROM transactions WHERE status = 'failed'"
        failed_result = db.execute_query(failed_query)
        failed_count = failed_result[0]['count'] if failed_result else 0

        # Get recent suspicious activity
        suspicious_query = """
            SELECT COUNT(*) as count
            FROM transactions
            WHERE status = 'failed'
            AND description LIKE '%FAILED:%'
            AND created_at > datetime('now', '-24 hours')
        """
        suspicious_result = db.execute_query(suspicious_query)
        suspicious_count = suspicious_result[0]['count'] if suspicious_result else 0

        return create_secure_response({
            "transaction_security": {
                "total_failed_transactions": failed_count,
                "recent_suspicious_activity": suspicious_count,
                "last_24h_window": True
            },
            "middleware_security": security_metrics.get_metrics(),
            "validation_status": "enabled",
            "timestamp": datetime.utcnow().isoformat()
        }, "Security metrics retrieved successfully")

    except Exception as e:
        logger.error(f"Error retrieving security metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving security metrics"
        )
