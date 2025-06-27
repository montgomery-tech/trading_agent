#!/usr/bin/env python3
"""
Debug script to check .env file loading and credentials
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def debug_env_loading():
    """Debug environment variable loading."""
    print("🔍 DEBUGGING ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    # Check current working directory
    print(f"Current working directory: {os.getcwd()}")
    
    # Check for .env file
    env_file = Path(".env")
    print(f".env file exists: {env_file.exists()}")
    
    if env_file.exists():
        print(f".env file path: {env_file.absolute()}")
        print(f".env file size: {env_file.stat().st_size} bytes")
        
        # Read .env file content (safely)
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()
            print(f".env file lines: {len(lines)}")
            
            # Check for API key lines (without showing actual values)
            has_api_key = any('KRAKEN_API_KEY' in line for line in lines)
            has_api_secret = any('KRAKEN_API_SECRET' in line for line in lines)
            
            print(f"Has KRAKEN_API_KEY line: {has_api_key}")
            print(f"Has KRAKEN_API_SECRET line: {has_api_secret}")
            
        except Exception as e:
            print(f"Error reading .env file: {e}")
    
    # Check environment variables directly
    print("\n🔑 Environment Variables:")
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    
    print(f"KRAKEN_API_KEY: {'SET' if api_key else 'NOT SET'}")
    print(f"KRAKEN_API_SECRET: {'SET' if api_secret else 'NOT SET'}")
    
    if api_key:
        print(f"API Key length: {len(api_key)}")
        print(f"API Key preview: {api_key[:10]}...")
    
    if api_secret:
        print(f"API Secret length: {len(api_secret)}")
        print(f"API Secret preview: {api_secret[:10]}...")
    
    # Test settings module
    print("\n⚙️ Testing Settings Module:")
    try:
        from trading_systems.config.settings import settings
        
        print(f"Settings module loaded: ✅")
        print(f"Has API credentials: {settings.has_api_credentials()}")
        
        if settings.has_api_credentials():
            api_key, api_secret = settings.get_api_credentials()
            print(f"Settings API Key: {api_key[:10] if api_key else 'None'}...")
            print(f"Settings API Secret length: {len(api_secret) if api_secret else 0}")
            print(f"Validate credentials: {settings.validate_api_credentials()}")
        
    except Exception as e:
        print(f"Settings module error: {e}")

if __name__ == "__main__":
    debug_env_loading()
