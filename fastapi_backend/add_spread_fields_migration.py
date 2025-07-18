#!/usr/bin/env python3
"""
Database migration to add spread functionality fields
Run this script to update your database schema for spread support
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def run_migration(db_path="balance_tracker.db"):
    """Run the spread fields migration"""
    
    print("🔄 Running Spread Fields Migration")
    print("=" * 50)
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Database '{db_path}' not found!")
        print("Please ensure the database exists before running migration.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("📊 Adding spread fields to database...")
        
        # 1. Add spread_percentage to trading_pairs table
        print("\n1️⃣ Adding spread_percentage to trading_pairs table...")
        try:
            cursor.execute("""
                ALTER TABLE trading_pairs 
                ADD COLUMN spread_percentage DECIMAL(10, 6) DEFAULT 0.02
            """)
            print("   ✅ Added spread_percentage column (default: 2%)")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️ spread_percentage column already exists")
            else:
                raise
        
        # 2. Add execution_price to trades table
        print("\n2️⃣ Adding execution_price to trades table...")
        try:
            cursor.execute("""
                ALTER TABLE trades 
                ADD COLUMN execution_price DECIMAL(32, 8)
            """)
            print("   ✅ Added execution_price column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️ execution_price column already exists")
            else:
                raise
        
        # 3. Add client_price to trades table
        print("\n3️⃣ Adding client_price to trades table...")
        try:
            cursor.execute("""
                ALTER TABLE trades 
                ADD COLUMN client_price DECIMAL(32, 8)
            """)
            print("   ✅ Added client_price column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️ client_price column already exists")
            else:
                raise
        
        # 4. Add spread_amount to trades table
        print("\n4️⃣ Adding spread_amount to trades table...")
        try:
            cursor.execute("""
                ALTER TABLE trades 
                ADD COLUMN spread_amount DECIMAL(32, 8)
            """)
            print("   ✅ Added spread_amount column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️ spread_amount column already exists")
            else:
                raise
        
        # 5. Update existing trades to populate new fields (if any exist)
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
        
        # 6. Set default spread percentages for existing trading pairs
        print("\n6️⃣ Setting default spreads for trading pairs...")
        cursor.execute("""
            UPDATE trading_pairs 
            SET spread_percentage = CASE
                WHEN quote_currency = 'USD' THEN 0.02  -- 2% for USD pairs
                WHEN base_currency IN ('BTC', 'ETH') THEN 0.015  -- 1.5% for major cryptos
                ELSE 0.025  -- 2.5% for others
            END
            WHERE spread_percentage IS NULL OR spread_percentage = 0.02
        """)
        updated_pairs = cursor.rowcount
        print(f"   ✅ Updated spread for {updated_pairs} trading pairs")
        
        # 7. Create a migration tracking table if it doesn't exist
        print("\n7️⃣ Creating migration tracking...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Record this migration
        cursor.execute("""
            INSERT OR IGNORE INTO db_migrations (name, applied_at) 
            VALUES ('add_spread_fields', ?)
        """, (datetime.now(),))
        
        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show current trading pairs with spreads
        print("\n📊 Current Trading Pairs with Spreads:")
        cursor.execute("""
            SELECT symbol, spread_percentage * 100 as spread_pct 
            FROM trading_pairs 
            WHERE is_active = 1
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


def verify_migration(db_path="balance_tracker.db"):
    """Verify the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check trading_pairs columns
        cursor.execute("PRAGMA table_info(trading_pairs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'spread_percentage' in columns:
            print("✅ trading_pairs.spread_percentage exists")
        else:
            print("❌ trading_pairs.spread_percentage missing")
        
        # Check trades columns
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        
        required_columns = ['execution_price', 'client_price', 'spread_amount']
        for col in required_columns:
            if col in columns:
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
        print("\n🎉 Database is ready for spread functionality!")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)
