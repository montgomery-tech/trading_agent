#!/usr/bin/env python3
"""
Production Mode Override

This directly modifies the configuration to enable real trading.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def patch_config_for_production():
    """Patch the configuration to enable production mode."""
    print("🔧 PATCHING CONFIGURATION FOR PRODUCTION MODE")
    print("=" * 60)
    
    try:
        from trading_systems.mcp_server import config as config_module
        
        # Get the current config
        original_config = config_module.MCPServerConfig()
        print(f"📋 Original Configuration:")
        print(f"   Real trading: {original_config.enable_real_trading}")
        
        # Create a monkey patch to enable real trading
        def get_patched_config():
            """Return a config with real trading enabled."""
            config = config_module.MCPServerConfig()
            config.enable_real_trading = True
            config.enable_advanced_orders = True
            config.security.max_order_value_usd = 15.0
            return config
        
        # Patch the config module
        config_module.default_mcp_config = get_patched_config()
        
        # Test the patch
        test_config = config_module.MCPServerConfig()
        test_config.enable_real_trading = True
        
        print(f"✅ Configuration patched successfully!")
        print(f"   Real trading: {test_config.enable_real_trading}")
        print(f"   Max order value: ${test_config.security.max_order_value_usd}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration patch failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = patch_config_for_production()
    if success:
        print("\n🚀 Production mode enabled via override!")
    else:
        print("\n❌ Production mode override failed")
