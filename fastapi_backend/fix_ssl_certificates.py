#!/usr/bin/env python3
"""
fix_ssl_certificates.py
Fix SSL certificate issues on macOS for Kraken API access
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and report the result"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def install_certificates():
    """Install and update SSL certificates"""
    print("🔐 SSL CERTIFICATE INSTALLATION")
    print("=" * 50)
    print()
    
    # Install certifi
    success1 = run_command("pip3 install --upgrade certifi", "Installing certifi")
    
    # Install requests with security features
    success2 = run_command("pip3 install --upgrade 'requests[security]'", "Installing requests with security")
    
    # Try to find and run the Install Certificates command
    python_versions = ["3.9", "3.10", "3.11", "3.12", "3.13"]
    install_cert_found = False
    
    for version in python_versions:
        cert_path = f"/Applications/Python {version}/Install Certificates.command"
        if os.path.exists(cert_path):
            print(f"🔍 Found Python {version} certificate installer")
            success3 = run_command(f'"{cert_path}"', f"Running Install Certificates for Python {version}")
            if success3:
                install_cert_found = True
                break
    
    if not install_cert_found:
        print("⚠️  Python Install Certificates command not found")
        print("   This is normal if you installed Python via homebrew or pyenv")
    
    # Test the certificates
    print("\n🧪 Testing certificate installation...")
    test_command = '''python3 -c "import ssl, certifi; print('Certificate path:', certifi.where())"'''
    run_command(test_command, "Checking certificate path")
    
    return success1 and success2

def create_ssl_test():
    """Create a test script to verify SSL works"""
    test_script = '''#!/usr/bin/env python3
import ssl
import certifi
import urllib.request

def test_ssl():
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen('https://api.kraken.com/0/public/Time', context=context) as response:
            data = response.read()
            print("✅ SSL connection to Kraken API successful!")
            return True
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
        return False

if __name__ == "__main__":
    test_ssl()
'''
    
    with open("test_ssl_connection.py", "w") as f:
        f.write(test_script)
    
    os.chmod("test_ssl_connection.py", 0o755)
    print("✅ Created test_ssl_connection.py")

def main():
    print("🚀 SSL CERTIFICATE FIX FOR KRAKEN API")
    print("=" * 60)
    print()
    print("This script will fix SSL certificate issues on macOS")
    print("that prevent connection to the Kraken API.")
    print()
    
    proceed = input("Continue with SSL fix? (y/N): ")
    if proceed.lower() != 'y':
        print("SSL fix cancelled.")
        return
    
    # Install certificates
    success = install_certificates()
    
    # Create test script
    create_ssl_test()
    
    print("\n📋 NEXT STEPS:")
    print("=" * 30)
    
    if success:
        print("✅ SSL certificates installed successfully!")
        print()
        print("1. Test the SSL connection:")
        print("   python3 test_ssl_connection.py")
        print()
        print("2. If that works, test the Kraken connectivity:")
        print("   python3 ssl_fix_kraken_test.py")
        print()
        print("3. Then test your FastAPI application:")
        print("   python3 main.py")
    else:
        print("⚠️  Some certificate installation steps failed.")
        print()
        print("Try these manual steps:")
        print("1. pip3 install --upgrade certifi")
        print("2. Find your Python installation:")
        print("   ls /Applications/Python*")
        print("3. Run the Install Certificates command manually")
        print("4. Or use the relaxed SSL version of the Kraken client")

if __name__ == "__main__":
    main()
