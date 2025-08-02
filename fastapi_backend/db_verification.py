#!/usr/bin/env python3
"""
Database Verification Script
Check current state of currencies and trading_pairs tables
"""

import os
import sys
from decouple import config
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_state():
    """Check the current state of the database"""
    
    print("🔍 DATABASE STATE VERIFICATION")
    print("=" * 50)
    
    # Get database URL from environment
    database_url = config('DATABASE_URL', default='')
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        return False
    
    print(f"📋 Database URL: {database_url}")
    
    # Determine database type
    if database_url.startswith('postgresql'):
        return check_postgresql_state(database_url)
    elif database_url.startswith('sqlite'):
        return check_sqlite_state(database_url)
    else:
        print(f"❌ Unsupported database type in URL: {database_url}")
        return False

def check_postgresql_state(database_url):
    """Check PostgreSQL database state"""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(database_url)
        
        print("🐘 Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        )
        
        cursor = conn.cursor()
        
        # Check if tables exist
        print("\n📊 Checking table existence...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('currencies', 'trading_pairs')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Existing tables: {existing_tables}")
        
        # Check currencies table
        if 'currencies' in existing_tables:
            print("\n💰 Checking currencies table...")
            cursor.execute("SELECT COUNT(*) FROM currencies")
            currency_count = cursor.fetchone()[0]
            print(f"   Total currencies: {currency_count}")
            
            cursor.execute("SELECT code, name, is_fiat FROM currencies ORDER BY is_fiat DESC, code")
            currencies = cursor.fetchall()
            for code, name, is_fiat in currencies:
                currency_type = "Fiat" if is_fiat else "Crypto"
                print(f"   - {code}: {name} ({currency_type})")
        
        # Check trading_pairs table
        if 'trading_pairs' in existing_tables:
            print("\n📈 Checking trading_pairs table...")
            cursor.execute("SELECT COUNT(*) FROM trading_pairs")
            pairs_count = cursor.fetchone()[0]
            print(f"   Total trading pairs: {pairs_count}")
            
            cursor.execute("""
                SELECT symbol, base_currency, quote_currency, is_active 
                FROM trading_pairs 
                ORDER BY symbol
            """)
            pairs = cursor.fetchall()
            for symbol, base, quote, is_active in pairs:
                status = "Active" if is_active else "Inactive"
                print(f"   - {symbol}: {base}/{quote} ({status})")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ PostgreSQL verification complete!")
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def check_sqlite_state(database_url):
    """Check SQLite database state"""
    try:
        import sqlite3
        
        # Extract file path from URL
        db_path = database_url.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            print(f"❌ SQLite database file not found: {db_path}")
            return False
        
        print(f"📁 Connecting to SQLite: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if tables exist
        print("\n📊 Checking table existence...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('currencies', 'trading_pairs')
            ORDER BY name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Existing tables: {existing_tables}")
        
        # Check currencies table
        if 'currencies' in existing_tables:
            print("\n💰 Checking currencies table...")
            cursor.execute("SELECT COUNT(*) FROM currencies")
            currency_count = cursor.fetchone()[0]
            print(f"   Total currencies: {currency_count}")
            
            cursor.execute("SELECT code, name, is_fiat FROM currencies ORDER BY is_fiat DESC, code")
            currencies = cursor.fetchall()
            for row in currencies:
                currency_type = "Fiat" if row['is_fiat'] else "Crypto"
                print(f"   - {row['code']}: {row['name']} ({currency_type})")
        
        # Check trading_pairs table
        if 'trading_pairs' in existing_tables:
            print("\n📈 Checking trading_pairs table...")
            cursor.execute("SELECT COUNT(*) FROM trading_pairs")
            pairs_count = cursor.fetchone()[0]
            print(f"   Total trading pairs: {pairs_count}")
            
            cursor.execute("""
                SELECT symbol, base_currency, quote_currency, is_active 
                FROM trading_pairs 
                ORDER BY symbol
            """)
            pairs = cursor.fetchall()
            for row in pairs:
                status = "Active" if row['is_active'] else "Inactive"
                print(f"   - {row['symbol']}: {row['base_currency']}/{row['quote_currency']} ({status})")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ SQLite verification complete!")
        return True
        
    except Exception as e:
        print(f"❌ SQLite connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Starting database verification...")
    
    success = check_database_state()
    
    if success:
        print("\n🎉 Database verification completed successfully!")
        print("\nNext steps:")
        print("1. If data exists, proceed with fixing the API endpoints")
        print("2. If data is missing, run the migration script first")
    else:
        print("\n❌ Database verification failed!")
        print("Please check your database connection and setup.")
    
    sys.exit(0 if success else 1)
