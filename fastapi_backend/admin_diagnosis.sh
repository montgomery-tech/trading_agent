#!/bin/bash
# Quick Admin File Check - Verify deployment

echo "🔍 QUICK ADMIN FILE VERIFICATION"
echo "================================"

echo "📄 First 30 lines of admin.py:"
echo "------------------------------"
head -30 api/routes/admin.py

echo ""
echo "📄 Lines containing 'require_admin':"
echo "-----------------------------------"
grep -n "require_admin" api/routes/admin.py

echo ""
echo "📄 Lines containing 'AuthenticatedUser':"
echo "---------------------------------------"
grep -n "AuthenticatedUser" api/routes/admin.py

echo ""
echo "📄 Lines containing '@router.get':"
echo "---------------------------------"
grep -n "@router.get" api/routes/admin.py

echo ""
echo "📄 File size and line count:"
echo "---------------------------"
wc api/routes/admin.py

echo ""
echo "🧪 Test import:"
echo "--------------"
python3 -c "
try:
    from api.routes.admin import router
    print(f'✅ Import successful')
    print(f'Routes: {len(router.routes)}')
    for route in router.routes[:3]:  # Show first 3 routes
        print(f'  {route.methods} {route.path}')
except Exception as e:
    print(f'❌ Import failed: {e}')
"
