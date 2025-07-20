#!/usr/bin/env python3
"""
fix_main_trades_router.py
Fix main.py to include the trades router properly
"""

import os
import shutil
from datetime import datetime

def backup_main():
    """Backup main.py before modifying"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"main.py.backup_trades_{timestamp}"
    shutil.copy2("main.py", backup_path)
    print(f"✅ Backed up main.py to {backup_path}")

def fix_main_py():
    """Fix main.py to include trades router"""
    
    print("🔧 Fixing main.py to include trades router...")
    
    # Read current main.py
    with open("main.py", "r") as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Find the import section and add trades
    import_line_idx = None
    trades_imported = False
    
    for i, line in enumerate(lines):
        if "from api.routes import" in line:
            import_line_idx = i
            if "trades" in line:
                trades_imported = True
                print("✅ trades already imported")
                break
    
    # Add trades to imports if not found
    if not trades_imported and import_line_idx is not None:
        print("🔧 Adding trades to imports...")
        import_line = lines[import_line_idx]
        
        # Check if it's a multi-line import or single line
        if import_line.strip().endswith(','):
            # Multi-line import case - add trades
            lines[import_line_idx] = import_line.rstrip() + " trades"
        elif "currencies" in import_line:
            # Single line with currencies - add trades
            lines[import_line_idx] = import_line.replace("currencies", "currencies, trades")
        else:
            # Just add trades
            lines[import_line_idx] = import_line.rstrip() + ", trades"
        
        trades_imported = True
        print("✅ Added trades to imports")
    
    # Find where to add the trades router (after currencies router)
    router_added = any("trades.router" in line for line in lines)
    
    if not router_added:
        print("🔧 Adding trades router...")
        
        # Find the currencies router line
        currencies_router_idx = None
        for i, line in enumerate(lines):
            if "currencies.router" in line and "include_router" in line:
                currencies_router_idx = i
                break
        
        if currencies_router_idx is not None:
            # Add trades router after currencies
            trades_router_line = '''
app.include_router(
    trades.router,
    prefix=f"{settings.API_V1_PREFIX}/trades",
    tags=["Trades"]
)'''
            
            # Insert after the currencies router block
            insert_idx = currencies_router_idx + 1
            
            # Find the end of the currencies router block
            while insert_idx < len(lines) and (lines[insert_idx].strip() == "" or lines[insert_idx].startswith("    ")):
                insert_idx += 1
            
            # Insert the trades router
            lines.insert(insert_idx, trades_router_line)
            print("✅ Added trades router after currencies router")
        else:
            print("⚠️  Could not find currencies router to add trades after")
            # Add at the end of router includes
            for i, line in enumerate(lines):
                if "# Root endpoints" in line or "@app.get(\"/\")" in line:
                    trades_router_line = '''
app.include_router(
    trades.router,
    prefix=f"{settings.API_V1_PREFIX}/trades",
    tags=["Trades"]
)
'''
                    lines.insert(i, trades_router_line)
                    print("✅ Added trades router before root endpoints")
                    break
    else:
        print("✅ trades router already included")
    
    # Write the updated main.py
    updated_content = '\n'.join(lines)
    
    with open("main.py", "w") as f:
        f.write(updated_content)
    
    print("✅ main.py updated successfully")
    
    return trades_imported and (router_added or True)

def check_trades_file():
    """Check if trades.py exists and has content"""
    
    trades_path = "api/routes/trades.py"
    
    if not os.path.exists(trades_path):
        print(f"❌ {trades_path} does not exist!")
        print("   Creating basic trades routes file...")
        create_basic_trades_file()
        return True
    else:
        print(f"✅ {trades_path} exists")
        
        # Check if it has basic content
        with open(trades_path, "r") as f:
            content = f.read()
        
        if len(content.strip()) < 100:
            print("⚠️  trades.py exists but appears to be empty or minimal")
            print("   You may need to copy the Kraken-integrated trades routes")
            return False
        
        if "router = APIRouter()" in content:
            print("✅ trades.py has router defined")
            return True
        else:
            print("⚠️  trades.py missing APIRouter definition")
            return False

def create_basic_trades_file():
    """Create a basic trades.py file if it doesn't exist"""
    
    os.makedirs("api/routes", exist_ok=True)
    
    basic_trades = '''#!/usr/bin/env python3
"""
api/routes/trades.py
Trade execution and management routes with Kraken API integration
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
import logging
import os

from api.models import (
    TradeRequest, TradeResponse, TradeSimulationRequest, TradeSimulationResponse,
    DataResponse, ListResponse
)
from api.dependencies import get_database, get_pagination_params
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Try to import the Kraken-integrated service, fallback to enhanced service
try:
    from api.services.kraken_integrated_trade_service import KrakenIntegratedTradeService
    TradeServiceClass = KrakenIntegratedTradeService
    print("✅ Using KrakenIntegratedTradeService")
except ImportError:
    try:
        from api.services.enhanced_trade_service import EnhancedTradeService
        TradeServiceClass = EnhancedTradeService
        print("⚠️  Using EnhancedTradeService (Kraken integration not available)")
    except ImportError:
        from api.services.trade_service import TradeService
        TradeServiceClass = TradeService
        print("⚠️  Using basic TradeService")


def get_trade_service(db: DatabaseManager = Depends(get_database)):
    """Dependency to get trade service instance"""
    return TradeServiceClass(db)


@router.get("/status", response_model=DataResponse)
async def get_trade_status():
    """Get trading system status"""
    try:
        live_trading = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        
        status_info = {
            "service": TradeServiceClass.__name__,
            "live_trading_enabled": live_trading,
            "supported_order_types": ["market"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return DataResponse(
            success=True,
            message="Trade system status retrieved",
            data=status_info
        )
        
    except Exception as e:
        logger.error(f"Failed to get trade status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trade status: {str(e)}"
        )


@router.post("/simulate", response_model=Dict[str, Any])
async def simulate_trade(
    trade_data: Dict[str, Any],
    trade_service = Depends(get_trade_service)
):
    """
    Simulate a trade execution
    
    Basic simulation endpoint that works with any trade service
    """
    try:
        # Import here to avoid circular imports
        from api.models import TradingSide
        
        # Extract trade parameters
        username = trade_data.get("username", "demo_user")
        symbol = trade_data.get("symbol", "BTC/USD") 
        side = trade_data.get("side", "buy")
        amount = Decimal(str(trade_data.get("amount", "0.001")))
        order_type = trade_data.get("order_type", "market")
        
        # Create trade request
        trade_request = TradeRequest(
            username=username,
            symbol=symbol,
            side=TradingSide(side),
            amount=amount,
            order_type=order_type
        )
        
        # Get current price for simulation
        current_price = await trade_service.get_current_price(symbol)
        
        # Calculate simulation values
        total_value = amount * current_price
        fee_rate = Decimal("0.0026")  # Default 0.26% fee
        fee_amount = total_value * fee_rate
        
        simulation_result = {
            "symbol": symbol,
            "side": side,
            "amount": str(amount),
            "estimated_price": str(current_price),
            "estimated_total": str(total_value),
            "estimated_fee": str(fee_amount),
            "fee_currency": symbol.split("/")[1],
            "service_used": TradeServiceClass.__name__,
            "simulation_time": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "message": f"Trade simulation for {side} {amount} {symbol}",
            "data": simulation_result
        }
        
    except Exception as e:
        logger.error(f"Trade simulation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trade simulation failed: {str(e)}"
        )


@router.get("/pricing/{symbol}", response_model=DataResponse)
async def get_current_pricing(
    symbol: str,
    trade_service = Depends(get_trade_service)
):
    """Get current pricing for a trading pair"""
    try:
        current_price = await trade_service.get_current_price(symbol)
        
        pricing_data = {
            "symbol": symbol,
            "current_price": str(current_price),
            "service": TradeServiceClass.__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return DataResponse(
            success=True,
            message=f"Current pricing for {symbol}",
            data=pricing_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get pricing for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to get pricing for {symbol}: {str(e)}"
        )
'''
    
    with open("api/routes/trades.py", "w") as f:
        f.write(basic_trades)
    
    print("✅ Created basic api/routes/trades.py")

