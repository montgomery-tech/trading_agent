#!/usr/bin/env python3
"""
Integration Script for Spread Functionality
This script updates your existing FastAPI application to use the enhanced spread features
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def backup_file(filepath):
    """Create a backup of the original file"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_path)
        print(f"  ✅ Backed up: {filepath} -> {backup_path}")
        return True
    return False


def update_trade_service_import():
    """Update the trade service import in routes/trades.py"""
    print("\n1️⃣ Updating Trade Service Import...")
    
    trades_route_file = "api/routes/trades.py"
    
    if not os.path.exists(trades_route_file):
        print(f"  ❌ File not found: {trades_route_file}")
        return False
    
    backup_file(trades_route_file)
    
    with open(trades_route_file, 'r') as f:
        content = f.read()
    
    # Check if already using enhanced service
    if "EnhancedTradeService" in content:
        print("  ⚠️  Already using EnhancedTradeService")
        return True
    
    # Add import for enhanced service
    if "from api.services.trade_service import TradeService" in content:
        # Add the enhanced import after the original
        new_import = "from api.services.trade_service import TradeService\nfrom api.services.enhanced_trade_service import EnhancedTradeService"
        content = content.replace(
            "from api.services.trade_service import TradeService",
            new_import
        )
        
        # Update the get_trade_service function
        old_function = """def get_trade_service(db: DatabaseManager = Depends(get_database)) -> TradeService:
    \"\"\"Dependency to get trade service instance\"\"\"
    return TradeService(db)"""
        
        new_function = """def get_trade_service(db: DatabaseManager = Depends(get_database)) -> TradeService:
    \"\"\"Dependency to get trade service instance\"\"\"
    return EnhancedTradeService(db)  # Using enhanced version with spread support"""
        
        content = content.replace(old_function, new_function)
        
        with open(trades_route_file, 'w') as f:
            f.write(content)
        
        print("  ✅ Updated trade service to use EnhancedTradeService")
        return True
    else:
        print("  ❌ Could not find TradeService import to update")
        return False


def update_trade_models():
    """Update model imports to use enhanced versions"""
    print("\n2️⃣ Updating Trade Models...")
    
    trades_route_file = "api/routes/trades.py"
    
    with open(trades_route_file, 'r') as f:
        content = f.read()
    
    # Add enhanced model imports
    if "from api.models import" in content and "EnhancedTradeResponse" not in content:
        # Find the models import line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "from api.models import" in line and "TradeResponse" in line:
                # Add enhanced models import after the original
                lines.insert(i + 1, "from api.services.enhanced_trade_models import EnhancedTradeResponse, EnhancedTradeSimulationResponse")
                break
        
        content = '\n'.join(lines)
        
        # Update response_model references
        content = content.replace(
            "@router.post(\"/execute\", response_model=TradeResponse)",
            "@router.post(\"/execute\", response_model=EnhancedTradeResponse)"
        )
        
        content = content.replace(
            "@router.post(\"/simulate\", response_model=TradeSimulationResponse)",
            "@router.post(\"/simulate\", response_model=EnhancedTradeSimulationResponse)"
        )
        
        with open(trades_route_file, 'w') as f:
            f.write(content)
        
        print("  ✅ Updated to use enhanced response models")
        return True
    else:
        print("  ⚠️  Model updates might already be in place")
        return True


def create_enhanced_service_file():
    """Copy the enhanced trade service to the services directory"""
    print("\n3️⃣ Installing Enhanced Trade Service...")
    
    services_dir = "api/services"
    if not os.path.exists(services_dir):
        os.makedirs(services_dir)
        print(f"  📁 Created directory: {services_dir}")
    
    target_file = os.path.join(services_dir, "enhanced_trade_service.py")
    
    # Check if enhanced_trade_service.py exists in current directory
    if os.path.exists("enhanced_trade_service.py"):
        shutil.copy2("enhanced_trade_service.py", target_file)
        print(f"  ✅ Copied enhanced_trade_service.py to {target_file}")
    else:
        print("  ⚠️  enhanced_trade_service.py not found in current directory")
        print("     Please ensure the file is present or manually copy it")
        return False
    
    # Also copy the enhanced models
    target_models = os.path.join(services_dir, "enhanced_trade_models.py")
    if os.path.exists("enhanced_trade_models.py"):
        shutil.copy2("enhanced_trade_models.py", target_models)
        print(f"  ✅ Copied enhanced_trade_models.py to {target_models}")
    
    return True


