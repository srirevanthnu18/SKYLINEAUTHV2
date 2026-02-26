import hmac
import hashlib
import requests
import time

# Configuration - Replace with an actual app's details from your DB for a real test
# For this script, we assume the server is running on localhost:5000
BASE_URL = "http://localhost:5000/api/v1"
APP_NAME = "AppName"
OWNER_ID = "67beedf591b6e4e5be29283f" # Example MongoDB ObjectID
APP_SECRET = "06527581691230485967210348576921" # Example Secret (hex)
VERSION = "1.0"

def sign_response(data_json, key):
    return hmac.new(key.encode(), data_json.encode(), hashlib.sha256).hexdigest()

def test_compatibility():
    # 1. Initialization (Init)
    sent_key = "1234567890123456" # Mock sentKey
    init_data = {
        "type": "init",
        "ver": VERSION,
        "enckey": sent_key,
        "name": APP_NAME,
        "ownerid": OWNER_ID,
        "secret": APP_SECRET # Project sends this, though standard KeyAuth doesn't
    }
    
    print(f"Testing /init at {BASE_URL}...")
    try:
        response = requests.post(f"{BASE_URL}/init", data=init_data)
        if response.status_code != 200:
            print(f"Init Failed with status {response.status_code}: {response.text}")
            return

        json_resp = response.text
        signature = response.headers.get("signature")
        
        # Verify Init Signature (signed with APP_SECRET)
        expected_sig = sign_response(json_resp, APP_SECRET)
        if signature == expected_sig:
            print("[\u2713] Init Signature Verified!")
        else:
            print(f"[\u2717] Init Signature Mismatch!\nExpected: {expected_sig}\nGot: {signature}")
            return

        resp_obj = response.json()
        session_id = resp_obj.get("sessionid")
        print(f"[\u2713] Session ID: {session_id}")

        # 2. Login (Signed Action)
        login_data = {
            "type": "login",
            "username": "testuser",
            "pass": "testpass",
            "sessionid": session_id,
            "name": APP_NAME,
            "ownerid": OWNER_ID
        }
        
        print("\nTesting /login...")
        response = requests.post(f"{BASE_URL}/login", data=login_data)
        
        json_resp = response.text
        signature = response.headers.get("signature")
        
        # Verify Action Signature (signed with sentKey + "-" + secret)
        signing_key = f"{sent_key}-{APP_SECRET}"
        expected_sig = sign_response(json_resp, signing_key)
        
        if signature == expected_sig:
            print("[\u2713] Login Signature Verified!")
        else:
            print(f"[\u2717] Login Signature Mismatch!\nExpected: {expected_sig}\nGot: {signature}")

        print(f"Response: {json_resp}")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_compatibility()
