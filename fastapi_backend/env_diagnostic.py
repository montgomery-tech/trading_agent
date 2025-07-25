#!/usr/bin/env python3
"""
quick_env_fix.py
Quick fix script to resolve environment variable loading issues
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def backup_file(file_path):
    """Create a backup of a file"""
    if Path(file_path).exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backed up: {file_path} -> {backup_path}")
        return backup_path
    return None

def fix_main_py():
    """Add environment loading to main.py"""
    print("\n🔧 FIXING MAIN.PY - ADDING ENVIRONMENT LOADING")
    print("-" * 50)
    
    main_py = Path("main.py")
    if not main_py.exists():
        print("❌ main.py not found")
        return False
    
    # Backup first
    backup_file("main.py")
    
    # Read current content
    with open(main_py, 'r') as f:
        content = f.read()
    
    # Check if already has dotenv loading
    if 'load_dotenv' in content:
        print("ℹ️  main.py already has dotenv loading")
        return True
    
    # Add dotenv loading at the top
    dotenv_import = """#!/usr/bin/env python3
# Load environment variables before anything else
from dotenv import load_dotenv
load_dotenv()

"""
    
    # Remove existing shebang if present
    if content.startswith('#!/usr/bin/env python3'):
        lines = content.split('\n')
        content = '\n'.join(lines[1:])
    
    # Add the new header
    new_content = dotenv_import + content
    
    # Write back
    with open(main_py, 'w') as f:
        f.write(new_content)
    
    print("✅ Added environment loading to main.py")
    return True

def check_env_file_format():
    """Check and fix .env file format"""
    print("\n📄 CHECKING .ENV FILE FORMAT")
    print("-" * 50)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("💡 Creating a template .env file...")
        
        template_content = """# Kraken API Configuration
KRAKEN_API_KEY=your_kraken_api_key_here
KRAKEN_API_SECRET=your_kraken_api_secret_here

# Trading Configuration
ENABLE_LIVE_TRADING=false

# FastAPI Configuration
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your_secret_key_here

# Database
DATABASE_URL=sqlite:///trades.db
"""
        
        with open(env_file, 'w') as f:
            f.write(template_content)
        
        print("✅ Created template .env file")
        print("🔑 IMPORTANT: Update the Kraken API credentials in .env file!")
        return False
    
    # Read and analyze .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    print(f"📊 .env file has {len(lines)} lines")
    
    # Check for Kraken variables
    kraken_vars = []
    issues = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if 'KRAKEN_API' in line:
            kraken_vars.append(line)
            
            # Check format
            if '=' not in line:
                issues.append(f"Line {i}: Missing = sign")
            elif ' = ' in line:
                issues.append(f"Line {i}: Spaces around = sign (should be no spaces)")
            elif line.endswith('='):
                issues.append(f"Line {i}: Empty value")
    
    print(f"🔑 Found {len(kraken_vars)} Kraken API variables:")
    for var in kraken_vars:
        var_name = var.split('=')[0] if '=' in var else var
        print(f"   - {var_name}")
    
    if issues:
        print(f"⚠️  Found {len(issues)} formatting issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ .env file format looks good")
        return True

def test_loading():
    """Test if environment loading works"""
    print("\n🧪 TESTING ENVIRONMENT LOADING")
    print("-" * 50)
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv available")
        
        # Load .env file
        result = load_dotenv('.env', verbose=True)
        print(f"📄 Load result: {'✅ Success' if result else '❌ Failed'}")
        
        # Check critical variables
        api_key = os.getenv('KRAKEN_API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET')
        live_trading = os.getenv('ENABLE_LIVE_TRADING')
        
        print("\n🔍 Environment Variables Check:")
        print(f"   KRAKEN_API_KEY: {'✅ SET' if api_key else '❌ NOT SET'}")
        print(f"   KRAKEN_API_SECRET: {'✅ SET' if api_secret else '❌ NOT SET'}")
        print(f"   ENABLE_LIVE_TRADING: {live_trading or '❌ NOT SET'}")
        
        if api_key and api_secret:
            print(f"\n🎉 SUCCESS! Credentials are now loaded:")
            print(f"   API Key length: {len(api_key)}")
            print(f"   API Secret length: {len(api_secret)}")
            return True
        else:
            print(f"\n❌ Credentials still not loaded")
            return False
            
    except ImportError:
        print("❌ python-dotenv not installed")
        print("💡 Install with: pip install python-dotenv")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 CHECKING DEPENDENCIES")
    print("-" * 50)
    
    try:
        import dotenv
        print("✅ python-dotenv already installed")
    except ImportError:
        print("❌ python-dotenv not installed")
        print("💡 Installing python-dotenv...")
        os.system("pip install python-dotenv")

def main():
    print("🚀 QUICK ENVIRONMENT FIX")
    print("=" * 50)
    print("This script will fix common environment variable loading issues")
    print()
    
    # Step 1: Install dependencies
    install_dependencies()
    
    # Step 2: Check .env file format
    env_ok = check_env_file_format()
    
    # Step 3: Fix main.py
    main_ok = fix_main_py()
    
    # Step 4: Test loading
    if env_ok and main_ok:
        loading_ok = test_loading()
    else:
        loading_ok = False
    
    # Summary and next steps
    print("\n" + "=" * 50)
    print("🏁 SUMMARY")
    print("=" * 50)
    
    if loading_ok:
        print("🎉 SUCCESS! Environment variables should now load properly.")
        print("\n📋 Next steps:")
        print("1. Restart your FastAPI application: python main.py")
        print("2. Test the trading endpoint again")
        print("3. Check that ENABLE_LIVE_TRADING is set to 'true' for live trading")
    else:
        print("⚠️  Some issues remain. Manual fixes needed:")
        print("\n📋 Manual steps:")
        print("1. Edit your .env file and add your real Kraken API credentials")
        print("2. Make sure there are no spaces around the = signs")
        print("3. Set ENABLE_LIVE_TRADING=true for live trading")
        print("4. Restart your FastAPI application")
    
    print(f"\n💡 If issues persist, run: python env_diagnostic.py")

if __name__ == "__main__":
    main()
