#!/usr/bin/env python3
"""
kraken_trades_migration.py
Database migration to add Kraken-specific fields to trades table
"""

import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_kraken_trades_migration():
    """Add Kraken-specific fields to the trades table"""
    
    # Find the database file
    db_path = None
    possible_paths = [
        "balance_tracker.db",
        "database.db", 
        "fastapi_backend/balance_tracker.db",
        os.getenv("DATABASE_URL", "").replace("sqlite:///", "")
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        logger.error("Could not find database file. Please specify the correct path.")
        return False
    
    logger.info(f"Running Kraken trades migration on: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if trades table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='trades'
        """)
        
        if not cursor.fetchone():
            logger.error("Trades table not found. Please ensure your database is properly initialized.")
            return False
        
        # Add Kraken-specific columns
        migrations = [
            {
                "column": "execution_price",
                "sql": "ALTER TABLE trades ADD COLUMN execution_price DECIMAL(28, 18)",
                "description": "Actual execution price from Kraken"
            },
            {
                "column": "spread_amount", 
                "sql": "ALTER TABLE trades ADD COLUMN spread_amount DECIMAL(28, 18) DEFAULT 0",
                "description": "Spread amount applied to the trade"
            },
            {
                "column": "kraken_order_ids",
                "sql": "ALTER TABLE trades ADD COLUMN kraken_order_ids TEXT",
                "description": "Comma-separated Kraken order IDs"
            },
            {
                "column": "kraken_execution_data",
                "sql": "ALTER TABLE trades ADD COLUMN kraken_execution_data TEXT",
                "description": "JSON string of Kraken execution details"
            }
        ]
        
        for migration in migrations:
            try:
                # Check if column already exists
                cursor.execute(f"PRAGMA table_info(trades)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if migration["column"] not in columns:
                    logger.info(f"Adding column: {migration['column']}")
                    cursor.execute(migration["sql"])
                    logger.info(f"✅ Added {migration['column']} - {migration['description']}")
                else:
                    logger.info(f"⚠️  Column {migration['column']} already exists")
                    
            except sqlite3.Error as e:
                logger.error(f"❌ Failed to add {migration['column']}: {e}")
                return False
        
        # Create index for Kraken order IDs for faster lookups
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_kraken_order_ids 
                ON trades(kraken_order_ids)
            """)
            logger.info("✅ Created index on kraken_order_ids")
        except sqlite3.Error as e:
            logger.warning(f"Could not create index: {e}")
        
        # Commit changes
        conn.commit()
        logger.info("✅ Kraken trades migration completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        logger.info(f"Trades table now has {len(columns)} columns:")
        for col in columns:
            logger.info(f"  - {col[1]} ({col[2]})")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def create_kraken_test_data():
    """Create some test data to verify the migration works"""
    logger.info("Creating test data is optional and should be done manually")
    logger.info("Test the new fields by executing a trade through the API")


if __name__ == "__main__":
    print("🔄 Kraken Trades Migration")
    print("=" * 50)
    print("This migration adds Kraken-specific fields to the trades table:")
    print("  - execution_price: Actual price from Kraken")
    print("  - spread_amount: Spread markup applied")
    print("  - kraken_order_ids: Kraken order identifiers") 
    print("  - kraken_execution_data: Full execution details")
    print()
    
    confirm = input("Continue with migration? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        exit(0)
    
    success = run_kraken_trades_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Update your trade service to use KrakenIntegratedTradeService")
        print("2. Set up Kraken API credentials in your .env file")
        print("3. Test with ENABLE_LIVE_TRADING=false first")
        print("4. Run a test trade to verify the integration")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and fix any issues.")
        exit(1)
