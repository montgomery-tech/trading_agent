#!/bin/bash

echo "🔍 Debugging Database Transaction Issue"
echo "======================================="

echo "📊 The problem: Admin endpoint returns success but user not in database"
echo "   This indicates a database transaction/commit issue"

echo ""
echo "1️⃣  Checking database connection and table structure..."

python3 -c "
from api.database import DatabaseManager
from api.config import settings

db = DatabaseManager(settings.DATABASE_URL)
db.connect()

# Check users table structure
with db.get_cursor() as cursor:
    print('📋 Users table structure:')
    cursor.execute('''
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'users'
        ORDER BY ordinal_position;
    ''')
    
    for col in cursor.fetchall():
        print(f'   {col[0]} ({col[1]}) - nullable: {col[2]} - default: {col[3]}')
    
    # Check current user count
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    print(f'\\n📊 Current users in table: {count}')
"

echo ""
echo "2️⃣  Testing manual database insert..."

python3 -c "
from api.database import DatabaseManager
from api.config import settings
import uuid
import bcrypt
from datetime import datetime

try:
    db = DatabaseManager(settings.DATABASE_URL)
    db.connect()
    
    # Test manual insert
    user_id = str(uuid.uuid4())
    username = 'debugtest'
    email = 'debugtest@example.com'
    password = 'TestPass123!'
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with db.get_cursor() as cursor:
        # Delete any existing debug user
        cursor.execute('DELETE FROM users WHERE email = %s', (email,))
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (
                id, username, email, password_hash, first_name, last_name,
                is_active, is_verified, must_change_password, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            user_id, username, email, password_hash, 'Debug', 'Test',
            True, True, True, datetime.utcnow(), datetime.utcnow()
        ))
        
        # IMPORTANT: Explicitly commit
        db.connection.commit()
        print('✅ Manual insert completed with explicit commit')
        
        # Verify insert
        cursor.execute('SELECT username, email FROM users WHERE email = %s', (email,))
        result = cursor.fetchone()
        
        if result:
            print(f'✅ Manual insert verified: {result[0]} ({result[1]})')
        else:
            print('❌ Manual insert failed verification')
            
except Exception as e:
    print(f'❌ Manual insert failed: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "3️⃣  Checking admin endpoint database commit behavior..."

# Let's look at the admin.py file to see if it's missing commits
if [ -f "api/routes/admin.py" ]; then
    echo "🔍 Checking admin.py for database commit patterns..."
    
    if grep -q "commit" api/routes/admin.py; then
        echo "✅ Found commit statements in admin.py"
        echo "📋 Commit patterns:"
        grep -n -A 2 -B 2 "commit" api/routes/admin.py
    else
        echo "❌ NO COMMIT STATEMENTS found in admin.py!"
        echo "🔧 This is likely the problem - database changes not being committed"
        
        echo ""
        echo "📝 Admin.py database pattern:"
        grep -n -A 5 -B 5 "cursor.execute.*INSERT" api/routes/admin.py || echo "No INSERT statements found"
    fi
fi

echo ""
echo "4️⃣  Creating a fixed admin endpoint..."

# Create a simple fixed admin endpoint that ensures commits
cat > fixed_admin_endpoint.py << 'EOF'
from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_database
from api.database import DatabaseManager
import uuid
import bcrypt
from datetime import datetime

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.post("/users-fixed")
async def create_user_fixed(
    user_data: dict,
    db: DatabaseManager = Depends(get_database)
):
    """Fixed user creation with explicit commit"""
    
    try:
        email = user_data.get("email")
        full_name = user_data.get("full_name", "Test User")
        role = user_data.get("role", "trader")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email required")
        
        # Generate user data
        user_id = str(uuid.uuid4())
        username = email.split('@')[0] + str(int(datetime.now().timestamp()))
        temp_password = "TempPass123!"
        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        with db.get_cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="User already exists")
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, first_name, last_name,
                    is_active, is_verified, must_change_password, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, username, email, password_hash, 
                full_name.split()[0] if full_name else "Test",
                " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "User",
                True, True, True, datetime.utcnow(), datetime.utcnow()
            ))
            
            # CRITICAL: Explicit commit
            db.connection.commit()
            
            # Verify the insert worked
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                raise Exception("Insert verification failed")
        
        return {
            "success": True,
            "message": "User created with explicit commit",
            "user_id": user_id,
            "username": username,
            "email": email,
            "temporary_password": temp_password,
            "must_change_password": True
        }
        
    except Exception as e:
        # Rollback on error
        try:
            db.connection.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")

EOF

echo "✅ Created fixed admin endpoint"

echo ""
echo "🎯 Problem Analysis:"
echo "• Admin endpoint returns success but user not in database"
echo "• This indicates missing database commit() calls"
echo "• Database changes are being rolled back automatically"
echo ""
echo "🔧 Solutions to try:"
echo "1. Use the fixed endpoint: POST /api/v1/admin/users-fixed"
echo "2. Add explicit commit() calls to existing admin.py"
echo "3. Check database transaction settings"
