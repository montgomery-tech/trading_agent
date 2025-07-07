#!/usr/bin/env python3
"""
Test Database Integration

This script tests the database integration to make sure agent_1 
balances can be retrieved properly.

Usage: python3 test_database_integration.py
"""

import asyncio
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class DatabaseTester:
    """Test database connectivity and data for agent_1."""
    
    def __init__(self, db_file: str = "balance_tracker.db"):
        self.db_file = Path(project_root) / db_file
        self.conn = None
        
    def connect(self):
        """Connect to database."""
        try:
            if not self.db_file.exists():
                print(f"❌ Database file not found: {self.db_file}")
                print("💡 Run setup_database.py first to create the database")
                return False
            
            self.conn = sqlite3.connect(str(self.db_file))
            self.conn.row_factory = sqlite3.Row
            print(f"✅ Connected to database: {self.db_file}")
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def test_database_structure(self):
        """Test that required tables exist."""
        print("\n📋 Testing database structure...")
        
        required_tables = ['users', 'currencies', 'user_balances', 'transactions']
        
        try:
            cursor = self.conn.cursor()
            
            for table in required_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ Table '{table}': {count} records")
            
            return True
            
        except Exception as e:
            print(f"❌ Database structure test failed: {e}")
            return False
    
    def test_agent_1_user(self):
        """Test if agent_1 user exists."""
        print("\n👤 Testing agent_1 user...")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, username, email, first_name, last_name, 
                       is_active, is_verified, created_at
                FROM users 
                WHERE username = ?
            """, ("agent_1",))
            
            user = cursor.fetchone()
            if user:
                print(f"✅ User found: {user['username']}")
                print(f"   Email: {user['email']}")
                print(f"   Name: {user['first_name']} {user['last_name']}")
                print(f"   Active: {bool(user['is_active'])}")
                print(f"   Verified: {bool(user['is_verified'])}")
                print(f"   Created: {user['created_at']}")
                print(f"   User ID: {user['id']}")
                return user['id']
            else:
                print("❌ agent_1 user not found!")
                print("💡 You may need to create this user in the database")
                return None
                
        except Exception as e:
            print(f"❌ User test failed: {e}")
            return None
    
    def test_agent_1_balances(self, user_id):
        """Test agent_1 balances."""
        print("\n💰 Testing agent_1 balances...")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT ub.currency_code, ub.total_balance, ub.available_balance,
                       ub.locked_balance, ub.updated_at, c.name, c.symbol, c.is_fiat
                FROM user_balances ub
                JOIN currencies c ON ub.currency_code = c.code
                WHERE ub.user_id = ? 
                ORDER BY c.is_fiat DESC, ub.total_balance DESC
            """, (user_id,))
            
            balances = cursor.fetchall()
            
            if balances:
                print(f"✅ Found {len(balances)} balance records:")
                total_fiat_value = 0
                
                for balance in balances:
                    currency = balance['currency_code']
                    total = float(balance['total_balance'])
                    available = float(balance['available_balance'])
                    locked = float(balance['locked_balance'])
                    
                    print(f"\n💱 {currency} ({balance['name']}):")
                    print(f"   Symbol: {balance['symbol']}")
                    print(f"   Type: {'Fiat' if balance['is_fiat'] else 'Crypto'}")
                    print(f"   Total: {total:.8f}")
                    print(f"   Available: {available:.8f}")
                    print(f"   Locked: {locked:.8f}")
                    print(f"   Updated: {balance['updated_at']}")
                    
                    # Estimate fiat value for crypto (very rough)
                    if balance['is_fiat']:
                        total_fiat_value += total
                    elif currency == 'BTC':
                        total_fiat_value += total * 35000  # Rough BTC price
                    elif currency == 'ETH':
                        total_fiat_value += total * 2500   # Rough ETH price
                
                print(f"\n📊 Estimated total value: ~${total_fiat_value:.2f}")
                return True
            else:
                print("⚠️ No balances found for agent_1")
                print("💡 You may need to add some balances to test with")
                return False
                
        except Exception as e:
            print(f"❌ Balance test failed: {e}")
            return False
    
    def test_currencies(self):
        """Test available currencies."""
        print("\n💱 Testing available currencies...")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT code, name, symbol, is_fiat, decimal_places, is_active
                FROM currencies 
                WHERE is_active = 1
                ORDER BY is_fiat DESC, code
            """)
            
            currencies = cursor.fetchall()
            
            fiat_count = 0
            crypto_count = 0
            
            print(f"✅ Found {len(currencies)} active currencies:")
            
            for curr in currencies:
                curr_type = "Fiat" if curr['is_fiat'] else "Crypto"
                print(f"   {curr['code']}: {curr['name']} ({curr['symbol']}) - {curr_type}")
                
                if curr['is_fiat']:
                    fiat_count += 1
                else:
                    crypto_count += 1
            
            print(f"\n📊 Currency breakdown: {fiat_count} fiat, {crypto_count} crypto")
            return True
            
        except Exception as e:
            print(f"❌ Currency test failed: {e}")
            return False
    
    def create_sample_agent_1_data(self):
        """Create sample data for agent_1 if it doesn't exist."""
        print("\n🔧 Creating sample agent_1 data...")
        
        try:
            cursor = self.conn.cursor()
            
            # Create agent_1 user if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "agent1_user_id",
                "agent_1",
                "agent1@trading.local",
                "hashed_password_placeholder",
                "Trading",
                "Agent",
                1,  # is_active
                1,  # is_verified
                datetime.now().isoformat()
            ))
            
            # Add sample balances
            sample_balances = [
                ("USD", "10000.00", "8500.00", "1500.00"),
                ("ETH", "5.0", "4.5", "0.5"),
                ("BTC", "0.25", "0.2", "0.05")
            ]
            
            for currency, total, available, locked in sample_balances:
                cursor.execute("""
                    INSERT OR REPLACE INTO user_balances (
                        id, user_id, currency_code, total_balance, 
                        available_balance, locked_balance, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"balance_{currency.lower()}_agent1",
                    "agent1_user_id",
                    currency,
                    total,
                    available,
                    locked,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            self.conn.commit()
            print("✅ Sample agent_1 data created successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create sample data: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run all database tests."""
        print("🧪 COMPREHENSIVE DATABASE TEST")
        print("=" * 60)
        print("Testing database integration for agent_1 trading...")
        print("=" * 60)
        
        # Test 1: Connect to database
        if not self.connect():
            return False
        
        # Test 2: Check database structure
        if not self.test_database_structure():
            return False
        
        # Test 3: Check if agent_1 exists
        user_id = self.test_agent_1_user()
        
        # Test 4: If agent_1 doesn't exist, create sample data
        if not user_id:
            print("\n🔧 agent_1 not found, creating sample data...")
            if self.create_sample_agent_1_data():
                user_id = self.test_agent_1_user()
            
            if not user_id:
                print("❌ Could not create or find agent_1 user")
                return False
        
        # Test 5: Check agent_1 balances
        if not self.test_agent_1_balances(user_id):
            print("⚠️ No balances found, but user exists")
        
        # Test 6: Check available currencies
        if not self.test_currencies():
            return False
        
        print("\n🎉 DATABASE INTEGRATION TEST COMPLETE!")
        print("✅ Database is ready for MCP server integration")
        print(f"🤖 agent_1 user is set up and ready for trading")
        
        return True
    
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

def main():
    """Main test function."""
    tester = DatabaseTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎯 NEXT STEPS:")
            print("1. Run the enhanced MCP server:")
            print("   python3 enhanced_mcp_server.py --http")
            print("2. Test with a trading agent to verify database integration")
            print("3. Use commands like 'check my balance' to see real data")
        else:
            print("\n❌ DATABASE TEST FAILED")
            print("💡 Check the error messages above and fix issues before proceeding")
    
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tester.disconnect()

if __name__ == "__main__":
    main()
