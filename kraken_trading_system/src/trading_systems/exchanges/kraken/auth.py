"""
Kraken API authentication module.

This module implements the HMAC-SHA512 signature generation required
for authenticated Kraken REST API calls.
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
            data_with_nonce = data.copy()
            data_with_nonce['nonce'] = nonce
            
            # Create URL-encoded POST data string
            post_data = urllib.parse.urlencode(data_with_nonce)
            
            # Create the string to hash: nonce + POST data
            encoded_string = nonce + post_data
            
            # Calculate SHA256 hash of the encoded string
            sha256_hash = hashlib.sha256(encoded_string.encode('utf-8')).digest()
            
            # Create message for HMAC: URI path + SHA256 hash
            message = uri_path.encode('utf-8') + sha256_hash
            
            # Calculate HMAC-SHA512 using the decoded secret key
            hmac_signature = hmac.new(
                self.api_secret_decoded,
                message,
                hashlib.sha512
            )
            
            # Encode signature to base64
            signature = base64.b64encode(hmac_signature.digest()).decode('utf-8')
            
            self.log_info(
                "Generated API signature",
                uri_path=uri_path,
                nonce=nonce,
                post_data_length=len(post_data)
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

def test_signature_generation():
    """
    Test signature generation with known values.
    
    This uses the example from Kraken documentation to verify
    our implementation matches their expected output.
    """
    # Test data from Kraken documentation
    test_secret = "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="
    test_key = "test_key"
    
    authenticator = KrakenAuthenticator(test_key, test_secret)
    
    # Test data from documentation
    test_data = {
        "ordertype": "limit",
        "pair": "XBTUSD", 
        "price": 37500,
        "type": "buy",
        "volume": 1.25
    }
    
    test_nonce = "1616492376594"
    uri_path = "/0/private/AddOrder"
    
    nonce, signature = authenticator.create_signature(uri_path, test_data, test_nonce)
    
    # Expected signature from Kraken documentation
    expected_signature = "4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ=="
    
    return signature == expected_signature, signature, expected_signature


if __name__ == "__main__":
    # Test the implementation
    print("Testing Kraken signature generation...")
    success, actual, expected = test_signature_generation()
    
    if success:
        print("✅ Signature generation test PASSED!")
    else:
        print("❌ Signature generation test FAILED!")
        print(f"Expected: {expected}")
        print(f"Actual:   {actual}")
