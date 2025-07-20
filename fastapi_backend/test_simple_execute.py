#!/usr/bin/env python3
"""
test_simple_execute.py
Test the simple execute endpoint
"""

import requests
import json

def test_simple_execute():
    """Test the simple execute endpoint"""
    
    base_url = "http://localhost:8000"
    
    test_data = {
        "username": "demo_user",
        "symbol": "BTC-USD",
        "side": "buy",
        "amount": "0.0001",
        "order_type": "market"
    }
    
    print("🧪 Testing simple execute endpoint...")
    print(f"Request: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/trades/execute-simple",
            json=test_data,
            timeout=10
        )
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print("❌ FAILED!")
            print(f"Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_simple_execute()
