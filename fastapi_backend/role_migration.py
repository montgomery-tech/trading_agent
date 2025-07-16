#!/usr/bin/env python3
"""
Database Role Migration Script
Updates existing user roles to the new three-role system
"""

import logging
from datetime import datetime, timezone

# Add your project imports
from api.database import DatabaseManager
from api.config import settings

logger = logging.getLogger(__name__)

def migrate_user_roles():
    """Migrate existing user roles to new system"""
    
    try:
        # Initialize database connection
        db = DatabaseManager(settings.DATABASE_URL)
        db.connect()
        
        print("🔄 Starting role migration...")
        
        # Step 1: Check current role distribution
        print("📊 Current role distribution:")
        role_query = """
            SELECT COALESCE(role, 'NULL') as role, COUNT(*) as count 
            FROM users 
            GROUP BY COALESCE(role, 'NULL')
            ORDER BY count DESC
        """
        current_roles = db.execute_query(role_query, ())
        
        for row in current_roles:
            print(f"   {row['role']}: {row['count']} users")
        
        # Step 2: Update 'user' roles to 'viewer'
        print("\n🔄 Updating 'user' roles to 'viewer'...")
        
        if db.db_type == 'postgresql':
            update_user_query = "UPDATE users SET role = %s WHERE role = %s OR role IS NULL"
            params = ('viewer', 'user')
        else:
            update_user_query = "UPDATE users SET role = ? WHERE role = ? OR role IS NULL"
            params = ('viewer', 'user')
        
        db.execute_command(update_user_query, params)
        
        # Step 3: Ensure admin user has admin role
        print("🔑 Ensuring admin user has admin role...")
        
        if db.db_type == 'postgresql':
            admin_query = "UPDATE users SET role = %s WHERE email = %s"
            params = ('admin', 'garrett@montgomery-tech.net')
        else:
            admin_query = "UPDATE users SET role = ? WHERE email = ?"
            params = ('admin', 'garrett@montgomery-tech.net')
        
        db.execute_command(admin_query, params)
        
        # Step 4: Update any remaining 'read_only' roles to 'viewer'
        print("👁️  Updating 'read_only' roles to 'viewer'...")
        
        if db.db_type == 'postgresql':
            readonly_query = "UPDATE users SET role = %s WHERE role = %s"
            params = ('viewer', 'read_only')
        else:
            readonly_query = "UPDATE users SET role = ? WHERE role = ?"
            params = ('viewer', 'read_only')
        
        db.execute_command(readonly_query, params)
        
        # Step 5: Show updated role distribution
        print("\n✅ Updated role distribution:")
        updated_roles = db.execute_query(role_query, ())
        
        for row in updated_roles:
            print(f"   {row['role']}: {row['count']} users")
        
        # Step 6: Verify admin user
        print("\n🔍 Verifying admin user...")
        admin_check_query = """
            SELECT username, email, role, is_active 
            FROM users 
            WHERE role = 'admin'
        """
        admin_users = db.execute_query(admin_check_query, ())
        
        if admin_users:
            for admin in admin_users:
                print(f"   ✅ Admin: {admin['username']} ({admin['email']}) - Active: {admin['is_active']}")
        else:
            print("   ⚠️  No admin users found!")
        
        print("\n🎉 Role migration completed successfully!")
        
        print("\n📋 Next Steps:")
        print("   1. Update your code files with the role fixes")
        print("   2. Restart your FastAPI application")
        print("   3. Test admin login with new role system")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.error(f"Role migration failed: {e}")
        return False
        
    finally:
        try:
            db.disconnect()
        except:
            pass


if __name__ == "__main__":
    print("🚀 Trading API Role Migration")
    print("=" * 50)
    
    # Run migration
    success = migrate_user_roles()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        exit(0)
    else:
        print("\n❌ Migration failed!")
        exit(1)
