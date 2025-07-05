#!/usr/bin/env python3
"""
User Management Script
Add, view, and manage users in the balance tracking system
"""

import sqlite3
import sys
import re
import hashlib
import uuid
import getpass
from pathlib import Path
from datetime import datetime


class UserManager:
    def __init__(self, db_file="balance_tracker.db"):
        self.db_file = db_file
        self.conn = None
        
    def connect(self):
        """Connect to the database"""
        if not Path(self.db_file).exists():
            print(f"❌ Database file '{self.db_file}' not found!")
            print("Run the setup script first to create the database.")
            sys.exit(1)
            
        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ Connected to database: {self.db_file}")
        
    def disconnect(self):
        if self.conn:
            self.conn.close()
    
    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_username(self, username):
        """Validate username (3+ chars, alphanumeric + underscore)"""
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, ""
    
    def hash_password(self, password):
        """Hash password using SHA-256 (in production, use bcrypt or similar)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def check_user_exists(self, username=None, email=None):
        """Check if user already exists by username or email"""
        cursor = self.conn.cursor()
        
        if username:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return True, f"Username '{username}' already exists"
        
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return True, f"Email '{email}' already exists"
        
        return False, ""
    
    def create_user(self, username, email, password, first_name=None, last_name=None, 
                   is_verified=False, interactive=True):
        """Create a new user"""
        
        # Validate username
        valid, error = self.validate_username(username)
        if not valid:
            if interactive:
                print(f"❌ Invalid username: {error}")
                return None
            else:
                raise ValueError(f"Invalid username: {error}")
        
        # Validate email
        if not self.validate_email(email):
            error = "Invalid email format"
            if interactive:
                print(f"❌ {error}")
                return None
            else:
                raise ValueError(error)
        
        # Check if user exists
        exists, error = self.check_user_exists(username, email)
        if exists:
            if interactive:
                print(f"❌ {error}")
                return None
            else:
                raise ValueError(error)
        
        # Validate password
        if len(password) < 6:
            error = "Password must be at least 6 characters long"
            if interactive:
                print(f"❌ {error}")
                return None
            else:
                raise ValueError(error)
        
        # Create user
        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(password)
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name, 
                    is_verified, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id, username, email, password_hash, first_name, last_name, is_verified
            ))
            
            self.conn.commit()
            
            if interactive:
                print(f"✅ User created successfully!")
                print(f"   User ID: {user_id}")
                print(f"   Username: {username}")
                print(f"   Email: {email}")
                print(f"   Name: {first_name or 'N/A'} {last_name or 'N/A'}")
                print(f"   Verified: {'Yes' if is_verified else 'No'}")
            
            return user_id
            
        except sqlite3.Error as e:
            if interactive:
                print(f"❌ Database error: {e}")
                return None
            else:
                raise
    
    def list_users(self, limit=None, show_details=False):
        """List all users"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT id, username, email, first_name, last_name, is_active, 
                   is_verified, created_at, last_login
            FROM users 
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        if not users:
            print("No users found")
            return
        
        print(f"\n👥 USERS ({len(users)} total)")
        print("=" * 80)
        
        if show_details:
            for user in users:
                print(f"\n🔹 User ID: {user[0]}")
                print(f"   Username: {user[1]}")
                print(f"   Email: {user[2]}")
                print(f"   Name: {user[3] or 'N/A'} {user[4] or 'N/A'}")
                print(f"   Active: {'Yes' if user[5] else 'No'}")
                print(f"   Verified: {'Yes' if user[6] else 'No'}")
                print(f"   Created: {user[7]}")
                print(f"   Last Login: {user[8] or 'Never'}")
        else:
            # Simple table format
            print(f"{'Username':<15} {'Email':<25} {'Name':<20} {'Active':<8} {'Verified':<10} {'Created':<20}")
            print("-" * 100)
            
            for user in users:
                username = user[1]
                email = user[2][:24] if len(user[2]) > 24 else user[2]
                name = f"{user[3] or ''} {user[4] or ''}".strip()[:19]
                active = "Yes" if user[5] else "No"
                verified = "Yes" if user[6] else "No"
                created = user[7][:19] if user[7] else ""
                
                print(f"{username:<15} {email:<25} {name:<20} {active:<8} {verified:<10} {created:<20}")
    
    def get_user_info(self, username_or_id):
        """Get detailed information about a specific user"""
        cursor = self.conn.cursor()
        
        # Try to find by username first, then by ID
        cursor.execute("""
            SELECT id, username, email, first_name, last_name, is_active, 
                   is_verified, created_at, updated_at, last_login
            FROM users 
            WHERE username = ? OR id = ?
        """, (username_or_id, username_or_id))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found: {username_or_id}")
            return None
        
        print(f"\n👤 USER DETAILS")
        print("=" * 50)
        print(f"User ID: {user[0]}")
        print(f"Username: {user[1]}")
        print(f"Email: {user[2]}")
        print(f"First Name: {user[3] or 'Not provided'}")
        print(f"Last Name: {user[4] or 'Not provided'}")
        print(f"Active: {'Yes' if user[5] else 'No'}")
        print(f"Verified: {'Yes' if user[6] else 'No'}")
        print(f"Created: {user[7]}")
        print(f"Updated: {user[8]}")
        print(f"Last Login: {user[9] or 'Never'}")
        
        # Show user balances if any
        user_id = user[0]
        cursor.execute("""
            SELECT currency_code, total_balance, available_balance, locked_balance
            FROM user_balances 
            WHERE user_id = ?
            ORDER BY currency_code
        """, (user_id,))
        
        balances = cursor.fetchall()
        
        if balances:
            print(f"\n💰 BALANCES")
            print(f"{'Currency':<10} {'Total':<15} {'Available':<15} {'Locked':<15}")
            print("-" * 55)
            
            for balance in balances:
                currency = balance[0]
                total = balance[1]
                available = balance[2]
                locked = balance[3]
                
                print(f"{currency:<10} {total:<15} {available:<15} {locked:<15}")
        
        return user[0]  # Return user ID
    
    def update_user_status(self, username_or_id, active=None, verified=None):
        """Update user active/verified status"""
        cursor = self.conn.cursor()
        
        # Find user
        cursor.execute("SELECT id, username FROM users WHERE username = ? OR id = ?", 
                      (username_or_id, username_or_id))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found: {username_or_id}")
            return False
        
        user_id, username = user[0], user[1]
        updates = []
        params = []
        
        if active is not None:
            updates.append("is_active = ?")
            params.append(active)
        
        if verified is not None:
            updates.append("is_verified = ?")
            params.append(verified)
        
        if not updates:
            print("❌ No updates specified")
            return False
        
        # Update user
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        
        try:
            cursor.execute(query, params)
            self.conn.commit()
            
            print(f"✅ User '{username}' updated successfully")
            if active is not None:
                print(f"   Active: {'Yes' if active else 'No'}")
            if verified is not None:
                print(f"   Verified: {'Yes' if verified else 'No'}")
            
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Database error: {e}")
            return False
    
    def interactive_user_creation(self):
        """Interactive user creation wizard"""
        print("\n🆕 CREATE NEW USER")
        print("=" * 30)
        
        # Get username
        while True:
            username = input("Username (3+ chars, letters/numbers/underscore): ").strip()
            if not username:
                print("❌ Username cannot be empty")
                continue
                
            valid, error = self.validate_username(username)
            if not valid:
                print(f"❌ {error}")
                continue
                
            exists, error = self.check_user_exists(username=username)
            if exists:
                print(f"❌ {error}")
                continue
                
            break
        
        # Get email
        while True:
            email = input("Email address: ").strip()
            if not email:
                print("❌ Email cannot be empty")
                continue
                
            if not self.validate_email(email):
                print("❌ Invalid email format")
                continue
                
            exists, error = self.check_user_exists(email=email)
            if exists:
                print(f"❌ {error}")
                continue
                
            break
        
        # Get password
        while True:
            password = getpass.getpass("Password (6+ chars): ")
            if len(password) < 6:
                print("❌ Password must be at least 6 characters long")
                continue
            break
        
        # Get optional info
        first_name = input("First name (optional): ").strip() or None
        last_name = input("Last name (optional): ").strip() or None
        
        verified_input = input("Mark as verified? (y/N): ").strip().lower()
        is_verified = verified_input in ['y', 'yes']
        
        # Confirm creation
        print(f"\n📋 CONFIRM USER CREATION")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Name: {first_name or 'N/A'} {last_name or 'N/A'}")
        print(f"Verified: {'Yes' if is_verified else 'No'}")
        
        confirm = input("\nCreate this user? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            return self.create_user(username, email, password, first_name, last_name, is_verified)
        else:
            print("❌ User creation cancelled")
            return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage users in the balance tracking system")
    parser.add_argument("--db-file", default="balance_tracker.db", 
                       help="Database file path")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add user command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('--username', required=True, help='Username')
    add_parser.add_argument('--email', required=True, help='Email address')
    add_parser.add_argument('--password', help='Password (will prompt if not provided)')
    add_parser.add_argument('--first-name', help='First name')
    add_parser.add_argument('--last-name', help='Last name')
    add_parser.add_argument('--verified', action='store_true', help='Mark user as verified')
    
    # List users command
    list_parser = subparsers.add_parser('list', help='List users')
    list_parser.add_argument('--limit', type=int, help='Limit number of results')
    list_parser.add_argument('--details', action='store_true', help='Show detailed information')
    
    # Show user command
    show_parser = subparsers.add_parser('show', help='Show user details')
    show_parser.add_argument('user', help='Username or user ID')
    
    # Update user command
    update_parser = subparsers.add_parser('update', help='Update user status')
    update_parser.add_argument('user', help='Username or user ID')
    update_parser.add_argument('--activate', action='store_true', help='Activate user')
    update_parser.add_argument('--deactivate', action='store_true', help='Deactivate user')
    update_parser.add_argument('--verify', action='store_true', help='Verify user')
    update_parser.add_argument('--unverify', action='store_true', help='Unverify user')
    
    # Interactive command
    subparsers.add_parser('interactive', help='Interactive user creation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = UserManager(args.db_file)
    
    try:
        manager.connect()
        
        if args.command == 'add':
            password = args.password
            if not password:
                password = getpass.getpass("Password: ")
            
            manager.create_user(
                args.username, args.email, password,
                args.first_name, args.last_name, args.verified
            )
            
        elif args.command == 'list':
            manager.list_users(args.limit, args.details)
            
        elif args.command == 'show':
            manager.get_user_info(args.user)
            
        elif args.command == 'update':
            active = None
            if args.activate:
                active = True
            elif args.deactivate:
                active = False
            
            verified = None
            if args.verify:
                verified = True
            elif args.unverify:
                verified = False
            
            manager.update_user_status(args.user, active, verified)
            
        elif args.command == 'interactive':
            manager.interactive_user_creation()
        
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        manager.disconnect()


if __name__ == "__main__":
    main()
