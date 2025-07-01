#!/usr/bin/env python3
"""
Debug Account Balance Structure

Let's see what's actually in your account snapshot and find your balances.
"""

import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def debug_account_structure():
    """Debug the account snapshot structure to find balances."""
    print("🔍 DEBUGGING ACCOUNT BALANCE STRUCTURE")
    print("=" * 60)
    
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        
        client = KrakenWebSocketClient()
        await client.connect_private()
        
        if not client.is_private_connected:
            print("❌ Could not connect")
            return
        
        print("✅ Connected to live account")
        
        # Get account snapshot
        snapshot = await client.get_account_snapshot()
        
        if snapshot:
            print("\n📊 ACCOUNT SNAPSHOT ANALYSIS")
            print("-" * 40)
            
            print(f"Snapshot type: {type(snapshot)}")
            print(f"Snapshot attributes: {dir(snapshot)}")
            
            # Try different ways to access balances
            print(f"\n🔍 Exploring balance data...")
            
            # Method 1: Check if it has balances attribute
            if hasattr(snapshot, 'balances'):
                balances = snapshot.balances
                print(f"✅ Found balances attribute: {type(balances)}")
                
                if isinstance(balances, dict):
                    print(f"📊 Balance keys: {list(balances.keys())}")
                    for currency, amount in balances.items():
                        if float(amount) > 0:
                            print(f"   {currency}: {amount}")
                else:
                    print(f"📊 Balances attributes: {dir(balances)}")
            
            # Method 2: Check if it has account_data
            if hasattr(snapshot, 'account_data'):
                account_data = snapshot.account_data
                print(f"✅ Found account_data: {type(account_data)}")
                print(f"📊 Account data attributes: {dir(account_data)}")
            
            # Method 3: Check all attributes for balance-like data
            print(f"\n🔍 All snapshot attributes:")
            for attr in dir(snapshot):
                if not attr.startswith('_'):
                    try:
                        value = getattr(snapshot, attr)
                        if not callable(value):
                            print(f"   {attr}: {type(value)} = {str(value)[:100]}")
                    except:
                        print(f"   {attr}: <could not access>")
            
            # Method 4: Try to convert to dict or JSON
            print(f"\n🔍 Trying to serialize snapshot...")
            try:
                if hasattr(snapshot, '__dict__'):
                    snapshot_dict = snapshot.__dict__
                    print(f"📊 Snapshot dict keys: {list(snapshot_dict.keys())}")
                    
                    # Look for balance-related keys
                    for key, value in snapshot_dict.items():
                        if 'balance' in key.lower() or 'amount' in key.lower():
                            print(f"   Balance-related: {key} = {value}")
            except Exception as e:
                print(f"⚠️ Serialization failed: {e}")
        
        else:
            print("❌ No account snapshot available")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_account_structure())
