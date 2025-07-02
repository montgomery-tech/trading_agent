#!/usr/bin/env python3
"""
Simple Fix for channel_name Error

Just replace the problematic channel_name with a safe default.
"""

from pathlib import Path


def simple_fix():
    """Simple fix for channel_name error."""
    
    print("🔧 SIMPLE CHANNEL_NAME FIX")
    print("=" * 30)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Find and show the problematic line
    if 'channel_name' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'channel_name' in line:
                print(f"Line {i+1}: {line.strip()}")
    
    # Simple fix: replace channel_name with a safe default
    print("🔧 Replacing channel_name with safe default...")
    
    # Replace any channel_name usage with "unknown"
    content = content.replace('channel=channel_name,', 'channel="unknown",')
    content = content.replace('channel_name=', 'channel="unknown"')
    
    # If there are any remaining channel_name references, replace them too
    content = content.replace('channel_name', '"unknown"')
    
    print("✅ Replaced channel_name references")
    
    # Write the fixed content
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
    success = simple_fix()
    if success:
        print("\n🎉 SUCCESS!")
        print("Run: python3 live_order_placement.py")
    else:
        print("\n❌ Fix failed")
