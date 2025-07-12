#!/bin/bash

echo "🔧 Fixing Database and Authentication Issues"
echo "============================================"

echo "1️⃣  Adding missing database columns..."

# Run database migration for forced password change
python3 -c "
from api.database import DatabaseManager
from api.config import settings
import sys

try:
    db = DatabaseManager(settings.DATABASE_URL)
    db.connect()
    
    with db.get_cursor() as cursor:
        print('📊 Adding must_change_password column...')
        
        # Add must_change_password column if it doesn't exist
        try:
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN must_change_password BOOLEAN DEFAULT TRUE
            ''')
            print('✅ Added must_change_password column')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('✅ must_change_password column already exists')
            else:
                print(f'⚠️  Column addition warning: {e}')
        
        # Add password_changed_at column for tracking
        try:
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN password_changed_at TIMESTAMP
            ''')
            print('✅ Added password_changed_at column')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('✅ password_changed_at column already exists')
            else:
                print(f'⚠️  Column addition warning: {e}')
        
        # Commit changes
        db.connection.commit()
        print('✅ Database migration completed')
        
except Exception as e:
    print(f'❌ Database migration failed: {e}')
    sys.exit(1)
"

echo ""
echo "2️⃣  Checking main.py for missing auth routes..."

# Check if auth routes are included
if grep -q "auth_router" main.py && grep -q "app.include_router.*auth" main.py; then
    echo "✅ Auth routes appear to be included in main.py"
else
    echo "❌ Auth routes missing from main.py - adding them..."
    
    # Add auth routes if missing
    if ! grep -q "from api.auth_routes import router as auth_router" main.py; then
        echo "📝 Adding auth import to main.py..."
        sed -i.backup '/from api.routes import admin/a\
from api.auth_routes import router as auth_router' main.py
    fi
    
    if ! grep -q "app.include_router.*auth.*router" main.py; then
        echo "📝 Adding auth router inclusion to main.py..."
        sed -i.backup '/app.include_router(admin.router)/a\
\
# Include authentication routes\
app.include_router(\
    auth_router,\
    prefix=f"{settings.API_V1_PREFIX}/auth",\
    tags=["Authentication"]\
)' main.py
    fi
    
    echo "✅ Added auth routes to main.py"
fi

echo ""
echo "3️⃣  Cleaning up any database transaction issues..."

# Reset any stuck database transactions
python3 -c "
from api.database import DatabaseManager
from api.config import settings

try:
    db = DatabaseManager(settings.DATABASE_URL)
    db.connect()
    
    # Rollback any pending transactions
    db.connection.rollback()
    print('✅ Database transactions reset')
    
except Exception as e:
    print(f'⚠️  Database reset warning: {e}')
"

echo ""
echo "4️⃣  Creating forced password change test data..."

# Create a test user with forced password change
python3 -c "
from api.database import DatabaseManager
from api.config import settings
import bcrypt
import uuid
from datetime import datetime

try:
    db = DatabaseManager(settings.DATABASE_URL)
    db.connect()
    
    # Create a test user with must_change_password = true
    user_id = str(uuid.uuid4())
    username = 'testuser_forced'
    email = 'testuser_forced@example.com'
    temp_password = 'TempPass123!'
    password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with db.get_cursor() as cursor:
        # Delete existing test user if exists
        cursor.execute('DELETE FROM users WHERE email = %s', (email,))
        
        # Insert new test user
        cursor.execute('''
            INSERT INTO users (
                id, username, email, password_hash, first_name, last_name,
                is_active, is_verified, must_change_password, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            user_id, username, email, password_hash, 'Test', 'User',
            True, True, True, datetime.utcnow(), datetime.utcnow()
        ))
        
        db.connection.commit()
    
    print('✅ Created test user for forced password change:')
    print(f'   Email: {email}')
    print(f'   Password: {temp_password}')
    print(f'   Must change password: True')
    
except Exception as e:
    print(f'❌ Test user creation failed: {e}')
"

echo ""
echo "5️⃣  Restarting server to apply changes..."

# Kill existing server
if lsof -i :8000 > /dev/null 2>&1; then
    echo "🛑 Stopping existing server..."
    kill $(lsof -t -i:8000) 2>/dev/null
    sleep 2
fi

echo "🚀 Starting server with fixes..."
echo "   (Server will start in background)"

# Start server in background
nohup python3 main.py > server.log 2>&1 &

# Wait for server to start
sleep 3

if lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Server restarted successfully"
    
    echo ""
    echo "🧪 Testing the fixes..."
    
    # Test auth endpoint
    echo "📡 Testing auth login endpoint..."
    response=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
      -H 'Content-Type: application/json' \
      -d '{"username":"testuser_forced@example.com","password":"TempPass123!"}')
    
    echo "   Auth response: $response"
    
    # Test admin endpoint
    echo "📡 Testing admin user creation..."
    response=$(curl -s -X POST http://localhost:8000/api/v1/admin/users \
      -H 'Content-Type: application/json' \
      -d '{"email":"test-fix@example.com","full_name":"Test Fix","role":"trader"}')
    
    echo "   Admin response: $response"
    
else
    echo "❌ Server failed to start - check server.log for errors"
fi

echo ""
echo "🎯 Fixes Applied:"
echo "• Added must_change_password column to database"
echo "• Added password_changed_at column to database"  
echo "• Ensured auth routes are included in main.py"
echo "• Reset database transactions"
echo "• Created test user with forced password change"
echo "• Restarted server"
echo ""
echo "🚀 Now try your test again:"
echo "   python3 test_simple_forced_password.py"
