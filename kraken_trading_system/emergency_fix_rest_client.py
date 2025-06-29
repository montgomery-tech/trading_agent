#!/usr/bin/env python3
"""
Emergency Fix for Enhanced REST Client

The _make_request_with_retry method was accidentally removed during patching.
This script restores the complete method implementation.

Save as: emergency_fix_rest_client.py
Run with: python3 emergency_fix_rest_client.py
"""

import sys
from pathlib import Path

def restore_make_request_with_retry():
    """Restore the missing _make_request_with_retry method."""
    
    print("🚨 EMERGENCY FIX - ENHANCED REST CLIENT")
    print("=" * 60)
    print("Restoring missing _make_request_with_retry method...")
    
    rest_client_path = Path("src/trading_systems/exchanges/kraken/rest_client.py")
    
    if not rest_client_path.exists():
        print("❌ Enhanced REST Client file not found")
        return False
    
    try:
        # Read current content
        with open(rest_client_path, 'r') as f:
            content = f.read()
        
        print(f"📊 Current file size: {len(content)} characters")
        
        # Check if method is missing
        if 'def _make_request_with_retry(' in content:
            print("✅ _make_request_with_retry method already exists")
            return True
        
        print("❌ Confirmed: _make_request_with_retry method is missing")
        print("🔧 Adding complete _make_request_with_retry method...")
        
        # The complete _make_request_with_retry method implementation
        make_request_method = '''
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make a request with retry logic for handling temporary failures.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            data: Request data
            authenticated: Whether request requires authentication
            retry_count: Current retry attempt

        Returns:
            Response data from Kraken API

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limited
            ExchangeError: If API call fails
        """
        try:
            # Check authentication if required
            if authenticated:
                self._check_authentication()

            # Apply rate limiting
            await self._apply_rate_limiting()

            # Prepare request
            url = f"{self.base_url}{endpoint}"
            headers = {"User-Agent": "Enhanced-Kraken-Client/1.0"}

            self.log_info(
                "Making API request",
                method=method,
                endpoint=endpoint,
                authenticated=authenticated
            )

            if authenticated and data is not None:
                # Create authenticated request
                nonce, signature = self.authenticator.create_signature(endpoint, data)
                headers.update({
                    "API-Key": self.authenticator.api_key,
                    "API-Sign": signature
                })
                data["nonce"] = nonce

            # Make request
            if method == "GET":
                response = await self.client.get(url, headers=headers, params=data)
            else:  # POST
                response = await self.client.post(url, headers=headers, data=data)

            response.raise_for_status()
            result = response.json()

            # Handle Kraken-specific errors
            if "error" in result and result["error"]:
                error_msg = result["error"][0] if result["error"] else "Unknown error"
                self.log_error("Kraken API error", error_message=error_msg)
                
                # Check for authentication errors specifically
                if any(auth_error in error_msg.lower() for auth_error in 
                       ['invalid key', 'invalid signature', 'invalid nonce', 'permission denied']):
                    raise AuthenticationError(error_msg)
                elif 'rate limit' in error_msg.lower():
                    raise RateLimitError(error_msg)
                else:
                    raise ExchangeError(error_msg)

            return result

        except AuthenticationError:
            # Re-raise authentication errors without retry
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._make_request_with_retry(
                    method, endpoint, data, authenticated, retry_count + 1
                )
            raise ExchangeError(f"Network error after {self.max_retries} retries: {e}")
        except Exception as e:
            self.log_error("API request failed", error=e, endpoint=endpoint)
            raise ExchangeError(f"Request failed: {e}")

    async def _apply_rate_limiting(self):
        """Apply rate limiting to prevent API abuse."""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()
'''
        
        # Find a good insertion point - after _check_authentication
        insert_point = content.find('raise AuthenticationError("Invalid or test API credentials detected")')
        if insert_point != -1:
            # Find the end of the _check_authentication method
            method_end = content.find('\n\n    ', insert_point)
            if method_end != -1:
                content = content[:method_end] + make_request_method + content[method_end:]
                
                # Create backup
                backup_path = rest_client_path.with_suffix('.py.emergency_backup')
                with open(backup_path, 'w') as f:
                    with open(rest_client_path, 'r') as original:
                        f.write(original.read())
                print(f"💾 Emergency backup created: {backup_path}")
                
                # Write updated content
                with open(rest_client_path, 'w') as f:
                    f.write(content)
                
                print(f"✅ Successfully restored _make_request_with_retry method")
                print(f"📊 Updated file size: {len(content)} characters")
                
                return True
            else:
                print("❌ Could not find insertion point")
                return False
        else:
            print("❌ Could not find reference point for insertion")
            return False
            
    except Exception as e:
        print(f"❌ Error restoring method: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main emergency fix function."""
    print("🚨 Starting emergency fix for Enhanced REST Client...")
    
    success = restore_make_request_with_retry()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 EMERGENCY FIX COMPLETED SUCCESSFULLY!")
        print("✅ _make_request_with_retry method restored")
        print("✅ _apply_rate_limiting method included")
        print("\n📋 Next steps:")
        print("   1. Re-run: python3 test_enhanced_rest_client_full.py")
        print("   2. Verify all 10/10 tests pass")
        print("   3. Proceed with Task 3.2.B implementation")
    else:
        print("❌ EMERGENCY FIX FAILED")
        print("⚠️ Manual intervention required")
        print("\n🔧 Consider restoring from backup:")
        print("   src/trading_systems/exchanges/kraken/rest_client.py.backup")
    
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Emergency fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
