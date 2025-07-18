#!/usr/bin/env python3
"""
Fix the import errors in trades.py
"""

import os

def fix_trades_imports():
    """Fix the imports in trades.py"""
    
    trades_file = "api/routes/trades.py"
    
    print(f"🔧 Fixing imports in {trades_file}...")
    
    if not os.path.exists(trades_file):
        print(f"❌ {trades_file} not found!")
        return False
    
    # Read the file
    with open(trades_file, "r") as f:
        content = f.read()
    
    # Check what's being used
    issues = []
    if "EnhancedTradeResponse" in content and "from api.services.enhanced_trade_models import" not in content:
        issues.append("EnhancedTradeResponse not imported")
    if "EnhancedTradeSimulationResponse" in content and "from api.services.enhanced_trade_models import" not in content:
        issues.append("EnhancedTradeSimulationResponse not imported")
    
    print(f"Found {len(issues)} import issues")
    
    # Fix by replacing with standard models or adding imports
    if "EnhancedTradeResponse" in content:
        # Option 1: Replace with standard TradeResponse
        content = content.replace("response_model=EnhancedTradeResponse", "response_model=TradeResponse")
        content = content.replace("response_model=EnhancedTradeSimulationResponse", "response_model=TradeSimulationResponse")
        print("✅ Replaced Enhanced models with standard models")
    
    # Write back
    with open(trades_file, "w") as f:
        f.write(content)
    
    print("✅ Fixed imports in trades.py")
    return True

def check_current_imports():
    """Show current imports in trades.py"""
    
    trades_file = "api/routes/trades.py"
    
    print(f"\n📄 Current imports in {trades_file}:")
    print("-" * 50)
    
    if os.path.exists(trades_file):
        with open(trades_file, "r") as f:
            lines = f.readlines()
        
        # Show first 30 lines (imports section)
        for i, line in enumerate(lines[:30]):
            if line.strip():
                print(f"{i+1:3d}: {line.rstrip()}")
            if i > 5 and line.strip().startswith("@"):
                break

def create_working_trades_routes():
    """Create a working trades.py that properly uses the enhanced service"""
    
    working_trades = '''#!/usr/bin/env python3
"""
api/routes/trades.py
Trade execution and management routes with spread functionality
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from decimal import Decimal
import logging

from api.models import (
    TradeRequest, TradeResponse, TradeSimulationRequest, TradeSimulationResponse,
    DataResponse, ListResponse
)
from api.dependencies import get_database
from api.database import DatabaseManager
from api.services.enhanced_trade_service import EnhancedTradeService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_trade_service(db: DatabaseManager = Depends(get_database)) -> EnhancedTradeService:
    """Dependency to get enhanced trade service instance"""
    return EnhancedTradeService(db)


@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade_request: TradeRequest,
    trade_service: EnhancedTradeService = Depends(get_trade_service)
):
    """Execute a trade with spread calculation"""
    try:
        logger.info(f"Executing trade: {trade_request.side.value} {trade_request.amount} {trade_request.symbol}")
        trade_response = await trade_service.execute_trade(trade_request)
        return trade_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade execution failed: {str(e)}"
        )


@router.post("/simulate", response_model=TradeSimulationResponse)
async def simulate_trade(
    simulation_request: TradeSimulationRequest,
    trade_service: EnhancedTradeService = Depends(get_trade_service)
):
    """Simulate a trade with spread calculation"""
    try:
        logger.info(f"Simulating trade: {simulation_request.side.value} {simulation_request.amount} {simulation_request.symbol}")
        
        # Convert to TradeRequest
        trade_request = TradeRequest(
            username=simulation_request.username,
            symbol=simulation_request.symbol,
            side=simulation_request.side,
            amount=simulation_request.amount,
            price=simulation_request.price,
            order_type=simulation_request.order_type
        )
        
        # Simulate the trade
        simulation_result = await trade_service.simulate_trade(trade_request)
        
        # Convert to response model
        return TradeSimulationResponse(
            success=simulation_result['success'],
            message=simulation_result['message'],
            symbol=simulation_result.get('symbol'),
            side=simulation_result.get('side'),
            amount=simulation_result.get('amount'),
            estimated_price=simulation_result.get('estimated_price'),
            estimated_total=simulation_result.get('estimated_total'),
            estimated_fee=simulation_result.get('estimated_fee'),
            fee_currency=simulation_result.get('fee_currency'),
            current_balances=simulation_result.get('current_balances', {}),
            projected_balances=simulation_result.get('projected_balances', {}),
            validation_errors=simulation_result.get('validation_errors', []),
            warnings=simulation_result.get('warnings', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade simulation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade simulation failed: {str(e)}"
        )


@router.get("/", response_model=ListResponse)
async def list_trades(
    username: Optional[str] = None,
    symbol: Optional[str] = None,
    db: DatabaseManager = Depends(get_database)
):
    """List trades with optional filters"""
    try:
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if username:
            query += " AND user_id = (SELECT id FROM users WHERE username = %s)"
            params.append(username)
        
        if symbol:
            query += " AND trading_pair_id = (SELECT id FROM trading_pairs WHERE symbol = %s)"
            params.append(symbol.upper())
        
        query += " ORDER BY created_at DESC LIMIT 100"
        
        results = db.execute_query(query, params if params else None)
        
        return ListResponse(
            message=f"Retrieved {len(results)} trades",
            data=results
        )
        
    except Exception as e:
        logger.error(f"Error listing trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing trades: {str(e)}"
        )
'''
    
    with open("working_trades_routes.py", "w") as f:
        f.write(working_trades)
    
    print("✅ Created working_trades_routes.py")

if __name__ == "__main__":
    print("🚀 Fixing Trades Route Imports")
    print("=" * 50)
    
    # Show current state
    check_current_imports()
    
    # Try to fix
    if fix_trades_imports():
        print("\n✅ Imports fixed!")
        print("Try restarting FastAPI again")
    else:
        # Create working version
        create_working_trades_routes()
        
        print("\n💡 Alternative solution:")
        print("1. Replace trades.py with the working version:")
        print("   cp working_trades_routes.py api/routes/trades.py")
        print("2. Restart FastAPI: python3 main.py")
        
    print("\nThe issue was that trades.py was trying to use")
    print("EnhancedTradeResponse which doesn't exist in imports")
