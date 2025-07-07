#!/usr/bin/env python3
"""
Comprehensive test script for Trades API endpoints
Compatible with Python versions before 3.6 (no f-strings)
"""

import requests
import json
from decimal import Decimal
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def test_api_health():
    """Test API health endpoint first"""
    print("Testing API Health...")
    try:
        response = requests.get(BASE_URL + "/health")
        if response.status_code == 200:
            print("SUCCESS: API is healthy and running")
            return True
        else:
            print("ERROR: API health check failed: " + str(response.status_code))
            return False
    except Exception as e:
        print("ERROR: Cannot connect to API: " + str(e))
        print("   Make sure the API server is running on localhost:8000")
        return False


def test_trade_simulation():
    """Test trade simulation endpoint"""
    print("\nTesting Trade Simulation")
    print("=" * 50)

    # Test 1: Simulate ETH buy
    print("\n1. Testing POST /trades/simulate - ETH Buy")
    try:
        simulation_data = {
            "username": "agent_1",
            "symbol": "ETH/USD",
            "side": "buy",
            "amount": 0.01,
            "order_type": "market"
        }

        response = requests.post(
            BASE_URL + API_PREFIX + "/trades/simulate",
            json=simulation_data,
            headers={"Content-Type": "application/json"}
        )

        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Trade simulation completed")
            print("   Estimated price: $" + str(data.get('estimated_price', 'N/A')))
            print("   Estimated total: $" + str(data.get('estimated_total', 'N/A')))
            print("   Estimated fee: $" + str(data.get('estimated_fee', 'N/A')))
            print("   Validation errors: " + str(len(data.get('validation_errors', []))))

            if data.get('validation_errors'):
                print("   Errors: " + str(data['validation_errors']))
        else:
            print("ERROR: " + str(response.status_code) + " - " + response.text)

    except Exception as e:
        print("ERROR: " + str(e))

    # Test 2: Simulate ETH sell
    print("\n2. Testing POST /trades/simulate - ETH Sell")
    try:
        simulation_data = {
            "username": "agent_1",
            "symbol": "ETH/USD",
            "side": "sell",
            "amount": 0.01,
            "order_type": "market"
        }

        response = requests.post(
            BASE_URL + API_PREFIX + "/trades/simulate",
            json=simulation_data,
            headers={"Content-Type": "application/json"}
        )

        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Trade simulation completed")
            print("   Estimated price: $" + str(data.get('estimated_price', 'N/A')))
            print("   Estimated total: $" + str(data.get('estimated_total', 'N/A')))
            print("   Estimated fee: $" + str(data.get('estimated_fee', 'N/A')))
            print("   Validation errors: " + str(len(data.get('validation_errors', []))))

            if data.get('validation_errors'):
                print("   Errors: " + str(data['validation_errors']))
        else:
            print("ERROR: " + str(response.status_code) + " - " + response.text)

    except Exception as e:
        print("ERROR: " + str(e))


def test_trade_execution():
    """Test trade execution endpoint"""
    print("\nTesting Trade Execution")
    print("=" * 50)

    # Test 1: Execute small ETH sell
    print("\n1. Testing POST /trades/execute - Small ETH Sell")
    try:
        trade_data = {
            "username": "agent_1",
            "symbol": "ETH/USD",
            "side": "sell",
            "amount": 0.01,
            "order_type": "market",
            "description": "Test ETH sell order"
        }

        response = requests.post(
            BASE_URL + API_PREFIX + "/trades/execute",
            json=trade_data,
            headers={"Content-Type": "application/json"}
        )

        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            print("MAJOR SUCCESS: Trade executed!")
            print("   Trade ID: " + str(data.get('trade_id', 'N/A')))
            print("   Price: $" + str(data.get('price', 'N/A')))
            print("   Total value: $" + str(data.get('total_value', 'N/A')))
            print("   Fee: $" + str(data.get('fee_amount', 'N/A')))
            return data.get('trade_id')
        else:
            print("Expected failure: " + str(response.status_code) + " - " + response.text)
            print("   (This is expected if agent_1 has insufficient balance)")
            return None

    except Exception as e:
        print("ERROR: " + str(e))
        return None


def test_trade_history():
    """Test trade history endpoints"""
    print("\nTesting Trade History")
    print("=" * 50)

    # Test 1: Get user trades
    print("\n1. Testing GET /trades/user/agent_1")
    try:
        response = requests.get(BASE_URL + API_PREFIX + "/trades/user/agent_1")
        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            trade_count = len(data.get('data', []))
            print("SUCCESS: Retrieved " + str(trade_count) + " trades")

            # Show first trade if available
            if data.get('data'):
                first_trade = data['data'][0]
                print("   Latest trade: " + str(first_trade.get('symbol', 'N/A')) + " - " + str(first_trade.get('side', 'N/A')))
                print("   Amount: " + str(first_trade.get('amount', 'N/A')))
                print("   Price: $" + str(first_trade.get('price', 'N/A')))
                return first_trade.get('trade_id')
            else:
                print("   No trades found for agent_1")
                return None
        else:
            print("ERROR: " + str(response.status_code) + " - " + response.text)
            return None

    except Exception as e:
        print("ERROR: " + str(e))
        return None


