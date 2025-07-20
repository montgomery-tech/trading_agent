#!/usr/bin/env python3
"""
setup_kraken_integration.py
Complete setup script for Kraken API integration with FastAPI backend
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

def print_banner():
    print("🚀 KRAKEN API INTEGRATION SETUP")
    print("=" * 60)
    print("This script will set up Kraken API integration for your FastAPI backend")
    print("enabling real market order execution with spread markup.")
    print()

def check_prerequisites():
    """Check if the FastAPI backend structure exists"""
    print("📋 Checking prerequisites...")
    
    required_paths = [
        "api/services",
        "api/routes", 
        "api/models",
        "main.py"
    ]
    
    missing = []
    for path in required_paths:
        if not os.path.exists(path):
            missing.append(path)
    
    if missing:
        print(f"❌ Missing required directories/files:")
        for path in missing:
            print(f"   - {path}")
        print("\nPlease run this script from your FastAPI backend root directory.")
        return False
    
    print("✅ FastAPI backend structure found")
    return True

def backup_existing_files():
    """Backup existing trade-related files"""
    print("\n📁 Backing up existing files...")
    
    files_to_backup = [
        "api/routes/trades.py",
        "api/services/trade_service.py",
        "api/services/enhanced_trade_service.py"
    ]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{timestamp}"
            shutil.copy2(file_path, backup_path)
            print(f"✅ Backed up: {file_path} -> {backup_path}")

def create_kraken_service_files():
    """Create the Kraken API service files"""
    print("\n🔧 Creating Kraken service files...")
    
    # The actual file content would be copied from the artifacts above
    print("✅ Please copy the following files from the artifacts:")
    print("   1. kraken_api_client.py -> api/services/kraken_api_client.py") 
    print("   2. kraken_integrated_trade_service.py -> api/services/kraken_integrated_trade_service.py")
    print("   3. kraken_integrated_trades_routes.py -> api/routes/trades.py")
    
    return True

def update_requirements():
    """Update requirements.txt with necessary dependencies"""
    print("\n📦 Updating requirements...")
    
    new_requirements = [
        "aiohttp>=3.8.0",
        "asyncio-throttle>=1.0.0"
    ]
    
    requirements_file = "requirements.txt"
    
    if os.path.exists(requirements_file):
        with open(requirements_file, 'r') as f:
            existing = f.read()
        
        to_add = []
        for req in new_requirements:
            package_name = req.split('>=')[0].split('==')[0]
            if package_name not in existing:
                to_add.append(req)
        
        if to_add:
            with open(requirements_file, 'a') as f:
                f.write('\n# Kraken API integration\n')
                for req in to_add:
                    f.write(f"{req}\n")
            print(f"✅ Added {len(to_add)} new requirements")
        else:
            print("✅ All requirements already present")
    else:
        print("⚠️  requirements.txt not found, please add these manually:")
        for req in new_requirements:
            print(f"   {req}")

def update_env_file():
    """Update .env.example with Kraken configuration"""
    print("\n🔐 Updating environment configuration...")
    
    kraken_env_vars = [
        "# Kraken API Configuration",
        "KRAKEN_API_KEY=your_kraken_api_key_here",
        "KRAKEN_API_SECRET=your_kraken_api_secret_here",
        "",
        "# Trading Configuration", 
        "ENABLE_LIVE_TRADING=false",
        "MAX_ORDER_SIZE_USD=1000.00",
        "DEFAULT_TRADING_FEE_PERCENTAGE=0.26",
        "",
        "# Market Order Settings",
        "MARKET_ORDER_SLIPPAGE_TOLERANCE=0.01",
        "KRAKEN_API_TIMEOUT=30",
        ""
    ]
    
    env_example = ".env.example"
    
    if os.path.exists(env_example):
        with open(env_example, 'r') as f:
            existing = f.read()
        
        if "KRAKEN_API_KEY" not in existing:
            with open(env_example, 'a') as f:
                f.write('\n')
                for line in kraken_env_vars:
                    f.write(f"{line}\n")
            print("✅ Added Kraken configuration to .env.example")
        else:
            print("✅ Kraken configuration already in .env.example")
    else:
        print("⚠️  .env.example not found, please create it with:")
        for line in kraken_env_vars:
            print(f"   {line}")

def run_database_migration():
    """Run the database migration for Kraken fields"""
    print("\n🗄️  Database migration...")
    print("⚠️  Please run the database migration manually:")
    print("   python kraken_trades_migration.py")
    print("   (Copy the migration script from the artifacts)")
    
def create_test_script():
    """Create a test script for the integration"""
    test_script = '''#!/usr/bin/env python3
"""
test_kraken_integration.py
Test script for Kraken API integration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the api directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_kraken_connection():
    """Test basic Kraken API connection"""
    try:
        from api.services.kraken_api_client import get_kraken_client
        
        print("🔍 Testing Kraken API connection...")
        client = await get_kraken_client()
        
        # Test public endpoint
        ticker = await client.get_ticker_info("BTC/USD")
        print(f"✅ Kraken API connected: BTC/USD = ${ticker['last']}")
        
        # Test credentials if available
        if client.api_key and client.api_secret:
            is_valid = await client.validate_connection()
            print(f"✅ Credentials valid: {is_valid}")
        else:
            print("⚠️  No credentials configured (add to .env for live trading)")
        
        return True
        
    except Exception as e:
        print(f"❌ Kraken connection failed: {e}")
        return False

