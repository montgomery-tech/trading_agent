#!/usr/bin/env python3
"""
Database Migration Script - Add Role Support
Run this script to add role column to existing users table
"""

import logging
import sys
from datetime import datetime, timezone

# Add your project imports
from api.database import DatabaseManager
from api.config import settings

logger = logging.getLogger(__name__)

def migrate_database():
    """Add role column to users table and create initial admin user"""
    
    try:
        # Initialize database connection
        db = DatabaseManager(settings.DATABASE_URL)
        db.connect()
        
        print("🔄 Starting database migration...")
        
        # Step 1: Add role column to users table
        print("📝 Adding role column to users table...")
        
        if db.db_type == 'postgresql':
            # Check if role column already exists
            check_query = """
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'role'
            """
            results = db.execute_query(check_query, ())
            
            if not results:
                # Add role column with default value
                alter_query = """
                    ALTER TABLE users 
                    ADD COLUMN role VARCHAR(20) DEFAULT 'trader'
                """
                db.execute_command(alter_query, ())
                print("✅ Role column added to PostgreSQL users table")
            else:
                print("ℹ️  Role column already exists in PostgreSQL users table")
                
        else:
            # SQLite - more complex due to limited ALTER TABLE support
            print("ℹ️  SQLite detected - role will be handled in application logic")
            print("   Note: SQLite ALTER TABLE limitations require app-level role handling")
        
        # Step 2: Check for existing admin users
        print("👤 Checking for existing admin users...")
        
        admin_check_query = """
            SELECT COUNT(*) as admin_count 
            FROM users 
            WHERE role = 'admin' OR email IN ('admin@example.com', 'admin@localhost')
        """
        
        try:
            admin_results = db.execute_query(admin_check_query, ())
            admin_count = admin_results[0]['admin_count'] if admin_results else 0
        except:
            # If role column doesn't exist yet, check by email
            admin_check_query = """
                SELECT COUNT(*) as admin_count 
                FROM users 
                WHERE email IN ('admin@example.com', 'admin@localhost')
            """
            admin_results = db.execute_query(admin_check_query, ())
            admin_count = admin_results[0]['admin_count'] if admin_results else 0
        
        if admin_count == 0:
            print("⚠️  No admin users found!")
            print("\n🛠️  MANUAL ADMIN CREATION REQUIRED:")
            print("   1. Create an admin user through the API:")
            print(f"      POST {settings.API_V1_PREFIX}/auth/register")
            print("   2. Then manually update their role in the database:")
            if db.db_type == 'postgresql':
                print("      UPDATE users SET role = 'admin' WHERE email = 'your-admin-email@domain.com';")
            else:
                print("      Note: Role will be handled in application logic for SQLite")
            print("\n   OR use the admin creation helper below...")
            
            # Offer to create admin user
            create_admin = input("\n❓ Would you like to create an admin user now? (y/n): ").lower().strip()
            
            if create_admin == 'y':
                admin_email = input("Enter admin email: ").strip()
                admin_name = input("Enter admin full name: ").strip()
                
                if admin_email and admin_name:
                    success = create_initial_admin(db, admin_email, admin_name)
                    if success:
                        print("✅ Admin user created successfully!")
                    else:
                        print("❌ Failed to create admin user")
                else:
                    print("❌ Email and name are required")
        else:
            print(f"✅ Found {admin_count} existing admin user(s)")
        
        # Step 3: Update existing users to have default role
        print("🔄 Ensuring all users have roles assigned...")
        
        if db.db_type == 'postgresql':
            update_query = """
                UPDATE users 
                SET role = 'trader' 
                WHERE role IS NULL OR role = ''
            """
            db.execute_command(update_query, ())
            print("✅ Updated existing users with default 'trader' role")
        
        print("\n🎉 Database migration completed successfully!")
        print("\n📋 Next Steps:")
        print("   1. Restart your FastAPI application")
        print("   2. Test admin endpoints with your admin user")
        print("   3. Create additional users through the admin panel")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.error(f"Database migration failed: {e}")
        return False
        
    finally:
        try:
            db.disconnect()
        except:
            pass


def create_initial_admin(db: DatabaseManager, email: str, full_name: str) -> bool:
    """Create initial admin user"""
    try:
        import uuid
        import secrets
        from api.jwt_service import password_service
        
        # Generate admin user data
        user_id = str(uuid.uuid4())
        username = email.split('@')[0].lower() + "_admin"
        temporary_password = generate_secure_password()
        password_hash = password_service.hash_password(temporary_password)
        
        # Parse name
        name_parts = full_name.strip().split()
        first_name = name_parts[0] if name_parts else "Admin"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "User"
        
        # Insert admin user
        if db.db_type == 'postgresql':
            insert_query = """
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, role, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                user_id, username, email, password_hash, first_name, last_name,
                True, True, True, 'admin', datetime.now(timezone.utc), datetime.now(timezone.utc)
            )
        else:
            # SQLite
            insert_query = """
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                user_id, username, email, password_hash, first_name, last_name,
                True, True, True, datetime.now(timezone.utc), datetime.now(timezone.utc)
            )
        
        db.execute_command(insert_query, params)
        
        print(f"\n✅ Admin user created:")
        print(f"   📧 Email: {email}")
        print(f"   👤 Username: {username}")
        print(f"   🔑 Temporary Password: {temporary_password}")
        print(f"   ⚠️  IMPORTANT: Change this password on first login!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        return False


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure password for admin user"""
    import string
    import secrets
    
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]
    
    # Fill remaining length
    for _ in range(length - 4):
        password.append(secrets.choice(chars))
    
    # Shuffle and return
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


if __name__ == "__main__":
    print("🚀 Trading API Database Migration")
    print("=" * 50)
    
    # Run migration
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
