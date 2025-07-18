#!/usr/bin/env python3
"""
Fix the syntax error in main.py - missing comma before spread_management line
"""

import os
import shutil
from datetime import datetime

def fix_syntax_error():
    """Fix the missing comma syntax error in main.py"""
    
    print("🔧 Fixing syntax error in main.py...")
    
    # Backup current main.py
    backup_name = f"main.py.backup_syntax_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2("main.py", backup_name)
    print(f"✅ Backed up to {backup_name}")
    
    # Read main.py
    with open("main.py", "r") as f:
        content = f.read()
    
    # Find the error around line 110
    lines = content.split('\n')
    
    # Look for the spread_management line
    for i, line in enumerate(lines):
        if "app.include_router(spread_management.router" in line:
            print(f"Found spread_management router at line {i+1}")
            
            # Check the line before it
            if i > 0:
                prev_line = lines[i-1]
                print(f"Previous line: {prev_line.strip()}")
                
                # If the previous line is an app.include_router and doesn't end with comma
                if "app.include_router" in prev_line and not prev_line.rstrip().endswith(","):
                    print("❌ Missing comma found!")
                    # Add comma to the end of previous line
                    lines[i-1] = prev_line.rstrip() + ","
                    print("✅ Added missing comma")
    
    # Write back
    with open("main.py", "w") as f:
        f.write('\n'.join(lines))
    
    print("✅ Syntax error fixed!")
    
    # Show the fixed area
    print("\n📄 Fixed code section:")
    for i, line in enumerate(lines):
        if "trading_pairs.router" in line:
            # Show a few lines around the fix
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                marker = ">>>" if j == i or j == i+1 else "   "
                print(f"{marker} {lines[j]}")
            break

def verify_syntax():
    """Verify the Python syntax is correct"""
    print("\n🔍 Verifying Python syntax...")
    
    try:
        with open("main.py", "r") as f:
            code = f.read()
        
        # Try to compile the code
        compile(code, "main.py", "exec")
        print("✅ Python syntax is valid!")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error still present: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False

def show_router_section():
    """Show the router section of main.py for manual inspection"""
    print("\n📋 Current router section in main.py:")
    print("-" * 50)
    
    with open("main.py", "r") as f:
        lines = f.readlines()
    
    in_router_section = False
    for i, line in enumerate(lines):
        if "app.include_router" in line:
            in_router_section = True
        
        if in_router_section:
            print(f"{i+1:3d}: {line.rstrip()}")
            
        # Stop after we've seen all routers
        if in_router_section and line.strip() == "" and not any("app.include_router" in lines[j] for j in range(i+1, min(i+5, len(lines)))):
            break

if __name__ == "__main__":
    print("🚀 Fixing Syntax Error in main.py")
    print("=" * 50)
    
    # Fix the syntax error
    fix_syntax_error()
    
    # Verify it's fixed
    if verify_syntax():
        print("\n✅ All syntax errors fixed!")
        print("\n📋 Next steps:")
        print("1. Start FastAPI: python3 main.py")
        print("2. Run the test: python3 test_spread_functionality.py")
    else:
        print("\n❌ Syntax errors remain")
        show_router_section()
        print("\nPlease check the router section above and fix any issues manually")
