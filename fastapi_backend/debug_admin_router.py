#!/bin/bash

# =============================================================================
# Examine main.py Current Content
# Shows exactly what's in main.py to debug router issues
# =============================================================================

echo "🔍 Examining main.py Content"
echo "============================="

if [[ ! -f "main.py" ]]; then
    echo "❌ main.py not found!"
    exit 1
fi

echo "📄 Full main.py content:"
echo "------------------------"
cat -n main.py

echo ""
echo "🔍 Searching for specific patterns:"
echo "-----------------------------------"

echo "📦 Import statements:"
grep -n "^from\|^import" main.py

echo ""
echo "🔗 Router inclusions:"
grep -n -A 3 -B 1 "include_router" main.py

echo ""
echo "👑 Admin-related lines:"
grep -n -i "admin" main.py

echo ""
echo "🎯 FastAPI app definition:"
grep -n -A 5 -B 2 "FastAPI(" main.py

echo ""
echo "📋 Summary Check:"
echo "----------------"

# Check for admin import
if grep -q "from api.routes import admin" main.py; then
    echo "✅ Admin import found"
else
    echo "❌ Admin import missing"
fi

# Check for admin router inclusion
if grep -q "admin.router" main.py; then
    echo "✅ Admin router inclusion found"
else
    echo "❌ Admin router inclusion missing"
fi

# Check for admin prefix
if grep -q "/admin" main.py; then
    echo "✅ Admin prefix found"
else
    echo "❌ Admin prefix missing"
fi

echo ""
echo "🔍 Line-by-line analysis:"
echo "-------------------------"

# Show numbered lines with admin-related content
awk '/admin|Admin|ADMIN/ {print "Line " NR ": " $0}' main.py

echo ""
echo "🧪 Quick import test:"
echo "--------------------"

# Test if we can import the admin module
python3 -c "
try:
    from api.routes import admin
    print('✅ Admin import successful')
    print(f'   Router object: {admin.router}')
    print(f'   Router type: {type(admin.router)}')
except Exception as e:
    print(f'❌ Admin import failed: {e}')
    import traceback
    traceback.print_exc()
"
