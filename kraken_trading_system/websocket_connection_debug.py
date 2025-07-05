#!/usr/bin/env python3
"""
WebSocket Connection Diagnostic Tool

Diagnoses specific WebSocket connection issues to identify the root cause
of TLS/authentication problems.

This script will:
1. Test basic HTTPS connectivity to Kraken API
2. Test different TLS configurations
3. Verify API credentials format
4. Test token request with various HTTP client settings
5. Identify the specific failure point
"""

import asyncio
import ssl
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
import base64
import hashlib
import hmac
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.config.settings import settings
    from trading_systems.utils.exceptions import AuthenticationError, InvalidCredentialsError
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class WebSocketConnectionDiagnostic:
    """Comprehensive WebSocket connection diagnostic tool."""
    
    def __init__(self):
        self.results = {}
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        self.results[test_name] = {"success": success, "details": details}
    
    async def test_basic_https_connectivity(self):
        """Test basic HTTPS connectivity to Kraken."""
        print("\n🔗 TESTING BASIC HTTPS CONNECTIVITY")
        print("-" * 50)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://api.kraken.com/0/public/Time")
                
                if response.status_code == 200:
                    self.log_test("Basic HTTPS to Kraken", True, f"Status: {response.status_code}")
                    return True
                else:
                    self.log_test("Basic HTTPS to Kraken", False, f"Status: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("Basic HTTPS to Kraken", False, f"Error: {e}")
            return False
    
    async def test_api_credentials(self):
        """Test API credentials configuration."""
        print("\n🔑 TESTING API CREDENTIALS")
        print("-" * 50)
        
        try:
            has_creds = settings.has_api_credentials()
            self.log_test("API credentials configured", has_creds)
            
            if has_creds:
                api_key, api_secret = settings.get_api_credentials()
                
                # Validate format
                key_valid = api_key and len(api_key) > 10
                self.log_test("API key format", key_valid, f"Length: {len(api_key) if api_key else 0}")
                
                secret_valid = api_secret and len(api_secret) > 10
                self.log_test("API secret format", secret_valid, f"Length: {len(api_secret) if api_secret else 0}")
                
                # Test base64 decoding of secret
                try:
                    base64.b64decode(api_secret)
                    self.log_test("API secret base64 format", True)
                except Exception:
                    self.log_test("API secret base64 format", False, "Not valid base64")
                
                return key_valid and secret_valid
            else:
                return False
                
        except Exception as e:
            self.log_test("API credentials test", False, f"Error: {e}")
            return False
    
    def create_signature(self, api_secret: str, api_path: str, nonce: str, post_data: str) -> str:
        """Create API signature (same as token manager)."""
        api_secret_decoded = base64.b64decode(api_secret)
        sha256_hash = hashlib.sha256((nonce + post_data).encode('utf-8'))
        hmac_signature = hmac.new(
            api_secret_decoded,
            api_path.encode('utf-8') + sha256_hash.digest(),
            hashlib.sha512
        )
        return base64.b64encode(hmac_signature.digest()).decode('utf-8')
    
    async def test_token_request_with_different_clients(self):
        """Test token request with different HTTP client configurations."""
        print("\n🔧 TESTING DIFFERENT HTTP CLIENT CONFIGURATIONS")
        print("-" * 50)
        
        api_key, api_secret = settings.get_api_credentials()
        
        # Prepare request data
        nonce = str(int(time.time() * 1000))
        post_data = f"nonce={nonce}"
        api_path = "/0/private/GetWebSocketsToken"
        signature = self.create_signature(api_secret, api_path, nonce, post_data)
        
        headers = {
            "API-Key": api_key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"nonce": nonce}
        url = f"https://api.kraken.com{api_path}"
        
        # Test different client configurations
        configurations = [
            {
                "name": "Default httpx client",
                "config": {}
            },
            {
                "name": "Extended timeout",
                "config": {"timeout": 60.0}
            },
            {
                "name": "HTTP/1.1 only",
                "config": {"http2": False}
            },
            {
                "name": "Custom SSL context",
                "config": {"verify": self.create_ssl_context()}
            },
            {
                "name": "Disable SSL verification",
                "config": {"verify": False}
            }
        ]
        
        for config in configurations:
            try:
                print(f"\n🔍 Testing: {config['name']}")
                async with httpx.AsyncClient(**config['config']) as client:
                    response = await client.post(url, headers=headers, data=data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if "result" in result and "token" in result["result"]:
                            self.log_test(config['name'], True, "Token received successfully")
                            return True
                        else:
                            self.log_test(config['name'], False, f"API error: {result.get('error', 'Unknown')}")
                    else:
                        self.log_test(config['name'], False, f"HTTP {response.status_code}: {response.text[:100]}")
                        
            except httpx.ConnectError as e:
                self.log_test(config['name'], False, f"ConnectError: {str(e)[:100]}")
            except Exception as e:
                self.log_test(config['name'], False, f"Error: {str(e)[:100]}")
        
        return False
    
    def create_ssl_context(self):
        """Create a custom SSL context."""
        context = ssl.create_default_context()
        # Enable more TLS versions if needed
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        return context
    
    async def test_direct_websocket_connection(self):
        """Test direct WebSocket connection without token."""
        print("\n🌐 TESTING DIRECT WEBSOCKET CONNECTION")
        print("-" * 50)
        
        try:
            import websockets
            
            # Test public WebSocket
            async with websockets.connect("wss://ws.kraken.com") as websocket:
                # Send a simple subscription
                subscribe_msg = {
                    "event": "subscribe",
                    "pair": ["ETH/USD"],
                    "subscription": {"name": "ticker"}
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # Try to receive a response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                self.log_test("Public WebSocket connection", True, "Connection successful")
                return True
                
        except Exception as e:
            self.log_test("Public WebSocket connection", False, f"Error: {e}")
            return False
    
    async def test_system_ssl_settings(self):
        """Test system SSL settings and capabilities."""
        print("\n🔒 TESTING SYSTEM SSL SETTINGS")
        print("-" * 50)
        
        try:
            # Check SSL library version
            ssl_version = ssl.OPENSSL_VERSION
            self.log_test("SSL library version", True, ssl_version)
            
            # Check available ciphers
            context = ssl.create_default_context()
            ciphers = context.get_ciphers()
            self.log_test("SSL ciphers available", len(ciphers) > 0, f"{len(ciphers)} ciphers")
            
            # Check TLS versions
            min_version = context.minimum_version
            max_version = context.maximum_version
            self.log_test("TLS version support", True, f"Min: {min_version}, Max: {max_version}")
            
            return True
            
        except Exception as e:
            self.log_test("System SSL settings", False, f"Error: {e}")
            return False
    
    async def test_alternative_authentication_methods(self):
        """Test alternative ways to authenticate."""
        print("\n🔄 TESTING ALTERNATIVE AUTHENTICATION METHODS")
        print("-" * 50)
        
        try:
            # Test using REST client directly
            from trading_systems.exchanges.kraken.rest_client import EnhancedKrakenRestClient
            
            rest_client = EnhancedKrakenRestClient()
            auth_result = await rest_client.test_authentication()
            
            self.log_test("REST client authentication", auth_result)
            
            if auth_result:
                # If REST works, try to get token through REST client
                try:
                    balance_result = await rest_client.get_account_balance()
                    self.log_test("REST API account access", True, "Balance retrieved")
                except Exception as e:
                    self.log_test("REST API account access", False, f"Error: {e}")
            
            return auth_result
            
        except Exception as e:
            self.log_test("Alternative authentication", False, f"Error: {e}")
            return False
    
    async def run_full_diagnostic(self):
        """Run complete diagnostic suite."""
        print("🔍 WEBSOCKET CONNECTION DIAGNOSTIC TOOL")
        print("=" * 70)
        print("Diagnosing WebSocket connection issues...")
        print("=" * 70)
        
        # Run all diagnostic tests
        basic_connectivity = await self.test_basic_https_connectivity()
        credentials_ok = await self.test_api_credentials()
        
        if credentials_ok:
            token_request_ok = await self.test_token_request_with_different_clients()
        else:
            token_request_ok = False
            
        websocket_ok = await self.test_direct_websocket_connection()
        ssl_ok = await self.test_system_ssl_settings()
        alt_auth_ok = await self.test_alternative_authentication_methods()
        
        # Summary
        print("\n📊 DIAGNOSTIC SUMMARY")
        print("=" * 50)
        
        all_tests = [
            ("Basic HTTPS connectivity", basic_connectivity),
            ("API credentials", credentials_ok),
            ("Token request", token_request_ok),
            ("WebSocket connection", websocket_ok),
            ("SSL configuration", ssl_ok),
            ("Alternative authentication", alt_auth_ok)
        ]
        
        passed_tests = sum(1 for _, success in all_tests if success)
        total_tests = len(all_tests)
        
        for test_name, success in all_tests:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}")
        
        print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 30)
        
        if not basic_connectivity:
            print("🔧 Fix network connectivity to api.kraken.com")
        elif not credentials_ok:
            print("🔧 Check API credentials configuration")
        elif not token_request_ok:
            print("🔧 TLS/SSL configuration issue - try different client settings")
            print("   Consider checking firewall, proxy, or certificate settings")
        elif alt_auth_ok and not token_request_ok:
            print("🔧 Use REST API fallback until WebSocket token issue is resolved")
        else:
            print("✅ All systems appear functional")
        
        return passed_tests == total_tests


async def main():
    """Main diagnostic execution."""
    diagnostic = WebSocketConnectionDiagnostic()
    success = await diagnostic.run_full_diagnostic()
    
    if success:
        print("\n🎉 ALL DIAGNOSTICS PASSED!")
        print("WebSocket connection should work now.")
    else:
        print("\n⚠️ SOME ISSUES FOUND")
        print("Check recommendations above.")
    
    return success


if __name__ == "__main__":
    import json  # Add missing import
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
