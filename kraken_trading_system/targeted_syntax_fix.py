#!/usr/bin/env python3
"""
Targeted Syntax Error Fix

Direct fix for the specific syntax errors identified:
- websocket_client.py line 307: function name issue
- validate_task_3_3_a.py line 217: test method name issue

This script will read the files and fix the exact problematic lines.
"""

import sys
from pathlib import Path

def fix_websocket_client_line_307():
    """Fix the specific syntax error at line 307 in websocket_client.py."""
    
    print("🔧 Fixing WebSocket Client Line 307")
    print("-" * 40)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    print(f"📄 File has {len(lines)} lines")
    
    # Check line 307 (index 306)
    if len(lines) > 306:
        problematic_line = lines[306].strip()
        print(f"🔍 Line 307: {problematic_line}")
        
        # Common patterns to fix
        fixes = [
            ('def handle_order.current_state_change', 'def handle_order_state_change'),
            ('def order.current_state_', 'def order_state_'),
            ('def .*order.current_state.*', 'def handle_order_state_change'),
        ]
        
        fixed_line = lines[306]
        for pattern, replacement in fixes:
            if 'order.current_state' in fixed_line and 'def ' in fixed_line:
                # This is likely the broken function definition
                if 'handle_order.current_state_change' in fixed_line:
                    fixed_line = fixed_line.replace('handle_order.current_state_change', 'handle_order_state_change')
                elif 'def order.current_state_' in fixed_line:
                    # Extract the function name part after def and before (
                    import re
                    match = re.search(r'def ([^(]+)\(', fixed_line)
                    if match:
                        broken_name = match.group(1)
                        # Fix the broken name
                        fixed_name = broken_name.replace('order.current_state_', 'order_state_')
                        fixed_name = fixed_name.replace('.current_state', '_state')
                        fixed_line = re.sub(r'def [^(]+\(', f'def {fixed_name}(', fixed_line)
        
        if fixed_line != lines[306]:
            lines[306] = fixed_line
            print(f"✅ Fixed line 307: {fixed_line.strip()}")
            
            # Write back the file
            try:
                with open(websocket_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print("✅ WebSocket client file updated")
                return True
            except Exception as e:
                print(f"❌ Error writing file: {e}")
                return False
        else:
            print("ℹ️ Line 307 doesn't need fixing or couldn't be auto-fixed")
            print("🔍 Manual inspection needed")
            return False
    else:
        print("❌ File doesn't have 307 lines")
        return False

def fix_validation_test_line_217():
    """Fix the specific syntax error at line 217 in validate_task_3_3_a.py."""
    
    print("\n🔧 Fixing Validation Test Line 217")
    print("-" * 40)
    
    test_path = Path("validate_task_3_3_a.py")
    
    try:
        with open(test_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading validation test: {e}")
        return False
    
    print(f"📄 File has {len(lines)} lines")
    
    # Check line 217 (index 216)
    if len(lines) > 216:
        problematic_line = lines[216].strip()
        print(f"🔍 Line 217: {problematic_line}")
        
        fixed_line = lines[216]
        
        # Fix the broken test method name
        if '*test*order.current_state_synchronization' in fixed_line:
            fixed_line = fixed_line.replace('*test*order.current_state_synchronization', '_test_order_state_synchronization')
            print("✅ Fixed test method name")
        elif 'order.current_state_synchronization' in fixed_line and 'def ' in fixed_line:
            # More general fix for test methods
            import re
            fixed_line = re.sub(r'def [^(]*order\.current_state_([^(]*)\(', r'def _test_order_state_\1(', fixed_line)
            print("✅ Applied general test method fix")
        
        if fixed_line != lines[216]:
            lines[216] = fixed_line
            print(f"✅ Fixed line 217: {fixed_line.strip()}")
            
            # Write back the file
            try:
                with open(test_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print("✅ Validation test file updated")
                return True
            except Exception as e:
                print(f"❌ Error writing file: {e}")
                return False
        else:
            print("ℹ️ Line 217 doesn't need fixing or couldn't be auto-fixed")
            return False
    else:
        print("❌ File doesn't have 217 lines")
        return False

def scan_and_fix_all_syntax_errors():
    """Scan files for syntax errors and attempt to fix them."""
    
    print("\n🔍 Scanning for Additional Syntax Errors")
    print("-" * 40)
    
    files_to_check = [
        "src/trading_systems/exchanges/kraken/websocket_client.py",
        "src/trading_systems/exchanges/kraken/order_manager.py",
        "validate_task_3_3_a.py"
    ]
    
    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            continue
            
        print(f"\n📄 Checking {file_path}...")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            continue
        
        # Look for common broken patterns
        broken_patterns = [
            'def.*order.current_state.*(',
            'def.*\*test\*.*(',
            'async def.*\*test\*.*(',
        ]
        
        needs_fix = False
        for pattern in broken_patterns:
            import re
            if re.search(pattern, content):
                print(f"🔍 Found broken pattern: {pattern}")
                needs_fix = True
        
        if needs_fix:
            # Apply comprehensive fixes
            fixed_content = content
            
            # Fix function definitions
            fixed_content = re.sub(r'def handle_order\.current_state_change', 'def handle_order_state_change', fixed_content)
            fixed_content = re.sub(r'def ([^(]*order)\.current_state_([^(]*)\(', r'def \1_state_\2(', fixed_content)
            
            # Fix test method names
            fixed_content = re.sub(r'def \*test\*([^(]*)\(', r'def _test_\1(', fixed_content)
            fixed_content = re.sub(r'async def \*test\*([^(]*)\(', r'async def _test_\1(', fixed_content)
            
            # Fix specific broken patterns
            fixed_content = fixed_content.replace('*test*order.current_state_synchronization', '_test_order_state_synchronization')
            fixed_content = fixed_content.replace('*test*order.current_state_', '_test_order_state_')
            
            if fixed_content != content:
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    print(f"✅ Fixed syntax errors in {file_path}")
                except Exception as e:
                    print(f"❌ Error writing {file_path}: {e}")
            else:
                print(f"ℹ️ No fixes applied to {file_path}")
        else:
            print(f"✅ No syntax errors found in {file_path}")

def create_syntax_test():
    """Create a simple syntax test to verify Python can parse the files."""
    
    print("\n🧪 Creating Syntax Verification Test")
    print("-" * 40)
    
    syntax_test = '''#!/usr/bin/env python3
"""
Syntax verification test - checks if Python can parse our files.
"""

import ast
import sys
from pathlib import Path

def check_file_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def main():
    """Check syntax of key files."""
    print("🔍 SYNTAX VERIFICATION TEST")
    print("=" * 40)
    
    files_to_check = [
        "src/trading_systems/exchanges/kraken/websocket_client.py",
        "src/trading_systems/exchanges/kraken/order_manager.py", 
        "src/trading_systems/exchanges/kraken/order_models.py",
        "validate_task_3_3_a.py"
    ]
    
    all_good = True
    
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            is_valid, error = check_file_syntax(path)
            if is_valid:
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path}: {error}")
                all_good = False
        else:
            print(f"⚠️ {file_path}: File not found")
    
    print("\\n" + "=" * 40)
    if all_good:
        print("🎉 ALL FILES HAVE VALID SYNTAX!")
        print("Ready to test imports and functionality")
    else:
        print("❌ SYNTAX ERRORS STILL PRESENT")
        print("Manual review needed")
    print("=" * 40)

if __name__ == "__main__":
    main()
'''
    
    test_path = Path("syntax_verification_test.py")
    try:
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(syntax_test)
        print("✅ Created syntax verification test")
        return True
    except Exception as e:
        print(f"❌ Error creating syntax test: {e}")
        return False

def main():
    """Main execution function."""
    print("🎯 TARGETED SYNTAX ERROR FIX")
    print("=" * 50)
    print()
    print("Fixing specific syntax errors at known line numbers:")
    print("• websocket_client.py line 307")
    print("• validate_task_3_3_a.py line 217")
    print()
    
    success_count = 0
    total_fixes = 4
    
    # Fix 1: WebSocket client line 307
    if fix_websocket_client_line_307():
        success_count += 1
    
    # Fix 2: Validation test line 217
    if fix_validation_test_line_217():
        success_count += 1
    
    # Fix 3: Scan and fix additional errors
    scan_and_fix_all_syntax_errors()
    success_count += 1  # Count as success since it runs
    
    # Fix 4: Create syntax verification test
    if create_syntax_test():
        success_count += 1
    
    print("\n" + "=" * 50)
    print("📊 TARGETED FIX RESULTS")
    print("=" * 50)
    print(f"🎯 Fixes Attempted: {success_count}/{total_fixes}")
    
    print("\n🧪 Next Steps:")
    print("1. Run: python3 syntax_verification_test.py")
    print("2. If syntax is clean, try: python3 simple_syntax_validation.py")
    print("3. Finally: python3 validate_task_3_3_a.py")
    
    print("=" * 50)
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
