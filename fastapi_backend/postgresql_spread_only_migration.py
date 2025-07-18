#!/usr/bin/env python3
"""
PostgreSQL migration to add spread_percentage to trading_pairs only
(since trades table doesn't exist yet)
"""

import os
import psycopg2
from urllib.parse import urlparse
from decouple import config

def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL"""
    database_url = config('DATABASE_URL', default='')
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env")
        return None
    
    try:
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        )
        
        print(f"✅ Connected to PostgreSQL database: {parsed.path[1:]}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return None

def check_tables(conn):
    """Check which tables exist in PostgreSQL"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def run_migration():
    """Run the PostgreSQL migration for spread_percentage only"""
    print("🔄 Running PostgreSQL Spread Migration (trading_pairs only)")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check existing tables
        tables = check_tables(conn)
        print(f"\n📊 Existing tables: {tables}")
        
        if 'trading_pairs' not in tables:
            print("❌ trading_pairs table doesn't exist in PostgreSQL!")
            print("   The PostgreSQL database might not be fully set up")
            return False
        
        # Start transaction
        conn.autocommit = False
        
        # Add spread_percentage to trading_pairs
        print("\n1️⃣ Adding spread_percentage to trading_pairs table...")
        try:
            cursor.execute("""
                ALTER TABLE trading_pairs 
                ADD COLUMN IF NOT EXISTS spread_percentage DECIMAL(10, 6) DEFAULT 0.02
            """)
            print("   ✅ Added spread_percentage column (default: 2%)")
        except psycopg2.errors.DuplicateColumn:
            print("   ⚠️ spread_percentage column already exists")
            conn.rollback()
            return True  # Already done
        
        # Set different spreads for different pairs
        print("\n2️⃣ Setting default spreads for trading pairs...")
        cursor.execute("""
            UPDATE trading_pairs 
            SET spread_percentage = CASE
                WHEN quote_currency = 'USD' THEN 0.02
                WHEN base_currency IN ('BTC', 'ETH') THEN 0.015
                ELSE 0.025
            END
            WHERE spread_percentage = 0.02
        """)
        updated_pairs = cursor.rowcount
        print(f"   ✅ Updated spread for {updated_pairs} trading pairs")
        
        # Commit transaction
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show current trading pairs with spreads
        print("\n📊 Current Trading Pairs with Spreads:")
        cursor.execute("""
            SELECT symbol, spread_percentage * 100 as spread_pct 
            FROM trading_pairs 
            WHERE is_active = true
            ORDER BY symbol
        """)
        
        pairs = cursor.fetchall()
        if pairs:
            for symbol, spread_pct in pairs:
                print(f"   {symbol}: {spread_pct:.2f}%")
        else:
            print("   No active trading pairs found")
        
        # Note about trades table
        if 'trades' not in tables:
            print("\n⚠️ Note: trades table doesn't exist yet")
            print("   Spread fields for trades will need to be added when the table is created")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def verify_migration():
    """Verify the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Check if spread_percentage exists
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = 'trading_pairs' 
            AND column_name = 'spread_percentage'
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"✅ trading_pairs.spread_percentage exists ({result[1]})")
            
            # Test by selecting
            cursor.execute("SELECT COUNT(*) FROM trading_pairs WHERE spread_percentage IS NOT NULL")
            count = cursor.fetchone()[0]
            print(f"✅ {count} trading pairs have spread values")
        else:
            print("❌ trading_pairs.spread_percentage missing")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    # Run migration
    success = run_migration()
    
    if success:
        # Verify migration
        verify_migration()
        print("\n🎉 PostgreSQL spread_percentage is ready!")
        print("\n📋 Next steps:")
        print("1. Restart your FastAPI app")
        print("2. Test with: python3 test_spread_functionality.py")
        print("\nNote: When you create the trades table later, remember to add:")
        print("  - execution_price DECIMAL(32, 8)")
        print("  - client_price DECIMAL(32, 8)")
        print("  - spread_amount DECIMAL(32, 8)")
    else:
        print("\n❌ Migration failed")
