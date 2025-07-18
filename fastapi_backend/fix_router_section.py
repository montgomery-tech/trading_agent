#!/usr/bin/env python3
"""
Fix the messed up router section in main.py
"""

import os
import shutil
from datetime import datetime

def fix_router_section():
    """Fix the broken router section"""
    
    print("🔧 Fixing router section in main.py...")
    
    # Backup
    backup_name = f"main.py.backup_router_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2("main.py", backup_name)
    print(f"✅ Backed up to {backup_name}")
    
    # Read file
    with open("main.py", "r") as f:
        lines = f.readlines()
    
    # Find and fix the problematic section
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip the broken line 109
        if i < len(lines) - 1 and "app.include_router(," in line and "app.include_router(spread_management.router" in lines[i+1]:
            print(f"Found broken lines at {i+1}-{i+2}")
            # Skip the broken line
            i += 1
            # Fix the spread_management line
            fixed_lines.append("app.include_router(spread_management.router, prefix=\"/api/v1/trading-pairs\", tags=[\"trading-pairs\"])\n")
            fixed_lines.append("\n")
            fixed_lines.append("app.include_router(\n")
            i += 1
            continue
        
        fixed_lines.append(line)
        i += 1
    
    # Write back
    with open("main.py", "w") as f:
        f.writelines(fixed_lines)
    
    print("✅ Router section fixed!")

def show_fixed_section():
    """Show the fixed router section"""
    print("\n📄 Fixed router section:")
    print("-" * 50)
    
    with open("main.py", "r") as f:
        lines = f.readlines()
    
    # Show lines around the router section
    for i, line in enumerate(lines):
        if i >= 100 and i <= 120:  # Show lines 101-121
            print(f"{i+1:3d}: {line.rstrip()}")

def verify_imports():
    """Make sure spread_management is imported"""
    print("\n🔍 Verifying imports...")
    
    with open("main.py", "r") as f:
        content = f.read()
    
    if "spread_management" not in content:
        print("❌ spread_management not imported!")
        
        # Find imports and add it
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "from api.routes import" in line and "spread_management" not in line:
                # Add spread_management to this import
                if line.rstrip().endswith(")"):
                    lines[i] = line.rstrip()[:-1] + ", spread_management)"
                else:
                    lines[i] = line.rstrip() + ", spread_management"
                print("✅ Added spread_management to imports")
                break
        
        with open("main.py", "w") as f:
            f.write('\n'.join(lines))
    else:
        print("✅ spread_management is imported")

def final_syntax_check():
    """Final syntax check"""
    print("\n🔍 Final syntax check...")
    
    try:
        with open("main.py", "r") as f:
            code = f.read()
        compile(code, "main.py", "exec")
        print("✅ Syntax is valid!")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False

if __name__ == "__main__":
    print("🚀 Fixing Router Section")
    print("=" * 50)
    
    # First verify imports
    verify_imports()
    
    # Fix the router section
    fix_router_section()
    
    # Show the fixed section
    show_fixed_section()
    
    # Final syntax check
    if final_syntax_check():
        print("\n✅ All fixed! You can now start FastAPI:")
        print("   python3 main.py")
    else:
        print("\n❌ Still has issues. Please check main.py manually")
