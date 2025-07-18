#!/usr/bin/env python3
"""
Manual fix for main.py to add spread management routes
"""

import os
import shutil
from datetime import datetime

def fix_main_py():
    """Manually fix main.py to include spread routes"""
    
    print("🔧 Manually fixing main.py...")
    
    # Backup current main.py
    backup_name = f"main.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2("main.py", backup_name)
    print(f"✅ Backed up to {backup_name}")
    
    # Read current main.py
    with open("main.py", "r") as f:
        lines = f.readlines()
    
    # Find where routes are imported
    import_line_index = None
    for i, line in enumerate(lines):
        if "from api.routes import" in line:
            import_line_index = i
            break
    
    if import_line_index is None:
        print("❌ Could not find route imports!")
        return False
    
    # Check if spread_management is already imported
    if "spread_management" not in lines[import_line_index]:
        print("Adding spread_management to imports...")
        
        # Add spread_management to the import line
        import_line = lines[import_line_index].rstrip()
        if import_line.endswith(")"):
            # Multi-line import
            lines[import_line_index] = import_line[:-1] + ", spread_management)\n"
        else:
            # Single line import - need to check format
            if "," in import_line:
                lines[import_line_index] = import_line.rstrip() + ", spread_management\n"
            else:
                # Extract the single import
                parts = import_line.split("import")
                if len(parts) == 2:
                    lines[import_line_index] = parts[0] + "import " + parts[1].strip() + ", spread_management\n"
    
    # Find where routers are included
    found_router_section = False
    insert_after_index = None
    
    for i, line in enumerate(lines):
        if "app.include_router" in line and "trading_pairs" in line:
            insert_after_index = i
            found_router_section = True
            break
    
    if not found_router_section:
        print("❌ Could not find router inclusion section!")
        # Try to find any include_router
        for i, line in enumerate(lines):
            if "app.include_router" in line:
                insert_after_index = i
                found_router_section = True
                # Don't break, get the last one
    
    # Check if spread router already included
    spread_router_exists = any("spread_management.router" in line for line in lines)
    
    if not spread_router_exists and insert_after_index is not None:
        print("Adding spread_management router...")
        
        # Get indentation from the line we're inserting after
        indent = len(lines[insert_after_index]) - len(lines[insert_after_index].lstrip())
        
        # Create the new router line
        new_router_line = " " * indent + 'app.include_router(spread_management.router, prefix="/api/v1/trading-pairs", tags=["trading-pairs"])\n'
        
        # Insert after the found line
        lines.insert(insert_after_index + 1, new_router_line)
    
    # Write back the modified content
    with open("main.py", "w") as f:
        f.writelines(lines)
    
    print("✅ main.py has been updated!")
    
    # Show what was added
    print("\n📄 Changes made:")
    print("1. Added 'spread_management' to imports")
    print("2. Added spread_management.router with prefix '/api/v1/trading-pairs'")
    
    return True


def verify_files():
    """Verify all necessary files exist"""
    print("\n🔍 Verifying required files...")
    
    files_to_check = [
        ("api/routes/spread_management.py", "spread_management_routes.py"),
        ("api/services/enhanced_trade_service.py", "enhanced_trade_service.py"),
        ("api/services/enhanced_trade_models.py", "enhanced_trade_models.py"),
    ]
    
    all_good = True
    
    for target, source in files_to_check:
        if os.path.exists(target):
            print(f"✅ {target} exists")
        else:
            print(f"❌ {target} missing")
            if os.path.exists(source):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(source, target)
                print(f"  ✅ Copied from {source}")
            else:
                print(f"  ❌ Source file {source} not found!")
                all_good = False
    
    return all_good


if __name__ == "__main__":
    print("🚀 Manual Fix for Spread Routes")
    print("=" * 50)
    
    # First verify files
    if verify_files():
        # Then fix main.py
        if fix_main_py():
            print("\n✅ All fixes applied successfully!")
            print("\n📋 Next steps:")
            print("1. Stop your FastAPI app (Ctrl+C)")
            print("2. Restart it: python3 main.py")
            print("3. Check http://localhost:8000/docs")
            print("4. Run the test: python3 test_spread_functionality.py")
        else:
            print("\n❌ Could not complete main.py fixes")
    else:
        print("\n❌ Missing required files")
        print("Make sure all the spread-related files are in the current directory")
