#!/usr/bin/env python3
"""
Config Import Fix
Fixes the missing Field import in config.py
"""

import os
from pathlib import Path

def fix_config_imports():
    """Fix missing Field import in config.py"""
    print("🔧 Fixing imports in api/config.py...")
    
    config_file = Path('api/config.py')
    if not config_file.exists():
        print("❌ api/config.py not found")
        return False
    
    # Read current config
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Check if Field is already imported
    if 'from pydantic import Field' in content or 'Field' in content.split('\n')[0:10]:
        print("   ✅ Field import already exists")
    else:
        # Add Field import
        lines = content.split('\n')
        new_lines = []
        added_import = False
        
        for line in lines:
            if 'from pydantic import' in line and not added_import:
                # Add Field to existing pydantic import
                if 'Field' not in line:
                    line = line.rstrip().rstrip(')') + ', Field'
                    if not line.endswith(')'):
                        line += ')'
                added_import = True
            elif 'import pydantic' in line and not added_import:
                # Add separate Field import after pydantic import
                new_lines.append(line)
                new_lines.append('from pydantic import Field')
                added_import = True
                continue
            
            new_lines.append(line)
        
        if not added_import:
            # Add at the beginning with other imports
            import_line = 'from pydantic import Field'
            # Find where to insert
            for i, line in enumerate(new_lines):
                if line.startswith('from ') or line.startswith('import '):
                    continue
                else:
                    new_lines.insert(i, import_line)
                    break
        
        # Write updated config
        with open(config_file, 'w') as f:
            f.write('\n'.join(new_lines))
        
        print("   ✅ Added Field import to config.py")
    
    return True

def simplify_redis_settings():
    """Simplify Redis settings to not use Field() for now"""
    print("\n🔧 Simplifying Redis settings...")
    
    config_file = Path('api/config.py')
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Replace Field() definitions with simple defaults
    replacements = [
        ('RATE_LIMIT_REDIS_URL: Optional[str] = Field(\n        default="redis://localhost:6379/1",\n        env="RATE_LIMIT_REDIS_URL"\n    )',
         'RATE_LIMIT_REDIS_URL: Optional[str] = "redis://localhost:6379/1"'),
        
        ('RATE_LIMIT_FALLBACK_TO_MEMORY: bool = Field(\n        default=True,\n        env="RATE_LIMIT_FALLBACK_TO_MEMORY"\n    )',
         'RATE_LIMIT_FALLBACK_TO_MEMORY: bool = True'),
        
        ('RATE_LIMIT_AUTH_REQUESTS: int = Field(\n        default=10,\n        env="RATE_LIMIT_AUTH_REQUESTS"\n    )',
         'RATE_LIMIT_AUTH_REQUESTS: int = 10'),
        
        ('RATE_LIMIT_TRADING_REQUESTS: int = Field(\n        default=100,\n        env="RATE_LIMIT_TRADING_REQUESTS"\n    )',
         'RATE_LIMIT_TRADING_REQUESTS: int = 100'),
        
        ('RATE_LIMIT_INFO_REQUESTS: int = Field(\n        default=200,\n        env="RATE_LIMIT_INFO_REQUESTS"\n    )',
         'RATE_LIMIT_INFO_REQUESTS: int = 200'),
        
        ('RATE_LIMIT_ADMIN_REQUESTS: int = Field(\n        default=5,\n        env="RATE_LIMIT_ADMIN_REQUESTS"\n    )',
         'RATE_LIMIT_ADMIN_REQUESTS: int = 5'),
        
        ('RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(\n        default=60,\n        env="RATE_LIMIT_REQUESTS_PER_MINUTE"\n    )',
         'RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60'),
    ]
    
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
    
    if modified:
        with open(config_file, 'w') as f:
            f.write(content)
        print("   ✅ Simplified Redis settings")
    else:
        print("   ℹ️ Redis settings already simplified or not found")
    
    return True

def add_env_loading():
    """Add explicit environment variable loading for Redis settings"""
    print("\n🔧 Adding environment variable loading...")
    
    config_file = Path('api/config.py')
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Look for the _load_settings method and add Redis env loading
    if 'def _load_settings(self):' in content:
        # Add Redis env loading to existing method
        redis_env_loading = '''
        # Load Redis settings from environment
        self.RATE_LIMIT_REDIS_URL = os.getenv('RATE_LIMIT_REDIS_URL', 'redis://localhost:6379/1')
        self.RATE_LIMIT_FALLBACK_TO_MEMORY = os.getenv('RATE_LIMIT_FALLBACK_TO_MEMORY', 'true').lower() == 'true'
        self.RATE_LIMIT_AUTH_REQUESTS = int(os.getenv('RATE_LIMIT_AUTH_REQUESTS', '10'))
        self.RATE_LIMIT_TRADING_REQUESTS = int(os.getenv('RATE_LIMIT_TRADING_REQUESTS', '100'))
        self.RATE_LIMIT_INFO_REQUESTS = int(os.getenv('RATE_LIMIT_INFO_REQUESTS', '200'))
        self.RATE_LIMIT_ADMIN_REQUESTS = int(os.getenv('RATE_LIMIT_ADMIN_REQUESTS', '5'))
        self.RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))'''
        
        # Find the end of _load_settings method and add Redis loading
        lines = content.split('\n')
        new_lines = []
        in_load_settings = False
        added_redis_loading = False
        
        for line in lines:
            new_lines.append(line)
            
            if 'def _load_settings(self):' in line:
                in_load_settings = True
            elif in_load_settings and line.strip() == '' and not added_redis_loading:
                # Add Redis loading at the end of the method
                new_lines.extend(redis_env_loading.split('\n'))
                added_redis_loading = True
        
        if added_redis_loading:
            with open(config_file, 'w') as f:
                f.write('\n'.join(new_lines))
            print("   ✅ Added Redis environment variable loading")
        else:
            print("   ⚠️ Could not add Redis environment loading")
    
    return True

def test_config():
    """Test that config loads without errors"""
    print("\n🧪 Testing config loading...")
    
    try:
        import sys
        if 'api.config' in sys.modules:
            del sys.modules['api.config']
        
        from api.config import settings
        
        print(f"   ✅ Config loaded successfully")
        print(f"   RATE_LIMIT_REDIS_URL: {getattr(settings, 'RATE_LIMIT_REDIS_URL', 'NOT_FOUND')}")
        print(f"   RATE_LIMIT_FALLBACK_TO_MEMORY: {getattr(settings, 'RATE_LIMIT_FALLBACK_TO_MEMORY', 'NOT_FOUND')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Config loading failed: {e}")
        return False

def main():
    """Main fix function"""
    print("🔧 Config Import Fix")
    print("=" * 25)
    
    # Fix imports
    fix_config_imports()
    
    # Simplify Redis settings
    simplify_redis_settings()
    
    # Add environment variable loading
    add_env_loading()
    
    # Test config
    config_ok = test_config()
    
    if config_ok:
        print("\n✅ Config fix completed successfully!")
        print("\n🚀 Next Steps:")
        print("   1. Try starting FastAPI again: python3 main.py")
        print("   2. Run Redis diagnostic: python3 redis_rate_limiting_fix.py")
    else:
        print("\n❌ Config fix failed")
        print("   Check api/config.py for syntax errors")
    
    return config_ok

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
