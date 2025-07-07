#!/usr/bin/env python3
"""
api/services/trade_service.py
Core trading service for executing trades with proper balance management
"""

import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from contextlib import contextmanager

from fastapi import HTTPException, status
from api.database import DatabaseManager
from api.models import TradeRequest, TradeResponse, TradingSide, TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


class TradeService:
    """
    Core trading service that handles trade execution with proper balance management.

    This service provides atomic trade execution with the following features:
    - Balance validation and locking
    - Fee calculation and processing
    - Transaction record creation
    - Atomic database operations
    - Comprehensive error handling
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.default_fee_rate = Decimal("0.0025")  # 0.25% default trading fee

    @contextmanager
    def atomic_transaction(self):
        """Context manager for atomic database transactions"""
        try:
            # Start transaction
            self.db.connection.execute("BEGIN")
            yield
            # Commit transaction
            self.db.connection.commit()
        except Exception as e:
            # Rollback transaction on error
            self.db.connection.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise

    def validate_and_get_user(self, username: str) -> Dict[str, Any]:
        """
        Validate user exists and is active

        Args:
            username: Username to validate

        Returns:
            User data dictionary

        Raises:
            HTTPException: If user not found or not active
        """
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

    def validate_and_get_trading_pair(self, symbol: str) -> Dict[str, Any]:
        """
        Validate trading pair exists and is active

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')

        Returns:
            Trading pair data dictionary

        Raises:
            HTTPException: If trading pair not found or not active
        """
        query = """
            SELECT tp.id, tp.base_currency, tp.quote_currency, tp.symbol,
                   tp.min_trade_amount, tp.max_trade_amount, tp.price_precision,
                   tp.amount_precision, tp.is_active
            FROM trading_pairs tp
            WHERE tp.symbol = ? AND tp.is_active = 1
        """
        results = self.db.execute_query(query, (symbol.upper(),))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active trading pair '{symbol}' not found"
            )

        return results[0]

    def get_user_balance(self, user_id: str, currency_code: str) -> Dict[str, Any]:
        """
        Get user balance for a specific currency

        Args:
            user_id: User ID
            currency_code: Currency code

        Returns:
            Balance data dictionary

        Raises:
            HTTPException: If balance not found
        """
        query = """
            SELECT user_id, currency_code, total_balance, available_balance, locked_balance
            FROM user_balances
            WHERE user_id = ? AND currency_code = ?
        """
        results = self.db.execute_query(query, (user_id, currency_code))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Balance for {currency_code} not found for user"
            )

        return results[0]

    def calculate_trade_amounts(self, trade_request: TradeRequest, current_price: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Calculate trade amounts including fees

        Args:
            trade_request: Trade request data
            current_price: Current market price

        Returns:
            Tuple of (total_value, fee_amount, net_amount)
        """
        amount = trade_request.amount
        price = trade_request.price or current_price

        # Calculate total value
        total_value = amount * price

        # Calculate fee (percentage of total value)
        fee_amount = total_value * self.default_fee_rate
        fee_amount = fee_amount.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

        # Net amount depends on trade side
        if trade_request.side == TradingSide.BUY:
            # For buy orders, user pays total_value + fee in quote currency
            net_amount = total_value + fee_amount
        else:
            # For sell orders, user receives total_value - fee in quote currency
            net_amount = total_value - fee_amount

        return total_value, fee_amount, net_amount

    def get_current_price(self, symbol: str) -> Decimal:
        """
        Get current market price for a trading pair

        Note: This is a simplified implementation. In a real system, this would
        connect to a price feed or exchange API.

        Args:
            symbol: Trading pair symbol

        Returns:
            Current price as Decimal
        """
        # Simplified price simulation - in production, this would fetch from a price feed
        price_map = {
            'BTC/USD': Decimal('65000.00'),
            'ETH/USD': Decimal('3500.00'),
            'ETH/BTC': Decimal('0.0538'),
            'LTC/USD': Decimal('95.00'),
            'ADA/USD': Decimal('0.45'),
            'SOL/USD': Decimal('180.00')
        }

        base_price = price_map.get(symbol.upper(), Decimal('1.00'))

        # Add small random variation (±1%)
        import random
        variation = Decimal(str(random.uniform(0.99, 1.01)))
        current_price = base_price * variation

        return current_price.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

    def validate_trade_constraints(self, trade_request: TradeRequest, trading_pair: Dict[str, Any]) -> None:
        """
        Validate trade against trading pair constraints

        Args:
            trade_request: Trade request data
            trading_pair: Trading pair data

        Raises:
            HTTPException: If trade violates constraints
        """
        amount = trade_request.amount

        # Check minimum trade amount
        if trading_pair['min_trade_amount'] and amount < trading_pair['min_trade_amount']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trade amount {amount} is below minimum {trading_pair['min_trade_amount']}"
            )

        # Check maximum trade amount
        if trading_pair['max_trade_amount'] and amount > trading_pair['max_trade_amount']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trade amount {amount} exceeds maximum {trading_pair['max_trade_amount']}"
            )

    def validate_sufficient_balance(self, user_id: str, currency_code: str, required_amount: Decimal) -> Dict[str, Any]:
        """
        Validate user has sufficient balance for trade

        Args:
            user_id: User ID
            currency_code: Currency code
            required_amount: Required amount for trade

        Returns:
            Balance data dictionary

        Raises:
            HTTPException: If insufficient balance
        """
        balance = self.get_user_balance(user_id, currency_code)
        available_balance = Decimal(str(balance['available_balance']))

        if available_balance < required_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {currency_code} balance. Required: {required_amount}, Available: {available_balance}"
            )

        return balance

    def create_transaction_record(self, user_id: str, transaction_type: TransactionType,
                                amount: Decimal, currency_code: str,
                                balance_before: Decimal, balance_after: Decimal,
                                description: str, fee_amount: Decimal = None,
                                fee_currency: str = None, related_transaction_id: str = None) -> str:
        """
        Create a transaction record in the database

        Args:
            user_id: User ID
            transaction_type: Type of transaction
            amount: Transaction amount
            currency_code: Currency code
            balance_before: Balance before transaction
            balance_after: Balance after transaction
            description: Transaction description
            fee_amount: Optional fee amount
            fee_currency: Optional fee currency
            related_transaction_id: Optional related transaction ID

        Returns:
            Transaction ID
        """
        transaction_id = str(uuid.uuid4())

        query = """
            INSERT INTO transactions (
                id, user_id, transaction_type, status, amount, currency_code,
                fee_amount, fee_currency_code, balance_before, balance_after,
                description, related_transaction_id, created_at, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        now = datetime.utcnow()
        params = (
            transaction_id, user_id, transaction_type.value, TransactionStatus.COMPLETED.value,
            float(amount), currency_code, float(fee_amount) if fee_amount else None,
            fee_currency, float(balance_before), float(balance_after),
            description, related_transaction_id, now, now
        )

        self.db.execute_query(query, params)
        return transaction_id

    def update_balance(self, user_id: str, currency_code: str,
                      balance_change: Decimal, is_debit: bool = True) -> Tuple[Decimal, Decimal]:
        """
        Update user balance atomically

        Args:
            user_id: User ID
            currency_code: Currency code
            balance_change: Amount to change balance by
            is_debit: True for debit (subtract), False for credit (add)

        Returns:
            Tuple of (balance_before, balance_after)
        """
        # Get current balance
        balance = self.get_user_balance(user_id, currency_code)
        balance_before = Decimal(str(balance['available_balance']))

        # Calculate new balance
        if is_debit:
            balance_after = balance_before - balance_change
        else:
            balance_after = balance_before + balance_change

        # Update balance
        query = """
            UPDATE user_balances
            SET available_balance = ?, total_balance = ?, updated_at = ?
            WHERE user_id = ? AND currency_code = ?
        """

        now = datetime.utcnow()
        params = (float(balance_after), float(balance_after), now, user_id, currency_code)
        self.db.execute_query(query, params)

        return balance_before, balance_after

    def create_trade_record(self, user_id: str, trading_pair_id: str, side: TradingSide,
                           amount: Decimal, price: Decimal, total_value: Decimal,
                           fee_amount: Decimal, fee_currency: str,
                           base_transaction_id: str, quote_transaction_id: str,
                           fee_transaction_id: str = None) -> str:
        """
        Create a trade record in the database

        Args:
            user_id: User ID
            trading_pair_id: Trading pair ID
            side: Trade side (buy/sell)
            amount: Trade amount
            price: Trade price
            total_value: Total trade value
            fee_amount: Fee amount
            fee_currency: Fee currency
            base_transaction_id: Base currency transaction ID
            quote_transaction_id: Quote currency transaction ID
            fee_transaction_id: Optional fee transaction ID

        Returns:
            Trade ID
        """
        trade_id = str(uuid.uuid4())

        query = """
            INSERT INTO trades (
                id, user_id, trading_pair_id, side, amount, price, total_value,
                fee_amount, fee_currency_code, status, executed_at,
                base_transaction_id, quote_transaction_id, fee_transaction_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        now = datetime.utcnow()
        params = (
            trade_id, user_id, trading_pair_id, side.value, float(amount),
            float(price), float(total_value), float(fee_amount), fee_currency,
            'completed', now, base_transaction_id, quote_transaction_id,
            fee_transaction_id, now, now
        )

        self.db.execute_query(query, params)
        return trade_id

    async def execute_trade(self, trade_request: TradeRequest) -> TradeResponse:
        """
        Execute a trade with full atomic transaction management

        Args:
            trade_request: Trade request data

        Returns:
            Trade response with execution details

        Raises:
            HTTPException: If trade execution fails
        """
        try:
            # Validate user
            user = self.validate_and_get_user(trade_request.username)
            user_id = user['id']

            # Validate trading pair
            trading_pair = self.validate_and_get_trading_pair(trade_request.symbol)
            base_currency = trading_pair['base_currency']
            quote_currency = trading_pair['quote_currency']

            # Validate trade constraints
            self.validate_trade_constraints(trade_request, trading_pair)

            # Get current price
            current_price = self.get_current_price(trade_request.symbol)
            if trade_request.price:
                # For limit orders, use specified price
                execution_price = trade_request.price
            else:
                # For market orders, use current price
                execution_price = current_price

            # Calculate trade amounts
            total_value, fee_amount, net_amount = self.calculate_trade_amounts(trade_request, execution_price)

            # Execute trade atomically
            with self.atomic_transaction():
                if trade_request.side == TradingSide.BUY:
                    # BUY: User pays quote currency, receives base currency

                    # Validate sufficient quote currency balance
                    quote_balance = self.validate_sufficient_balance(user_id, quote_currency, net_amount)

                    # Update balances
                    quote_balance_before, quote_balance_after = self.update_balance(
                        user_id, quote_currency, net_amount, is_debit=True
                    )

                    base_balance_before, base_balance_after = self.update_balance(
                        user_id, base_currency, trade_request.amount, is_debit=False
                    )

                    # Create transaction records
                    quote_transaction_id = self.create_transaction_record(
                        user_id, TransactionType.TRADE_BUY, net_amount, quote_currency,
                        quote_balance_before, quote_balance_after,
                        f"Buy {trade_request.amount} {base_currency} at {execution_price}",
                        fee_amount, quote_currency
                    )

                    base_transaction_id = self.create_transaction_record(
                        user_id, TransactionType.TRADE_BUY, trade_request.amount, base_currency,
                        base_balance_before, base_balance_after,
                        f"Receive {trade_request.amount} {base_currency} from buy order",
                        related_transaction_id=quote_transaction_id
                    )

                else:
                    # SELL: User pays base currency, receives quote currency

                    # Validate sufficient base currency balance
                    base_balance = self.validate_sufficient_balance(user_id, base_currency, trade_request.amount)

                    # Update balances
                    base_balance_before, base_balance_after = self.update_balance(
                        user_id, base_currency, trade_request.amount, is_debit=True
                    )

                    quote_balance_before, quote_balance_after = self.update_balance(
                        user_id, quote_currency, net_amount, is_debit=False
                    )

                    # Create transaction records
                    base_transaction_id = self.create_transaction_record(
                        user_id, TransactionType.TRADE_SELL, trade_request.amount, base_currency,
                        base_balance_before, base_balance_after,
                        f"Sell {trade_request.amount} {base_currency} at {execution_price}"
                    )

                    quote_transaction_id = self.create_transaction_record(
                        user_id, TransactionType.TRADE_SELL, net_amount, quote_currency,
                        quote_balance_before, quote_balance_after,
                        f"Receive {net_amount} {quote_currency} from sell order",
                        fee_amount, quote_currency, related_transaction_id=base_transaction_id
                    )

                # Create trade record
                trade_id = self.create_trade_record(
                    user_id, trading_pair['id'], trade_request.side,
                    trade_request.amount, execution_price, total_value,
                    fee_amount, quote_currency, base_transaction_id, quote_transaction_id
                )

                # Create successful response
                return TradeResponse(
                    success=True,
                    message=f"Trade executed successfully: {trade_request.side.value} {trade_request.amount} {trade_request.symbol}",
                    trade_id=trade_id,
                    symbol=trade_request.symbol,
                    side=trade_request.side.value,
                    amount=trade_request.amount,
                    price=execution_price,
                    total_value=total_value,
                    fee_amount=fee_amount,
                    fee_currency=quote_currency,
                    status='completed',
                    base_currency_balance_before=base_balance_before,
                    base_currency_balance_after=base_balance_after,
                    quote_currency_balance_before=quote_balance_before,
                    quote_currency_balance_after=quote_balance_after,
                    base_transaction_id=base_transaction_id,
                    quote_transaction_id=quote_transaction_id,
                    executed_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Trade execution failed: {str(e)}"
            )

    async def simulate_trade(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """
        Simulate a trade without executing it

        Args:
            trade_request: Trade request data

        Returns:
            Simulation results

        Raises:
            HTTPException: If user or trading pair not found
        """
        # Validate user (this will raise HTTPException if not found)
        user = self.validate_and_get_user(trade_request.username)
        user_id = user['id']

        # Validate trading pair (this will raise HTTPException if not found)
        trading_pair = self.validate_and_get_trading_pair(trade_request.symbol)
        base_currency = trading_pair['base_currency']
        quote_currency = trading_pair['quote_currency']

        # Validate trade constraints (this will raise HTTPException if invalid)
        self.validate_trade_constraints(trade_request, trading_pair)

        # Get current price
        current_price = self.get_current_price(trade_request.symbol)
        execution_price = trade_request.price or current_price

        # Calculate trade amounts
        total_value, fee_amount, net_amount = self.calculate_trade_amounts(trade_request, execution_price)

        # Get current balances
        try:
            base_balance = self.get_user_balance(user_id, base_currency)
            base_current = Decimal(str(base_balance['available_balance']))
        except HTTPException:
            base_current = Decimal('0')

        try:
            quote_balance = self.get_user_balance(user_id, quote_currency)
            quote_current = Decimal(str(quote_balance['available_balance']))
        except HTTPException:
            quote_current = Decimal('0')

        # Calculate projected balances
        if trade_request.side == TradingSide.BUY:
            base_projected = base_current + trade_request.amount
            quote_projected = quote_current - net_amount
            required_balance = net_amount
            required_currency = quote_currency
        else:
            base_projected = base_current - trade_request.amount
            quote_projected = quote_current + net_amount
            required_balance = trade_request.amount
            required_currency = base_currency

        # Check for validation errors
        validation_errors = []
        if (trade_request.side == TradingSide.BUY and quote_current < net_amount) or \
           (trade_request.side == TradingSide.SELL and base_current < trade_request.amount):
            validation_errors.append(f"Insufficient {required_currency} balance. Required: {required_balance}, Available: {quote_current if trade_request.side == TradingSide.BUY else base_current}")

        return {
            'success': True,
            'message': f"Trade simulation for {trade_request.side.value} {trade_request.amount} {trade_request.symbol}",
            'symbol': trade_request.symbol,
            'side': trade_request.side.value,
            'amount': trade_request.amount,
            'estimated_price': execution_price,
            'estimated_total': total_value,
            'estimated_fee': fee_amount,
            'fee_currency': quote_currency,
            'current_balances': {
                base_currency: base_current,
                quote_currency: quote_current
            },
            'projected_balances': {
                base_currency: base_projected,
                quote_currency: quote_projected
            },
            'validation_errors': validation_errors,
            'warnings': []
        }
