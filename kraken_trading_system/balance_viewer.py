#!/usr/bin/env python3
"""
Balance Viewer Script
View and analyze user balances in the balance tracking system
"""

import sqlite3
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime


class BalanceViewer:
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

    def print_separator(self, char="=", length=80):
        """Print a separator line"""
        print(char * length)

    def format_amount(self, amount, width=15):
        """Format amount for display"""
        if amount == 0:
            return f"{'0.00':<{width}}"

        # Convert to float for display
        amount_float = float(amount)

        # Format based on magnitude
        if abs(amount_float) >= 1:
            return f"{amount_float:,.2f}"[:width].ljust(width)
        else:
            return f"{amount_float:.8f}".rstrip('0').rstrip('.')[:width].ljust(width)

    def get_user_by_identifier(self, identifier):
        """Get user by username or user ID"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, username, email, first_name, last_name, is_active, is_verified
            FROM users
            WHERE username = ? OR id = ?
        """, (identifier, identifier))
        return cursor.fetchone()

    def show_user_balances(self, identifier, show_zero_balances=False, currency_filter=None):
        """Show balances for a specific user"""
        user = self.get_user_by_identifier(identifier)
        if not user:
            print(f"❌ User not found: {identifier}")
            return False

        user_id, username, email, first_name, last_name, is_active, is_verified = user

        print(f"\n👤 USER BALANCES")
        self.print_separator()
        print(f"Username: {username}")
        print(f"Email: {email}")
        if first_name or last_name:
            print(f"Name: {first_name or ''} {last_name or ''}".strip())
        print(f"Status: {'Active' if is_active else 'Inactive'} | {'Verified' if is_verified else 'Unverified'}")
        print(f"User ID: {user_id}")

        # Build query for balances
        query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance,
                   ub.locked_balance, ub.updated_at, c.name, c.symbol, c.is_fiat
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
        """
        params = [user_id]

        if not show_zero_balances:
            query += " AND ub.total_balance > 0"

        if currency_filter:
            query += " AND ub.currency_code = ?"
            params.append(currency_filter.upper())

        query += " ORDER BY c.is_fiat DESC, ub.total_balance DESC, ub.currency_code"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        balances = cursor.fetchall()

        if not balances:
            if currency_filter:
                print(f"\n💰 No {currency_filter} balance found")
            else:
                print(f"\n💰 No balances found")
            return True

        print(f"\n💰 BALANCES")
        self.print_separator("-", 80)
        print(f"{'Currency':<12} {'Total':<18} {'Available':<18} {'Locked':<18} {'Last Updated':<20}")
        self.print_separator("-", 80)

        total_fiat_value = Decimal('0')
        fiat_currencies = []

        for balance in balances:
            currency_code = balance[0]
            total = Decimal(str(balance[1]))
            available = Decimal(str(balance[2]))
            locked = Decimal(str(balance[3]))
            updated = balance[4][:19] if balance[4] else 'Never'
            currency_name = balance[5]
            symbol = balance[6]
            is_fiat = balance[7]

            # Format currency display
            currency_display = f"{currency_code}"
            if symbol and symbol != currency_code:
                currency_display += f" ({symbol})"

            # Format amounts
            total_str = self.format_amount(total, 18)
            available_str = self.format_amount(available, 18)
            locked_str = self.format_amount(locked, 18)

            # Add indicator for locked funds
            lock_indicator = " 🔒" if locked > 0 else ""

            print(f"{currency_display:<12} {total_str} {available_str} {locked_str} {updated:<20}{lock_indicator}")

            # Track fiat currencies for summary
            if is_fiat:
                fiat_currencies.append((currency_code, total))

        # Show summary
        print(f"\n📊 SUMMARY")
        print(f"Total currencies: {len(balances)}")

        # Count locked funds
        locked_count = sum(1 for b in balances if Decimal(str(b[3])) > 0)
        if locked_count > 0:
            print(f"Currencies with locked funds: {locked_count}")

        # Show fiat total if multiple fiat currencies
        if len(fiat_currencies) > 1:
            print(f"Fiat currencies: {', '.join([f'{curr}: {self.format_amount(amt, 12).strip()}' for curr, amt in fiat_currencies])}")

        return True

    def show_all_balances(self, min_balance=None, currency_filter=None, show_inactive_users=False):
        """Show balances for all users"""
        print(f"\n👥 ALL USER BALANCES")
        self.print_separator()

        # Build query
        query = """
            SELECT u.username, u.email, u.is_active, u.is_verified,
                   ub.currency_code, ub.total_balance, ub.available_balance,
                   ub.locked_balance, c.symbol, c.is_fiat
            FROM users u
            JOIN user_balances ub ON u.id = ub.user_id
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.total_balance > 0
        """
        params = []

        if not show_inactive_users:
            query += " AND u.is_active = 1"

        if min_balance is not None:
            query += " AND ub.total_balance >= ?"
            params.append(str(min_balance))

        if currency_filter:
            query += " AND ub.currency_code = ?"
            params.append(currency_filter.upper())

        query += " ORDER BY u.username, c.is_fiat DESC, ub.total_balance DESC"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        balances = cursor.fetchall()

        if not balances:
            print("No balances found matching criteria")
            return

        print(f"{'Username':<15} {'Currency':<10} {'Total':<18} {'Available':<18} {'Status':<12}")
        self.print_separator("-", 80)

        current_user = None
        user_count = 0
        total_balance_entries = 0

        for balance in balances:
            username = balance[0]
            email = balance[1]
            is_active = balance[2]
            is_verified = balance[3]
            currency_code = balance[4]
            total = Decimal(str(balance[5]))
            available = Decimal(str(balance[6]))
            locked = Decimal(str(balance[7]))
            symbol = balance[8]
            is_fiat = balance[9]

            # Track user count
            if username != current_user:
                current_user = username
                user_count += 1

            total_balance_entries += 1

            # Format display
            total_str = self.format_amount(total, 18)
            available_str = self.format_amount(available, 18)

            # Status indicators
            status_parts = []
            if not is_active:
                status_parts.append("Inactive")
            if not is_verified:
                status_parts.append("Unverified")
            if locked > 0:
                status_parts.append("🔒Locked")

            status = " | ".join(status_parts) if status_parts else "Active"

            print(f"{username:<15} {currency_code:<10} {total_str} {available_str} {status:<12}")

        print(f"\n📊 SUMMARY: {user_count} users with {total_balance_entries} balance entries")

    def show_currency_summary(self, currency_code=None):
        """Show summary by currency"""
        if currency_code:
            currency_code = currency_code.upper()
            print(f"\n💱 {currency_code} BALANCE SUMMARY")
        else:
            print(f"\n💱 CURRENCY BALANCE SUMMARY")

        self.print_separator()

        # Build query
        if currency_code:
            query = """
                SELECT ub.currency_code, c.name, c.symbol, c.is_fiat,
                       COUNT(ub.user_id) as user_count,
                       SUM(ub.total_balance) as total_supply,
                       SUM(ub.available_balance) as total_available,
                       SUM(ub.locked_balance) as total_locked,
                       AVG(ub.total_balance) as avg_balance,
                       MIN(ub.total_balance) as min_balance,
                       MAX(ub.total_balance) as max_balance
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                JOIN users u ON ub.user_id = u.id
                WHERE ub.total_balance > 0 AND u.is_active = 1 AND ub.currency_code = ?
                GROUP BY ub.currency_code, c.name, c.symbol, c.is_fiat
            """
            params = [currency_code]
        else:
            query = """
                SELECT ub.currency_code, c.name, c.symbol, c.is_fiat,
                       COUNT(ub.user_id) as user_count,
                       SUM(ub.total_balance) as total_supply,
                       SUM(ub.available_balance) as total_available,
                       SUM(ub.locked_balance) as total_locked,
                       AVG(ub.total_balance) as avg_balance,
                       MIN(ub.total_balance) as min_balance,
                       MAX(ub.total_balance) as max_balance
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                JOIN users u ON ub.user_id = u.id
                WHERE ub.total_balance > 0 AND u.is_active = 1
                GROUP BY ub.currency_code, c.name, c.symbol, c.is_fiat
                ORDER BY c.is_fiat DESC, total_supply DESC
            """
            params = []

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        summaries = cursor.fetchall()

        if not summaries:
            if currency_code:
                print(f"No {currency_code} balances found")
            else:
                print("No balances found")
            return

        if currency_code:
            # Detailed view for single currency
            summary = summaries[0]
            currency_name = summary[1]
            symbol = summary[2]
            is_fiat = summary[3]
            user_count = summary[4]
            total_supply = Decimal(str(summary[5]))
            total_available = Decimal(str(summary[6]))
            total_locked = Decimal(str(summary[7]))
            avg_balance = Decimal(str(summary[8]))
            min_balance = Decimal(str(summary[9]))
            max_balance = Decimal(str(summary[10]))

            print(f"Currency: {currency_code} - {currency_name}")
            print(f"Symbol: {symbol}")
            print(f"Type: {'Fiat' if is_fiat else 'Cryptocurrency'}")
            print(f"\n📊 STATISTICS:")
            print(f"Users with balance: {user_count}")
            print(f"Total supply: {self.format_amount(total_supply).strip()}")
            print(f"Total available: {self.format_amount(total_available).strip()}")
            print(f"Total locked: {self.format_amount(total_locked).strip()}")
            print(f"Average balance: {self.format_amount(avg_balance).strip()}")
            print(f"Minimum balance: {self.format_amount(min_balance).strip()}")
            print(f"Maximum balance: {self.format_amount(max_balance).strip()}")

            if total_locked > 0:
                locked_percentage = (total_locked / total_supply) * 100
                print(f"Locked percentage: {locked_percentage:.2f}%")
        else:
            # Table view for all currencies
            print(f"{'Currency':<10} {'Users':<8} {'Total Supply':<18} {'Available':<18} {'Locked':<18}")
            self.print_separator("-", 80)

            for summary in summaries:
                currency = summary[0]
                user_count = summary[4]
                total_supply = Decimal(str(summary[5]))
                total_available = Decimal(str(summary[6]))
                total_locked = Decimal(str(summary[7]))

                supply_str = self.format_amount(total_supply, 18)
                available_str = self.format_amount(total_available, 18)
                locked_str = self.format_amount(total_locked, 18)

                print(f"{currency:<10} {user_count:<8} {supply_str} {available_str} {locked_str}")

    def show_balance_distribution(self, currency_code):
        """Show balance distribution for a currency"""
        currency_code = currency_code.upper()

        print(f"\n📈 {currency_code} BALANCE DISTRIBUTION")
        self.print_separator()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT u.username, ub.total_balance, ub.available_balance, ub.locked_balance
            FROM user_balances ub
            JOIN users u ON ub.user_id = u.id
            WHERE ub.currency_code = ? AND ub.total_balance > 0 AND u.is_active = 1
            ORDER BY ub.total_balance DESC
        """, (currency_code,))

        balances = cursor.fetchall()

        if not balances:
            print(f"No {currency_code} balances found")
            return

        # Calculate distribution stats
        total_supply = sum(Decimal(str(b[1])) for b in balances)

        print(f"{'Rank':<6} {'Username':<15} {'Balance':<18} {'% of Supply':<12} {'Available':<18}")
        self.print_separator("-", 80)

        for i, balance in enumerate(balances, 1):
            username = balance[0]
            total = Decimal(str(balance[1]))
            available = Decimal(str(balance[2]))
            locked = Decimal(str(balance[3]))

            percentage = (total / total_supply) * 100 if total_supply > 0 else 0

            total_str = self.format_amount(total, 18)
            available_str = self.format_amount(available, 18)
            percentage_str = f"{percentage:.2f}%"

            lock_indicator = " 🔒" if locked > 0 else ""

            print(f"{i:<6} {username:<15} {total_str} {percentage_str:<12} {available_str}{lock_indicator}")

        print(f"\nTotal users: {len(balances)}")
        print(f"Total supply: {self.format_amount(total_supply).strip()}")

        # Show concentration stats
        if len(balances) >= 3:
            top_3_total = sum(Decimal(str(b[1])) for b in balances[:3])
            top_3_percentage = (top_3_total / total_supply) * 100
            print(f"Top 3 users hold: {top_3_percentage:.2f}% of supply")

    def search_balances(self, min_amount=None, max_amount=None, currency_filter=None, username_filter=None):
        """Search balances with filters"""
        print(f"\n🔍 BALANCE SEARCH")
        self.print_separator()

        query = """
            SELECT u.username, u.email, ub.currency_code, ub.total_balance,
                   ub.available_balance, ub.locked_balance, c.symbol
            FROM user_balances ub
            JOIN users u ON ub.user_id = u.id
            JOIN currencies c ON ub.currency_code = c.code
            WHERE u.is_active = 1 AND ub.total_balance > 0
        """
        params = []

        if min_amount is not None:
            query += " AND ub.total_balance >= ?"
            params.append(str(min_amount))

        if max_amount is not None:
            query += " AND ub.total_balance <= ?"
            params.append(str(max_amount))

        if currency_filter:
            query += " AND ub.currency_code = ?"
            params.append(currency_filter.upper())

        if username_filter:
            query += " AND u.username LIKE ?"
            params.append(f"%{username_filter}%")

        query += " ORDER BY ub.total_balance DESC"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

        if not results:
            print("No balances found matching search criteria")
            return

        # Show search criteria
        criteria = []
        if min_amount is not None:
            criteria.append(f"Min amount: {min_amount}")
        if max_amount is not None:
            criteria.append(f"Max amount: {max_amount}")
        if currency_filter:
            criteria.append(f"Currency: {currency_filter}")
        if username_filter:
            criteria.append(f"Username contains: {username_filter}")

        if criteria:
            print(f"Search criteria: {' | '.join(criteria)}")
            print()

        print(f"{'Username':<15} {'Currency':<10} {'Total':<18} {'Available':<18} {'Locked':<15}")
        self.print_separator("-", 80)

        for result in results:
            username = result[0]
            currency = result[2]
            total = Decimal(str(result[3]))
            available = Decimal(str(result[4]))
            locked = Decimal(str(result[5]))

            total_str = self.format_amount(total, 18)
            available_str = self.format_amount(available, 18)
            locked_str = self.format_amount(locked, 15)

            print(f"{username:<15} {currency:<10} {total_str} {available_str} {locked_str}")

        print(f"\nFound {len(results)} matching balances")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="View user balances in the balance tracking system")
    parser.add_argument("--db-file", default="balance_tracker.db",
                       help="Database file path")

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # User balance command
    user_parser = subparsers.add_parser('user', help='Show balances for specific user')
    user_parser.add_argument('identifier', help='Username or user ID')
    user_parser.add_argument('--currency', help='Filter by currency')
    user_parser.add_argument('--show-zero', action='store_true', help='Show zero balances')

    # All balances command
    all_parser = subparsers.add_parser('all', help='Show balances for all users')
    all_parser.add_argument('--min-balance', type=float, help='Minimum balance filter')
    all_parser.add_argument('--currency', help='Filter by currency')
    all_parser.add_argument('--show-inactive', action='store_true', help='Include inactive users')

    # Currency summary command
    currency_parser = subparsers.add_parser('currency', help='Show currency summary')
    currency_parser.add_argument('currency_code', nargs='?', help='Specific currency code')

    # Distribution command
    dist_parser = subparsers.add_parser('distribution', help='Show balance distribution')
    dist_parser.add_argument('currency_code', help='Currency code')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search balances')
    search_parser.add_argument('--min-amount', type=float, help='Minimum amount')
    search_parser.add_argument('--max-amount', type=float, help='Maximum amount')
    search_parser.add_argument('--currency', help='Currency filter')
    search_parser.add_argument('--username', help='Username filter')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    viewer = BalanceViewer(args.db_file)

    try:
        viewer.connect()

        if args.command == 'user':
            viewer.show_user_balances(
                args.identifier,
                args.show_zero,
                args.currency
            )

        elif args.command == 'all':
            viewer.show_all_balances(
                args.min_balance,
                getattr(args, 'currency', None),
                args.show_inactive
            )

        elif args.command == 'currency':
            viewer.show_currency_summary(args.currency_code)

        elif args.command == 'distribution':
            viewer.show_balance_distribution(args.currency_code)

        elif args.command == 'search':
            viewer.search_balances(
                args.min_amount,
                args.max_amount,
                args.currency,
                args.username
            )

    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        viewer.disconnect()


if __name__ == "__main__":
    main()
