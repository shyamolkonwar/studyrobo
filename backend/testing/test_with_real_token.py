#!/usr/bin/env python3
"""
Test with a real Supabase token
"""

import os
import sys
sys.path.append('/Users/shyamolkonwar/Documents/studyrobo/backend')

from supabase import create_client
from app.core.config import settings
import requests

def get_real_token():
    """Get a real token by authenticating with Supabase"""
    try:
        # Use anon client to sign in
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

        # Try to sign in with email/password (you'll need to replace with actual credentials)
        # Or use the token from browser dev tools
        print("To get a real token:")
        print("1. Open browser dev tools")
        print("2. Go to Application/Storage -> Local Storage")
        print("3. Look for supabase.auth.token")
        print("4. Copy the access_token value")

        return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def test_with_service_role():
    """Test what the service role can see"""
    print("=== Testing with Service Role ===")

    service_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    try:
        # Get all documents
        docs = service_client.table('documents').select('*').execute()
        print(f"Service role sees {len(docs.data) if docs.data else 0} documents")

        if docs.data:
            for doc in docs.data:
                print(f"  - ID: {doc['id']}, User ID: {doc['user_id']}, File: {doc['original_file_name']}")

            # Test getting documents for user_id = 1
            user_docs = service_client.table('documents').select('*').eq('user_id', 1).execute()
            print(f"Service role sees {len(user_docs.data) if user_docs.data else 0} documents for user_id=1")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_with_service_role()