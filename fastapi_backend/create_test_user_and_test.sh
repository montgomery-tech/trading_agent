#!/bin/bash

echo "🧪 Creating Fresh Test User and Testing Complete Flow"
echo "====================================================="

echo "1️⃣  Creating a fresh test user via admin endpoint..."

# Create a user with a timestamp to ensure uniqueness
timestamp=$(date +%s)
test_email="testuser${timestamp}@example.com"

echo "📧 Creating user: $test_email"

# Create user via admin endpoint
create_response=$(curl -s -X POST http://localhost:8000/api/v1/admin/users \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$test_email\",\"full_name\":\"Test User $timestamp\",\"role\":\"trader\"}")

echo "📋 Admin creation response:"
echo "$create_response" | python3 -m json.tool 2>/dev/null || echo "$create_response"

# Extract the temporary password
temp_password=$(echo "$create_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print(data.get('temporary_password', ''))
    else:
        print('ERROR: ' + str(data.get('error', 'Unknown error')))
except Exception as e:
    print('PARSE_ERROR: ' + str(e))
" 2>/dev/null)

if [[ "$temp_password" == ERROR:* ]] || [[ "$temp_password" == PARSE_ERROR:* ]]; then
    echo "❌ User creation failed: $temp_password"
    exit 1
elif [ -z "$temp_password" ]; then
    echo "❌ No temporary password received"
    exit 1
else
    echo "✅ User created with temporary password: $temp_password"
fi

echo ""
echo "2️⃣  Verifying user exists in database..."

# Check if user exists in database
db_check=$(python3 -c "
from api.database import DatabaseManager
from api.config import settings

db = DatabaseManager(settings.DATABASE_URL)
db.connect()

with db.get_cursor() as cursor:
    cursor.execute('SELECT username, email, must_change_password FROM users WHERE email = %s', ('$test_email',))
    user = cursor.fetchone()
    
    if user:
        print(f'FOUND: {user[0]} ({user[1]}) - Must change: {user[2]}')
    else:
        print('NOT_FOUND')
")

if [[ "$db_check" == "NOT_FOUND" ]]; then
    echo "❌ User not found in database after creation!"
    exit 1
else
    echo "✅ User confirmed in database: $db_check"
fi

echo ""
echo "3️⃣  Testing login with temporary password..."

# Test login
login_response=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$test_email\",\"password\":\"$temp_password\"}")

echo "📋 Login response:"
echo "$login_response" | python3 -m json.tool 2>/dev/null || echo "$login_response"

# Check if login indicates forced password change is needed
if echo "$login_response" | grep -q "must_change_password"; then
    echo "✅ Login correctly detected forced password change requirement!"
elif echo "$login_response" | grep -q "success.*true"; then
    echo "⚠️  Login succeeded but didn't detect forced password change"
elif echo "$login_response" | grep -q "Authentication failed"; then
    echo "❌ Login failed with authentication error"
    
    echo ""
    echo "🔍 Debugging login issue..."
    
    # Let's try to understand why login is failing
    debug_login=$(python3 -c "
from api.database import DatabaseManager
from api.config import settings
import bcrypt

db = DatabaseManager(settings.DATABASE_URL)
db.connect()

with db.get_cursor() as cursor:
    cursor.execute('SELECT username, password_hash FROM users WHERE email = %s', ('$test_email',))
    user = cursor.fetchone()
    
    if user:
        username, stored_hash = user
        test_password = '$temp_password'
        
        print(f'Username: {username}')
        print(f'Testing password: {test_password}')
        print(f'Stored hash length: {len(stored_hash)}')
        
        try:
            if bcrypt.checkpw(test_password.encode('utf-8'), stored_hash.encode('utf-8')):
                print('✅ Password verification successful')
            else:
                print('❌ Password verification failed')
        except Exception as e:
            print(f'❌ Password check error: {e}')
    else:
        print('❌ User not found for password check')
")
    
    echo "🔍 Password verification debug:"
    echo "$debug_login"
    
else
    echo "❓ Unexpected login response"
fi

echo ""
echo "🎯 Summary:"
echo "• User creation: $(if echo "$create_response" | grep -q '"success":true'; then echo "✅ Success"; else echo "❌ Failed"; fi)"
echo "• Database storage: $(if [[ "$db_check" != "NOT_FOUND" ]]; then echo "✅ Success"; else echo "❌ Failed"; fi)"
echo "• Login test: $(if echo "$login_response" | grep -q "must_change_password\|success"; then echo "✅ Working"; else echo "❌ Failed"; fi)"

echo ""
echo "📋 Test credentials for manual testing:"
echo "   Email: $test_email"
echo "   Password: $temp_password"
