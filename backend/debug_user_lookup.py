#!/usr/bin/env python3
"""
Debug script to check user lookup issue
"""

import asyncio
import httpx
import json
import jwt
from dotenv import load_dotenv
import os

load_dotenv()

async def debug_user_lookup():
    """Debug the user lookup process"""

    print("🔍 Debugging User Lookup Issue")
    print("=" * 50)

    # Test with a fake JWT to see the structure
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X2dvb2dsZV9pZDEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImF1ZCI6InRlc3QiLCJpc3MiOiJ0ZXN0IiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE5MDAwMDAwMDB9.test"

    try:
        # Decode the fake token to see structure
        payload = jwt.decode(fake_token, options={"verify_signature": False})
        print(f"🔑 JWT Token Structure:")
        print(f"   sub (user_id): {payload.get('sub')}")
        print(f"   email: {payload.get('email')}")
        print(f"   other claims: {payload}")
    except Exception as e:
        print(f"❌ Failed to decode token: {e}")

    print("\n📊 Checking database connection and user lookup...")

    # Test the actual database lookup
    try:
        from app.core.supabase_client import get_supabase_client

        client = get_supabase_client()

        # Test users table structure
        print("\n🏗️  Testing users table access...")

        # Try to get a user (this might show RLS issues)
        try:
            result = client.table('users').select('*').limit(1).execute()
            print(f"✅ Users table access: {len(result.data) if result.data else 0} records found")
            if result.data:
                print(f"   Sample user structure: {list(result.data[0].keys())}")
        except Exception as e:
            print(f"❌ Users table access failed: {e}")

        # Test with a specific google_id
        test_google_id = "test_google_id123"
        try:
            result = client.table('users').select('id, google_id, email').eq('google_id', test_google_id).execute()
            print(f"🔍 Lookup test for google_id '{test_google_id}': {len(result.data) if result.data else 0} records")
        except Exception as e:
            print(f"❌ User lookup test failed: {e}")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    print("\n🎯 Potential Issues:")
    print("1. JWT token 'sub' field doesn't match database 'google_id' field")
    print("2. RLS policies preventing user lookup")
    print("3. Database connection issues")
    print("4. User record format mismatch")

    print("\n💡 To get your actual JWT token:")
    print("1. Open browser DevTools")
    print("2. Go to your app and login")
    print("3. Look in Network tab for API requests")
    print("4. Find Authorization header with Bearer token")
    print("5. Copy that token and test with it")

if __name__ == "__main__":
    asyncio.run(debug_user_lookup())