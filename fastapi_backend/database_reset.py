#!/usr/bin/env python3
"""
Database Reset Script
Properly closes all connections and resets the database state
"""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def reset_database():
    """Reset database connections and transactions"""
    
    print("🔄 Resetting database...")
    
    try:
        # Connect directly to PostgreSQL with autocommit
        conn = psycopg2.connect(
            host="localhost",
            database="balance_tracker", 
            user="garrettroth",
            autocommit=True
        )
        
        cursor = conn.cursor()
        
        # Rollback any pending transactions
        print("📊 Rolling back any pending transactions...")
        cursor.execute("ROLLBACK;")
        
        # Check users table structure
        print("🔍 Checking users table structure...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("📋 Current users table columns:")
        for col in columns:
            print(f"   {col[0]} ({col[1]}) - nullable: {col[2]}")
        
        # Check if must_change_password exists and add if needed
        column_names = [col[0] for col in columns]
        
        if 'must_change_password' not in column_names:
            print("➕ Adding must_change_password column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN must_change_password BOOLEAN DEFAULT TRUE;
            """)
            print("✅ Added must_change_password column")
        else:
            print("✅ must_change_password column already exists")
        
        if 'password_changed_at' not in column_names:
            print("➕ Adding password_changed_at column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN password_changed_at TIMESTAMP;
            """)
            print("✅ Added password_changed_at column")
        else:
            print("✅ password_changed_at column already exists")
        
        # Test a simple query
        print("🧪 Testing database operations...")
        cursor.execute("SELECT COUNT(*) FROM users;")
        count = cursor.fetchone()[0]
        print(f"✅ Database working - {count} users in table")
        
        cursor.close()
        conn.close()
        
        print("✅ Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)