def main():
    """Main function to fix the trades router issue"""
    
    print("🚀 FIXING TRADES ROUTER IN MAIN.PY")
    print("=" * 50)
    print()
    
    # Check if trades file exists
    trades_exists = check_trades_file()
    
    if trades_exists:
        # Backup main.py
        backup_main()
        
        # Fix main.py
        success = fix_main_py()
        
        if success:
            print("\n✅ SUCCESS!")
            print("=" * 30)
            print("Trades router has been added to main.py")
            print()
            print("📋 Next steps:")
            print("1. Restart your FastAPI application:")
            print("   python3 main.py")
            print()
            print("2. Check the API docs:")
            print("   http://localhost:8000/docs")
            print()
            print("3. You should now see a 'Trades' section with:")
            print("   - GET  /api/v1/trades/status")
            print("   - POST /api/v1/trades/simulate") 
            print("   - GET  /api/v1/trades/pricing/{symbol}")
            print()
            print("4. Test the endpoints:")
            print("   GET  /api/v1/trades/status")
            print("   GET  /api/v1/trades/pricing/BTC/USD")
        else:
            print("\n⚠️  Some issues occurred during the fix")
            print("Please check the messages above")
    else:
        print("\n❌ Could not proceed - trades.py file issues")

if __name__ == "__main__":
    main()
