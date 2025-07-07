#!/usr/bin/env python3
"""
Quick script to check agent_1's balances and suggest working trades
"""

import requests

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def main():
    print("💰 Checking agent_1 balances...")
    
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/balances/user/agent_1")
        
        if response.status_code == 200:
            data = response.json()
            balances = data.get('data', [])
            
            print("✅ Current balances:")
            has_tradeable = False
            suggestions = []
            
            for balance in balances:
                amount = float(balance['available_balance'])
                currency = balance['currency_code']
                print(f"   - {amount} {currency}")
                
                # Suggest trades based on balances
                if currency == 'USD' and amount > 30:
                    suggestions.append(f"✅ Can buy ETH (need ~$35)")
                    has_tradeable = True
                elif currency == 'ETH' and amount > 0.01:
                    suggestions.append(f"✅ Can sell {currency} for USD")
                    has_tradeable = True
                elif currency in ['BTC', 'LTC', 'ADA', 'SOL'] and amount > 0:
                    suggestions.append(f"✅ Can sell {currency} for USD")
                    has_tradeable = True
            
            print("\n🎯 Trading suggestions:")
            if suggestions:
                for suggestion in suggestions:
                    print(f"   {suggestion}")
            else:
                print("   ⚠️  Limited trading options with current balances")
                print("   💡 Try selling any non-USD assets to get USD for purchases")
            
            print(f"\n🔗 Available trading pairs:")
            pairs_response = requests.get(f"{BASE_URL}{API_PREFIX}/trading-pairs")
            if pairs_response.status_code == 200:
                pairs_data = pairs_response.json()
                pairs = pairs_data.get('data', [])
                for pair in pairs:
                    symbol = pair.get('symbol', 'N/A')
                    min_amount = pair.get('min_trade_amount', 'N/A')
                    print(f"   - {symbol} (min: {min_amount})")
            
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