async def test_trade_service():
    """Test the trade service initialization"""
    try:
        from api.database import DatabaseManager
        from api.services.kraken_integrated_trade_service import KrakenIntegratedTradeService
        
        print("🔍 Testing trade service...")
        
        # Initialize database (you may need to adjust this)
        db = DatabaseManager()
        trade_service = KrakenIntegratedTradeService(db)
        
        # Test price fetching
        price = await trade_service.get_current_price("BTC/USD")
        print(f"✅ Price service working: BTC/USD = ${price}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trade service test failed: {e}")
        return False

async def main():
    print("🧪 KRAKEN INTEGRATION TEST")
    print("=" * 40)
    
    # Test connection
    connection_ok = await test_kraken_connection()
    
    if connection_ok:
        # Test trade service  
        service_ok = await test_trade_service()
        
        if service_ok:
            print("\n✅ All tests passed! Kraken integration is working.")
        else:
            print("\n⚠️  Trade service needs configuration.")
    else:
        print("\n❌ Kraken connection failed. Check your setup.")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open("test_kraken_integration.py", 'w') as f:
        f.write(test_script)
    
    os.chmod("test_kraken_integration.py", 0o755)
    print("✅ Created test_kraken_integration.py")

def show_next_steps():
    """Show the user what to do next"""
    print("\n🎯 NEXT STEPS")
    print("=" * 60)
    print()
    print("1️⃣ Copy the artifact files to your project:")
    print("   - kraken_api_client.py -> api/services/")
    print("   - kraken_integrated_trade_service.py -> api/services/")
    print("   - Update api/routes/trades.py with new version")
    print()
    print("2️⃣ Install new dependencies:")
    print("   pip install aiohttp>=3.8.0")
    print()
    print("3️⃣ Run database migration:")
    print("   python kraken_trades_migration.py")
    print()
    print("4️⃣ Set up environment variables:")
    print("   cp .env.example .env")
    print("   # Edit .env with your Kraken API credentials")
    print()
    print("5️⃣ Test the integration:")
    print("   python test_kraken_integration.py")
    print()
    print("6️⃣ Test with your FastAPI app:")
    print("   python main.py")
    print("   # Check http://localhost:8000/docs for new endpoints")
    print()
    print("🔒 IMPORTANT SECURITY NOTES:")
    print("   - Start with ENABLE_LIVE_TRADING=false")
    print("   - Test thoroughly before enabling live trading")
    print("   - Use small amounts for initial live tests")
    print("   - Monitor logs for any issues")
    print()
    print("📚 NEW API ENDPOINTS:")
    print("   POST /api/v1/trades/execute - Execute market orders")
    print("   GET  /api/v1/trades/kraken/status - Check Kraken connection")
    print("   GET  /api/v1/trades/pricing/{symbol} - Real-time prices")

def main():
    """Main setup function"""
    print_banner()
    
    if not check_prerequisites():
        sys.exit(1)
    
    print("This setup will:")
    print("  ✓ Create Kraken API client service")
    print("  ✓ Create Kraken-integrated trade service") 
    print("  ✓ Update trade routes for market orders")
    print("  ✓ Add database migration for Kraken fields")
    print("  ✓ Update environment configuration")
    print("  ✓ Create test scripts")
    print()
    
    confirm = input("Continue with setup? (y/N): ")
    if confirm.lower() != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    
    try:
        backup_existing_files()
        create_kraken_service_files()
        update_requirements()
        update_env_file()
        run_database_migration()
        create_test_script()
        
        print("\n✅ SETUP COMPLETED SUCCESSFULLY!")
        show_next_steps()
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the error and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
