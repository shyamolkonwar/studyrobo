#!/usr/bin/env python3
"""
Test the auth fix for document retrieval
"""

import os
import sys
sys.path.append('/Users/shyamolkonwar/Documents/studyrobo/backend')

from supabase import create_client
from app.core.config import settings

def test_auth_fix():
    """Test document retrieval with proper authentication context"""

    print("=== Testing Auth Fix ===")

    # Create auth client
    auth_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    # Create a valid JWT token for testing (this should match your actual user token)
    # For this test, we'll use the actual token from the logs
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYjgxNmViZC1jMjhlLTQ2NDQtYjAzYS1jMWZlMzhjYzQ1Y2IiLCJlbWFpbCI6InNoeWFtb2xrLm9rd2FyQGV4YW1wbGUuY29tIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE2MDAwMDAwMDAsImV4cCI6MTkyMDAwMDAwMH0.test"

    print(f"\n1. Testing WITHOUT auth context:")
    try:
        docs = auth_client.table('documents').select('*').eq('user_id', 1).execute()
        print(f"   Found {len(docs.data) if docs.data else 0} documents")
    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n2. Testing WITH auth context:")
    try:
        # Set auth context
        auth_client.auth.set_session(test_token, test_token)
        print(f"   Set auth session for user bb816ebd-c28e-4644-b03a-c1fe38cc45cb")

        # Now try to get documents
        docs = auth_client.table('documents').select('*').eq('user_id', 1).execute()
        print(f"   Found {len(docs.data) if docs.data else 0} documents")
        if docs.data:
            for doc in docs.data:
                print(f"   - {doc['original_file_name']} ({doc['file_type']})")
        else:
            print("   No documents found")

    except Exception as e:
        print(f"   Error: {e}")

    print(f"\n3. Testing service role for comparison:")
    try:
        service_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        docs = service_client.table('documents').select('*').eq('user_id', 1).execute()
        print(f"   Found {len(docs.data) if docs.data else 0} documents")
        if docs.data:
            for doc in docs.data:
                print(f"   - {doc['original_file_name']} ({doc['file_type']})")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_auth_fix()