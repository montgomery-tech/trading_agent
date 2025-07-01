#!/usr/bin/env python3
"""
Simple Environment Variable Test
"""

import os
import sys
from pathlib import Path

def check_environment():
    print("🔍 SIMPLE ENVIRONMENT CHECK")
    print("=" * 40)
    
    # Check current directory
    cwd = Path.cwd()
    print(f"📁 Current directory: {cwd}")
    
    # Check for env files
    env_example = Path("env_example.sh")
    env_file = Path(".env")
    
    print(f"📄 env_example.sh: {'✅' if env_example.exists() else '❌'}")
    print(f"📄 .env file: {'✅' if env_file.exists() else '❌'}")
    
    # Check environment variables
    print(f"\n🔑 Environment Variables:")
    
    vars_to_check = [
        'KRAKEN_API_KEY',
        'KRAKEN_API_SECRET', 
        'USE_SANDBOX',
        'ENVIRONMENT',
        'LOG_LEVEL'
    ]
    
    found_vars = 0
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            found_vars += 1
            if 'API' in var:
                # Hide sensitive values
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"   {var}: ✅ {display_value}")
            else:
                print(f"   {var}: ✅ {value}")
        else:
            print(f"   {var}: ❌ Not set")
    
    print(f"\n📊 Summary: {found_vars}/{len(vars_to_check)} variables found")
    
    if found_vars >= 2:  # At least API key and secret
        print("✅ Environment variables loaded successfully!")
        return True
    else:
        print("❌ Environment variables not loaded")
        return False

if __name__ == "__main__":
    check_environment()
