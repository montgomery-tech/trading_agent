#!/usr/bin/env python3
"""
Fix API Key Hash in Database
Updates the corrupted hash with the correct bcrypt hash
"""

import os
import psycopg2
from urllib.parse import urlparse
from passlib.context import CryptContext

# Configure bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def fix_api_key_hash():
    """Fix the corrupted API key hash in the database"""
    
    # The correct values
    api_key = "btapi_WIzZEd7BYB1TBBIy_CTonaCJy7Id4yNfsABWNeMVW7ww7x9qj"
    key_id = "btapi_WIzZEd7BYB1TBBIy"
    correct_hash = "$2b$12$Fld5fxzO0Ku5z.OxtiIG8.Ueb5cXmQUUIr/BwesFip1ry1TTncw7i"
    
    print("🔧 Fixing API Key Hash")
    print("=" * 50)
    print(f"Key ID: {key_id}")
    print(f"API Key: {api_key}")
    print(f"Correct Hash: {correct_hash}")
    print("")
    
    # Verify the hash is correct first
    try:
        hash_matches = pwd_context.verify(api_key, correct_hash)
        if not hash_matches:
            print("❌ The provided hash doesn't match the API key!")
            print("Please double-check the hash value.")
            return False
        print("✅ Hash verification passed - proceeding with database update")
    except Exception as e:
        print(f"❌ Hash verification error: {e}")
        return False
    
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
        
        # Show current hash
        cursor.execute("SELECT key_hash FROM api_keys WHERE key_id = %s", (key_id,))
        current_hash = cursor.fetchone()
        
        if current_hash:
            print(f"Current hash in DB: {current_hash[0]}")
        else:
            print("❌ Key not found in database")
            return False
        
        # Update the hash
        cursor.execute("""
            UPDATE api_keys 
            SET key_hash = %s 
            WHERE key_id = %s
        """, (correct_hash, key_id))
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        if rows_updated > 0:
            print(f"✅ Updated {rows_updated} record(s)")
            
            # Verify the update
            cursor.execute("SELECT key_hash FROM api_keys WHERE key_id = %s", (key_id,))
            updated_hash = cursor.fetchone()[0]
            print(f"New hash in DB: {updated_hash}")
            
            # Test verification again
            test_match = pwd_context.verify(api_key, updated_hash)
            if test_match:
                print("✅ Hash verification now works!")
            else:
                print("❌ Hash verification still fails")
                return False
                
        else:
            print("❌ No records updated")
            return False
        
        cursor.close()
        conn.close()
        
        print("")
        print("🎉 API Key Hash Fixed Successfully!")
        print("=" * 50)
        print("The API key should now work for authentication.")
        print("")
        print("🧪 Test the fix:")
        print(f'curl -H "Authorization: Bearer {api_key}" \\')
        print('     http://localhost:8000/api/v1/admin/users')
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("Starting API key hash fix...")
    fix_api_key_hash()
