#!/usr/bin/env python3
"""
Database Migration for Forced Password Change Features
Task 2.1b: Adds columns needed for forced password change system
"""

import os
import sys
from pathlib import Path

def main():
    """Run database migration for password features"""
    
    print("🗄️  Database Migration for Forced Password Change System")
    print("========================================================")
    
    database_url = os.getenv('DATABASE_URL', 'postgresql://garrettroth@localhost:5432/balance_tracker')
    
    if database_url.startswith(('postgresql', 'postgres')):
        migrate_postgresql(database_url)
    elif database_url.startswith('sqlite'):
        migrate_sqlite(database_url.replace('sqlite:///', ''))
    else:
        print(f"❌ Unsupported database type: {database_url}")
        return False
    
    return True


def migrate_postgresql(database_url):
    """Migrate PostgreSQL database"""
    print("🔧 Migrating PostgreSQL database for password features...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Add password-related columns if they don't exist
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT false",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'trader'"
        ]
        
        for migration in migrations:
            try:
                cursor.execute(migration)
                print(f"✅ Applied: {migration}")
            except Exception as e:
                print(f"⚠️  Warning: {migration} - {e}")
        
        # Update existing admin users to not require password change
        cursor.execute("""
            UPDATE users 
            SET must_change_password = false 
            WHERE role = 'admin' AND must_change_password IS NULL
        """)
        print("✅ Updated existing admin users")
        
        # Update users created by admin system to require password change
        cursor.execute("""
            UPDATE users 
            SET must_change_password = true 
            WHERE must_change_password IS NULL AND created_at > '2025-07-12'
        """)
        print("✅ Set password change requirement for new users")
        
        conn.commit()
        print("✅ PostgreSQL migration completed successfully")
        
    except Exception as e:
        print(f"❌ PostgreSQL migration failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True


def migrate_sqlite(db_path):
    """Migrate SQLite database"""
    print(f"🔧 Migrating SQLite database: {db_path}")
    
    try:
        import sqlite3
        
        if not Path(db_path).exists():
            print(f"❌ Database file not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add password-related columns if they don't exist
        migrations = [
            "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN password_reset_token TEXT",
            "ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP",
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'trader'"
        ]
        
        for migration in migrations:
            try:
                cursor.execute(migration)
                print(f"✅ Applied: {migration}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⏩ Skipped (already exists): {migration}")
                else:
                    print(f"⚠️  Warning: {migration} - {e}")
        
        # Update existing admin users
        cursor.execute("""
            UPDATE users 
            SET must_change_password = 0 
            WHERE role = 'admin'
        """)
        
        # Update users created by admin system
        cursor.execute("""
            UPDATE users 
            SET must_change_password = 1 
            WHERE must_change_password IS NULL AND datetime(created_at) > '2025-07-12'
        """)
        
        conn.commit()
        print("✅ SQLite migration completed successfully")
        
    except Exception as e:
        print(f"❌ SQLite migration failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\n📋 What was added:")
        print("   • must_change_password column (forces password change)")
        print("   • password_changed_at column (tracks when password was last changed)")
        print("   • password_reset_token column (for password reset functionality)")
        print("   • password_reset_expires column (token expiration)")
        print("   • role column (if missing)")
        print("\n🔧 Next steps:")
        print("   1. Add auth routes to main.py")
        print("   2. Test login with existing users")
        print("   3. Test forced password change flow")
        print("")
        
    sys.exit(0 if success else 1)
