#!/usr/bin/env python3
"""
Simple Config Patch for Redis Settings
Directly patches the config.py file to add missing Redis settings
"""

import os
from pathlib import Path

def patch_config_file():
    """Patch the config.py file to add Redis settings"""
    print("🔧 Patching api/config.py for Redis settings...")

    config_file = Path('api/config.py')
    if not config_file.exists():
        print("❌ api/config.py not found")
        return False

    # Read current config
    with open(config_file, 'r') as f:
        content = f.read()

    # Check if already patched
    if 'RATE_LIMIT_REDIS_URL' in content:
        print("   ✅ Config file already contains Redis settings")
        return True

    # Backup original
    backup_file = config_file.with_suffix('.py.backup')
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"   ✅ Backed up config to {backup_file}")

    # Find where to add Redis settings (after existing rate limit settings)
    lines = content.split('\n')
    new_lines = []
    added = False

    for i, line in enumerate(lines):
        new_lines.append(line)

        # Look for the end of the class definition to add Redis settings
        if 'RATE_LIMIT_ENABLED' in line and not added:
            # Add Redis settings after this line
            redis_patch = '''
    # Redis Rate Limiting Settings
    RATE_LIMIT_REDIS_URL: Optional[str] = Field(
        default="redis://localhost:6379/1",
        env="RATE_LIMIT_REDIS_URL"
    )
    RATE_LIMIT_FALLBACK_TO_MEMORY: bool = Field(
        default=True,
        env="RATE_LIMIT_FALLBACK_TO_MEMORY"
    )
    RATE_LIMIT_AUTH_REQUESTS: int = Field(
        default=10,
        env="RATE_LIMIT_AUTH_REQUESTS"
    )
    RATE_LIMIT_TRADING_REQUESTS: int = Field(
        default=100,
        env="RATE_LIMIT_TRADING_REQUESTS"
    )
    RATE_LIMIT_INFO_REQUESTS: int = Field(
        default=200,
        env="RATE_LIMIT_INFO_REQUESTS"
    )
    RATE_LIMIT_ADMIN_REQUESTS: int = Field(
        default=5,
        env="RATE_LIMIT_ADMIN_REQUESTS"
    )
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60,
        env="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )'''
            new_lines.append(redis_patch)
            added = True

    if not added:
        print("❌ Could not find appropriate place to add Redis settings")
        return False

    # Write patched config
    with open(config_file, 'w') as f:
        f.write('\n'.join(new_lines))

    print("   ✅ Patched config.py with Redis settings")
    return True

def verify_patch():
    """Verify the patch worked"""
    print("\n🔍 Verifying patch...")

    try:
        # Force reload of config module
        import sys
        if 'api.config' in sys.modules:
            del sys.modules['api.config']

        from api.config import settings

        # Test the new settings
        redis_url = getattr(settings, 'RATE_LIMIT_REDIS_URL', 'NOT_FOUND')
        fallback = getattr(settings, 'RATE_LIMIT_FALLBACK_TO_MEMORY', 'NOT_FOUND')

        print(f"   RATE_LIMIT_REDIS_URL: {redis_url}")
        print(f"   RATE_LIMIT_FALLBACK_TO_MEMORY: {fallback}")

        if redis_url != 'NOT_FOUND' and fallback != 'NOT_FOUND':
            print("   ✅ Redis settings are now available")
            return True
        else:
            print("   ❌ Redis settings still not available")
            return False

    except Exception as e:
        print(f"   ❌ Error verifying patch: {e}")
        return False

def main():
    """Main patch function"""
    print("🔧 Simple Config Patch for Redis Settings")
    print("=" * 45)

    # Patch the config file
    patch_ok = patch_config_file()
    if not patch_ok:
        return False

    # Verify the patch
    verify_ok = verify_patch()
    if not verify_ok:
        print("\n❌ Patch verification failed")
        return False

    print("\n✅ Config patch completed successfully!")
    print("\n🚀 Next Steps:")
    print("   1. Restart any running FastAPI application")
    print("   2. Run: python3 redis_rate_limiting_fix.py")
    print("   3. Redis settings should now load from .env")

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
