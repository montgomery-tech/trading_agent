#!/usr/bin/env python3
"""
Simple Admin Router Debug Script
Quick checks to identify the admin router issue
"""

import os
import sys

def main():
    print("🔍 Simple Admin Router Debug")
    print("=" * 30)
    
    # Check 1: File structure
    print("📁 Checking files...")
    files_to_check = [
        "main.py",
        "api/routes/admin.py", 
        "api/models/user_admin.py",
        "api/services/email_service.py"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
    
    print()
    
    # Check 2: Admin import
    print("🧪 Testing admin import...")
    try:
        from api.routes import admin
        print("✅ Admin module imported successfully")
        print(f"   Router object: {admin.router}")
        print(f"   Router type: {type(admin.router)}")
    except Exception as e:
        print(f"❌ Admin import failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # Check 3: Router routes
    print("🛣️  Checking admin router routes...")
    try:
        routes = admin.router.routes
        print(f"   Number of routes: {len(routes)}")
        for route in routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = list(route.methods) if hasattr(route.methods, '__iter__') else [route.methods]
                print(f"     {methods} {route.path}")
    except Exception as e:
        print(f"❌ Error checking routes: {e}")
    
    print()
    
    # Check 4: Main.py content
    print("📝 Checking main.py...")
    try:
        with open("main.py", "r") as f:
            content = f.read()
        
        has_admin_import = "from api.routes import admin" in content
        has_admin_router = "admin.router" in content
        
        print(f"   Admin import: {'✅' if has_admin_import else '❌'}")
        print(f"   Admin router: {'✅' if has_admin_router else '❌'}")
        
        if not has_admin_import or not has_admin_router:
            print("   📋 Lines with 'admin':")
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'admin' in line.lower():
                    print(f"     Line {i+1}: {line.strip()}")
                    
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
    
    print()
    
    # Check 5: Test server endpoints
    print("🌐 Testing server endpoints...")
    try:
        import requests
        
        # Test if server is running
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            print(f"✅ Server responding: {response.status_code}")
        except Exception as e:
            print(f"❌ Server not responding: {e}")
            return
        
        # Test admin endpoint
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/admin/users",
                json={"email": "test@example.com", "first_name": "Test", "last_name": "User", "role": "user"},
                timeout=5
            )
            print(f"   Admin endpoint status: {response.status_code}")
            if response.status_code == 404:
                print("   ❌ Admin endpoint not found (this is the problem)")
            else:
                print("   ✅ Admin endpoint found")
        except Exception as e:
            print(f"   ❌ Error testing admin endpoint: {e}")
            
    except ImportError:
        print("❌ requests module not available")
    
    print()
    print("🎯 Quick Fixes to Try:")
    print("-" * 25)
    print("1. Restart the server completely:")
    print("   kill $(lsof -t -i:8000); sleep 2; python3 main.py")
    print()
    print("2. Check server logs for import errors")
    print()
    print("3. Try manual router test:")
    print("   python3 -c \"from api.routes.admin import router; print('OK')\"")

if __name__ == "__main__":
    main()
