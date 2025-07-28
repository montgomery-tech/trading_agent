#!/usr/bin/env python3
"""
Fix require_admin Dependency Issue
Fixes the bug where require_admin returns a function instead of calling it
"""

import os

def fix_auth_dependencies():
    """Fix the require_admin dependency definition"""
    
    auth_file = "api/auth_dependencies.py"
    
    if not os.path.exists(auth_file):
        print(f"❌ File not found: {auth_file}")
        return False
    
    print("🔧 Fixing auth_dependencies.py...")
    
    # Read the current file
    with open(auth_file, 'r') as f:
        content = f.read()
    
    # Find and fix the problematic require_admin definition
    old_line = "require_admin = require_admin_api_key"
    new_line = "require_admin = require_admin_api_key()"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("✅ Fixed require_admin definition")
    else:
        print("❌ Could not find require_admin definition to fix")
        return False
    
    # Also fix other similar definitions if they exist
    fixes = [
        ("require_trader_or_admin = require_trader_or_admin_api_key", "require_trader_or_admin = require_trader_or_admin_api_key()"),
        ("require_verified_access = require_verified_user_api_key", "require_verified_access = require_verified_user_api_key()"),
        ("require_verified_trader_access = require_verified_trader_api_key", "require_verified_trader_access = require_verified_trader_api_key()"),
    ]
    
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Fixed {old.split('=')[0].strip()}")
    
    # Write the updated file
    with open(auth_file, 'w') as f:
        f.write(content)
    
    print("✅ Updated auth_dependencies.py")
    return True

def fix_api_key_admin_route():
    """Fix the API key admin route to use the correct dependency"""
    
    route_file = "api/routes/api_key_admin.py"
    
    if not os.path.exists(route_file):
        print(f"❌ File not found: {route_file}")
        return False
    
    print("🔧 Checking api_key_admin.py...")
    
    # Read the current file
    with open(route_file, 'r') as f:
        content = f.read()
    
    # Check if the import and usage are correct
    if 'from api.auth_dependencies import require_admin' in content:
        print("✅ require_admin import is correct")
        
        if 'admin: AuthenticatedAPIKeyUser = Depends(require_admin)' in content:
            print("✅ require_admin usage is correct")
            return True
        else:
            print("❌ require_admin usage is incorrect")
            # Could add a fix here if needed
            return False
    else:
        print("❌ require_admin import is missing or incorrect")
        return False

def test_fix():
    """Test if the fix will work"""
    
    print("🧪 Testing the fix...")
    
    try:
        # Try importing the auth dependencies
        import sys
        import os
        sys.path.insert(0, os.getcwd())
        
        from api.auth_dependencies import require_admin
        
        # Check if require_admin is now a function (which is correct)
        if callable(require_admin):
            print("✅ require_admin is now callable (correct)")
            return True
        else:
            print("❌ require_admin is not callable")
            return False
            
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing require_admin Dependency Issue")
    print("=" * 60)
    
    # Fix the auth dependencies
    auth_success = fix_auth_dependencies()
    
    # Check the API key admin route
    route_success = fix_api_key_admin_route()
    
    # Test the fix
    test_success = test_fix()
    
    if auth_success and route_success and test_success:
        print("\n🎉 require_admin dependency fixed!")
        print("=" * 60)
        print("✅ Fixed require_admin definition in auth_dependencies.py")
        print("✅ Verified API key admin route usage")
        print("✅ Import test passed")
        print("")
        print("🔄 Next steps:")
        print("1. Restart your FastAPI server:")
        print("   Press Ctrl+C to stop the current server")
        print("   Then: python3 -m uvicorn main:app --reload")
        print("")
        print("2. Test the API key creation:")
        print('   curl -X POST \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -H "Authorization: Bearer btapi_WIzZEd7BYB1TBBIy_CTonaCJy7Id4yNfsABWNeMVW7ww7x9qj" \\')
        print('        -d \'{"user_id": "1c6e8997-413a-4be3-ad48-90619823a833", "name": "Test Key", "description": "Test", "permissions_scope": "inherit"}\' \\')
        print('        http://localhost:8000/api/v1/admin/api-keys')
        print("")
        print("Expected: 201 Created with new API key details")
        
    else:
        print("\n❌ Fix failed")
        print("Please check the error messages above")