def test_trade_details(trade_id):
    """Test trade details endpoint"""
    if not trade_id:
        print("\nSkipping trade details test - no trade ID available")
        return

    print("\n2. Testing GET /trades/" + str(trade_id))
    try:
        response = requests.get(BASE_URL + API_PREFIX + "/trades/" + str(trade_id))
        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            trade_data = data.get('data', {})
            print("SUCCESS: Retrieved trade details")
            print("   Trade ID: " + str(trade_data.get('trade_id', 'N/A')))
            print("   Symbol: " + str(trade_data.get('symbol', 'N/A')))
            print("   Side: " + str(trade_data.get('side', 'N/A')))
            print("   Amount: " + str(trade_data.get('amount', 'N/A')))
            print("   Status: " + str(trade_data.get('status', 'N/A')))
        else:
            print("ERROR: " + str(response.status_code) + " - " + response.text)

    except Exception as e:
        print("ERROR: " + str(e))


def test_trade_statistics():
    """Test trade statistics endpoint"""
    print("\nTesting Trade Statistics")
    print("=" * 50)

    print("\n1. Testing GET /trades/stats/summary")
    try:
        response = requests.get(BASE_URL + API_PREFIX + "/trades/stats/summary")
        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            stats = data.get('data', {})
            print("SUCCESS: Retrieved trade statistics")
            print("   Total trades: " + str(stats.get('total_trades', 0)))
            print("   Buy trades: " + str(stats.get('buy_trades', 0)))
            print("   Sell trades: " + str(stats.get('sell_trades', 0)))
            print("   Total volume: $" + str(stats.get('total_volume', 0)))
            print("   Total fees: $" + str(stats.get('total_fees', 0)))
            print("   Unique users: " + str(stats.get('unique_users', 0)))

            top_pairs = stats.get('top_trading_pairs', [])
            if top_pairs:
                print("   Top trading pairs:")
                for pair in top_pairs[:3]:
                    print("     - " + str(pair.get('symbol', 'N/A')) + ": " + str(pair.get('trade_count', 0)) + " trades")
        else:
            print("ERROR: " + str(response.status_code) + " - " + response.text)

    except Exception as e:
        print("ERROR: " + str(e))


def test_list_all_trades():
    """Test list all trades endpoint"""
    print("\nTesting List All Trades")
    print("=" * 50)

    print("\n1. Testing GET /trades/")
    try:
        response = requests.get(BASE_URL + API_PREFIX + "/trades/?limit=10")
        print("Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()
            trade_count = len(data.get('data', []))
            print("SUCCESS: Retrieved " + str(trade_count) + " trades")

            # Show trades summary
            trades = data.get('data', [])
            if trades:
                print("   Recent trades:")
                for trade in trades[:3]:
                    username = str(trade.get('username', 'N/A'))
                    symbol = str(trade.get('symbol', 'N/A'))
                    side = str(trade.get('side', 'N/A'))
                    print("     - " + username + ": " + symbol + " " + side)
            else:
                print("   No trades found in system")
        else:
            print("ERROR: " + str(response.status_code) + " - " + response.text)

    except Exception as e:
        print("ERROR: " + str(e))


def test_error_cases():
    """Test error handling"""
    print("\nTesting Error Cases")
    print("=" * 50)

    # Test 1: Invalid user
    print("\n1. Testing invalid user")
    try:
        trade_data = {
            "username": "nonexistent_user",
            "symbol": "ETH/USD",
            "side": "buy",
            "amount": 0.01,
            "order_type": "market"
        }

        response = requests.post(
            BASE_URL + API_PREFIX + "/trades/simulate",
            json=trade_data,
            headers={"Content-Type": "application/json"}
        )

        print("Status: " + str(response.status_code))
        if response.status_code == 404:
            print("SUCCESS: Correctly returned 404 for non-existent user")
        else:
            print("Unexpected status: " + str(response.status_code))

    except Exception as e:
        print("ERROR: " + str(e))

    # Test 2: Invalid trading pair
    print("\n2. Testing invalid trading pair")
    try:
        trade_data = {
            "username": "agent_1",
            "symbol": "INVALID/PAIR",
            "side": "buy",
            "amount": 0.01,
            "order_type": "market"
        }

        response = requests.post(
            BASE_URL + API_PREFIX + "/trades/simulate",
            json=trade_data,
            headers={"Content-Type": "application/json"}
        )

        print("Status: " + str(response.status_code))
        if response.status_code == 404:
            print("SUCCESS: Correctly returned 404 for invalid trading pair")
        else:
            print("Unexpected status: " + str(response.status_code))

    except Exception as e:
        print("ERROR: " + str(e))


def main():
    """Run all tests"""
    print("Starting Comprehensive Trades API Tests")
    print("=" * 60)

    # First check if API is running
    if not test_api_health():
        print("\nCannot proceed with tests - API is not accessible")
        print("   Please start the API server first:")
        print("   python main.py")
        return

    # Run all test suites
    test_trade_simulation()

    # Try to execute a trade (might fail due to insufficient balance)
    trade_id = test_trade_execution()

    # Test trade history
    history_trade_id = test_trade_history()

    # Test trade details with any available trade ID
    test_trade_details(trade_id or history_trade_id)

    # Test statistics
    test_trade_statistics()

    # Test list all trades
    test_list_all_trades()

    # Test error cases
    test_error_cases()

    print("\n" + "=" * 60)
    print("Comprehensive Test Summary:")
    print("   - Trade simulation endpoints tested")
    print("   - Trade execution endpoints tested")
    print("   - Trade history endpoints tested")
    print("   - Trade statistics endpoints tested")
    print("   - Error handling tested")
    print("   - Check the results above for any failures")
    print("   - Note: Some trade executions may fail due to insufficient balance")
    print("   - This is expected behavior for agent_1")
    print("=" * 60)


if __name__ == "__main__":
    main()
