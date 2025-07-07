#!/usr/bin/env python3
"""
Test script for Trading Pairs API endpoints
"""

import requests
import json
from decimal import Decimal

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def test_trading_pairs_endpoints():
    """Test all trading pairs endpoints"""

    print("🧪 Testing Trading Pairs API Endpoints")
    print("=" * 50)

    # Test 1: Get all trading pairs
    print("\n1. Testing GET /trading-pairs")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Retrieved {len(data.get('data', []))} trading pairs")

            # Show first trading pair if available
            if data.get('data'):
                first_pair = data['data'][0]
                print(f"   Sample pair: {first_pair.get('symbol', 'N/A')}")
                print(f"   Base: {first_pair.get('base_currency', {}).get('code', 'N/A')}")
                print(f"   Quote: {first_pair.get('quote_currency', {}).get('code', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Get specific trading pair
    print("\n2. Testing GET /trading-pairs/BTC/USD")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/BTC/USD")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Retrieved trading pair details")
            pair_data = data.get('data', {})
            print(f"   Symbol: {pair_data.get('symbol', 'N/A')}")
            print(f"   Min amount: {pair_data.get('min_trade_amount', 'N/A')}")
            print(f"   Max amount: {pair_data.get('max_trade_amount', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Validate trading pair
    print("\n3. Testing GET /trading-pairs/BTC/USD/validate")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/BTC/USD/validate?amount=0.001")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Validation completed")
            validation_data = data.get('data', {})
            print(f"   Is valid: {validation_data.get('is_valid', 'N/A')}")
            print(f"   Errors: {validation_data.get('errors', [])}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Test filtering by currency
    print("\n4. Testing GET /trading-pairs?base_currency=BTC")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs?base_currency=BTC")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Retrieved {len(data.get('data', []))} BTC pairs")

            for pair in data.get('data', [])[:3]:  # Show first 3
                print(f"   - {pair.get('symbol', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 5: Test non-existent pair
    print("\n5. Testing GET /trading-pairs/INVALID/PAIR")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/INVALID/PAIR")
        print(f"Status: {response.status_code}")

        if response.status_code == 404:
            print(f"✅ Success: Correctly returned 404 for non-existent pair")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 6: Test symbol endpoint (alternative)
    print("\n6. Testing GET /trading-pairs/by-symbol/BTC%2FUSD")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs/by-symbol/BTC%2FUSD")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Retrieved trading pair via symbol endpoint")
            pair_data = data.get('data', {})
            print(f"   Symbol: {pair_data.get('symbol', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("   - All trading pairs endpoints tested")
    print("   - Check the results above for any failures")
    print("   - Make sure the API server is running on localhost:8000")
    print("   - Two ways to access specific pairs:")
    print("     * /trading-pairs/BTC/USD (separate path parameters)")
    print("     * /trading-pairs/by-symbol/BTC%2FUSD (URL-encoded symbol)")
    print("=" * 50)


def test_api_health():
    """Test API health endpoint first"""
    print("🏥 Testing API Health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API is healthy and running")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure the API server is running on localhost:8000")
        return False


if __name__ == "__main__":
    print("🚀 Starting Trading Pairs API Tests")
    print("=" * 50)

    # First check if API is running
    if test_api_health():
        test_trading_pairs_endpoints()
    else:
        print("\n❌ Cannot proceed with tests - API is not accessible")
        print("   Please start the API server first:")
        print("   python main.py")
