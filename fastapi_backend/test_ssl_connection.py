#!/usr/bin/env python3
import ssl
import certifi
import urllib.request

def test_ssl():
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen('https://api.kraken.com/0/public/Time', context=context) as response:
            data = response.read()
            print("✅ SSL connection to Kraken API successful!")
            return True
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
        return False

if __name__ == "__main__":
    test_ssl()
