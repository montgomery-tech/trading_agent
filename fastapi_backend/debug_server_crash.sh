#!/bin/bash

# =============================================================================
# Debug Server Crash
# Identifies why the FastAPI server is crashing
# =============================================================================

echo "🐛 Debugging Server Crash"
echo "========================="

echo "🔍 Checking if server is actually running..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Server is running on port 8000"
    echo "   PID: $(lsof -t -i:8000)"
else
    echo "❌ No server running on port 8000"
fi

echo ""
echo "🧪 Testing main.py import directly..."

# Test importing main.py to see if there are errors
python3 -c "
import sys
import traceback

print('Testing main.py import...')
try:
    import main
    print('✅ main.py imported successfully')
    
    if hasattr(main, 'app'):
        print('✅ FastAPI app object found')
        
        # Check routes
        routes = []
        for route in main.app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        print(f'✅ Total routes: {len(routes)}')
        admin_routes = [r for r in routes if 'admin' in r]
        print(f'✅ Admin routes: {admin_routes}')
        
    else:
        print('❌ No app object found in main.py')
        
except ImportError as e:
    print(f'❌ Import error in main.py: {e}')
    traceback.print_exc()
except SyntaxError as e:
    print(f'❌ Syntax error in main.py: {e}')
    traceback.print_exc()
except Exception as e:
    print(f'❌ Other error importing main.py: {e}')
    traceback.print_exc()
"

echo ""
echo "🔍 Checking main.py syntax..."

# Check for syntax errors
python3 -m py_compile main.py
if [ $? -eq 0 ]; then
    echo "✅ main.py syntax is valid"
else
    echo "❌ main.py has syntax errors"
fi

echo ""
echo "📋 Checking recent changes to main.py..."

# Show what the admin router inclusion looks like now
echo "Current admin router inclusion:"
grep -n -A 3 -B 1 "admin.router" main.py || echo "❌ No admin.router found in main.py"

echo ""
echo "🔍 Checking for missing imports..."

# Check if all required modules are importable
python3 -c "
imports_to_test = [
    'fastapi',
    'api.config',
    'api.database', 
    'api.routes.admin',
    'api.auth_routes',
    'api.security'
]

for module in imports_to_test:
    try:
        __import__(module)
        print(f'✅ {module}')
    except Exception as e:
        print(f'❌ {module}: {e}')
"

echo ""
echo "🚀 Trying to start server with verbose output..."

# Try to start server and capture any startup errors
echo "Starting server with error capture..."
timeout 10s python3 main.py 2>&1 | head -20

echo ""
echo "🔧 Manual debugging steps:"
echo "1. Check the admin router inclusion in main.py"
echo "2. Look for any import errors in the output above"  
echo "3. Try running: python3 -c 'import main; print(\"OK\")'"
echo "4. Check if uvicorn is installed: pip3 list | grep uvicorn"
