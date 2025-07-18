#!/usr/bin/env python3
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
    print(f"\n1️⃣ Getting spread for {TEST_SYMBOL}...")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/spreads/{TEST_SYMBOL}")
    
    if response.status_code == 200:
        spread_data = response.json()["data"]
        spread_pct = spread_data["spread_percentage"]
        print(f"   Current spread: {spread_pct * 100:.2f}%")
    else:
        print(f"   ❌ Failed to get spread: {response.status_code}")
        return
    
    # 2. Simulate a BUY trade
    print(f"\n2️⃣ Simulating BUY trade...")
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
    print(f"\n3️⃣ Simulating SELL trade...")
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
    print("\n\n🧪 Testing Spread Management")
    print("=" * 50)
    
    # Get all spreads
    print("\n1️⃣ Getting all trading pair spreads...")
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
    
    print("\n✅ Test complete!")
