#!/usr/bin/env python3
"""
Transaction Manager Script
Process deposits and withdrawals for the balance tracking system
"""

import sqlite3
import sys
import uuid
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation


class TransactionManager:
    def __init__(self, db_file="balance_tracker.db"):
        self.db_file = db_file
        self.conn = None
        
    def connect(self):
        """Connect to the database"""
        if not Path(self.db_file).exists():
            print(f"❌ Database file '{self.db_file}' not found!")
            print("Run the setup script first to create the database.")
            sys.exit(1)
            
        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ Connected to database: {self.db_file}")
        
    def disconnect(self):
        if self.conn:
            self.conn.close()
    
    def get_user_by_username(self, username):
        """Get user by username"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, username, email, is_active 
            FROM users 
            WHERE username = ? AND is_active = 1
        """, (username,))
        return cursor.fetchone()
    
    def get_available_currencies(self):
        """Get list of available currencies"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT code, name, symbol 
            FROM currencies 
            WHERE is_active = 1 
            ORDER BY code
        """)
        return cursor.fetchall()
    
    def get_user_balance(self, user_id, currency_code):
        """Get current balance for user and currency"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT total_balance, available_balance, locked_balance 
            FROM user_balances 
            WHERE user_id = ? AND currency_code = ?
        """, (user_id, currency_code))
        
        result = cursor.fetchone()
        if result:
            return {
                'total': Decimal(str(result[0])),
                'available': Decimal(str(result[1])),
                'locked': Decimal(str(result[2]))
            }
        else:
            return {
                'total': Decimal('0'),
                'available': Decimal('0'),
                'locked': Decimal('0')
            }
    
    def create_or_update_balance(self, user_id, currency_code, new_total, new_available, new_locked=None):
        """Create or update user balance"""
        if new_locked is None:
            new_locked = Decimal('0')
            
        cursor = self.conn.cursor()
        
        # Check if balance record exists
        cursor.execute("""
            SELECT id FROM user_balances WHERE user_id = ? AND currency_code = ?
        """, (user_id, currency_code))
        
        if cursor.fetchone():
            # Update existing balance
            cursor.execute("""
                UPDATE user_balances 
                SET total_balance = ?, available_balance = ?, locked_balance = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND currency_code = ?
            """, (str(new_total), str(new_available), str(new_locked), user_id, currency_code))
        else:
            # Create new balance record
            balance_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_balances (id, user_id, currency_code, total_balance, 
                                         available_balance, locked_balance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (balance_id, user_id, currency_code, str(new_total), 
                  str(new_available), str(new_locked)))
    
    def create_balance_snapshot(self, user_id, currency_code, total_balance, available_balance, 
                              locked_balance, transaction_id, snapshot_type='transaction'):
        """Create a balance snapshot for audit purposes"""
        snapshot_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO balance_snapshots (
                id, user_id, currency_code, total_balance, available_balance, 
                locked_balance, snapshot_type, triggered_by_transaction_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, user_id, currency_code, str(total_balance), 
            str(available_balance), str(locked_balance), snapshot_type, transaction_id
        ))
    
    def process_deposit(self, username, amount, currency_code, description=None, 
                       external_reference=None, auto_confirm=False):
        """Process a deposit transaction"""
        print(f"\n💰 PROCESSING DEPOSIT")
        print("=" * 40)
        
        try:
            # Validate amount
            amount = Decimal(str(amount))
            if amount <= 0:
                print("❌ Amount must be positive")
                return None
        except (InvalidOperation, ValueError):
            print("❌ Invalid amount format")
            return None
        
        # Get user
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ User not found or inactive: {username}")
            return None
        
        user_id = user[0]
        
        # Check currency exists
        cursor = self.conn.cursor()
        cursor.execute("SELECT code FROM currencies WHERE code = ? AND is_active = 1", (currency_code,))
        if not cursor.fetchone():
            print(f"❌ Currency not found or inactive: {currency_code}")
            return None
        
        # Get current balance
        current_balance = self.get_user_balance(user_id, currency_code)
        balance_before = current_balance['total']
        balance_after = balance_before + amount
        
        # Display transaction details
        print(f"User: {user[1]} ({user[2]})")
        print(f"Amount: {amount} {currency_code}")
        print(f"Current balance: {balance_before} {currency_code}")
        print(f"New balance: {balance_after} {currency_code}")
        if description:
            print(f"Description: {description}")
        if external_reference:
            print(f"External reference: {external_reference}")
        
        # Confirm transaction
        if not auto_confirm:
            confirm = input(f"\nConfirm deposit? (Y/n): ").strip().lower()
            if confirm not in ['', 'y', 'yes']:
                print("❌ Deposit cancelled")
                return None
        
        # Process transaction
        transaction_id = str(uuid.uuid4())
        
        try:
            # Create transaction record
            cursor.execute("""
                INSERT INTO transactions (
                    id, user_id, transaction_type, status, amount, currency_code,
                    balance_before, balance_after, description, external_reference,
                    created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                transaction_id, user_id, 'deposit', 'completed', str(amount), currency_code,
                str(balance_before), str(balance_after), description, external_reference
            ))
            
            # Update user balance (all deposited funds are available)
            self.create_or_update_balance(
                user_id, currency_code, balance_after, balance_after, Decimal('0')
            )
            
            # Create balance snapshot
            self.create_balance_snapshot(
                user_id, currency_code, balance_after, balance_after, 
                Decimal('0'), transaction_id
            )
            
            self.conn.commit()
            
            print(f"\n✅ Deposit completed successfully!")
            print(f"Transaction ID: {transaction_id}")
            print(f"New balance: {balance_after} {currency_code}")
            
            return transaction_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"❌ Database error: {e}")
            return None
    
    def process_withdrawal(self, username, amount, currency_code, description=None, 
                          external_reference=None, auto_confirm=False):
        """Process a withdrawal transaction"""
        print(f"\n💸 PROCESSING WITHDRAWAL")
        print("=" * 40)
        
        try:
            # Validate amount
            amount = Decimal(str(amount))
            if amount <= 0:
                print("❌ Amount must be positive")
                return None
        except (InvalidOperation, ValueError):
            print("❌ Invalid amount format")
            return None
        
        # Get user
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ User not found or inactive: {username}")
            return None
        
        user_id = user[0]
        
        # Check currency exists
        cursor = self.conn.cursor()
        cursor.execute("SELECT code FROM currencies WHERE code = ? AND is_active = 1", (currency_code,))
        if not cursor.fetchone():
            print(f"❌ Currency not found or inactive: {currency_code}")
            return None
        
        # Get current balance
        current_balance = self.get_user_balance(user_id, currency_code)
        balance_before = current_balance['total']
        available_balance = current_balance['available']
        
        # Check sufficient funds
        if available_balance < amount:
            print(f"❌ Insufficient funds!")
            print(f"Available balance: {available_balance} {currency_code}")
            print(f"Requested amount: {amount} {currency_code}")
            
            # Still record the failed transaction
            transaction_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO transactions (
                    id, user_id, transaction_type, status, amount, currency_code,
                    balance_before, balance_after, description, external_reference,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                transaction_id, user_id, 'withdrawal', 'failed', str(amount), currency_code,
                str(balance_before), str(balance_before), 
                f"FAILED: {description or 'Withdrawal'} (Insufficient funds)", external_reference
            ))
            self.conn.commit()
            
            return None
        
        balance_after = balance_before - amount
        
        # Display transaction details
        print(f"User: {user[1]} ({user[2]})")
        print(f"Amount: {amount} {currency_code}")
        print(f"Available balance: {available_balance} {currency_code}")
        print(f"Balance after withdrawal: {balance_after} {currency_code}")
        if description:
            print(f"Description: {description}")
        if external_reference:
            print(f"External reference: {external_reference}")
        
        # Confirm transaction
        if not auto_confirm:
            confirm = input(f"\nConfirm withdrawal? (Y/n): ").strip().lower()
            if confirm not in ['', 'y', 'yes']:
                print("❌ Withdrawal cancelled")
                return None
        
        # Process transaction
        transaction_id = str(uuid.uuid4())
        
        try:
            # Create transaction record
            cursor.execute("""
                INSERT INTO transactions (
                    id, user_id, transaction_type, status, amount, currency_code,
                    balance_before, balance_after, description, external_reference,
                    created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                transaction_id, user_id, 'withdrawal', 'completed', str(amount), currency_code,
                str(balance_before), str(balance_after), description, external_reference
            ))
            
            # Update user balance
            new_available = available_balance - amount
            new_locked = current_balance['locked']
            self.create_or_update_balance(
                user_id, currency_code, balance_after, new_available, new_locked
            )
            
            # Create balance snapshot
            self.create_balance_snapshot(
                user_id, currency_code, balance_after, new_available, 
                new_locked, transaction_id
            )
            
            self.conn.commit()
            
            print(f"\n✅ Withdrawal completed successfully!")
            print(f"Transaction ID: {transaction_id}")
            print(f"New balance: {balance_after} {currency_code}")
            
            return transaction_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"❌ Database error: {e}")
            return None
    
    def show_user_balances(self, username):
        """Show current balances for a user"""
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ User not found: {username}")
            return
        
        user_id = user[0]
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, 
                   ub.locked_balance, c.name, c.symbol
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
            ORDER BY ub.currency_code
        """, (user_id,))
        
        balances = cursor.fetchall()
        
        print(f"\n💰 BALANCES for {user[1]}")
        print("=" * 60)
        
        if not balances:
            print("No balances found")
            return
        
        print(f"{'Currency':<12} {'Total':<15} {'Available':<15} {'Locked':<15}")
        print("-" * 60)
        
        for balance in balances:
            currency = f"{balance[0]} ({balance[5]})"
            total = balance[1]
            available = balance[2]
            locked = balance[3]
            
            print(f"{currency:<12} {total:<15} {available:<15} {locked:<15}")
    
    def show_recent_transactions(self, username, limit=10):
        """Show recent transactions for a user"""
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ User not found: {username}")
            return
        
        user_id = user[0]
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT transaction_type, status, amount, currency_code, 
                   balance_before, balance_after, description, created_at
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        transactions = cursor.fetchall()
        
        print(f"\n📋 RECENT TRANSACTIONS for {user[1]} (last {limit})")
        print("=" * 80)
        
        if not transactions:
            print("No transactions found")
            return
        
        for tx in transactions:
            tx_type = tx[0]
            status = tx[1]
            amount = f"{tx[2]} {tx[3]}"
            before = tx[4]
            after = tx[5]
            desc = tx[6] or "No description"
            created = tx[7][:19] if tx[7] else ""
            
            status_icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
            
            print(f"\n{status_icon} {tx_type.upper()} - {status}")
            print(f"   Amount: {amount}")
            print(f"   Balance: {before} → {after}")
            print(f"   Description: {desc}")
            print(f"   Date: {created}")
    
    def interactive_deposit(self):
        """Interactive deposit wizard"""
        print(f"\n💰 DEPOSIT WIZARD")
        print("=" * 30)
        
        # Get username
        username = input("Username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return None
        
        # Verify user exists
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ User not found or inactive: {username}")
            return None
        
        # Show available currencies
        currencies = self.get_available_currencies()
        print(f"\nAvailable currencies:")
        for curr in currencies:
            print(f"  {curr[0]} - {curr[1]} ({curr[2]})")
        
        # Get currency
        currency_code = input("\nCurrency code: ").strip().upper()
        if not currency_code:
            print("❌ Currency code cannot be empty")
            return None
        
        # Get amount
        try:
            amount = input("Amount: ").strip()
            amount = Decimal(amount)
            if amount <= 0:
                print("❌ Amount must be positive")
                return None
        except (InvalidOperation, ValueError):
            print("❌ Invalid amount format")
            return None
        
        # Get optional details
        description = input("Description (optional): ").strip() or None
        external_ref = input("External reference (optional): ").strip() or None
        
        # Process deposit
        return self.process_deposit(username, amount, currency_code, description, external_ref)
    
    def interactive_withdrawal(self):
        """Interactive withdrawal wizard"""
        print(f"\n💸 WITHDRAWAL WIZARD")
        print("=" * 30)
        
        # Get username
        username = input("Username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return None
        
        # Verify user exists and show current balances
        user = self.get_user_by_username(username)
        if not user:
            print(f"❌ User not found or inactive: {username}")
            return None
        
        # Show current balances
        self.show_user_balances(username)
        
        # Get currency
        currency_code = input("\nCurrency code to withdraw: ").strip().upper()
        if not currency_code:
            print("❌ Currency code cannot be empty")
            return None
        
        # Check current balance for this currency
        user_id = user[0]
        current_balance = self.get_user_balance(user_id, currency_code)
        if current_balance['available'] == 0:
            print(f"❌ No available balance for {currency_code}")
            return None
        
        print(f"Available balance: {current_balance['available']} {currency_code}")
        
        # Get amount
        try:
            amount = input("Amount to withdraw: ").strip()
            amount = Decimal(amount)
            if amount <= 0:
                print("❌ Amount must be positive")
                return None
        except (InvalidOperation, ValueError):
            print("❌ Invalid amount format")
            return None
        
        # Get optional details
        description = input("Description (optional): ").strip() or None
        external_ref = input("External reference (optional): ").strip() or None
        
        # Process withdrawal
        return self.process_withdrawal(username, amount, currency_code, description, external_ref)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Process deposits and withdrawals")
    parser.add_argument("--db-file", default="balance_tracker.db", 
                       help="Database file path")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Deposit command
    deposit_parser = subparsers.add_parser('deposit', help='Process a deposit')
    deposit_parser.add_argument('--username', required=True, help='Username')
    deposit_parser.add_argument('--amount', required=True, help='Amount to deposit')
    deposit_parser.add_argument('--currency', required=True, help='Currency code')
    deposit_parser.add_argument('--description', help='Description')
    deposit_parser.add_argument('--external-ref', help='External reference')
    deposit_parser.add_argument('--auto-confirm', action='store_true', help='Skip confirmation')
    
    # Withdrawal command
    withdraw_parser = subparsers.add_parser('withdraw', help='Process a withdrawal')
    withdraw_parser.add_argument('--username', required=True, help='Username')
    withdraw_parser.add_argument('--amount', required=True, help='Amount to withdraw')
    withdraw_parser.add_argument('--currency', required=True, help='Currency code')
    withdraw_parser.add_argument('--description', help='Description')
    withdraw_parser.add_argument('--external-ref', help='External reference')
    withdraw_parser.add_argument('--auto-confirm', action='store_true', help='Skip confirmation')
    
    # Balance command
    balance_parser = subparsers.add_parser('balance', help='Show user balances')
    balance_parser.add_argument('username', help='Username')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show transaction history')
    history_parser.add_argument('username', help='Username')
    history_parser.add_argument('--limit', type=int, default=10, help='Number of transactions to show')
    
    # Interactive commands
    subparsers.add_parser('interactive-deposit', help='Interactive deposit wizard')
    subparsers.add_parser('interactive-withdraw', help='Interactive withdrawal wizard')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = TransactionManager(args.db_file)
    
    try:
        manager.connect()
        
        if args.command == 'deposit':
            manager.process_deposit(
                args.username, args.amount, args.currency.upper(),
                args.description, args.external_ref, args.auto_confirm
            )
            
        elif args.command == 'withdraw':
            manager.process_withdrawal(
                args.username, args.amount, args.currency.upper(),
                args.description, args.external_ref, args.auto_confirm
            )
            
        elif args.command == 'balance':
            manager.show_user_balances(args.username)
            
        elif args.command == 'history':
            manager.show_recent_transactions(args.username, args.limit)
            
        elif args.command == 'interactive-deposit':
            manager.interactive_deposit()
            
        elif args.command == 'interactive-withdraw':
            manager.interactive_withdrawal()
        
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.disconnect()


if __name__ == "__main__":
    main()

