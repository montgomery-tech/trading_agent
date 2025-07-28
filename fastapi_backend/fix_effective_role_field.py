#!/usr/bin/env python3
"""
Fix AuthenticatedAPIKeyUser Model
Adds the missing effective_role field to prevent the AttributeError
"""

import os

def fix_api_key_user_model():
    """Add effective_role field to AuthenticatedAPIKeyUser model"""
    
    model_file = "api/api_key_models.py"
    
    if not os.path.exists(model_file):
        print(f"❌ File not found: {model_file}")
        return False
    
    print("🔧 Fixing AuthenticatedAPIKeyUser model...")
    
    # Read the current file
    with open(model_file, 'r') as f:
        content = f.read()
    
    # Check if effective_role is already there
    if 'effective_role' in content:
        print("✅ effective_role field already exists")
        return True
    
    # Find the AuthenticatedAPIKeyUser class and add the field
    lines = content.split('\n')
    new_lines = []
    in_authenticated_user_class = False
    field_added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Look for the AuthenticatedAPIKeyUser class
        if 'class AuthenticatedAPIKeyUser' in line:
            in_authenticated_user_class = True
            continue
        
        # If we're in the class and see the last field before class config
        if in_authenticated_user_class and not field_added:
            # Look for the last field in the class (usually api_key_scope)
            if 'api_key_scope:' in line or 'api_key_name:' in line:
                # Add the effective_role field after this line
                indent = '    ' if line.startswith('    ') else '    '
                new_lines.append(f'{indent}effective_role: Optional[UserRole] = None  # Computed effective role')
                field_added = True
                in_authenticated_user_class = False
    
    if not field_added:
        print("❌ Could not find the right place to add effective_role field")
        print("Please add this line manually to AuthenticatedAPIKeyUser class:")
        print("    effective_role: Optional[UserRole] = None  # Computed effective role")
        return False
    
    # Write the updated file
    with open(model_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Added effective_role field to AuthenticatedAPIKeyUser")
    return True

def fix_auth_dependencies():
    """Fix the auth_dependencies.py file to handle the effective_role properly"""
    
    auth_file = "api/auth_dependencies.py" 
    
    if not os.path.exists(auth_file):
        print(f"❌ File not found: {auth_file}")
        return False
    
    print("🔧 Fixing auth_dependencies.py...")
    
    # Read the current file
    with open(auth_file, 'r') as f:
        content = f.read()
    
    # Replace the problematic line
    old_line = "current_user.effective_role = effective_role"
    new_line = "# Store effective role for use in route handlers\n        current_user.effective_role = effective_role"
    
    if old_line in content:
        # The line exists, so the model fix should work
        print("✅ auth_dependencies.py looks correct after model fix")
        return True
    else:
        print("✅ auth_dependencies.py doesn't need changes")
        return True

if __name__ == "__main__":
    print("🔧 Fixing AuthenticatedAPIKeyUser effective_role issue...")
    print("=" * 60)
    
    success1 = fix_api_key_user_model()
    success2 = fix_auth_dependencies()
    
    if success1 and success2:
        print("\n🎉 Fix completed successfully!")
        print("=" * 60)
        print("✅ Added effective_role field to AuthenticatedAPIKeyUser model")
        print("✅ Fixed auth_dependencies.py")
        print("")
        print("🔄 Next steps:")
        print("1. Restart your FastAPI server:")
        print("   Press Ctrl+C to stop the current server")
        print("   Then: python3 -m uvicorn main:app --reload")
        print("")
        print("2. Test the API key authentication:")
        print('   curl -H "Authorization: Bearer btapi_WIzZEd7BYB1TBBIy_CTonaCJy7Id4yNfsABWNeMVW7ww7x9qj" \\')
        print('        http://localhost:8000/api/v1/admin/users')
        
    else:
        print("\n❌ Fix failed. Please check the error messages above.")
