#!/usr/bin/env python3
"""
Direct Fix for WebSocket Syntax Error

Simple, direct fix for the syntax error on line 93.
"""

from pathlib import Path


def direct_fix():
    """Apply direct fix to the syntax error."""
    
    print("🔧 DIRECT SYNTAX FIX")
    print("=" * 30)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    print(f"📋 Total lines: {len(lines)}")
    
    # Look at lines around line 93
    for i in range(88, min(98, len(lines))):
        line_num = i + 1
        line = lines[i].rstrip()
        marker = " >>> " if line_num == 93 else "     "
        print(f"{marker}Line {line_num}: {repr(line)}")
    
    # Direct fix: remove the problematic lines and fix the structure
    print("\n🔧 Applying direct fix...")
    
    # Find the problematic section and fix it
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip the problematic lines around 93
        if i >= 92 and i <= 95:  # Lines 93-96
            if 'order_management_enabled=' in line:
                print(f"   Skipping problematic line {i+1}: {line.strip()}")
                i += 1
                continue
            elif line.strip() == ')':
                # Check if this is an orphaned closing parenthesis
                if i >= 93:
                    print(f"   Skipping orphaned closing paren on line {i+1}")
                    i += 1
                    continue
        
        fixed_lines.append(line)
        i += 1
    
    # Write the fixed content
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print("✅ Fixed file written")
        
        # Test the syntax
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        compile(content, str(websocket_path), 'exec')
        print("✅ Syntax is now correct!")
        return True
        
    except SyntaxError as e:
        print(f"❌ Still has syntax error: {e.msg} on line {e.lineno}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = direct_fix()
    if success:
        print("\n🎉 SUCCESS!")
        print("Run: python3 live_order_placement.py")
    else:
        print("\n❌ Manual fix needed")
