#!/usr/bin/env python3
"""
Debug version of Enhanced REST Client tests to identify issues.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

print("🔍 DEBUG: Starting test script...")

try:
    print("🔍 DEBUG: Attempting imports...")
    from trading_systems.exchanges.kraken.rest_client import EnhancedKrakenRestClient
    print("✅ Enhanced REST Client imported")

    from trading_systems.exchanges.kraken.auth import KrakenAuthenticator
    print("✅ KrakenAuthenticator imported")

    from trading_systems.utils.exceptions import (
        OrderError,
        ExchangeError,
        RateLimitError,
        AuthenticationError
    )
    print("✅ Exception classes imported")

except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🔍 DEBUG: Testing basic functionality...")

def test_basic_functionality():
    """Test basic functionality without async complexity."""
    try:
        print("🔍 DEBUG: Creating client...")
        client = EnhancedKrakenRestClient()
        print("✅ Client created successfully")

        print("🔍 DEBUG: Testing parameter validation...")
        result = client._validate_order_parameters("XBTUSD", "buy", "limit", "1.0", "50000.00")
        print(f"✅ Parameter validation result: {result}")

        print("🔍 DEBUG: Testing invalid parameters...")
        try:
            client._validate_order_parameters("", "buy", "limit", "1.0", "50000")
            print("❌ Should have raised OrderError")
            return False
        except OrderError as e:
            print(f"✅ OrderError properly raised: {e}")

        print("🔍 DEBUG: Testing method existence...")
        methods_to_check = [
            'place_market_order',
            'place_limit_order',
            'cancel_order',
            'get_order_status'
        ]

        for method in methods_to_check:
            if hasattr(client, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False

        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Test that all required imports work."""
    try:
        print("🔍 DEBUG: Testing import functionality...")

        # Test asyncio
        import asyncio
        print("✅ asyncio imported")

        # Test unittest.mock
        from unittest.mock import MagicMock, patch
        print("✅ unittest.mock imported")

        # Test decimal
        from decimal import Decimal
        print("✅ Decimal imported")

        # Test httpx
        import httpx
        print("✅ httpx imported")

        return True

    except ImportError as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Main debug function."""
    print("🔍 DEBUG VERSION - Enhanced REST Client Test")
    print("=" * 50)

    tests_passed = 0
    total_tests = 2

    # Test 1: Import functionality
    print("\n1️⃣ TESTING IMPORTS")
    if test_imports():
        tests_passed += 1
        print("✅ IMPORTS: PASSED")
    else:
        print("❌ IMPORTS: FAILED")

    # Test 2: Basic functionality
    print("\n2️⃣ TESTING BASIC FUNCTIONALITY")
    if test_basic_functionality():
        tests_passed += 1
        print("✅ BASIC FUNCTIONALITY: PASSED")
    else:
        print("❌ BASIC FUNCTIONALITY: FAILED")

    # Results
    print("\n" + "=" * 50)
    print("🔍 DEBUG RESULTS")
    print("=" * 50)
    print(f"Tests Passed: {tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        print("🎉 DEBUG TESTS PASSED!")
        print("The Enhanced REST Client is working correctly.")
        print("You can now run the full test suite or proceed with implementation.")
    else:
        print("❌ Some debug tests failed - need to investigate further")

    return tests_passed == total_tests

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Debug interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Debug error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
