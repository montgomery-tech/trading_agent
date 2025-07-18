#!/usr/bin/env python3
"""
PostgreSQL migration to add spread functionality fields
"""

import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime
from decouple import config

def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL"""
    database_url = config('DATABASE_URL', default='')
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env")
        return None
    
    if 'postgresql' not in database_url and 'postgres' not in database_url:
        print(f"❌ DATABASE_URL is not PostgreSQL: {database_url[:50]}...")
        return None
    
    try:
        # Parse the database URL
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

def run_migration():
    """Run the PostgreSQL migration"""
    print("🔄 Running PostgreSQL Spread Fields Migration")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Start transaction
        conn.autocommit = False
        
        print("\n📊 Adding spread fields to database...")
        
        # 1. Add spread_percentage to trading_pairs
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
            conn.autocommit = False
        
        # 2. Add execution_price to trades
        print("\n2️⃣ Adding execution_price to trades table...")
        try:
            cursor.execute("""
                ALTER TABLE trades 
                ADD COLUMN IF NOT EXISTS execution_price DECIMAL(32, 8)
            """)
            print("   ✅ Added execution_price column")
        except psycopg2.errors.DuplicateColumn:
            print("   ⚠️ execution_price column already exists")
        
        # 3. Add client_price to trades
        print("\n3️⃣ Adding client_price to trades table...")
        try:
            cursor.execute("""
                ALTER TABLE trades 
                ADD COLUMN IF NOT EXISTS client_price DECIMAL(32, 8)
            """)
            print("   ✅ Added client_price column")
        except psycopg2.errors.DuplicateColumn:
            print("   ⚠️ client_price column already exists")
        
        # 4. Add spread_amount to trades
        print("\n4️⃣ Adding spread_amount to trades table...")
        try:
            cursor.execute("""
                ALTER TABLE trades 
                ADD COLUMN IF NOT EXISTS spread_amount DECIMAL(32, 8)
            """)
            print("   ✅ Added spread_amount column")
        except psycopg2.errors.DuplicateColumn:
            print("   ⚠️ spread_amount column already exists")
        
        # 5. Update existing trades
        print("\n5️⃣ Updating existing trades...")
        cursor.execute("""
            UPDATE trades 
            SET execution_price = price,
                client_price = price,
                spread_amount = 0
            WHERE execution_price IS NULL
        """)
        updated_rows = cursor.rowcount
        print(f"   ✅ Updated {updated_rows} existing trade records")
        
        # 6. Set spreads for trading pairs
        print("\n6️⃣ Setting default spreads for trading pairs...")
        cursor.execute("""
            UPDATE trading_pairs 
            SET spread_percentage = CASE
                WHEN quote_currency = 'USD' THEN 0.02
                WHEN base_currency IN ('BTC', 'ETH') THEN 0.015
                ELSE 0.025
            END
            WHERE spread_percentage IS NULL OR spread_percentage = 0.02
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
        for symbol, spread_pct in pairs:
            print(f"   {symbol}: {spread_pct:.2f}%")
        
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
        
        # Check trading_pairs columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trading_pairs' 
            AND column_name = 'spread_percentage'
        """)
        
        if cursor.fetchone():
            print("✅ trading_pairs.spread_percentage exists")
        else:
            print("❌ trading_pairs.spread_percentage missing")
        
        # Check trades columns
        for col in ['execution_price', 'client_price', 'spread_amount']:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' 
                AND column_name = %s
            """, (col,))
            
            if cursor.fetchone():
                print(f"✅ trades.{col} exists")
            else:
                print(f"❌ trades.{col} missing")
        
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
        print("\n🎉 PostgreSQL database is ready for spread functionality!")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        print("\n💡 Make sure:")
        print("1. DATABASE_URL is set correctly in .env")
        print("2. PostgreSQL server is running")
        print("3. You have permission to alter tables")
