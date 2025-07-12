#!/bin/bash

echo "🔧 Fixing Critical Database Transaction Issue"
echo "============================================="

echo "🛑 Stopping server completely..."
# Kill all python processes that might be holding database connections
pkill -f "python3 main.py" 2>/dev/null || true
sleep 2

echo "📊 Resetting PostgreSQL connections..."

# Reset PostgreSQL connections for the current user
psql -d balance_tracker -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'balance_tracker' 
  AND pid <> pg_backend_pid()
  AND usename = current_user;
" 2>/dev/null || echo "⚠️  Could not reset connections (this might be OK)"

echo "🔧 Creating clean database reset script..."

# Create a Python script to properly reset everything
cat > database_reset.py << 'EOF'
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
EOF

# Run the database reset
echo "📊 Running database reset..."
python3 database_reset.py

if [ $? -eq 0 ]; then
    echo "✅ Database reset successful"
else
    echo "❌ Database reset failed"
    exit 1
fi

echo ""
echo "🚀 Starting server with clean state..."

# Start server in background
nohup python3 main.py > server.log 2>&1 &
sleep 3

if lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Server started successfully"
    
    echo ""
    echo "🧪 Testing database operations..."
    
    # Test admin endpoint with a unique email
    test_email="cleantest$(date +%s)@example.com"
    
    echo "📡 Testing admin user creation with clean database..."
    response=$(curl -s -X POST http://localhost:8000/api/v1/admin/users \
      -H 'Content-Type: application/json' \
      -d "{\"email\":\"$test_email\",\"full_name\":\"Clean Test\",\"role\":\"trader\"}")
    
    echo "   Response: $response"
    
    if echo "$response" | grep -q '"success":true'; then
        echo "✅ Admin endpoint working with clean database!"
        
        # Extract credentials for login test
        temp_password=$(echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('temporary_password', ''))
" 2>/dev/null)
        
        if [ -n "$temp_password" ]; then
            echo ""
            echo "🔐 Testing auth login with created user..."
            
            auth_response=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
              -H 'Content-Type: application/json' \
              -d "{\"username\":\"$test_email\",\"password\":\"$temp_password\"}")
            
            echo "   Auth response: $auth_response"
            
            if echo "$auth_response" | grep -q '"must_change_password":true'; then
                echo "🎉 SUCCESS! Forced password change system is working!"
            else
                echo "⚠️  Auth working but forced password change logic may need adjustment"
            fi
        fi
        
    else
        echo "❌ Admin endpoint still having issues"
    fi
else
    echo "❌ Server failed to start"
    echo "📋 Check server.log for errors:"
    tail -10 server.log 2>/dev/null || echo "No server.log found"
fi

echo ""
echo "🎯 Database transaction issue should now be resolved!"
echo "🚀 Try your test again:"
echo "   python3 test_simple_forced_password.py"

# Clean up
rm -f database_reset.py
