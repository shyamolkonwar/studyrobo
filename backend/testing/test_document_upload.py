#!/usr/bin/env python3
"""
Test script to check if the document upload works after RLS fixes
"""

import asyncio
import httpx
import json

async def test_document_upload():
    """Test document upload endpoint"""

    # You'll need to get a real JWT token from your Supabase auth
    # For now, let's test the user documents endpoint first

    async with httpx.AsyncClient() as client:
        # Test the health endpoint
        try:
            response = await client.get('http://localhost:8000/api/v1/auth/health')
            print(f"✅ Auth health: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Auth health failed: {e}")
            return

        # Test user documents endpoint (this will fail without auth, but should show different error)
        try:
            response = await client.get('http://localhost:8000/api/v1/documents/user')
            print(f"📄 Documents endpoint (no auth): {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Documents endpoint failed: {e}")

        print("\n" + "="*50)
        print("If you want to test with actual authentication:")
        print("1. Get a JWT token from your Supabase auth")
        print("2. Run the SQL script 'backend/fix_rls_policies.sql' in Supabase SQL Editor")
        print("3. Use the token in Authorization header: 'Bearer <your-jwt-token>'")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(test_document_upload())