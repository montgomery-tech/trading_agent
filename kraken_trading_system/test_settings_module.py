#!/usr/bin/env python3
"""
Test Python Settings Module

This tests if the settings module can read the .env file properly.
"""

import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_settings_module():
    print("🧪 TESTING PYTHON SETTINGS MODULE")
    print("=" * 50)
    
    try:
        from trading_systems.config.settings import settings
        print("✅ Settings module imported successfully")
        
        # Test if settings can read .env file
        print(f"\n📄 Settings configuration:")
        print(f"   Environment file: {settings.model_config.get('env_file', 'None')}")
        print(f"   Case sensitive: {settings.model_config.get('case_sensitive', 'Unknown')}")
        
        # Check credentials
        print(f"\n🔑 Credential Check:")
        has_creds = settings.has_api_credentials()
        print(f"   Has API credentials: {'✅ Yes' if has_creds else '❌ No'}")
        
        if has_creds:
            api_key, api_secret = settings.get_api_credentials()
            print(f"   API Key: {api_key[:8]}...{api_key[-4:]} ({len(api_key)} chars)")
            print(f"   API Secret: {api_secret[:8]}...{api_secret[-4:]} ({len(api_secret)} chars)")
            
            # Validate format
            is_valid = settings.validate_api_credentials()
            print(f"   Validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
            
            print(f"\n⚙️ Other Settings:")
            print(f"   Use sandbox: {settings.use_sandbox}")
            print(f"   Environment: {settings.environment}")
            print(f"   Log level: {settings.log_level}")
            
            print("\n🎉 SUCCESS! Settings module can read your API credentials!")
            return True
        else:
            print(f"\n❌ Settings module cannot read credentials")
            print(f"   Raw kraken_api_key: {'SET' if settings.kraken_api_key else 'NOT SET'}")
            print(f"   Raw kraken_api_secret: {'SET' if settings.kraken_api_secret else 'NOT SET'}")
            return False
            
    except Exception as e:
        print(f"❌ Settings module error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_settings_module()
    if success:
        print("\n✅ Ready to test live connectivity!")
    else:
        print("\n❌ Need to fix settings configuration first")
