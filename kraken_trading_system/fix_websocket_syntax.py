#!/usr/bin/env python3
"""
Fix WebSocket Client Syntax Error

Fix the unexpected indent error on line 93 of websocket_client.py
"""

import sys
from pathlib import Path


def fix_syntax_error():
    """Fix the syntax error in websocket_client.py."""
    
    print("🔧 FIXING WEBSOCKET CLIENT SYNTAX ERROR")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Try to compile and identify the exact error
    try:
        compile(content, str(websocket_path), 'exec')
        print("✅ No syntax errors found")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error on line {e.lineno}: {e.msg}")
        print(f"   Text: {e.text}")
        
        lines = content.split('\n')
        error_line_num = e.lineno - 1  # 0-indexed
        
        if error_line_num < len(lines):
            error_line = lines[error_line_num]
            print(f"   Error line: '{error_line}'")
            
            # Common fixes for indentation errors
            if e.msg == "unexpected indent":
                # Check previous line
                if error_line_num > 0:
                    prev_line = lines[error_line_num - 1]
                    print(f"   Previous line: '{prev_line}'")
                    
                    # If previous line ends with colon, current line should be indented
                    if prev_line.strip().endswith(':'):
                        # Check if current line needs more indentation
                        if error_line.strip() and not error_line.startswith('    '):
                            lines[error_line_num] = '    ' + error_line.strip()
                            print("   ✅ Added missing indentation")
                        elif error_line.startswith('        '):  # Too much indentation
                            lines[error_line_num] = '    ' + error_line.lstrip()
                            print("   ✅ Fixed excessive indentation")
                    else:
                        # Previous line doesn't need indented continuation
                        # Remove excessive indentation
                        if error_line.startswith('    '):
                            lines[error_line_num] = error_line[4:]
                            print("   ✅ Removed unexpected indentation")
                        elif error_line.startswith('        '):
                            lines[error_line_num] = error_line[8:]
                            print("   ✅ Removed excessive indentation")
            
            elif "invalid character" in e.msg:
                # Remove invalid characters (like emoji)
                clean_line = ''.join(char for char in error_line if ord(char) < 128)
                if clean_line != error_line:
                    lines[error_line_num] = clean_line
                    print("   ✅ Removed invalid characters")
            
            # Write fixed content
            fixed_content = '\n'.join(lines)
            
            # Test the fix
            try:
                compile(fixed_content, str(websocket_path), 'exec')
                print("   ✅ Syntax error fixed!")
                
                with open(websocket_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print("✅ Fixed file written")
                return True
                
            except SyntaxError as e2:
                print(f"   ❌ Still has syntax error: {e2.msg} on line {e2.lineno}")
                
                # Try a more aggressive fix - look around the error area
                return fix_surrounding_lines(lines, error_line_num, websocket_path)
        
        return False
    
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")
        return False


def fix_surrounding_lines(lines, error_line_num, websocket_path):
    """Fix syntax errors by examining surrounding lines."""
    
    print("🔧 Attempting broader syntax fix...")
    
    # Look at lines around the error
    start_line = max(0, error_line_num - 5)
    end_line = min(len(lines), error_line_num + 5)
    
    print(f"Examining lines {start_line + 1} to {end_line}:")
    
    for i in range(start_line, end_line):
        line = lines[i]
        marker = " >>> " if i == error_line_num else "     "
        print(f"{marker}Line {i+1}: {repr(line)}")
        
        # Fix common issues
        if i == error_line_num:
            # Remove any weird indentation
            if line.strip():
                # Count leading spaces in surrounding lines to determine correct indentation
                prev_indent = 0
                if i > 0 and lines[i-1].strip():
                    prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                
                # If previous line ends with colon, add 4 spaces
                if i > 0 and lines[i-1].strip().endswith(':'):
                    correct_indent = prev_indent + 4
                else:
                    correct_indent = prev_indent
                
                lines[i] = ' ' * correct_indent + line.strip()
                print(f"   Fixed indentation to {correct_indent} spaces")
    
    # Test the fix
    fixed_content = '\n'.join(lines)
    
    try:
        compile(fixed_content, str(websocket_path), 'exec')
        print("✅ Broader syntax fix successful!")
        
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return True
        
    except SyntaxError as e:
        print(f"❌ Still has error: {e.msg} on line {e.lineno}")
        print("Manual fix required")
        return False


def main():
    """Main execution function."""
    print("🔧 FIXING WEBSOCKET CLIENT SYNTAX ERROR")
    print("=" * 60)
    print("Fixing the unexpected indent error...")
    print()
    
    success = fix_syntax_error()
    
    if success:
        print("\n🎉 SUCCESS: Syntax Error Fixed!")
        print("=" * 60)
        print("✅ WebSocket client syntax is now valid")
        print("✅ Ready to test live order placement")
        print()
        print("🚀 TEST AGAIN:")
        print("python3 live_order_placement.py")
        return True
    else:
        print("\n❌ SYNTAX FIX FAILED")
        print("Manual intervention required")
        print("Check line 93 in src/trading_systems/exchanges/kraken/websocket_client.py")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
