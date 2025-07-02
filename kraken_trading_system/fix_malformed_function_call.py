#!/usr/bin/env python3
"""
Fix Malformed Function Call

Fix the specific malformed log_websocket_event call that's causing syntax errors.
"""

import sys
from pathlib import Path


def fix_malformed_call():
    """Fix the malformed function call."""
    
    print("🔧 FIXING MALFORMED FUNCTION CALL")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Find and fix the malformed log_websocket_event call
    print("🔍 Looking for malformed log_websocket_event call...")
    
    # The problematic pattern
    malformed_pattern = '''log_websocket_event(
                        self.logger,
                        "unknown_private_data",
                        channel=channel_name,
                        data_type=type(data).__name__,
                        data_preview=str(data)[:200] if isinstance(data, (dict, list)) else None
                    ).__name__,
        order_management_enabled=self._order_management_enabled
        )'''
    
    # Correct version
    correct_pattern = '''log_websocket_event(
                        self.logger,
                        "unknown_private_data",
                        channel=channel_name,
                        data_type=type(data).__name__,
                        data_preview=str(data)[:200] if isinstance(data, (dict, list)) else None
                    )'''
    
    if malformed_pattern in content:
        content = content.replace(malformed_pattern, correct_pattern)
        print("✅ Fixed malformed log_websocket_event call")
    else:
        # Try to find it with flexible whitespace
        print("Looking for pattern with flexible matching...")
        
        # Find the start of the problematic section
        start_marker = 'log_websocket_event('
        start_pos = content.find(start_marker)
        
        while start_pos != -1:
            # Find the matching closing parenthesis
            paren_count = 1
            pos = start_pos + len(start_marker)
            end_pos = -1
            
            while pos < len(content) and paren_count > 0:
                if content[pos] == '(':
                    paren_count += 1
                elif content[pos] == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        end_pos = pos
                        break
                pos += 1
            
            if end_pos != -1:
                # Extract the function call
                call_text = content[start_pos:end_pos + 1]
                
                # Check if this is the problematic call
                if '"unknown_private_data"' in call_text and ').__name__' in call_text:
                    print("🔍 Found problematic call")
                    
                    # Look for what comes after this call
                    after_call = content[end_pos + 1:end_pos + 200]
                    
                    if 'order_management_enabled' in after_call:
                        # This is definitely the malformed call
                        # Find where the actual end should be
                        actual_end = content.find(')', end_pos + 1)
                        if actual_end != -1:
                            # Replace the entire malformed section
                            malformed_section = content[start_pos:actual_end + 1]
                            
                            # Create the correct version
                            correct_call = '''log_websocket_event(
                        self.logger,
                        "unknown_private_data",
                        channel=channel_name,
                        data_type=type(data).__name__,
                        data_preview=str(data)[:200] if isinstance(data, (dict, list)) else None
                    )'''
                            
                            content = content.replace(malformed_section, correct_call)
                            print("✅ Fixed malformed function call")
                            break
            
            # Look for next occurrence
            start_pos = content.find(start_marker, start_pos + 1)
    
    # Also check for any orphaned order_management_enabled lines
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Remove any standalone order_management_enabled lines that don't belong
        if 'order_management_enabled=self._order_management_enabled' in line:
            # Check if this line is properly part of a function call
            if i > 0 and not lines[i-1].strip().endswith('(') and not lines[i-1].strip().endswith(','):
                print(f"✅ Removed orphaned line {i+1}: {line.strip()}")
                continue  # Skip this line
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Test the fix
    try:
        compile(content, str(websocket_path), 'exec')
        print("✅ Syntax is now correct")
        
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed file written")
        return True
        
    except SyntaxError as e:
        print(f"❌ Still has syntax error: {e.msg} on line {e.lineno}")
        print(f"   Text: {e.text}")
        return False
    
    except Exception as e:
        print(f"❌ Error testing syntax: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 FIXING MALFORMED FUNCTION CALL")
    print("=" * 60)
    print("Fixing the specific malformed log_websocket_event call...")
    print()
    
    success = fix_malformed_call()
    
    if success:
        print("\n🎉 SUCCESS: Malformed Call Fixed!")
        print("=" * 60)
        print("✅ Fixed the broken log_websocket_event call")
        print("✅ WebSocket client syntax is now valid")
        print()
        print("🚀 TEST AGAIN:")
        print("python3 live_order_placement.py")
        return True
    else:
        print("\n❌ MALFORMED CALL FIX FAILED")
        print("The issue may require manual editing")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
