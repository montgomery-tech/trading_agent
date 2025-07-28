#!/usr/bin/env python3
"""
Fix main.py API Key Admin Import
Adds the missing api_key_admin import to main.py
"""

import os

def fix_main_py_imports():
    """Fix the missing api_key_admin import in main.py"""
    
    main_file = "main.py"
    
    if not os.path.exists(main_file):
        print(f"❌ File not found: {main_file}")
        return False
    
    print("🔧 Fixing main.py imports...")
    
    # Read the current file
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if api_key_admin is already imported
    if 'from api.routes import' in content and 'api_key_admin' in content:
        print("✅ api_key_admin import already exists")
        
        # Check if it's actually being used
        if 'api_key_admin.router' in content:
            print("✅ api_key_admin router is registered")
            return True
        else:
            print("❌ api_key_admin imported but router not registered")
    
    # Find the imports section and add api_key_admin if missing
    lines = content.split('\n')
    new_lines = []
    import_fixed = False
    
    for i, line in enumerate(lines):
        # Look for the route imports line
        if 'from api.routes import' in line and not import_fixed:
            if 'api_key_admin' not in line:
                # Add api_key_admin to the import
                if line.strip().endswith(','):
                    # Multi-line import
                    new_lines.append(line)
                    # Look for the end of the multi-line import
                    j = i + 1
                    while j < len(lines) and not lines[j].strip().startswith('from'):
                        if ')' in lines[j]:
                            # End of import found
                            new_lines.append(f"    api_key_admin,")
                            break
                        j += 1
                    import_fixed = True
                else:
                    # Single line import - add comma and api_key_admin
                    new_line = line.rstrip() + ", api_key_admin"
                    new_lines.append(new_line)
                    import_fixed = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # If we couldn't find the right import line, add it manually
    if not import_fixed:
        # Look for other route imports and add after them
        for i, line in enumerate(new_lines):
            if 'from api.routes import admin' in line:
                new_lines.insert(i + 1, "from api.routes import api_key_admin")
                import_fixed = True
                break
    
    if not import_fixed:
        print("❌ Could not find where to add the import")
        print("Please add this line manually after other route imports:")
        print("from api.routes import api_key_admin")
        return False
    
    # Write the updated file
    with open(main_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Added api_key_admin import to main.py")
    return True

def verify_api_key_admin_registration():
    """Verify that api_key_admin router is properly registered"""
    
    main_file = "main.py"
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    print("🔍 Verifying API key admin router registration...")
    
    # Check for import
    has_import = 'api_key_admin' in content and 'from api.routes import' in content
    print(f"{'✅' if has_import else '❌'} api_key_admin import: {has_import}")
    
    # Check for router registration
    has_router = 'api_key_admin.router' in content
    print(f"{'✅' if has_router else '❌'} api_key_admin.router registration: {has_router}")
    
    # Check for correct prefix
    has_prefix = 'prefix=f"{settings.API_V1_PREFIX}/admin"' in content
    print(f"{'✅' if has_prefix else '❌'} correct prefix: {has_prefix}")
    
    if has_import and has_router and has_prefix:
        print("✅ API key admin router should be working")
        return True
    else:
        print("❌ API key admin router configuration has issues")
        return False

if __name__ == "__main__":
    print("🔧 Fixing main.py API Key Admin Configuration")
    print("=" * 60)
    
    # First, try to fix the imports
    import_success = fix_main_py_imports()
    
    # Then verify everything is correct
    registration_success = verify_api_key_admin_registration()
    
    if import_success and registration_success:
        print("\n🎉 main.py API Key Admin configuration fixed!")
        print("=" * 60)
        print("")
        print("🔄 Next steps:")
        print("1. Restart your FastAPI server:")
        print("   Press Ctrl+C to stop the current server")
        print("   Then: python3 -m uvicorn main:app --reload")
        print("")
        print("2. Test the API key creation endpoint:")
        print('   curl -X POST \\')
        print('        -H "Content-Type: application/json" \\')
        print('        -H "Authorization: Bearer btapi_WIzZEd7BYB1TBBIy_CTonaCJy7Id4yNfsABWNeMVW7ww7x9qj" \\')
        print('        -d \'{"user_id": "1c6e8997-413a-4be3-ad48-90619823a833", "name": "Test Key", "description": "Test", "permissions_scope": "inherit"}\' \\')
        print('        http://localhost:8000/api/v1/admin/api-keys')
        print("")
        print("Expected: 201 Created with new API key details")
        
    else:
        print("\n❌ Configuration fix failed")
        print("Please check the error messages above and fix manually")
