#!/usr/bin/env python3
"""
Add trades routes to main.py if they're missing
"""

import os

def add_trades_to_main():
    """Add trades router to main.py"""
    
    print("🔧 Adding trades routes to main.py...")
    
    # Read main.py
    with open("main.py", "r") as f:
        lines = f.readlines()
    
    # Check if trades is already imported
    trades_imported = False
    import_line_idx = None
    
    for i, line in enumerate(lines):
        if "from api.routes import" in line:
            import_line_idx = i
            if "trades" in line:
                trades_imported = True
                print("✅ trades already imported")
    
    # Add trades to imports if needed
    if not trades_imported and import_line_idx is not None:
        # Add trades to the import
        import_line = lines[import_line_idx].rstrip()
        if import_line.endswith(")"):
            # Multi-line import
            lines[import_line_idx] = import_line[:-1] + ", trades)\n"
        else:
            # Single line import
            lines[import_line_idx] = import_line + ", trades\n"
        print("✅ Added trades to imports")
    
    # Check if trades router is included
    trades_router_exists = any("trades.router" in line for line in lines)
    
    if not trades_router_exists:
        # Find where to add it (after other routers)
        insert_idx = None
        for i, line in enumerate(lines):
            if "app.include_router(currencies.router" in line:
                # Add after currencies router
                insert_idx = i + 1
                break
        
        if insert_idx:
            # Add trades router
            indent = "    " if lines[insert_idx-1].strip().startswith("app.") else ""
            new_router = f'\n{indent}app.include_router(trades.router, prefix="/api/v1/trades", tags=["trades"])\n'
            lines.insert(insert_idx, new_router)
            print("✅ Added trades router to main.py")
    else:
        print("✅ trades router already included")
    
    # Write back
    with open("main.py", "w") as f:
        f.writelines(lines)
    
    print("✅ main.py updated")

def check_trades_file():
    """Check if trades.py exists"""
    
    trades_file = "api/routes/trades.py"
    
    if not os.path.exists(trades_file):
        print(f"❌ {trades_file} not found!")
        print("\n💡 You need to create the trades routes file.")
        print("   The trades functionality might be in a different file")
        print("   or needs to be implemented.")
        return False
    
    print(f"✅ {trades_file} exists")
    
    # Check if it has simulate endpoint
    with open(trades_file, "r") as f:
        content = f.read()
    
    if "/simulate" in content:
        print("✅ Simulate endpoint found in trades.py")
    else:
        print("❌ Simulate endpoint NOT found in trades.py")
        print("   The EnhancedTradeService has simulate_trade method")
        print("   but the endpoint might not be implemented")
    
    return True

def create_minimal_trades_route():
    """Create a minimal trades route file if needed"""
    
    minimal_trades = '''#!/usr/bin/env python3
"""
Minimal trades routes for testing spread functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from decimal import Decimal

from api.models import DataResponse
from api.dependencies import get_database
from api.database import DatabaseManager
from api.services.enhanced_trade_service import EnhancedTradeService

router = APIRouter()


def get_trade_service(db: DatabaseManager = Depends(get_database)) -> EnhancedTradeService:
    """Get enhanced trade service instance"""
    return EnhancedTradeService(db)


@router.post("/simulate", response_model=DataResponse)
async def simulate_trade(
    trade_data: Dict[str, Any],
    trade_service: EnhancedTradeService = Depends(get_trade_service)
):
    """Simulate a trade with spread calculation"""
    try:
        # Create a basic trade request
        from api.models import TradeRequest, TradingSide
        
        trade_request = TradeRequest(
            username=trade_data.get("username", "demo_user"),
            symbol=trade_data.get("symbol", "BTC/USD"),
            side=TradingSide(trade_data.get("side", "buy")),
            amount=Decimal(str(trade_data.get("amount", "0.001"))),
            order_type=trade_data.get("order_type", "market")
        )
        
        # Simulate the trade
        result = await trade_service.simulate_trade(trade_request)
        
        return DataResponse(
            message="Trade simulation successful",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
'''
    
    with open("minimal_trades_routes.py", "w") as f:
        f.write(minimal_trades)
    
    print("✅ Created minimal_trades_routes.py")
    print("   You can copy this to api/routes/trades.py if needed")

if __name__ == "__main__":
    print("🚀 Adding Trades Routes")
    print("=" * 50)
    
    # Check if trades.py exists
    if check_trades_file():
        # Add to main.py
        add_trades_to_main()
        
        print("\n✅ Done! Restart FastAPI to load the trades routes")
    else:
        # Create minimal version
        create_minimal_trades_route()
        
        print("\n📋 Next steps:")
        print("1. Copy minimal_trades_routes.py to api/routes/trades.py")
        print("2. Run this script again to add it to main.py")
        print("3. Restart FastAPI")
        
    print("\nAfter restarting, check http://localhost:8000/docs")
    print("You should see a 'trades' section with the simulate endpoint")
