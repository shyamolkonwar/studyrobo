#!/usr/bin/env python3
"""
Test the document endpoint directly without JWT
"""

import requests
import json

def test_direct_endpoint():
    """Test by creating a test endpoint that bypasses auth temporarily"""

    print("=== Testing Direct Document Access ===")

    # Create a simple test endpoint call
    url = "http://localhost:8000/api/v1/documents/user"

    # Let's try with a different approach - create a real JWT
    # For now, let's create a temporary test endpoint

    # First, let's see what happens when we make the request with a valid format JWT
    # even if it's not signed correctly

    real_payload = {
        "sub": "bb816ebd-c28e-4644-b03a-c1fe38cc45cb",
        "email": "shyamol.business@gmail.com",
        "role": "authenticated",
        "iat": 1600000000,
        "exp": 1920000000
    }

    # Create a simple JWT (unsigned, just for testing the parsing)
    import base64
    import json

    header = {"alg": "HS256", "typ": "JWT"}
    payload = real_payload

    # Encode without signature
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

    fake_jwt = f"{header_b64}.{payload_b64}.signature"

    print(f"Generated test JWT: {fake_jwt[:50]}...")

    headers = {
        'Authorization': f'Bearer {fake_jwt}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Found {len(data)} documents")
            for doc in data:
                print(f"  - {doc.get('original_file_name', 'Unknown')} ({doc.get('file_type', 'unknown')})")
        else:
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_direct_endpoint()