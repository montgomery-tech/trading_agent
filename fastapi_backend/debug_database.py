#!/usr/bin/env python3
"""
Debug database to check if spread fields exist and what the actual database structure is
"""

import sqlite3
import os
from pathlib import Path

def check_database_file():
    """Check which database file exists and is being used"""
    print("🔍 Checking for database files...")
    print("-" * 50)
    
    possible_dbs = [
        "balance_tracker.db",
        "database.db",
        "fastapi.db",
        "app.db",
        "data.db"
    ]
    
    for db_file in possible_dbs:
        if os.path.exists(db_file):
            size = os.path.getsize(db_file) / 1024  # Size in KB
            print(f"✅ Found: {db_file} ({size:.1f} KB)")
            
            # Check if it has tables
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"   Tables: {[t[0] for t in tables]}")
                conn.close()
            except Exception as e:
                print(f"   Error reading: {e}")
    
    # Check .env for DATABASE_URL
    if os.path.exists(".env"):
        print("\n📄 Checking .env for DATABASE_URL...")
        with open(".env", "r") as f:
            for line in f:
                if "DATABASE_URL" in line and not line.strip().startswith("#"):
                    print(f"   {line.strip()}")

def check_trading_pairs_table(db_path="balance_tracker.db"):
    """Check the structure of trading_pairs table"""
    print(f"\n🔍 Checking trading_pairs table in {db_path}...")
    print("-" * 50)
    
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(trading_pairs)")
        columns = cursor.fetchall()
        
        print("📊 Columns in trading_pairs table:")
        has_spread = False
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            if "spread" in col_name.lower():
                print(f"   ✅ {col_name} ({col_type})")
                has_spread = True
            else:
                print(f"   • {col_name} ({col_type})")
        
        if not has_spread:
            print("\n❌ No spread_percentage column found!")
        
        # Check sample data
        cursor.execute("SELECT COUNT(*) FROM trading_pairs")
        count = cursor.fetchone()[0]
        print(f"\n📈 Total trading pairs: {count}")
        
        if count > 0:
            # Try to select with spread_percentage
            try:
                cursor.execute("SELECT symbol, spread_percentage FROM trading_pairs LIMIT 3")
                rows = cursor.fetchall()
                print("\n📊 Sample spreads:")
                for symbol, spread in rows:
                    print(f"   {symbol}: {float(spread)*100:.2f}%")
            except sqlite3.OperationalError as e:
                if "no such column" in str(e):
                    print("\n❌ spread_percentage column doesn't exist!")
                    print("   The migration may not have run on the correct database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def check_api_database_config():
    """Check what database the API is actually using"""
    print("\n🔍 Checking API database configuration...")
    print("-" * 50)
    
    # Check api/config.py or api/database.py
    config_files = [
        "api/config.py",
        "api/database.py",
        "api/core/config.py"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n📄 Checking {config_file}...")
            with open(config_file, "r") as f:
                content = f.read()
                
            # Look for database configuration
            for line in content.split('\n'):
                if "DATABASE" in line or "sqlite" in line or ".db" in line:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        print(f"   {stripped[:100]}...")

def suggest_fix():
    """Suggest how to fix the issue"""
    print("\n💡 Suggested fixes:")
    print("-" * 50)
    print("1. The API might be using a different database file than the migration")
    print("2. Try running the migration on the correct database:")
    print("   python3 add_spread_fields_migration.py")
    print("3. Or manually add the column:")
    print('   sqlite3 balance_tracker.db "ALTER TABLE trading_pairs ADD COLUMN spread_percentage DECIMAL(10,6) DEFAULT 0.02;"')
    print("4. Check if the API is using PostgreSQL instead of SQLite")

if __name__ == "__main__":
    print("🔧 Database Debug Tool")
    print("=" * 50)
    
    check_database_file()
    check_trading_pairs_table()
    check_api_database_config()
    suggest_fix()
    
    print("\n✅ Debug complete!")
