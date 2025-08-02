#!/usr/bin/env python3
"""
Fix trading_pairs import error in main.py
"""

import os
import shutil
from datetime import datetime

def backup_main():
    """Backup main.py before fixing"""
    if os.path.exists("main.py"):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"main.py.backup_import_fix_{timestamp}"
        shutil.copy2("main.py", backup_path)
        print(f"✅ Backed up main.py to {backup_path}")
        return True
    return False

def fix_trading_pairs_import():
    """Fix the missing trading_pairs import in main.py"""
    
    if not os.path.exists("main.py"):
        print("❌ main.py not found!")
        return False
    
    print("🔧 Fixing trading_pairs import in main.py...")
    
    # Read the current file
    with open("main.py", 'r') as f:
        content = f.read()
    
    fixes_applied = 0
    
    # Check if trading_pairs is being used but not imported
    if 'trading_pairs.router' in content and 'trading_pairs' not in content.split('trading_pairs.router')[0]:
        print("🔍 Found trading_pairs.router usage without import")
        
        # Find the imports section
        lines = content.split('\n')
        import_section_end = -1
        
        # Look for existing api.routes imports
        for i, line in enumerate(lines):
            if 'from api.routes import' in line:
                # Check if this is a multi-line import or single line
                if line.strip().endswith(','):
                    # Multi-line import - find the end
                    j = i + 1
                    while j < len(lines) and (lines[j].strip().endswith(',') or not lines[j].strip()):
                        j += 1
                    import_section_end = j
                    
                    # Add trading_pairs to the import
                    if 'trading_pairs' not in line:
                        # Find the last import line before the closing
                        insert_line = j - 1
                        while insert_line > i and not lines[insert_line].strip():
                            insert_line -= 1
                        
                        if lines[insert_line].strip() and not lines[insert_line].strip().endswith(','):
                            lines[insert_line] = lines[insert_line].rstrip() + ','
                        
                        # Add trading_pairs import
                        lines.insert(insert_line + 1, '    trading_pairs')
                        fixes_applied += 1
                        print("✅ Added trading_pairs to multi-line import")
                        break
                        
                elif 'currencies' in line or 'trades' in line:
                    # Single line import - add trading_pairs
                    if 'trading_pairs' not in line:
                        lines[i] = line.replace('currencies', 'currencies, trading_pairs') if 'currencies' in line else line.replace('trades', 'trades, trading_pairs')
                        fixes_applied += 1
                        print("✅ Added trading_pairs to single-line import")
                        break
        
        # If no existing api.routes import found, add one
        if import_section_end == -1 and fixes_applied == 0:
            # Find a good place to add the import (after other imports)
            insert_index = 0
            for i, line in enumerate(lines):
                if line.startswith('from api.') or line.startswith('import '):
                    insert_index = i + 1
            
            lines.insert(insert_index, 'from api.routes import trading_pairs')
            fixes_applied += 1
            print("✅ Added new trading_pairs import")
    
    # Also check if the file is trying to use trading_pairs without the router being included
    if 'trading_pairs.router' in content and 'include_router' not in content.split('trading_pairs.router')[1].split('\n')[0]:
        print("🔍 Found trading_pairs.router usage that might need router inclusion")
    
    # Write the fixed content back
    if fixes_applied > 0:
        try:
            with open("main.py", 'w') as f:
                f.write('\n'.join(lines))
            print(f"✅ Applied {fixes_applied} import fixes to main.py")
            
            # Test if the imports work now
            try:
                with open("main.py", 'r') as f:
                    test_content = f.read()
                compile(test_content, "main.py", 'exec')
                print("✅ Syntax is still valid after import fix!")
                return True
            except SyntaxError as e:
                print(f"❌ Syntax error introduced: {e.msg} on line {e.lineno}")
                return False
            except Exception as e:
                print(f"⚠️ Compilation succeeded, but there might be runtime issues: {e}")
                return True
        except Exception as e:
            print(f"❌ Error writing fixed file: {e}")
            return False
    else:
        print("ℹ️ No import fixes needed or couldn't automatically fix")
        print("🔍 Manual inspection needed")
        
        # Show the current imports for debugging
        print("\nCurrent imports in main.py:")
        with open("main.py", 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if 'import' in line and ('api.routes' in line or 'trading_pairs' in line):
                print(f"  Line {i+1}: {line.strip()}")
        
        return False

def check_trading_pairs_file():
    """Check if trading_pairs.py file exists"""
    
    trading_pairs_file = "api/routes/trading_pairs.py"
    
    if os.path.exists(trading_pairs_file):
        print(f"✅ {trading_pairs_file} exists")
        
        # Check if it has a router
        with open(trading_pairs_file, 'r') as f:
            content = f.read()
        
        if 'router = APIRouter()' in content:
            print("✅ trading_pairs.py has router defined")
            return True
        else:
            print("❌ trading_pairs.py missing router definition")
            return False
    else:
        print(f"❌ {trading_pairs_file} does not exist")
        print("📋 You need to create this file first")
        return False

def main():
    """Main execution"""
    print("🔧 FIXING TRADING_PAIRS IMPORT ERROR")
    print("=" * 40)
    
    # Check if trading_pairs file exists first
    if not check_trading_pairs_file():
        print("\n❌ Cannot fix import - trading_pairs.py file is missing")
        print("\n📋 You need to:")
        print("1. Create api/routes/trading_pairs.py file")
        print("2. OR remove the trading_pairs.router usage from main.py")
        return False
    
    # Backup first
    backup_main()
    
    # Apply fixes
    if fix_trading_pairs_import():
        print("\n🎉 trading_pairs import fixed!")
        print("\nNow try running:")
        print("python3 -m uvicorn main:app --reload")
    else:
        print("\n❌ Could not fix import automatically")
        print("\n📋 Manual fix needed:")
        print("1. Find the line with 'from api.routes import ...'")
        print("2. Add 'trading_pairs' to that import")
        print("3. OR create the missing trading_pairs.py file")

if __name__ == "__main__":
    main()