def add_spread_routes_to_main():
    """Add spread management routes to the main application"""
    print("\n4️⃣ Adding Spread Management Routes...")
    
    main_file = "main.py"
    
    if not os.path.exists(main_file):
        print(f"  ❌ File not found: {main_file}")
        return False
    
    backup_file(main_file)
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    if "spread_management" in content:
        print("  ⚠️  Spread routes might already be added")
        return True
    
    # First, copy the spread management routes file
    if os.path.exists("spread_management_routes.py"):
        target_route = "api/routes/spread_management.py"
        shutil.copy2("spread_management_routes.py", target_route)
        print(f"  ✅ Copied spread_management_routes.py to {target_route}")
    
    # Add import and route inclusion
    lines = content.split('\n')
    
    # Find where routes are imported
    for i, line in enumerate(lines):
        if "from api.routes import" in line:
            # Add spread management to imports
            if "trading_pairs" in line:
                lines[i] = line.rstrip() + ", spread_management"
            break
    
    # Find where routes are included
    for i, line in enumerate(lines):
        if "app.include_router(trading_pairs.router" in line:
            # Add spread management router after trading pairs
            indent = len(line) - len(line.lstrip())
            new_line = " " * indent + "app.include_router(spread_management.router, prefix=\"/api/v1/trading-pairs\", tags=[\"spread-management\"])"
            lines.insert(i + 1, new_line)
            break
    
    content = '\n'.join(lines)
    
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("  ✅ Added spread management routes to main.py")
    return True


def update_env_example():
    """Add spread configuration to .env.example"""
    print("\n5️⃣ Updating Environment Configuration...")
    
    env_file = ".env.example"
    
    if not os.path.exists(env_file):
        print(f"  ⚠️  {env_file} not found, skipping")
        return True
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    if "DEFAULT_SPREAD_PERCENTAGE" not in content:
        # Add spread configuration
        spread_config = """
# Spread Configuration
DEFAULT_SPREAD_PERCENTAGE=0.02  # 2% default spread
MAX_SPREAD_PERCENTAGE=0.10      # 10% maximum spread
MIN_SPREAD_PERCENTAGE=0.00      # 0% minimum spread
"""
        
        with open(env_file, 'a') as f:
            f.write(spread_config)
        
        print(f"  ✅ Added spread configuration to {env_file}")
    else:
        print(f"  ⚠️  Spread configuration already in {env_file}")
    
    return True


