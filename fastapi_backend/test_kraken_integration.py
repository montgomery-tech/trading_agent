#!/usr/bin/env python3
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
            print("
✅ All tests passed! Kraken integration is working.")
        else:
            print("
⚠️  Trade service needs configuration.")
    else:
        print("
❌ Kraken connection failed. Check your setup.")

if __name__ == "__main__":
    asyncio.run(main())
