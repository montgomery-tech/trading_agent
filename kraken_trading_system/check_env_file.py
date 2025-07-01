#!/usr/bin/env python3
"""
Check for Hidden .env File and API Credentials

This script will help locate and check the .env file and API credentials
that might be hidden in your system.
"""

import os
import sys
from pathlib import Path

def check_hidden_env_file():
    """Check for hidden .env file and API credentials."""
    print("🔍 CHECKING FOR HIDDEN .ENV FILE AND API CREDENTIALS")
    print("=" * 70)
    
    # Get current directory
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check for .env file (including hidden)
    env_file = current_dir / ".env"
    print(f"\n📄 Checking for .env file at: {env_file}")
    
    if env_file.exists():
        print("✅ .env file found!")
        print(f"📄 File size: {env_file.stat().st_size} bytes")
        print(f"📄 File permissions: {oct(env_file.stat().st_mode)[-3:]}")
        
        # Try to read the file safely
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            print(f"📄 Number of lines: {len(lines)}")
            
            # Check for API key lines without revealing actual values
            has_api_key = any('KRAKEN_API_KEY' in line and '=' in line for line in lines)
            has_api_secret = any('KRAKEN_API_SECRET' in line and '=' in line for line in lines)
            
            print(f"🔑 Contains KRAKEN_API_KEY: {'✅ Yes' if has_api_key else '❌ No'}")
            print(f"🔑 Contains KRAKEN_API_SECRET: {'✅ Yes' if has_api_secret else '❌ No'}")
            
            # Show structure without revealing values
            print("\n📋 .env file structure (values hidden):")
            for i, line in enumerate(lines, 1):
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key = line.split('=')[0]
                        print(f"   Line {i}: {key}=***HIDDEN***")
                    else:
                        print(f"   Line {i}: {line}")
                elif line.strip():
                    print(f"   Line {i}: {line}")  # Comments are ok to show
                    
        except PermissionError:
            print("❌ Permission denied reading .env file")
        except Exception as e:
            print(f"❌ Error reading .env file: {e}")
    else:
        print("❌ .env file not found")
    
    # Check for other possible env files
    print(f"\n🔍 Checking for other environment files...")
    env_files_to_check = [
        ".env.local",
        ".env.development", 
        ".env.production",
        "env_example.sh",
        ".environment",
        "config.env"
    ]
    
    for env_filename in env_files_to_check:
        env_path = current_dir / env_filename
        if env_path.exists():
            print(f"✅ Found: {env_filename}")
        else:
            print(f"❌ Not found: {env_filename}")
    
    # Check environment variables directly
    print(f"\n🔍 Checking current environment variables...")
    api_key = os.getenv('KRAKEN_API_KEY')
    api_secret = os.getenv('KRAKEN_API_SECRET')
    use_sandbox = os.getenv('USE_SANDBOX')
    
    print(f"🔑 KRAKEN_API_KEY in environment: {'✅ Set' if api_key else '❌ Not set'}")
    print(f"🔑 KRAKEN_API_SECRET in environment: {'✅ Set' if api_secret else '❌ Not set'}")
    print(f"⚙️ USE_SANDBOX in environment: {'✅ Set' if use_sandbox else '❌ Not set'}")
    
    if api_key:
        print(f"🔑 API Key length: {len(api_key)} characters")
        print(f"🔑 API Key preview: {api_key[:8]}...{api_key[-4:]}")
    
    if api_secret:
        print(f"🔑 Secret length: {len(api_secret)} characters")
        print(f"🔑 Secret preview: {api_secret[:8]}...{api_secret[-4:]}")

def list_all_files():
    """List all files including hidden ones."""
    print(f"\n📂 ALL FILES IN CURRENT DIRECTORY (including hidden):")
    print("-" * 50)
    
    try:
        current_dir = Path.cwd()
        all_files = sorted(current_dir.iterdir())
        
        for item in all_files:
            if item.is_file():
                size = item.stat().st_size
                hidden = "🙈" if item.name.startswith('.') else "📄"
                print(f"{hidden} {item.name} ({size} bytes)")
            elif item.is_dir():
                hidden = "🙈" if item.name.startswith('.') else "📁"
                print(f"{hidden} {item.name}/ (directory)")
                
    except Exception as e:
        print(f"❌ Error listing files: {e}")

def show_env_setup_instructions():
    """Show instructions for setting up .env file."""
    print(f"\n💡 HOW TO SET UP .ENV FILE:")
    print("=" * 50)
    print("If you need to create or edit your .env file:")
    print()
    print("1. Create .env file:")
    print("   touch .env")
    print()
    print("2. Edit with your preferred editor:")
    print("   nano .env")
    print("   # or")
    print("   code .env")
    print("   # or") 
    print("   vim .env")
    print()
    print("3. Add your Kraken API credentials:")
    print("   KRAKEN_API_KEY=your_api_key_here")
    print("   KRAKEN_API_SECRET=your_api_secret_here")
    print("   USE_SANDBOX=false")
    print()
    print("4. Check the file was created:")
    print("   ls -la | grep .env")
    print()
    print("5. Verify contents (safely):")
    print("   python3 check_env_file.py")

if __name__ == "__main__":
    check_hidden_env_file()
    list_all_files()
    show_env_setup_instructions()
