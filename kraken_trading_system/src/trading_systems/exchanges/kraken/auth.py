"""
Kraken API authentication module - FIXED VERSION.

This module implements the HMAC-SHA512 signature generation required
for authenticated Kraken REST API calls.

Fixed based on official Kraken documentation.
"""

import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Dict, Any, Optional, Tuple

from ...utils.exceptions import AuthenticationError, InvalidCredentialsError
from ...utils.logger import LoggerMixin


class KrakenAuthenticator(LoggerMixin):
    """
    Handles Kraken API authentication including signature generation.
    
    Implements the HMAC-SHA512 signature algorithm required by Kraken:
    API-Sign = HMAC-SHA512 of (URI path + SHA256(nonce + POST data)) and base64 decoded secret API key
    
    FIXED: Now uses the correct algorithm from official Kraken documentation.
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the authenticator with API credentials.
        
        Args:
            api_key: Kraken API public key
            api_secret: Kraken API secret key (base64 encoded)
            
        Raises:
            InvalidCredentialsError: If credentials are invalid or missing
        """
        super().__init__()
        
        if not api_key or not api_secret:
            raise InvalidCredentialsError("API key and secret are required")
        
        self.api_key = api_key
        
        # Validate and decode API secret
        try:
            self.api_secret_decoded = base64.b64decode(api_secret)
        except Exception as e:
            raise InvalidCredentialsError(f"Invalid API secret format: {e}")
        
        self.log_info("Kraken authenticator initialized", api_key_length=len(api_key))
    
    def generate_nonce(self) -> str:
        """
        Generate a nonce (number used once) for API requests.
        
        Kraken requires nonces to be increasing values. We use millisecond
        timestamp to ensure uniqueness and proper ordering.
        
        Returns:
            String representation of current timestamp in milliseconds
        """
        return str(int(time.time() * 1000))
    
    def create_signature(
        self, 
        uri_path: str, 
        data: Dict[str, Any], 
        nonce: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create HMAC-SHA512 signature for Kraken API request.
        
        FIXED: Uses the correct algorithm from official Kraken documentation.
        
        Args:
            uri_path: API endpoint path (e.g., "/0/private/Balance")
            data: Dictionary of POST data parameters
            nonce: Optional nonce (will be generated if not provided)
            
        Returns:
            Tuple of (nonce, signature) where signature is base64 encoded
            
        Raises:
            AuthenticationError: If signature generation fails
        """
        try:
            # Generate nonce if not provided
            if nonce is None:
                nonce = self.generate_nonce()
            
            # Add nonce to data
            data_with_nonce = {"nonce": nonce}
            data_with_nonce.update(data)
            data_with_nonce['nonce'] = nonce
            
            # Create URL-encoded POST data string
            postdata = urllib.parse.urlencode(data_with_nonce)
            
            # FIXED: Create the encoded string correctly: nonce + postdata (not nonce + postdata)
            # This is the key fix - the string to hash is: str(nonce) + postdata
            encoded = (str(data_with_nonce['nonce']) + postdata).encode('utf-8')
            
            # Calculate SHA256 hash of the encoded string
            sha256_hash = hashlib.sha256(encoded).digest()
            
            # Create message for HMAC: URI path + SHA256 hash (both as bytes)
            message = uri_path.encode('utf-8') + sha256_hash
            
            # Calculate HMAC-SHA512 using the decoded secret key
            mac = hmac.new(self.api_secret_decoded, message, hashlib.sha512)
            
            # Encode signature to base64
            signature = base64.b64encode(mac.digest()).decode('utf-8')
            
            self.log_info(
                "Generated API signature",
                uri_path=uri_path,
                nonce=nonce,
                postdata_length=len(postdata)
            )
            
            return nonce, signature
            
        except Exception as e:
            self.log_error("Failed to generate API signature", error=e)
            raise AuthenticationError(f"Signature generation failed: {e}")
    
    def create_headers(
        self, 
        uri_path: str, 
        data: Dict[str, Any], 
        nonce: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create complete authentication headers for Kraken API request.
        
        Args:
            uri_path: API endpoint path
            data: POST data parameters
            nonce: Optional nonce
            
        Returns:
            Dictionary containing API-Key and API-Sign headers
        """
        nonce, signature = self.create_signature(uri_path, data, nonce)
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def validate_credentials(self) -> bool:
        """
        Validate that the API credentials are properly formatted.
        
        Returns:
            True if credentials appear valid, False otherwise
        """
        try:
            # Check API key format (should be alphanumeric)
            if not self.api_key.replace('+', '').replace('/', '').replace('=', '').isalnum():
                return False
            
            # Check that secret was properly base64 decoded
            if len(self.api_secret_decoded) < 32:  # Should be at least 256 bits
                return False
            
            return True
            
        except Exception:
            return False


def create_authenticator_from_settings(settings) -> Optional[KrakenAuthenticator]:
    """
    Create a KrakenAuthenticator from application settings.
    
    Args:
        settings: Application settings object
        
    Returns:
        KrakenAuthenticator instance or None if credentials not available
        
    Raises:
        InvalidCredentialsError: If credentials are invalid
    """
    api_key, api_secret = settings.get_api_credentials()
    
    if not api_key or not api_secret:
        return None
    
    return KrakenAuthenticator(api_key, api_secret)


# Utility functions for testing and validation

def get_kraken_signature(urlpath: str, data: Dict[str, Any], secret: str) -> str:
    """
    Official Kraken signature function from their documentation.
    
    This is the reference implementation from Kraken's API docs.
    """
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


def test_signature_generation():
    """
    Test signature generation with known values from Kraken documentation.
    
    This uses the exact example from Kraken documentation to verify
    our implementation matches their expected output.
    """
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
    
    # Test with official function
    expected_signature = get_kraken_signature(urlpath, data, api_sec)
    
    # Test with our implementation
    test_key = "test_key"
    authenticator = KrakenAuthenticator(test_key, api_sec)
    
    # Remove nonce from data since our method adds it
    test_data = data.copy()
    del test_data['nonce']
    
    nonce, actual_signature = authenticator.create_signature(urlpath, test_data, data['nonce'])
    
    return actual_signature == expected_signature, actual_signature, expected_signature


if __name__ == "__main__":
    # Test the implementation
    print("Testing FIXED Kraken signature generation...")
    success, actual, expected = test_signature_generation()
    
    if success:
        print("✅ Signature generation test PASSED!")
        print(f"Signature: {actual}")
    else:
        print("❌ Signature generation test FAILED!")
        print(f"Expected: {expected}")
        print(f"Actual:   {actual}")
    
    # Test the official function directly
    print("\nTesting official Kraken function...")
    api_sec = "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="
    data = {
        "nonce": "1616492376594",
        "ordertype": "limit",
        "pair": "XBTUSD",
        "price": 37500,
        "type": "buy",
        "volume": 1.25
    }
    
    signature = get_kraken_signature("/0/private/AddOrder", data, api_sec)
    expected = "4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ=="
    
    print(f"Official function result: {signature}")
    print(f"Expected from docs:       {expected}")
    print(f"Match: {signature == expected}")