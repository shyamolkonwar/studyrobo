#!/usr/bin/env python3
"""
Create a properly formatted test JWT
"""

import jwt
import json

def create_test_jwt():
    """Create a test JWT that will pass verification with verify_signature=False"""

    payload = {
        "sub": "bb816ebd-c28e-4644-b03a-c1fe38cc45cb",
        "email": "shyamol.business@gmail.com",
        "role": "authenticated",
        "iat": 1734775600,
        "exp": 1926311600
    }

    # Create token without signature (or with fake signature)
    token = jwt.encode(payload, "fake-secret", algorithm="HS256")
    print(f"Generated JWT: {token}")

    # Test decoding it
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"Decoded successfully: {decoded}")
        return token
    except Exception as e:
        print(f"Decode error: {e}")
        return None

if __name__ == "__main__":
    token = create_test_jwt()
    if token:
        print(f"\nUse this token for testing:")
        print(token)