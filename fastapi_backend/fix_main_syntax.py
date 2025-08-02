#!/usr/bin/env python3
"""
Fix main.py syntax error - specifically the \n character issue
"""

import os
import shutil
from datetime import datetime

def backup_main():
    """Backup main.py before fixing"""
    if os.path.exists("main.py"):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"main.py.backup_syntax_fix_{timestamp}"
        shutil.copy2("main.py", backup_path)
        print(f"✅ Backed up main.py to {backup_path}")
        return True
    return False

def fix_main_syntax():
    """Fix the syntax error in main.py"""
    
    if not os.path.exists("main.py"):
        print("❌ main.py not found!")
        return False
    
    print("🔧 Fixing main.py syntax error...")
    
    # Read the current file
    with open("main.py", 'r') as f:
        content = f.read()
    
    # Common issues that cause this error:
    # 1. Literal \n characters instead of actual newlines
    # 2. Escaped backslashes that shouldn't be escaped
    
    fixes_applied = 0
    
    # Fix 1: Replace literal \n with actual newlines
    if '\\n' in content:
        content = content.replace('\\n', '\n')
        fixes_applied += 1
        print("✅ Fixed literal \\n characters")
    
    # Fix 2: Replace literal \' with actual single quotes
    if "\\'" in content:
        content = content.replace("\\'", "'")
        fixes_applied += 1
        print("✅ Fixed literal \\' characters")
    
    # Fix 3: Replace literal \" with actual double quotes
    if '\\"' in content:
        content = content.replace('\\"', '"')
        fixes_applied += 1
        print("✅ Fixed literal \\\" characters")
    
    # Fix 4: Look for and fix any other escape sequence issues
    problematic_patterns = [
        ('\\\\n', '\n'),  # Double escaped newlines
        ('\\\\t', '\t'),  # Double escaped tabs
        ('\\\\r', '\r'),  # Double escaped carriage returns
    ]
    
    for pattern, replacement in problematic_patterns:
        if pattern in content:
            content = content.replace(pattern, replacement)
            fixes_applied += 1
            print(f"✅ Fixed {pattern} pattern")
    
    # Fix 5: Check for specific line 221 issues
    lines = content.split('\n')
    if len(lines) >= 221:
        line_221 = lines[220]  # 0-indexed
        if '\\' in line_221 and line_221.strip().endswith('\\'):
            # This line ends with a backslash - probably a broken line continuation
            print(f"🔍 Line 221 before fix: {repr(line_221)}")
            
            # Remove the trailing backslash if it's not supposed to be there
            if line_221.strip() == '\\' or line_221.strip().endswith('\\'):
                lines[220] = line_221.rstrip('\\').rstrip()
                fixes_applied += 1
                print(f"✅ Fixed line 221: {repr(lines[220])}")
    
    # Write the fixed content back
    if fixes_applied > 0:
        try:
            with open("main.py", 'w') as f:
                f.write('\n'.join(lines) if 'lines' in locals() else content)
            print(f"✅ Applied {fixes_applied} fixes to main.py")
            
            # Test if the syntax is now valid
            try:
                with open("main.py", 'r') as f:
                    test_content = f.read()
                compile(test_content, "main.py", 'exec')
                print("✅ Syntax is now valid!")
                return True
            except SyntaxError as e:
                print(f"❌ Still has syntax error: {e.msg} on line {e.lineno}")
                # Show the problematic line
                test_lines = test_content.split('\n')
                if e.lineno <= len(test_lines):
                    print(f"   Problematic line: {repr(test_lines[e.lineno - 1])}")
                return False
        except Exception as e:
            print(f"❌ Error writing fixed file: {e}")
            return False
    else:
        print("ℹ️ No obvious syntax fixes needed")
        # Still test the syntax
        try:
            compile(content, "main.py", 'exec')
            print("✅ Syntax is already valid!")
            return True
        except SyntaxError as e:
            print(f"❌ Syntax error found: {e.msg} on line {e.lineno}")
            # Show the problematic line
            lines = content.split('\n')
            if e.lineno <= len(lines):
                print(f"   Problematic line: {repr(lines[e.lineno - 1])}")
            return False

def main():
    """Main execution"""
    print("🔧 FIXING MAIN.PY SYNTAX ERROR")
    print("=" * 40)
    
    # Backup first
    backup_main()
    
    # Apply fixes
    if fix_main_syntax():
        print("\n🎉 main.py syntax fixed!")
        print("\nNow try running:")
        print("python3 -m uvicorn main:app --reload")
    else:
        print("\n❌ Could not fix main.py automatically")
        print("Manual inspection needed - check line 221")
        print("Look for:")
        print("- Literal \\n characters that should be actual newlines")
        print("- Unescaped backslashes")
        print("- Line continuation characters (\\) at end of lines")

if __name__ == "__main__":
    main()
