#!/usr/bin/env python3
"""
Quick test for the FIXED authentication implementation.
This should show the signature generation now working correctly.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test the fixed signature generation directly
def test_fixed_signature():
    """Test the fixed signature generation."""
    print("🔧 Testing FIXED Signature Generation")
    print("=" * 50)
    
    # Official function from Kraken docs
    import urllib.parse
    import hashlib
    import hmac
    import base64
    
    def get_kraken_signature(urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    # Test data from Kraken documentation
    api_sec = "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="
    data = {
        "nonce": "1616492376594",
        "ordertype": "limit",
        "pair": "XBTUSD",
        "price": 37500,
        "type": "buy",
        "volume": 1.25
    }
    urlpath = "/0/private/AddOrder"
    
    # Expected result from Kraken docs
    expected = "4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ=="
    
    # Test official function
    result = get_kraken_signature(urlpath, data, api_sec)
    
    print(f"Expected: {expected}")
    print(f"Got:      {result}")
    print(f"Match:    {result == expected}")
    
    if result == expected:
        print("✅ Official function working correctly!")
        return True
    else:
        print("❌ Official function not working")
        return False

def test_with_our_implementation():
    """Test with our fixed implementation."""
    print("\n🔧 Testing Our FIXED Implementation")
    print("=" * 50)
    
    try:
        from trading_systems.exchanges.kraken.auth import KrakenAuthenticator
        
        # Same test data
        api_sec = "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="
        test_key = "test_key"
        
        auth = KrakenAuthenticator(test_key, api_sec)
        
        # Test data (without nonce since our method adds it)
        data = {
            "ordertype": "limit",
            "pair": "XBTUSD",
            "price": 37500,
            "type": "buy",
            "volume": 1.25
        }
        urlpath = "/0/private/AddOrder"
        test_nonce = "1616492376594"
        
        # Generate signature
        nonce, signature = auth.create_signature(urlpath, data, test_nonce)
        
        # Expected result
        expected = "4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ=="
        
        print(f"Expected: {expected}")
        print(f"Got:      {signature}")
        print(f"Match:    {signature == expected}")
        
        if signature == expected:
            print("✅ Our implementation working correctly!")
            return True
        else:
            print("❌ Our implementation still has issues")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to update the auth.py file with the fixed version")
        return False

def main():
    """Run the tests."""
    print("🔐 TESTING FIXED KRAKEN AUTHENTICATION")
    print("=" * 60)
    
    # Test 1: Official function
    official_works = test_fixed_signature()
    
    # Test 2: Our implementation
    our_works = test_with_our_implementation()
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    
    if official_works and our_works:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Authentication fix is working correctly")
        print("\nNext steps:")
        print("1. Update auth.py with the fixed version")
        print("2. Run the full test suite: python3 test_rest_authentication.py")
    elif official_works:
        print("⚠️ Official function works, but our implementation needs updating")
        print("Please replace auth.py with the fixed version")
    else:
        print("❌ Something is wrong with the test environment")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
