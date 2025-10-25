#!/usr/bin/env python3
"""
Apply RLS fix for documents table using direct SQL execution
"""

import os
import sys
sys.path.append('/Users/shyamolkonwar/Documents/studyrobo/backend')

import requests
from app.core.config import settings

def apply_rls_fix():
    """Apply RLS policies to allow authenticated users to read their own documents"""

    # SQL to create proper RLS policies
    sql_statements = [
        # Drop all existing policies first
        "DROP POLICY IF EXISTS \"Authenticated users can read documents\" ON documents CASCADE;",
        "DROP POLICY IF EXISTS \"Authenticated users can read all documents\" ON documents CASCADE;",
        "DROP POLICY IF EXISTS \"Allow authenticated users to read documents\" ON documents CASCADE;",
        "DROP POLICY IF EXISTS \"read_documents\" ON documents CASCADE;",

        # Create a policy that allows users to read their own documents
        """
        CREATE POLICY "Users can read own documents" ON documents
        FOR SELECT TO authenticated
        USING (auth.uid()::text = user_id::text);
        """,

        # Create a policy that allows users to insert their own documents
        """
        CREATE POLICY "Users can insert own documents" ON documents
        FOR INSERT TO authenticated
        WITH CHECK (auth.uid()::text = user_id::text);
        """,

        # Create a policy that allows users to update their own documents
        """
        CREATE POLICY "Users can update own documents" ON documents
        FOR UPDATE TO authenticated
        USING (auth.uid()::text = user_id::text)
        WITH CHECK (auth.uid()::text = user_id::text);
        """,

        # Create a policy that allows users to delete their own documents
        """
        CREATE POLICY "Users can delete own documents" ON documents
        FOR DELETE TO authenticated
        USING (auth.uid()::text = user_id::text);
        """,

        # Ensure RLS is enabled
        "ALTER TABLE documents ENABLE ROW LEVEL SECURITY;"
    ]

    # Use Supabase SQL API
    url = f"{settings.SUPABASE_URL}/rest/v1/rpc/sql"
    headers = {
        'Authorization': f'Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
        'apikey': settings.SUPABASE_SERVICE_ROLE_KEY
    }

    print("Applying RLS policies...")

    # Try using direct SQL execution via POST to /sql endpoint (if available)
    for i, sql in enumerate(sql_statements):
        print(f"\nExecuting statement {i+1}/{len(sql_statements)}")
        print(f"SQL: {sql.strip()[:100]}...")

        try:
            # Try different endpoints
            endpoints_to_try = [
                f"{settings.SUPABASE_URL}/rest/v1/sql",
                f"{settings.SUPABASE_URL}/rest/v1/rpc/sql",
                f"{settings.SUPABASE_URL}/rest/v1/rpc/exec"
            ]

            success = False
            for endpoint in endpoints_to_try:
                try:
                    response = requests.post(endpoint, json={'query': sql}, headers=headers, timeout=10)
                    if response.status_code in [200, 201, 204]:
                        print(f"   ✓ Success via {endpoint}")
                        success = True
                        break
                    else:
                        print(f"   ✗ Failed via {endpoint}: {response.status_code} - {response.text[:200]}")
                except Exception as e:
                    print(f"   ✗ Error via {endpoint}: {e}")
                    continue

            if not success:
                print(f"   ⚠ Could not execute statement via API")

        except Exception as e:
            print(f"   ✗ Error executing statement: {e}")

    print("\nRLS fix attempt completed.")

if __name__ == "__main__":
    apply_rls_fix()