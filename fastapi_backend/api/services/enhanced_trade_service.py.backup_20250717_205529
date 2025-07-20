#!/usr/bin/env python3
"""
Enhanced Trade Service with Spread Functionality
This module extends the existing TradeService to include spread calculations
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple, Any

from api.services.trade_service import TradeService as BaseTradeService
from api.models import TradeRequest, TradeResponse, TradingSide

logger = logging.getLogger(__name__)


class EnhancedTradeService(BaseTradeService):
    """
    Enhanced trade service that adds spread functionality to market orders.
    Inherits from the base TradeService and overrides specific methods.
    """

    def get_trading_pair_with_spread(self, symbol: str) -> Dict[str, Any]:
        """
        Get trading pair information including spread percentage

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USD')

        Returns:
            Trading pair data including spread_percentage
        """
        trading_pair = self.validate_and_get_trading_pair(symbol)
        
        # If spread_percentage is not in the result, fetch it separately
        if 'spread_percentage' not in trading_pair:
            query = """
                SELECT spread_percentage 
                FROM trading_pairs 
                WHERE id = ?
            """
            result = self.db.execute_query(query, (trading_pair['id'],))
            if result:
                trading_pair['spread_percentage'] = Decimal(str(result[0]['spread_percentage']))
            else:
                # Default spread if not found
                trading_pair['spread_percentage'] = Decimal('0.02')  # 2% default
        
        return trading_pair

    def calculate_spread_adjusted_price(self, market_price: Decimal, spread_percentage: Decimal, 
                                      side: TradingSide) -> Tuple[Decimal, Decimal]:
        """
        Calculate the client price with spread applied

        Args:
            market_price: The actual market execution price
            spread_percentage: The spread percentage (e.g., 0.02 for 2%)
            side: Trade side (buy/sell)

        Returns:
            Tuple of (client_price, spread_amount)
        """
        if side == TradingSide.BUY:
            # For buy orders: client pays more than market price
            client_price = market_price * (Decimal('1') + spread_percentage)
        else:
            # For sell orders: client receives less than market price
            client_price = market_price * (Decimal('1') - spread_percentage)
        
        # Round to 8 decimal places
        client_price = client_price.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
        
        # Calculate spread amount (always positive)
        spread_amount = abs(client_price - market_price)
        
        return client_price, spread_amount

    def calculate_trade_amounts_with_spread(self, trade_request: TradeRequest, 
                                          market_price: Decimal, 
                                          spread_percentage: Decimal) -> Dict[str, Decimal]:
        """
        Calculate all trade amounts including spread

        Args:
            trade_request: Trade request data
            market_price: Current market price
            spread_percentage: Spread percentage to apply

        Returns:
            Dictionary with all calculated amounts
        """
        amount = trade_request.amount
        
        # Calculate client price with spread
        client_price, spread_amount_per_unit = self.calculate_spread_adjusted_price(
            market_price, spread_percentage, trade_request.side
        )
        
        # Calculate values based on execution price (market price)
        execution_total = amount * market_price
        
        # Calculate values based on client price
        client_total = amount * client_price
        
        # Total spread revenue
        total_spread_amount = amount * spread_amount_per_unit
        
        # Calculate fee on the client total
        fee_amount = client_total * self.default_fee_rate
        fee_amount = fee_amount.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
        
        # Net amount for the client
        if trade_request.side == TradingSide.BUY:
            # Client pays: client_total + fee
            net_amount = client_total + fee_amount
        else:
            # Client receives: client_total - fee
            net_amount = client_total - fee_amount
        
        return {
            'execution_price': market_price,
            'client_price': client_price,
            'execution_total': execution_total,
            'client_total': client_total,
            'fee_amount': fee_amount,
            'net_amount': net_amount,
            'spread_amount': total_spread_amount,
            'spread_percentage': spread_percentage
        }

    async def execute_trade(self, trade_request: TradeRequest) -> TradeResponse:
        """
        Execute a trade with spread calculation

        Overrides the base execute_trade method to include spread functionality
        """
        try:
            # Validate user
            user = self.validate_and_get_user(trade_request.username)
            user_id = user['id']

            # Get trading pair with spread information
            trading_pair = self.get_trading_pair_with_spread(trade_request.symbol)
            base_currency = trading_pair['base_currency']
            quote_currency = trading_pair['quote_currency']
            spread_percentage = trading_pair['spread_percentage']

            # Validate trade constraints
            self.validate_trade_constraints(trade_request, trading_pair)

            # Get current market price
            market_price = self.get_current_price(trade_request.symbol)
            
            # For market orders, apply spread. For limit orders, use specified price
            if trade_request.order_type == "market":
                # Calculate all amounts with spread
                amounts = self.calculate_trade_amounts_with_spread(
                    trade_request, market_price, spread_percentage
                )
                execution_price = amounts['execution_price']
                client_price = amounts['client_price']
                total_value = amounts['client_total']
                fee_amount = amounts['fee_amount']
                net_amount = amounts['net_amount']
                spread_amount = amounts['spread_amount']
            else:
                # Limit orders: no spread applied (future implementation)
                execution_price = trade_request.price or market_price
                client_price = execution_price
                total_value, fee_amount, net_amount = self.calculate_trade_amounts(
                    trade_request, execution_price
                )
                spread_amount = Decimal('0')

            # Execute trade atomically
            with self.atomic_transaction():
                if trade_request.side == TradingSide.BUY:
                    # Buy: debit quote currency, credit base currency
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
                        f"Buy {trade_request.amount} {base_currency} at {client_price}"
                    )
                    
                    base_transaction_id = self.create_transaction_record(
                        user_id, TransactionType.TRADE_BUY, trade_request.amount, base_currency,
                        base_balance_before, base_balance_after,
                        f"Receive {trade_request.amount} {base_currency} from buy order",
                        related_transaction_id=quote_transaction_id
                    )
                    
                else:
                    # Sell: debit base currency, credit quote currency
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
                        f"Sell {trade_request.amount} {base_currency} at {client_price}"
                    )
                    
                    quote_transaction_id = self.create_transaction_record(
                        user_id, TransactionType.TRADE_SELL, net_amount, quote_currency,
                        quote_balance_before, quote_balance_after,
                        f"Receive {net_amount} {quote_currency} from sell order",
                        fee_amount, quote_currency, related_transaction_id=base_transaction_id
                    )

                # Create enhanced trade record with spread information
                trade_id = self.create_trade_record_with_spread(
                    user_id, trading_pair['id'], trade_request.side,
                    trade_request.amount, execution_price, client_price,
                    total_value, fee_amount, spread_amount, fee_currency,
                    base_transaction_id, quote_transaction_id
                )

                # Return enhanced response
                return TradeResponse(
                    success=True,
                    message=f"Trade executed successfully: {trade_request.side.value} {trade_request.amount} {trade_request.symbol}",
                    trade_id=trade_id,
                    symbol=trade_request.symbol,
                    side=trade_request.side.value,
                    amount=trade_request.amount,
                    price=client_price,  # Client sees their price
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
                    created_at=datetime.utcnow(),
                    # Additional spread information (optional, could be hidden from client)
                    execution_price=execution_price,
                    client_price=client_price,
                    spread_amount=spread_amount
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Trade execution failed: {str(e)}"
            )

    def create_trade_record_with_spread(self, user_id: str, trading_pair_id: str, 
                                       side: TradingSide, amount: Decimal, 
                                       execution_price: Decimal, client_price: Decimal,
                                       total_value: Decimal, fee_amount: Decimal, 
                                       spread_amount: Decimal, fee_currency: str,
                                       base_transaction_id: str, quote_transaction_id: str,
                                       fee_transaction_id: str = None) -> str:
        """
        Create a trade record with spread information

        Args:
            All parameters from base method plus:
            execution_price: Actual market execution price
            client_price: Price shown to client (with spread)
            spread_amount: Total spread amount

        Returns:
            Trade ID
        """
        trade_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO trades (
                id, user_id, trading_pair_id, side, amount, price, total_value,
                fee_amount, fee_currency_code, status, executed_at,
                base_transaction_id, quote_transaction_id, fee_transaction_id,
                execution_price, client_price, spread_amount,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.utcnow()
        params = (
            trade_id, user_id, trading_pair_id, side.value, float(amount),
            float(client_price), float(total_value), float(fee_amount), fee_currency,
            'completed', now, base_transaction_id, quote_transaction_id,
            fee_transaction_id, float(execution_price), float(client_price),
            float(spread_amount), now, now
        )
        
        self.db.execute_query(query, params)
        return trade_id

    async def simulate_trade(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """
        Simulate a trade with spread calculation

        Overrides base simulate_trade to show spread impact
        """
        # Get base simulation result
        base_result = await super().simulate_trade(trade_request)
        
        # Get trading pair with spread
        trading_pair = self.get_trading_pair_with_spread(trade_request.symbol)
        spread_percentage = trading_pair['spread_percentage']
        
        # Get market price
        market_price = self.get_current_price(trade_request.symbol)
        
        # Calculate spread-adjusted amounts
        if trade_request.order_type == "market":
            amounts = self.calculate_trade_amounts_with_spread(
                trade_request, market_price, spread_percentage
            )
            
            # Update simulation result with spread information
            base_result['execution_price'] = amounts['execution_price']
            base_result['client_price'] = amounts['client_price']
            base_result['estimated_price'] = amounts['client_price']
            base_result['estimated_total'] = amounts['client_total']
            base_result['estimated_fee'] = amounts['fee_amount']
            base_result['spread_amount'] = amounts['spread_amount']
            base_result['spread_percentage'] = float(spread_percentage * 100)
            
            # Add spread warning if significant
            if spread_percentage > Decimal('0.03'):  # More than 3%
                base_result['warnings'].append(
                    f"High spread of {float(spread_percentage * 100):.2f}% will be applied"
                )
        
        return base_result
