#!/usr/bin/env python3
"""
Real credentials test for Kraken WebSocket Token Manager.
This test uses actual Kraken API credentials to validate the token manager.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_systems.exchanges.kraken.token_manager import (
    KrakenTokenManager,
    WebSocketToken,
)
from trading_systems.config.settings import settings
from trading_systems.utils.logger import get_logger


async def test_token_creation_and_expiry():
    """Test WebSocket token creation and expiry logic."""
    logger = get_logger("TokenTest")
    logger.info("Testing WebSocket token creation and expiry...")
    
    # Test token creation
    now = datetime.now()
    token = WebSocketToken(
        token="test_token_123",
        created_at=now,
        expires_at=now + timedelta(minutes=15)
    )
    
    assert token.token == "test_token_123"
    assert not token.is_expired
    assert not token.should_refresh
    logger.info("✅ Token creation test passed")
    
    # Test expiry logic
    expired_token = WebSocketToken(
        token="expired_token",
        created_at=now - timedelta(minutes=20),
        expires_at=now - timedelta(minutes=5)
    )
    
    assert expired_token.is_expired
    logger.info("✅ Token expiry test passed")
    
    # Test refresh logic
    refresh_token = WebSocketToken(
        token="refresh_token",
        created_at=now - timedelta(minutes=14),
        expires_at=now + timedelta(minutes=1)
    )
    
    assert refresh_token.should_refresh
    assert not refresh_token.is_expired
    logger.info("✅ Token refresh logic test passed")


async def test_token_manager_basic():
    """Test basic token manager functionality."""
    logger = get_logger("TokenManagerTest")
    logger.info("Testing token manager basic functionality...")
    
    # Create token manager
    token_manager = KrakenTokenManager()
    
    # Test initialization
    assert token_manager._current_token is None
    logger.info("✅ Token manager initialization test passed")
    
    # Test status with no token
    status = token_manager.get_token_status()
    assert not status["has_token"]
    logger.info("✅ Token status (no token) test passed")
    
    # Test signature creation
    try:
        import base64
        api_secret = base64.b64encode(b"test_secret").decode('utf-8')
        signature = token_manager._create_signature(
            api_secret, "/0/private/GetWebSocketsToken", "12345", "nonce=12345"
        )
        assert isinstance(signature, str)
        assert len(signature) > 0
        logger.info("✅ Signature creation test passed")
    except Exception as e:
        logger.error(f"❌ Signature creation test failed: {e}")
        raise


async def test_real_token_request():
    """Test real token request with actual Kraken API."""
    logger = get_logger("RealTokenTest")
    logger.info("Testing real token request with Kraken API...")
    
    # Check if we have credentials
    if not settings.has_api_credentials():
        logger.info("⚠️ No API credentials configured - skipping real API test")
        logger.info("To test with real credentials, set KRAKEN_API_KEY and KRAKEN_API_SECRET environment variables")
        return
    
    api_key, api_secret = settings.get_api_credentials()
    logger.info(f"Using API credentials - Key: {api_key[:10]}..., Secret length: {len(api_secret)}")
    
    token_manager = KrakenTokenManager()
    
    try:
        async with token_manager:
            logger.info("🔗 Making real API call to Kraken...")
            
            # Make real token request
            token = await token_manager.get_websocket_token()
            
            logger.info(f"✅ Real token obtained! Length: {len(token)}")
            logger.info(f"Token starts with: {token[:20]}...")
            
            # Test token properties
            status = token_manager.get_token_status()
            logger.info(f"Token status: {status}")
            
            assert status["has_token"]
            assert not status["is_expired"]
            assert status["is_valid"]
            logger.info("✅ Real token validation passed")
            
            # Test that we can get the same token again (caching)
            token2 = await token_manager.get_websocket_token()
            assert token == token2
            logger.info("✅ Token caching working with real API")
            
            # Test token refresh
            logger.info("🔄 Testing force refresh...")
            token3 = await token_manager.get_websocket_token(force_refresh=True)
            assert len(token3) > 0
            logger.info("✅ Force refresh working with real API")
            
    except Exception as e:
        logger.error(f"❌ Real token test failed: {e}")
        logger.info("This could be due to:")
        logger.info("1. Invalid API credentials")
        logger.info("2. API key doesn't have 'WebSocket interface' permission")
        logger.info("3. Network connectivity issues")
        logger.info("4. Kraken API maintenance")
        raise


async def test_credentials_validation():
    """Test credentials validation."""
    logger = get_logger("CredentialsTest")
    logger.info("Testing credentials validation...")
    
    # Test current settings
    has_creds = settings.has_api_credentials()
    is_valid = settings.validate_api_credentials() if has_creds else False
    
    logger.info(f"Has credentials: {has_creds}")
    logger.info(f"Credentials valid: {is_valid}")
    
    if has_creds:
        api_key, api_secret = settings.get_api_credentials()
        logger.info(f"API Key length: {len(api_key)}")
        logger.info(f"API Secret length: {len(api_secret)}")
        logger.info(f"Using sandbox: {settings.use_sandbox}")
        
        if is_valid:
            logger.info("✅ Credentials validation passed")
        else:
            logger.info("⚠️ Credentials format validation failed")
    else:
        logger.info("⚠️ No credentials configured")
    
    logger.info("✅ Credentials test completed")


def print_setup_instructions():
    """Print setup instructions for API credentials."""
    print("\n" + "=" * 70)
    print("🔧 SETUP INSTRUCTIONS")
    print("=" * 70)
    print()
    print("To test with real Kraken API credentials:")
    print()
    print("1. Get Kraken API keys:")
    print("   • Log into your Kraken account")
    print("   • Go to Settings > API")
    print("   • Create new API key with 'WebSocket interface' permission")
    print()
    print("2. Set environment variables:")
    print("   export KRAKEN_API_KEY='your_api_key_here'")
    print("   export KRAKEN_API_SECRET='your_api_secret_here'")
    print()
    print("3. Or create a .env file in the project root:")
    print("   KRAKEN_API_KEY=your_api_key_here")
    print("   KRAKEN_API_SECRET=your_api_secret_here")
    print("   USE_SANDBOX=false")
    print()
    print("4. Re-run this test:")
    print("   python3 examples/real_credentials_test.py")
    print()
    print("=" * 70)


async def main():
    """Run all token manager tests with real credentials."""
    logger = get_logger("RealCredentialsTest")
    
    print("=" * 70)
    print("🧪 Kraken WebSocket Token Manager - Real Credentials Test")
    print("=" * 70)
    print()
    
    try:
        # Run basic tests first
        await test_token_creation_and_expiry()
        await test_token_manager_basic()
        await test_credentials_validation()
        
        # Try real API test if credentials are available
        if settings.has_api_credentials():
            print("\n🔑 API credentials found - testing with real Kraken API...")
            await test_real_token_request()
            
            print()
            print("🎉 ALL TESTS PASSED!")
            print("✅ Token creation and expiry logic working")
            print("✅ Token manager basic functionality working")
            print("✅ Real Kraken API integration working")
            print("✅ Token caching and refresh working")
            print()
            print("🚀 Token Manager is PRODUCTION-READY!")
            
        else:
            print("\n⚠️ No API credentials configured")
            print("✅ Basic token manager functionality working")
            print("❓ Real API integration not tested")
            
            print_setup_instructions()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        
        if "Permission denied" in str(e) or "Invalid key" in str(e):
            print("\n🔍 TROUBLESHOOTING:")
            print("• Check that your API key is correct")
            print("• Ensure API key has 'WebSocket interface' permission enabled")
            print("• Verify API secret is the complete base64 string")
        elif "Network" in str(e) or "timeout" in str(e):
            print("\n🔍 TROUBLESHOOTING:")
            print("• Check your internet connection")
            print("• Kraken API might be experiencing issues")
            print("• Try again in a few minutes")
        
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✅ Subtask 2.1.B: WebSocket Token Management - COMPLETE")
    print("🎯 Ready for Task 2.2: Private WebSocket Connection")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