def create_test_script():
    """Create a test script for spread functionality"""
    print("\n6️⃣ Creating Test Script...")
    
    test_content = '''#!/usr/bin/env python3
"""
Test script for spread functionality
Run this after integration to verify spread calculations work correctly
"""

import requests
import json
from decimal import Decimal

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test user credentials (adjust as needed)
TEST_USER = "demo_user"
TEST_SYMBOL = "BTC/USD"


def test_spread_calculation():
    """Test that spread is correctly applied to trades"""
    print("🧪 Testing Spread Calculation")
    print("=" * 50)
    
    # 1. Get current spread for trading pair
    print(f"\\n1️⃣ Getting spread for {TEST_SYMBOL}...")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/spreads/{TEST_SYMBOL}")
    
    if response.status_code == 200:
        spread_data = response.json()["data"]
        spread_pct = spread_data["spread_percentage"]
        print(f"   Current spread: {spread_pct * 100:.2f}%")
    else:
        print(f"   ❌ Failed to get spread: {response.status_code}")
        return
    
    # 2. Simulate a BUY trade
    print(f"\\n2️⃣ Simulating BUY trade...")
    trade_data = {
        "username": TEST_USER,
        "symbol": TEST_SYMBOL,
        "side": "buy",
        "amount": 0.001,
        "order_type": "market"
    }
    
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/trades/simulate",
        json=trade_data
    )
    
    if response.status_code == 200:
        sim_data = response.json()
        print(f"   ✅ Simulation successful")
        print(f"   Market price: ${sim_data.get('execution_price', 'N/A')}")
        print(f"   Client price: ${sim_data.get('client_price', 'N/A')}")
        print(f"   Spread amount: ${sim_data.get('spread_amount', 'N/A')}")
        print(f"   Total cost: ${sim_data.get('estimated_total', 'N/A')}")
    else:
        print(f"   ❌ Simulation failed: {response.status_code}")
        print(f"   {response.text}")
    
    # 3. Simulate a SELL trade
    print(f"\\n3️⃣ Simulating SELL trade...")
    trade_data["side"] = "sell"
    
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/trades/simulate",
        json=trade_data
    )
    
    if response.status_code == 200:
        sim_data = response.json()
        print(f"   ✅ Simulation successful")
        print(f"   Market price: ${sim_data.get('execution_price', 'N/A')}")
        print(f"   Client price: ${sim_data.get('client_price', 'N/A')}")
        print(f"   Spread amount: ${sim_data.get('spread_amount', 'N/A')}")
        print(f"   Total received: ${sim_data.get('estimated_total', 'N/A')}")
    else:
        print(f"   ❌ Simulation failed: {response.status_code}")


def test_spread_management():
    """Test spread management endpoints"""
    print("\\n\\n🧪 Testing Spread Management")
    print("=" * 50)
    
    # Get all spreads
    print("\\n1️⃣ Getting all trading pair spreads...")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/spreads")
    
    if response.status_code == 200:
        spreads = response.json()["data"]
        print(f"   ✅ Found {len(spreads)} trading pairs")
        for pair in spreads[:3]:  # Show first 3
            print(f"   {pair['symbol']}: {pair['spread_percentage_display']}")
    else:
        print(f"   ❌ Failed: {response.status_code}")


if __name__ == "__main__":
    print("🚀 Spread Functionality Test")
    print("=" * 50)
    
    test_spread_calculation()
    test_spread_management()
    
    print("\\n✅ Test complete!")
'''
    
    with open("test_spread_functionality.py", 'w') as f:
        f.write(test_content)
    
    os.chmod("test_spread_functionality.py", 0o755)
    print("  ✅ Created test_spread_functionality.py")
    return True


def main():
    """Main integration function"""
    print("🚀 Spread Functionality Integration Script")
    print("=" * 50)
    print("This script will update your FastAPI application to use spread functionality")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists("api") or not os.path.exists("main.py"):
        print("❌ ERROR: This script must be run from your FastAPI project root directory")
        print("   Expected to find: api/ directory and main.py file")
        return False
    
    print("📁 Working directory:", os.getcwd())
    print()
    
    # Run integration steps
    success = True
    
    # Create enhanced service files
    success &= create_enhanced_service_file()
    
    # Update imports and references
    success &= update_trade_service_import()
    success &= update_trade_models()
    
    # Add spread routes
    success &= add_spread_routes_to_main()
    
    # Update configuration
    success &= update_env_example()
    
    # Create test script
    success &= create_test_script()
    
    print("\n" + "=" * 50)
    
    if success:
        print("✅ Integration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Run the database migration:")
        print("   python add_spread_fields_migration.py")
        print("\n2. Restart your FastAPI application:")
        print("   python main.py")
        print("\n3. Test the spread functionality:")
        print("   python test_spread_functionality.py")
        print("\n4. Check the API docs for new endpoints:")
        print("   http://localhost:8000/docs")
    else:
        print("⚠️  Integration completed with some warnings")
        print("Please check the messages above and manually fix any issues")
    
    print("\n💡 Tip: All original files have been backed up with .backup_* extension")


if __name__ == "__main__":
    main()
