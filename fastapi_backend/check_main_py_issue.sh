#!/bin/bash

echo "🔍 Investigating main.py Router Inclusion Issue"
echo "==============================================="

echo "📋 Current main.py admin-related content:"
echo "-----------------------------------------"
grep -n -A 3 -B 3 -i admin main.py

echo ""
echo "📋 All router inclusions in main.py:"
echo "------------------------------------"
grep -n -A 4 -B 1 "include_router" main.py

echo ""
echo "📋 All import statements in main.py:"
echo "------------------------------------"
grep -n "^from\|^import" main.py

echo ""
echo "🧪 Testing if admin router routes have correct prefix:"
echo "-----------------------------------------------------"
python3 -c "
from api.routes.admin import router
print('Admin router prefix:', getattr(router, 'prefix', 'None'))
print('Admin router routes:')
for route in router.routes:
    if hasattr(route, 'path'):
        print(f'  {route.path}')
"

echo ""
echo "🌐 Checking what paths are actually available on server:"
echo "--------------------------------------------------------"
curl -s http://localhost:8000/openapi.json | python3 -c "
import json
import sys
data = json.load(sys.stdin)
paths = list(data.get('paths', {}).keys())
print('Available paths on server:')
for path in sorted(paths):
    print(f'  {path}')
    
admin_paths = [p for p in paths if 'admin' in p.lower()]
if admin_paths:
    print(f'\\nAdmin paths found: {admin_paths}')
else:
    print('\\n❌ No admin paths found in server!')
"

echo ""
echo "🔧 Checking if there are import errors in main.py:"
echo "---------------------------------------------------"
python3 -c "
import sys
try:
    import main
    print('✅ main.py imports successfully')
    
    # Check if app object exists and has admin routes
    if hasattr(main, 'app'):
        app = main.app
        print(f'✅ FastAPI app found: {app}')
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        print(f'Total routes in app: {len(routes)}')
        admin_routes = [r for r in routes if 'admin' in r.lower()]
        if admin_routes:
            print(f'✅ Admin routes in app: {admin_routes}')
        else:
            print('❌ No admin routes found in FastAPI app!')
            print('Available routes:', routes[:10])
    else:
        print('❌ No app object found in main.py')
        
except Exception as e:
    print(f'❌ Error importing main.py: {e}')
    import traceback
    traceback.print_exc()
"
