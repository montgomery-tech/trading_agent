#!/usr/bin/env python3
"""
Debug script to test the admin user listing directly
This helps identify the exact issue with the user listing endpoint
"""

import os
import sys
sys.path.append('.')

from api.database import DatabaseManager
from datetime import datetime

def test_user_listing():
    """Test the user listing query directly"""

    print("🔍 Debug: Testing Admin User Listing")
    print("=" * 40)

    try:
        # Get database connection
        database_url = os.getenv('DATABASE_URL', 'postgresql://garrettroth@localhost:5432/balance_tracker')
        print(f"Database URL: {database_url}")

        db = DatabaseManager(database_url)
        db.connect()

        print("✅ Database connected successfully")

        # Test the exact query from admin.py
        print("\n🧪 Testing user listing query...")

        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, first_name, last_name,
                       is_active, created_at, last_login
                FROM users
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            print(f"✅ Query executed successfully, found {len(rows)} users")

            if rows:
                print("\n📋 Users found:")
                for i, row in enumerate(rows):
                    print(f"   {i+1}. ID: {row['id']}")
                    print(f"      Username: {row['username']}")
                    print(f"      Email: {row['email']}")
                    print(f"      First Name: {row['first_name']}")
                    print(f"      Last Name: {row['last_name']}")
                    print(f"      Active: {row['is_active']}")
                    print(f"      Created: {row['created_at']}")
                    print(f"      Last Login: {row['last_login']}")

                    # Test full_name construction
                    full_name = None
                    if row['first_name'] and row['last_name']:
                        full_name = f"{row['first_name']} {row['last_name']}"
                    elif row['first_name']:
                        full_name = row['first_name']
                    elif row['last_name']:
                        full_name = row['last_name']

                    print(f"      Constructed Full Name: {full_name}")
                    print("")

            else:
                print("❌ No users found in database")

                # Let's check if the table exists
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'users'
                """)

                table_exists = cursor.fetchone()
                if table_exists:
                    print("✅ Users table exists")
                else:
                    print("❌ Users table does not exist!")

                    # List all tables
                    cursor.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                    """)

                    tables = cursor.fetchall()
                    print(f"📋 Available tables: {[table[0] for table in tables]}")

        db.disconnect()
        print("\n✅ Database debugging completed successfully")
        return True

    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_user_listing()
    if success:
        print("\n🎯 The database query works fine.")
        print("   The issue is likely in the admin route error handling.")
        print("   Check your server logs for the exact error.")
    else:
        print("\n⚠️  Database query failed.")
        print("   This explains why the admin user listing isn't working.")
