#!/bin/bash

echo "🔧 Fixing Test Data Format"
echo "=========================="

echo "📝 The admin endpoint expects:"
echo "   - 'full_name' (not 'first_name' + 'last_name')"
echo "   - role: 'admin', 'trader', or 'viewer' (not 'user')"

echo ""
echo "🧪 Testing with correct format..."

curl -X POST http://localhost:8000/api/v1/admin/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","full_name":"Test User","role":"trader"}' \
  | python3 -m json.tool

echo ""
echo "🔧 Updating test scripts..."

# Fix the test_forced_password_change.py if it exists
if [ -f "test_forced_password_change.py" ]; then
    echo "📝 Updating test_forced_password_change.py..."
    
    # Create backup
    cp test_forced_password_change.py test_forced_password_change.py.backup
    
    # Fix the user data format
    sed -i.tmp 's/"first_name": "Test"/"full_name": "Test User"/g' test_forced_password_change.py
    sed -i.tmp 's/"last_name": "User",//g' test_forced_password_change.py
    sed -i.tmp 's/"role": "user"/"role": "trader"/g' test_forced_password_change.py
    
    # Clean up
    rm -f test_forced_password_change.py.tmp
    
    echo "✅ Updated test_forced_password_change.py"
fi

# Fix the improved test script if it exists  
if [ -f "test_forced_password_change_improved.py" ]; then
    echo "📝 Updating test_forced_password_change_improved.py..."
    
    # Create backup
    cp test_forced_password_change_improved.py test_forced_password_change_improved.py.backup
    
    # Fix the user data format in the improved script
    sed -i.tmp 's/"first_name": "Test"/"full_name": "Test User"/g' test_forced_password_change_improved.py
    sed -i.tmp 's/"last_name": "User",//g' test_forced_password_change_improved.py  
    sed -i.tmp 's/"role": "user"/"role": "trader"/g' test_forced_password_change_improved.py
    
    # Clean up
    rm -f test_forced_password_change_improved.py.tmp
    
    echo "✅ Updated test_forced_password_change_improved.py"
fi

echo ""
echo "🚀 Now you can run the tests:"
echo "   python3 test_forced_password_change_improved.py"
echo ""
echo "🎯 Or test manually with correct data:"
echo "   curl -X POST http://localhost:8000/api/v1/admin/users \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\":\"newuser@example.com\",\"full_name\":\"New User\",\"role\":\"trader\"}'"
