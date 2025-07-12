#!/usr/bin/env python3
"""
FIXED main.py - Adds missing admin router
This fixes the 404 error for /api/v1/admin/users endpoint
"""

import sys
import os

def fix_main_py():
    """Add admin router to main.py"""
    
    print("🔧 Fixing main.py to include admin router")
    print("=========================================")
    
    # Read current main.py
    if not os.path.exists('main.py'):
        print("❌ main.py file not found!")
        return False
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Check if admin router is already included
    if 'api.routes.admin' in content or 'admin.router' in content:
        print("✅ Admin router already included in main.py")
        return True
    
    print("📝 Adding admin router import and inclusion...")
    
    # Create the fixed content
    lines = content.split('\n')
    new_lines = []
    
    # Find where to add the admin import
    auth_import_added = False
    admin_import_added = False
    admin_router_added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Add admin import after auth import
        if ('from api.routes import auth' in line or 'from api.auth_routes import' in line) and not admin_import_added:
            new_lines.append('from api.routes import admin')
            admin_import_added = True
            print("✅ Added admin import")
        
        # Add admin router after auth router
        if ('app.include_router(auth' in line or 'auth.router' in line) and not admin_router_added:
            # Find the end of this router inclusion
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(')'):
                j += 1
            
            # Add admin router after auth router
            if j < len(lines):
                new_lines.extend([
                    '',
                    '# Include admin routes',
                    'app.include_router(',
                    '    admin.router,',
                    '    prefix=f"{settings.API_V1_PREFIX}/admin",',
                    '    tags=["Admin"]',
                    ')'
                ])
                admin_router_added = True
                print("✅ Added admin router inclusion")
    
    # If we couldn't find the auth router, add admin router after other routers
    if not admin_router_added:
        # Find where routers are included and add admin router
        for i, line in enumerate(lines):
            if 'app.include_router(' in line and 'users.router' in lines[i+1] if i+1 < len(lines) else False:
                # Insert admin router before users router
                insert_index = i
                admin_router_lines = [
                    '# Include admin routes',
                    'app.include_router(',
                    '    admin.router,',
                    '    prefix=f"{settings.API_V1_PREFIX}/admin",',
                    '    tags=["Admin"]',
                    ')',
                    ''
                ]
                
                for j, admin_line in enumerate(admin_router_lines):
                    new_lines.insert(insert_index + j, admin_line)
                
                admin_router_added = True
                print("✅ Added admin router before users router")
                break
    
    # If still not added, add it at the end of router inclusions
    if not admin_router_added:
        # Find last router inclusion
        last_router_index = -1
        for i, line in enumerate(new_lines):
            if 'app.include_router(' in line:
                # Find the end of this router inclusion
                j = i + 1
                while j < len(new_lines) and not new_lines[j].strip().startswith(')'):
                    j += 1
                if j < len(new_lines):
                    last_router_index = j
        
        if last_router_index > -1:
            admin_router_lines = [
                '',
                '# Include admin routes',
                'app.include_router(',
                '    admin.router,',
                '    prefix=f"{settings.API_V1_PREFIX}/admin",',
                '    tags=["Admin"]',
                ')'
            ]
            
            for j, admin_line in enumerate(admin_router_lines):
                new_lines.insert(last_router_index + 1 + j, admin_line)
            
            admin_router_added = True
            print("✅ Added admin router at end of router inclusions")
    
    # Add import if not added yet
    if not admin_import_added:
        # Find other imports and add admin import
        for i, line in enumerate(new_lines):
            if line.startswith('from api.routes import') or 'import users' in line:
                new_lines.insert(i + 1, 'from api.routes import admin')
                admin_import_added = True
                print("✅ Added admin import")
                break
        
        # If still not added, add after other api imports
        if not admin_import_added:
            for i, line in enumerate(new_lines):
                if line.startswith('from api.') and 'import' in line:
                    new_lines.insert(i + 1, 'from api.routes import admin')
                    admin_import_added = True
                    print("✅ Added admin import after api imports")
                    break
    
    if admin_import_added and admin_router_added:
        # Write the fixed content
        with open('main.py', 'w') as f:
            f.write('\n'.join(new_lines))
        
        print("✅ Successfully updated main.py with admin router")
        return True
    else:
        print("❌ Failed to add admin router to main.py")
        print(f"   Import added: {admin_import_added}")
        print(f"   Router added: {admin_router_added}")
        return False

def verify_fix():
    """Verify the fix was applied correctly"""
    print("\n🔍 Verifying main.py fix...")
    
    if not os.path.exists('main.py'):
        print("❌ main.py not found")
        return False
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    has_import = 'from api.routes import admin' in content
    has_router = 'admin.router' in content and 'API_V1_PREFIX}/admin' in content
    
    print(f"   ✅ Admin import: {'Found' if has_import else 'Missing'}")
    print(f"   ✅ Admin router: {'Found' if has_router else 'Missing'}")
    
    if has_import and has_router:
        print("✅ main.py fix verified successfully!")
        return True
    else:
        print("❌ main.py fix verification failed")
        return False

def main():
    """Main function"""
    print("🚀 Admin Router Fix for main.py")
    print("=" * 40)
    
    success = fix_main_py()
    
    if success:
        verify_fix()
        print("\n🎉 Fix completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Restart your FastAPI server")
        print("   2. Check that /api/v1/admin/users endpoint is available")
        print("   3. Run your forced password change tests")
        print("\n🔗 Test the endpoint:")
        print("   curl -X POST http://localhost:8000/api/v1/admin/users \\")
        print("     -H 'Content-Type: application/json' \\")
        print('     -d \'{"email":"test@example.com","first_name":"Test","last_name":"User","role":"user"}\'')
    else:
        print("\n❌ Fix failed - manual intervention required")
        print("\n📝 Manual steps:")
        print("   1. Add this import to main.py:")
        print("      from api.routes import admin")
        print("   2. Add this router inclusion:")
        print("      app.include_router(admin.router, prefix=f\"{settings.API_V1_PREFIX}/admin\", tags=[\"Admin\"])")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
