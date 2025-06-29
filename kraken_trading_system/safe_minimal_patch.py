#!/usr/bin/env python3
"""
Safe Minimal Patch for Enhanced REST Client

This script safely adds ONLY the missing get_trade_history method
without touching any other functionality.

Save as: safe_minimal_patch.py
Run with: python3 safe_minimal_patch.py
"""

import sys
from pathlib import Path

def apply_safe_minimal_patch():
    """Safely add only the get_trade_history method."""
    
    print("🔧 SAFE MINIMAL PATCH - ENHANCED REST CLIENT")
    print("=" * 60)
    print("Adding only the missing get_trade_history method...")
    
    rest_client_path = Path("src/trading_systems/exchanges/kraken/rest_client.py")
    
    if not rest_client_path.exists():
        print("❌ Enhanced REST Client file not found")
        return False
    
    try:
        # Read current content
        with open(rest_client_path, 'r') as f:
            content = f.read()
        
        print(f"📊 Current file size: {len(content)} characters")
        
        # Check if method already exists
        if 'def get_trade_history(' in content:
            print("✅ get_trade_history method already exists")
            return True
        
        print("❌ get_trade_history method missing")
        print("🔧 Adding get_trade_history method safely...")
        
        # Find the get_closed_orders method as reference point
        closed_orders_start = content.find('async def get_closed_orders(')
        if closed_orders_start == -1:
            print("❌ Could not find get_closed_orders method for reference")
            return False
        
        # Find the end of get_closed_orders method
        # Look for the next method or end of class
        search_start = closed_orders_start + 100  # Start search after method definition
        next_method = content.find('\n    async def ', search_start)
        if next_method == -1:
            next_method = content.find('\n    def ', search_start)
        if next_method == -1:
            # Must be the last method, find class end or file end
            next_method = content.find('\n\n\n', search_start)
            if next_method == -1:
                next_method = len(content)
        
        # The get_trade_history method to insert
        trade_history_method = '''
    async def get_trade_history(self, **kwargs) -> Dict[str, Any]:
        """
        Get trade history.

        Args:
            **kwargs: Query parameters (type, trades, start, end, ofs)

        Returns:
            Trade history response from Kraken

        Raises:
            ExchangeError: If API call fails
        """
        try:
            response = await self._make_request_with_retry(
                "POST",
                "/0/private/TradesHistory",
                kwargs
            )

            return response

        except Exception as e:
            self.log_error("Failed to get trade history", error=e)
            raise
'''
        
        # Insert the method
        content = content[:next_method] + trade_history_method + content[next_method:]
        
        # Create a minimal backup
        backup_path = rest_client_path.with_suffix('.py.minimal_backup')
        with open(backup_path, 'w') as f:
            with open(rest_client_path, 'r') as original:
                f.write(original.read())
        print(f"💾 Minimal backup created: {backup_path}")
        
        # Write updated content
        with open(rest_client_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Successfully added get_trade_history method")
        print(f"📊 Updated file size: {len(content)} characters")
        
        # Verify the file is syntactically correct
        try:
            compile(content, str(rest_client_path), 'exec')
            print("✅ Syntax validation passed")
        except SyntaxError as e:
            print(f"❌ Syntax error detected: {e}")
            # Restore backup
            with open(backup_path, 'r') as f:
                original_content = f.read()
            with open(rest_client_path, 'w') as f:
                f.write(original_content)
            print("🔄 Restored from backup due to syntax error")
            return False
        
        return True
            
    except Exception as e:
        print(f"❌ Error applying patch: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main safe patching function."""
    print("🔧 Starting safe minimal patch for Enhanced REST Client...")
    
    success = apply_safe_minimal_patch()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SAFE PATCH COMPLETED SUCCESSFULLY!")
        print("✅ get_trade_history method added safely")
        print("✅ Syntax validation passed")
        print("\n📋 Next steps:")
        print("   1. Re-run: python3 test_enhanced_rest_client_full.py")
        print("   2. Should get 9/10 or 10/10 tests passing")
        print("   3. Proceed with Task 3.2.B implementation")
    else:
        print("❌ SAFE PATCH FAILED")
        print("⚠️ File remains unchanged")
    
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Patching interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

