#!/bin/bash

echo "🔍 Diagnosing Database and Authentication Issues"
echo "==============================================="

echo "1️⃣  Checking database connection and tables..."

# Test database connection
python3 -c "
import sys
try:
    from api.database import DatabaseManager
    from api.config import settings
    
    print('📊 Testing database connection...')
    db = DatabaseManager(settings.DATABASE_URL)
    db.connect()
    print('✅ Database connection successful')
    
    # Check if users table exists and has data
    with db.get_cursor() as cursor:
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            print(f'✅ Users table exists with {count} records')
            
            # Check table structure
            cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s', ('users',))
            columns = [row[0] for row in cursor.fetchall()]
            print(f'📋 Users table columns: {columns}')
            
            # Check for must_change_password column
            if 'must_change_password' in columns:
                print('✅ must_change_password column exists')
            else:
                print('❌ must_change_password column missing!')
            
        except Exception as e:
            print(f'❌ Users table issue: {e}')
            
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"

echo ""
echo "2️⃣  Checking authentication routes..."

# Check if auth routes are properly loaded
python3 -c "
try:
    import main
    
    routes = []
    for route in main.app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    auth_routes = [r for r in routes if '/auth/' in r]
    admin_routes = [r for r in routes if '/admin/' in r]
    
    print('📋 Auth routes found:')
    for route in auth_routes:
        print(f'   {route}')
    
    print('📋 Admin routes found:')
    for route in admin_routes:
        print(f'   {route}')
    
    # Check specifically for required routes
    required_routes = ['/api/v1/auth/login', '/api/v1/auth/change-password', '/api/v1/admin/users']
    
    for route in required_routes:
        if route in routes:
            print(f'✅ {route} - Found')
        else:
            print(f'❌ {route} - Missing')
            
except Exception as e:
    print(f'❌ Error checking routes: {e}')
"

echo ""
echo "3️⃣  Testing auth endpoint directly..."

# Test if auth login endpoint exists
echo "📡 Testing /api/v1/auth/login endpoint..."
response=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"test"}')

http_code="${response: -3}"
body="${response%???}"

echo "   HTTP Status: $http_code"
echo "   Response: $body"

if [ "$http_code" = "404" ]; then
    echo "❌ Auth login endpoint not found!"
elif [ "$http_code" = "500" ]; then
    echo "⚠️  Auth endpoint exists but has server error"
elif [ "$http_code" = "422" ]; then
    echo "✅ Auth endpoint exists (422 = validation error is expected)"
else
    echo "✅ Auth endpoint responding with status $http_code"
fi

echo ""
echo "4️⃣  Checking for missing database migrations..."

# Check if we need to run database migrations
echo "📊 Checking if database needs forced password change migration..."

python3 -c "
try:
    from api.database import DatabaseManager
    from api.config import settings
    
    db = DatabaseManager(settings.DATABASE_URL)
    db.connect()
    
    with db.get_cursor() as cursor:
        # Check if must_change_password column exists
        cursor.execute('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        ''', ('users', 'must_change_password'))
        
        result = cursor.fetchone()
        
        if result:
            print('✅ must_change_password column exists')
        else:
            print('❌ must_change_password column missing - migration needed!')
            print('   Run: ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT TRUE;')
            
except Exception as e:
    print(f'❌ Migration check failed: {e}')
"

echo ""
echo "5️⃣  Summary and recommendations..."
echo "================================="
echo ""
echo "Based on the diagnostic above, likely issues:"
echo "• Missing must_change_password column in users table"
echo "• Auth routes not properly included in main.py"
echo "• Database transaction errors from failed operations"
echo ""
echo "🔧 Next steps:"
echo "1. Run database migration to add missing columns"
echo "2. Ensure auth routes are included in main.py"  
echo "3. Restart server and test again"
