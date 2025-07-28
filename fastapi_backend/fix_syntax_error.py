#!/usr/bin/env python3
"""
Fix Syntax Error in users.py
Fixes the unclosed parenthesis issue introduced by the route fix
"""

import os
import re

def fix_users_syntax_error():
    """Fix the syntax error in users.py"""
    
    users_file = "api/routes/users.py"
    
    if not os.path.exists(users_file):
        print(f"❌ File not found: {users_file}")
        return False
    
    print("🔧 Fixing syntax error in users.py...")
    
    # Read the current file
    with open(users_file, 'r') as f:
        content = f.read()
    
    # Fix the unclosed parenthesis issue
    fixes_made = 0
    
    # Common syntax error patterns to fix
    syntax_fixes = [
        # Fix unclosed @router.get("/" 
        (r'@router\.get\("/"\s*$', r'@router.get("/")'),
        (r'@router\.get\("/"\s*\n', r'@router.get("/")\n'),
        (r'@router\.get\("/$', r'@router.get("/")'),
        
        # Fix any other unclosed decorators
        (r'@router\.(get|post|put|delete)\("([^"]*)"?\s*$', r'@router.\1("\2")'),
        (r'@router\.(get|post|put|delete)\("([^"]*)"?\s*\n', r'@router.\1("\2")\n'),
    ]
    
    for old_pattern, new_pattern in syntax_fixes:
        if re.search(old_pattern, content, re.MULTILINE):
            content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
            fixes_made += 1
            print(f"✅ Fixed pattern: {old_pattern}")
    
    # Also check for any other common syntax issues
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check for incomplete decorators
        if line.strip().startswith('@router.') and '(' in line and ')' not in line:
            # This line has an unclosed parenthesis
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith(('async def', '@')):
                # Next line doesn't look like a function definition or another decorator
                # So this decorator is probably incomplete
                line = line.rstrip() + ')'
                fixes_made += 1
                print(f"✅ Fixed incomplete decorator on line {i + 1}: {line.strip()}")
        
        fixed_lines.append(line)
    
    if fixes_made > 0:
        # Write the updated file
        with open(users_file, 'w') as f:
            f.write('\n'.join(fixed_lines))
        print(f"✅ Applied {fixes_made} syntax fixes to users.py")
        return True
    else:
        print("ℹ️ No syntax errors found in users.py")
        return True

def check_all_route_files_syntax():
    """Check all route files for syntax errors"""
    
    route_files = [
        "api/routes/users.py",
        "api/routes/currencies.py", 
        "api/routes/transactions.py",
        "api/routes/balances.py",
        "api/routes/trades.py",
        "api/routes/trading_pairs.py"
    ]
    
    print("🔍 Checking all route files for syntax errors...")
    
    for route_file in route_files:
        if not os.path.exists(route_file):
            print(f"⚠️ File not found: {route_file} (skipping)")
            continue
        
        try:
            # Try to compile the file to check for syntax errors
            with open(route_file, 'r') as f:
                content = f.read()
            
            compile(content, route_file, 'exec')
            print(f"✅ {route_file}: No syntax errors")
            
        except SyntaxError as e:
            print(f"❌ {route_file}: Syntax error on line {e.lineno}: {e.msg}")
            
            # Try to fix common issues
            if 'was never closed' in e.msg and '(' in e.msg:
                print(f"🔧 Attempting to fix unclosed parenthesis in {route_file}")
                
                lines = content.split('\n')
                if e.lineno <= len(lines):
                    problematic_line = lines[e.lineno - 1]
                    print(f"   Problematic line: {problematic_line.strip()}")
                    
                    # Fix the line
                    if problematic_line.strip().endswith('("'):
                        lines[e.lineno - 1] = problematic_line + '")'
                        print(f"   Fixed to: {lines[e.lineno - 1].strip()}")
                        
                        # Write the fix
                        with open(route_file, 'w') as f:
                            f.write('\n'.join(lines))
                        print(f"✅ Fixed syntax error in {route_file}")
            
        except Exception as e:
            print(f"❌ {route_file}: Other error: {e}")

def test_import_main():
    """Test if main.py can be imported successfully"""
    
    print("🧪 Testing main.py import...")
    
    try:
        import sys
        import os
        
        # Add current directory to path
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Try importing main
        import main
        print("✅ main.py imports successfully")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in main.py or imported modules: {e}")
        print(f"   File: {e.filename}")
        print(f"   Line: {e.lineno}")
        print(f"   Error: {e.msg}")
        return False
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing Syntax Errors")
    print("=" * 40)
    
    # Fix the specific users.py syntax error
    users_success = fix_users_syntax_error()
    
    # Check all route files for syntax errors
    check_all_route_files_syntax()
    
    # Test if main.py can be imported
    import_success = test_import_main()
    
    if users_success and import_success:
        print("\n🎉 Syntax Errors Fixed!")
        print("=" * 40)
        print("✅ Fixed users.py syntax error")
        print("✅ Checked all route files")
        print("✅ main.py imports successfully")
        print("")
        print("🔄 Next steps:")
        print("1. Restart your FastAPI server:")
        print("   python3 -m uvicorn main:app --reload")
        print("")
        print("2. If server starts successfully, run tests:")
        print("   ./api_test.sh")
        
    else:
        print("\n❌ Some issues remain")  
        print("Please check the error messages above")
