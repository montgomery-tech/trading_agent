#!/usr/bin/env python3
"""
fix_symbol_mapping.py
Update Kraken API client to handle URL-safe symbol formats
"""

def update_kraken_client_symbol_mapping():
    """Update the symbol mapping in kraken_api_client.py"""
    
    print("🔧 Updating Kraken API client symbol mapping...")
    
    # Read the current file
    with open("api/services/kraken_api_client.py", "r") as f:
        content = f.read()
    
    # Find the symbol_mapping section
    start_marker = "self.symbol_mapping = {"
    end_marker = "}"
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("❌ Could not find symbol_mapping in kraken_api_client.py")
        return False
    
    # Find the end of the mapping
    brace_count = 0
    end_idx = start_idx + len(start_marker)
    for i, char in enumerate(content[start_idx + len(start_marker):], start_idx + len(start_marker)):
        if char == '{':
            brace_count += 1
        elif char == '}':
            if brace_count == 0:
                end_idx = i + 1
                break
            brace_count -= 1
    
    # Create enhanced symbol mapping
    enhanced_mapping = '''self.symbol_mapping = {
            # Standard format (BTC/USD)
            "BTC/USD": "XBTUSD",
            "ETH/USD": "ETHUSD", 
            "ETH/BTC": "ETHXBT",
            "LTC/USD": "LTCUSD",
            "ADA/USD": "ADAUSD",
            "SOL/USD": "SOLUSD",
            
            # URL-safe format (BTC-USD)
            "BTC-USD": "XBTUSD",
            "ETH-USD": "ETHUSD",
            "ETH-BTC": "ETHXBT", 
            "LTC-USD": "LTCUSD",
            "ADA-USD": "ADAUSD",
            "SOL-USD": "SOLUSD",
            
            # Compact format (BTCUSD)
            "BTCUSD": "XBTUSD",
            "ETHUSD": "ETHUSD",
            "ETHBTC": "ETHXBT",
            "LTCUSD": "LTCUSD", 
            "ADAUSD": "ADAUSD",
            "SOLUSD": "SOLUSD"
        }'''
    
    # Replace the mapping
    new_content = content[:start_idx] + enhanced_mapping + content[end_idx:]
    
    # Backup the original
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"api/services/kraken_api_client.py.backup_symbols_{timestamp}"
    shutil.copy2("api/services/kraken_api_client.py", backup_path)
    print(f"✅ Backed up original to {backup_path}")
    
    # Write the updated file
    with open("api/services/kraken_api_client.py", "w") as f:
        f.write(new_content)
    
    print("✅ Updated kraken_api_client.py with enhanced symbol mapping")
    return True

def test_symbol_formats():
    """Test the different symbol formats"""
    
    test_commands = [
        'curl "http://localhost:8000/api/v1/trades/pricing/BTC%2FUSD"',  # URL encoded
        'curl "http://localhost:8000/api/v1/trades/pricing/BTC-USD"',    # Dash format
        'curl "http://localhost:8000/api/v1/trades/pricing/BTCUSD"',     # Compact format
    ]
    
    print("\n🧪 Test these commands after restarting your FastAPI app:")
    for cmd in test_commands:
        print(f"  {cmd}")

def update_frontend_guidance():
    """Provide guidance for frontend integration"""
    
    print("\n📋 FRONTEND INTEGRATION GUIDANCE:")
    print("=" * 50)
    print()
    print("When building your frontend, use these URL-safe formats:")
    print()
    print("✅ RECOMMENDED:")
    print("  BTC-USD, ETH-USD, ETH-BTC (dash format)")
    print("  BTCUSD, ETHUSD, ETHBTC (compact format)")
    print()
    print("⚠️  AVOID:")
    print("  BTC/USD (requires URL encoding to BTC%2FUSD)")
    print()
    print("🔧 API Usage:")
    print("  GET /api/v1/trades/pricing/BTC-USD")
    print("  GET /api/v1/trades/pricing/BTCUSD") 
    print("  POST /api/v1/trades/simulate")
    print("    {\"symbol\": \"BTC-USD\", \"side\": \"buy\", \"amount\": \"0.001\"}")

def main():
    print("🔧 FIXING SYMBOL MAPPING FOR URL-SAFE FORMATS")
    print("=" * 60)
    
    # Update the symbol mapping
    success = update_kraken_client_symbol_mapping()
    
    if success:
        print("\n✅ SYMBOL MAPPING UPDATED!")
        print("=" * 30)
        print()
        print("📋 Next steps:")
        print("1. Restart your FastAPI app:")
        print("   # Stop with Ctrl+C, then:")
        print("   python3 main.py")
        print()
        print("2. Test the URL-safe formats:")
        test_symbol_formats()
        print()
        update_frontend_guidance()
        print()
        print("🎉 After this fix, all your trade endpoints should work!")
    else:
        print("\n❌ Failed to update symbol mapping")
        print("Please manually update the symbol_mapping in kraken_api_client.py")

if __name__ == "__main__":
    main()
