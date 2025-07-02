#!/usr/bin/env python3
"""
Fix Typing Imports in WebSocket Client

Fix the missing Union import that's causing the NameError.
"""

import sys
from pathlib import Path


def fix_typing_imports():
    """Fix the missing typing imports in WebSocket client."""
    
    print("🔧 FIXING TYPING IMPORTS")
    print("=" * 50)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        with open(websocket_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ WebSocket client file not found: {websocket_path}")
        return False
    except Exception as e:
        print(f"❌ Error reading WebSocket client: {e}")
        return False
    
    # Check if Union is already imported
    if 'from typing import' in content and 'Union' in content:
        # Check if Union is in the existing typing import
        typing_import_start = content.find('from typing import')
        typing_import_end = content.find('\n', typing_import_start)
        typing_import_line = content[typing_import_start:typing_import_end]
        
        if 'Union' in typing_import_line:
            print("✅ Union already imported in typing import")
            return True
    
    print("🔧 Adding Union to typing imports...")
    
    # Find the existing typing import line
    if 'from typing import' in content:
        # Find the typing import line
        typing_start = content.find('from typing import')
        typing_end = content.find('\n', typing_start)
        typing_line = content[typing_start:typing_end]
        
        # Add Union to the existing import
        if 'Union' not in typing_line:
            # Replace the line to include Union
            imports = typing_line.replace('from typing import ', '').strip()
            if imports:
                new_typing_line = f"from typing import {imports}, Union"
            else:
                new_typing_line = "from typing import Union"
            
            new_content = content[:typing_start] + new_typing_line + content[typing_end:]
        else:
            print("✅ Union already in typing imports")
            return True
    else:
        # Add new typing import at the top with other imports
        # Find a good place to insert (after other imports)
        import_section_end = content.find('from ...utils.exceptions import')
        if import_section_end == -1:
            # Try to find after pathlib import or any other import
            import_section_end = content.find('import asyncio')
            if import_section_end == -1:
                import_section_end = content.find('import json')
        
        if import_section_end != -1:
            # Find the end of that import line
            line_end = content.find('\n', import_section_end)
            new_typing_import = '\nfrom typing import Any, AsyncGenerator, Dict, List, Optional, Set, Union'
            new_content = content[:line_end] + new_typing_import + content[line_end:]
        else:
            # Add at the very beginning
            new_typing_import = 'from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Union\n'
            new_content = new_typing_import + content
    
    # Also need to import Decimal if not already imported
    if 'from decimal import Decimal' not in new_content:
        print("🔧 Adding Decimal import...")
        # Add Decimal import near other imports
        typing_import_pos = new_content.find('from typing import')
        if typing_import_pos != -1:
            line_end = new_content.find('\n', typing_import_pos)
            decimal_import = '\nfrom decimal import Decimal'
            new_content = new_content[:line_end] + decimal_import + new_content[line_end:]
    
    try:
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Fixed typing imports in WebSocket client")
        return True
    except Exception as e:
        print(f"❌ Error writing WebSocket client: {e}")
        return False


def verify_imports():
    """Verify that imports are working correctly."""
    print("\n🧪 VERIFYING IMPORTS")
    print("=" * 50)
    
    try:
        # Test the import
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        
        print("✅ WebSocket client imports successfully")
        
        # Test that order methods exist
        client = KrakenWebSocketClient()
        
        if hasattr(client, 'place_market_order'):
            print("✅ place_market_order method exists")
        else:
            print("❌ place_market_order method missing")
            return False
        
        if hasattr(client, 'place_limit_order'):
            print("✅ place_limit_order method exists")
        else:
            print("❌ place_limit_order method missing")
            return False
        
        print("✅ All order placement methods present")
        return True
        
    except ImportError as e:
        print(f"❌ Import still failing: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 FIXING WEBSOCKET CLIENT TYPING IMPORTS")
    print("=" * 60)
    print("Fixing the Union import error...")
    print()
    
    success1 = fix_typing_imports()
    
    if success1:
        success2 = verify_imports()
        
        if success2:
            print("\n🎉 SUCCESS: Typing Imports Fixed!")
            print("=" * 60)
            print("✅ Union and Decimal imports added")
            print("✅ WebSocket client imports successfully")
            print("✅ Order placement methods available")
            print()
            print("🚀 Ready to test again:")
            print("python3 test_websocket_order_implementation.py")
            return True
        else:
            print("\n❌ Import verification failed")
            return False
    else:
        print("\n❌ Failed to fix typing imports")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
