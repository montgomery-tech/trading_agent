#!/bin/bash

echo "🔧 Simple Database Fix"
echo "====================="

echo "1️⃣  Killing any existing server processes..."
pkill -f "python3 main.py" 2>/dev/null || true
sleep 2

echo "2️⃣  Testing database with simple connection..."

# Simple database test and fix
python3 -c "
import psycopg2
import sys

try:
    # Simple connection without autocommit parameter
    conn = psycopg2.connect(
        host='localhost',
        database='balance_tracker', 
        user='garrettroth'
    )
    
    # Set autocommit after connection
    conn.autocommit = True
    cursor = conn.cursor()
    
    print('✅ Database connection successful')
    
    # Check users table
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    print(f'✅ Users table has {count} records')
    
    # Check if must_change_password column exists
    cursor.execute('''
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'must_change_password'
    ''')
    
    if cursor.fetchone():
        print('✅ must_change_password column exists')
    else:
        print('➕ Adding must_change_password column...')
        cursor.execute('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT TRUE')
        print('✅ Added must_change_password column')
    
    # Test insert/select to verify database is working
    cursor.execute('BEGIN')
    cursor.execute('SELECT 1')
    result = cursor.fetchone()[0]
    cursor.execute('COMMIT')
    
    if result == 1:
        print('✅ Database transactions working')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Database error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Database is working correctly"
else
    echo "❌ Database issues persist"
    exit 1
fi

echo ""
echo "3️⃣  Starting server..."

# Start server
python3 main.py &
SERVER_PID=$!

# Wait for server to start
sleep 3

if lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Server started successfully"
    
    echo ""
    echo "4️⃣  Testing endpoints..."
    
    # Test with a completely unique email
    test_email="finaltest$(date +%s)@example.com"
    
    echo "🧪 Testing admin endpoint..."
    response=$(curl -s -X POST http://localhost:8000/api/v1/admin/users \
      -H 'Content-Type: application/json' \
      -d "{\"email\":\"$test_email\",\"full_name\":\"Final Test\",\"role\":\"trader\"}")
    
    if echo "$response" | grep -q '"success":true'; then
        echo "✅ Admin endpoint working!"
        echo "   Response: $response"
        
        # Get the temp password for auth test
        temp_password=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('temporary_password', ''))
except:
    pass
" 2>/dev/null)
        
        if [ -n "$temp_password" ]; then
            echo ""
            echo "🔐 Testing auth endpoint..."
            auth_response=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
              -H 'Content-Type: application/json' \
              -d "{\"username\":\"$test_email\",\"password\":\"$temp_password\"}")
            
            echo "   Auth response: $auth_response"
            
            if echo "$auth_response" | grep -q '"must_change_password":true'; then
                echo "🎉 SUCCESS! Forced password change working!"
            else
                echo "⚠️  Auth endpoint working but check forced password logic"
            fi
        fi
        
    else
        echo "❌ Admin endpoint issues:"
        echo "   $response"
    fi
    
else
    echo "❌ Server failed to start"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
    fi
fi

echo ""
echo "🎯 Next steps:"
echo "• If admin endpoint works: python3 test_simple_forced_password.py"
echo "• If still issues: Check server logs for specific errors"
