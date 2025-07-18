#!/usr/bin/env python3
"""
Fixed PostgreSQL migration for spread_percentage
"""

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

def run_migration():
    """Run the PostgreSQL migration"""
    print("🔄 Running PostgreSQL Spread Migration")
    print("=" * 50)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        # Use autocommit mode to avoid transaction issues
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if column already exists
        print("\n🔍 Checking if spread_percentage already exists...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trading_pairs' 
            AND column_name = 'spread_percentage'
        """)
        
        if cursor.fetchone():
            print("   ⚠️ spread_percentage column already exists!")
            print("   ✅ No migration needed")
            
            # Show current spreads
            cursor.execute("""
                SELECT symbol, spread_percentage * 100 as spread_pct 
                FROM trading_pairs 
                WHERE is_active = true
                ORDER BY symbol
            """)
            
            pairs = cursor.fetchall()
            if pairs:
                print("\n📊 Current Trading Pairs with Spreads:")
                for symbol, spread_pct in pairs:
                    print(f"   {symbol}: {spread_pct:.2f}%")
            
            cursor.close()
            conn.close()
            return True
        
        # Add the column
        print("\n1️⃣ Adding spread_percentage to trading_pairs table...")
        cursor.execute("""
            ALTER TABLE trading_pairs 
            ADD COLUMN spread_percentage DECIMAL(10, 6) DEFAULT 0.02
        """)
        print("   ✅ Added spread_percentage column (default: 2%)")
        
        # Update spreads
        print("\n2️⃣ Setting default spreads for trading pairs...")
        cursor.execute("""
            UPDATE trading_pairs 
            SET spread_percentage = CASE
                WHEN quote_currency = 'USD' THEN 0.02
                WHEN base_currency IN ('BTC', 'ETH') THEN 0.015
                ELSE 0.025
            END
        """)
        updated_pairs = cursor.rowcount
        print(f"   ✅ Updated spread for {updated_pairs} trading pairs")
        
        # Show results
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
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except psycopg2.errors.DuplicateColumn as e:
        print("   ⚠️ Column already exists (this is OK)")
        return True
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    # Run migration
    success = run_migration()
    
    if success:
        print("\n🎉 PostgreSQL is ready for spread functionality!")
        print("\n📋 Next steps:")
        print("1. Restart your FastAPI app: python3 main.py")
        print("2. Test with: python3 test_spread_functionality.py")
    else:
        print("\n❌ Please check the errors above")
