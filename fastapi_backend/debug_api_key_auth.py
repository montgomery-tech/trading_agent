#!/usr/bin/env python3
"""
Debug API Key Authentication
Diagnoses why API key authentication is failing
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse
from passlib.context import CryptContext

# Configure bcrypt for API key verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def debug_api_key_auth():
    """Debug API key authentication issues"""
    
    # The API key that should work
    test_api_key = "btapi_WIzZEd7BYB1TBBIy_CTonaCJy7Id4yNfsABWNeMVW7ww7x9qj"
    expected_key_id = "btapi_WIzZEd7BYB1TBBIy"
    
    print("🔍 API Key Authentication Debug")
    print("=" * 50)
    print(f"Testing API Key: {test_api_key}")
    print(f"Expected Key ID: {expected_key_id}")
    print("")
    
    # Database connection
    database_url = os.getenv('DATABASE_URL', 'postgresql://garrettroth@localhost:5432/balance_tracker')
    
    try:
        # Connect to PostgreSQL
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        )
        
        print("✅ Connected to PostgreSQL database")
        
        cursor = conn.cursor()
        
        # Step 1: Check if the api_keys table exists and has data
        print("\n📋 Step 1: Check API keys table")
        print("-" * 30)
        
        cursor.execute("SELECT COUNT(*) FROM api_keys")
        total_keys = cursor.fetchone()[0]
        print(f"Total API keys in database: {total_keys}")
        
        if total_keys == 0:
            print("❌ No API keys found in database!")
            print("The database tables exist but are empty.")
            return False
        
        # Step 2: Look for the specific key ID
        print(f"\n📋 Step 2: Look for key ID '{expected_key_id}'")
        print("-" * 30)
        
        cursor.execute("""
            SELECT key_id, key_hash, is_active, user_id, name, created_at
            FROM api_keys 
            WHERE key_id = %s
        """, (expected_key_id,))
        
        key_record = cursor.fetchone()
        
        if not key_record:
            print(f"❌ Key ID '{expected_key_id}' not found in database!")
            
            # Show what keys do exist
            cursor.execute("SELECT key_id, name, is_active FROM api_keys LIMIT 5")
            existing_keys = cursor.fetchall()
            print(f"\nExisting keys in database:")
            for key_id, name, is_active in existing_keys:
                status = "✅ active" if is_active else "❌ inactive"
                print(f"  - {key_id} ({name}) - {status}")
            
            return False
        
        key_id_db, key_hash_db, is_active, user_id, name, created_at = key_record
        print(f"✅ Found key in database:")
        print(f"   Key ID: {key_id_db}")
        print(f"   Name: {name}")
        print(f"   Active: {is_active}")
        print(f"   User ID: {user_id}")
        print(f"   Created: {created_at}")
        print(f"   Hash: {key_hash_db[:50]}...")
        
        # Step 3: Test hash verification
        print(f"\n📋 Step 3: Test hash verification")
        print("-" * 30)
        
        try:
            hash_matches = pwd_context.verify(test_api_key, key_hash_db)
            if hash_matches:
                print("✅ Hash verification PASSED")
            else:
                print("❌ Hash verification FAILED")
                print("The stored hash doesn't match the provided API key")
                return False
        except Exception as e:
            print(f"❌ Hash verification error: {e}")
            return False
        
        # Step 4: Check user exists and is active
        print(f"\n📋 Step 4: Check associated user")
        print("-" * 30)
        
        cursor.execute("""
            SELECT id, username, email, role, is_active, is_verified
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user_record = cursor.fetchone()
        
        if not user_record:
            print(f"❌ User {user_id} not found!")
            return False
        
        user_id_db, username, email, role, user_is_active, is_verified = user_record
        print(f"✅ Found associated user:")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print(f"   Active: {user_is_active}")
        print(f"   Verified: {is_verified}")
        
        if not user_is_active:
            print("❌ User account is inactive!")
            return False
        
        # Step 5: Test the authentication logic manually
        print(f"\n📋 Step 5: Manual authentication test")
        print("-" * 30)
        
        # Simulate the authentication logic
        if is_active and user_is_active and hash_matches:
            print("✅ All authentication checks PASSED")
            print("The API key should work!")
            print("")
            print("🎯 DIAGNOSIS:")
            print("The API key and database are correct.")
            print("The issue is likely in the FastAPI authentication code.")
        else:
            print("❌ Authentication checks FAILED")
            print(f"   Key active: {is_active}")
            print(f"   User active: {user_is_active}")
            print(f"   Hash matches: {hash_matches}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("Starting API key authentication debug...")
    debug_api_key_auth()
