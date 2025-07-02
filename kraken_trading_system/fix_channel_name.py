#!/usr/bin/env python3
"""
Fix channel_name NameError

Fix the missing channel_name variable in the WebSocket client.
"""

from pathlib import Path


def fix_channel_name_error():
    """Fix the channel_name NameError."""
    
    print("🔧 FIXING CHANNEL_NAME ERROR")
    print("=" * 40)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Find where channel_name is used but not defined
    if 'channel_name' in content:
        print("🔍 Found channel_name usage")
        
        # Look for the problematic log_websocket_event call
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'channel_name' in line and 'log_websocket_event' in line:
                print(f"   Found on line {i+1}: {line.strip()}")
                
                # Look at surrounding context
                start_context = max(0, i - 10)
                end_context = min(len(lines), i + 5)
                
                print("   Context:")
                for j in range(start_context, end_context):
                    marker = " >>> " if j == i else "     "
                    print(f"{marker}Line {j+1}: {lines[j].strip()}")
                
                # Find where channel_name should be defined
                # Look for the pattern where we extract channel_name from data
                found_definition = False
                for k in range(max(0, i - 20), i):
                    if 'channel_name =' in lines[k] or 'data[2]' in lines[k]:
                        print(f"   Found channel definition on line {k+1}: {lines[k].strip()}")
                        found_definition = True
                        break
                
                if not found_definition:
                    # Add the missing channel_name definition
                    print("   Adding missing channel_name definition...")
                    
                    # Find the start of the function/method this is in
                    method_start = i
                    while method_start > 0 and not lines[method_start].strip().startswith('def '):
                        method_start -= 1
                    
                    # Look for where we process data and should extract channel_name
                    insert_line = i - 5  # Insert a few lines before the log call
                    
                    # Add the channel_name extraction
                    channel_definition = "                channel_name = data[2] if isinstance(data, list) and len(data) > 2 else 'unknown'"
                    
                    lines.insert(insert_line, channel_definition)
                    print(f"   Inserted channel_name definition at line {insert_line + 1}")
                
                break
        
        # Alternative: if we can't fix it properly, just replace channel_name with a safe default
        if not found_definition:
            print("🔧 Applying fallback fix...")
            content = content.replace('channel=channel_name,', 'channel="unknown",')
            print("   Replaced channel_name with 'unknown'")
    
    else:
        print("✅ No channel_name usage found")
        return True
    
    # Write the fixed content
    if found_definition:
        content = '\n'.join(lines)
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed file written")
        
        # Test the syntax
        compile(content, str(websocket_path), 'exec')
        print("✅ Syntax is correct!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = fix_channel_name_error()
    if success:
        print("\n🎉 SUCCESS!")
        print("Run: python3 live_order_placement.py")
    else:
        print("\n❌ Fix failed")
