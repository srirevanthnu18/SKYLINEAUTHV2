"""
Neutron SDK - Python Authentication Library
============================================
Use this SDK to authenticate users in your Python application.

Usage:
    from neutron_sdk import NeutronAuth
    
    auth = NeutronAuth()
    result = auth.login("username", "password", hwid="optional-hwid")
    
    if result['success']:
        print(f"Welcome, {result['user']['username']}!")
    else:
        print(f"Error: {result['error']}")
"""

import requests
import hashlib
import uuid


class NeutronAuth:
    def __init__(self):
        # Pre-configured credentials for your application
        self.api_url = "{{API_URL}}"
        self.app_secret = "{{APP_SECRET}}"
        self.app_name = "{{APP_NAME}}"
        self.version = "{{VERSION}}"
    
    def _get_hwid(self):
        """Generate a hardware ID based on system information."""
        try:
            return str(uuid.getnode())
        except:
            return "unknown"
    
    def login(self, username: str, password: str, hwid: str = None) -> dict:
        """
        Authenticate a user with the Neutron API.
        
        Args:
            username: The user's key/username
            password: The user's password
            hwid: Hardware ID (auto-generated if not provided)
        
        Returns:
            dict with 'success', 'user' or 'error' keys
        """
        if hwid is None:
            hwid = self._get_hwid()
        
        payload = {
            "secret": self.app_secret,
            "username": username,
            "password": password,
            "hwid": hwid
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/login",
                json=payload,
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def check_license(self, license_key: str) -> dict:
        """
        Check if a license key is valid.
        
        Args:
            license_key: The license key to check
        
        Returns:
            dict with 'success' and license details or 'error'
        """
        payload = {
            "secret": self.app_secret,
            "license": license_key
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/check",
                json=payload,
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}


# Example usage
if __name__ == "__main__":
    auth = NeutronAuth()
    
    # Login example
    result = auth.login("your-key", "your-password")
    
    if result.get("success"):
        print(f"✓ Login successful!")
        print(f"  Username: {result['user']['username']}")
        print(f"  Expiry: {result['user']['expiry']}")
    else:
        print(f"✗ Login failed: {result.get('error')}")
