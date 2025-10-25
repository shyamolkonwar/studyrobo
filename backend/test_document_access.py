#!/usr/bin/env python3
"""
Debug script to test document retrieval with different authentication methods
"""

import os
import sys
sys.path.append('/Users/shyamolkonwar/Documents/studyrobo/backend')

from supabase import create_client
from app.core.config import settings

def test_document_access():
    """Test document access with different clients"""

    print("=== Testing Document Access ===")

    # Create service role client (bypasses RLS)
    service_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    # Create anon client (subject to RLS)
    anon_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    # Test with service role first
    print("\n1. Testing with SERVICE ROLE client (should bypass RLS):")
    try:
        service_docs = service_client.table('documents').select('*').eq('user_id', 1).execute()
        print(f"   Found {len(service_docs.data) if service_docs.data else 0} documents")
        if service_docs.data:
            print(f"   Sample doc: {service_docs.data[0]['original_file_name']}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test with anon client without auth
    print("\n2. Testing with ANON client (no auth token):")
    try:
        anon_docs = anon_client.table('documents').select('*').eq('user_id', 1).execute()
        print(f"   Found {len(anon_docs.data) if anon_docs.data else 0} documents")
        if anon_docs.data:
            print(f"   Sample doc: {anon_docs.data[0]['original_file_name']}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test with anon client and fake auth token
    print("\n3. Testing with ANON client (with fake auth token):")
    try:
        # Use a fake JWT that just needs to be well-formed
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYjgxNmViZC1jMjhlLTQ2NDQtYjAzYS1jMWZlMzhjYzQ1Y2IiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImlhdCI6MTYwMDAwMDAwMH0.invalid"

        anon_client.auth.set_session(fake_token)
        auth_docs = anon_client.table('documents').select('*').eq('user_id', 1).execute()
        print(f"   Found {len(auth_docs.data) if auth_docs.data else 0} documents")
        if auth_docs.data:
            print(f"   Sample doc: {auth_docs.data[0]['original_file_name']}")
    except Exception as e:
        print(f"   Error: {e}")

    # Check current RLS policies
    print("\n4. Checking current RLS policies:")
    try:
        # Try to get info about RLS policies
        policies = service_client.table('pg_policies').select('*').eq('tablename', 'documents').execute()
        print(f"   Found {len(policies.data) if policies.data else 0} policies")
        if policies.data:
            for policy in policies.data:
                print(f"   Policy: {policy}")
    except Exception as e:
        print(f"   Error checking policies: {e}")

    # Try to get RLS status directly from the database
    try:
        print("\n5. Checking if RLS is enabled on documents table:")
        result = service_client.rpc('exec', {'sql': 'SELECT rowsecurity FROM pg_tables WHERE tablename = \'documents\''}).execute()
        print(f"   RLS enabled: {result.data}")
    except Exception as e:
        print(f"   Error checking RLS status: {e}")

if __name__ == "__main__":
    test_document_access()