#!/usr/bin/env python3
"""
Test the fix for document retrieval by simulating a frontend request
"""

import requests
import json

def test_document_retrieval():
    """Test the document retrieval endpoint with a real JWT token"""

    # First, let's get a real token by logging in through Supabase
    # For now, let's create a test with the token from the logs

    # This should be a real JWT token from your authenticated session
    # You can get this from browser dev tools or from your Supabase dashboard
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiYjgxNmViZC1jMjhlLTQ2NDQtYjAzYS1jMWZlMzhjYzQ1Y2IiLCJlbWFpbCI6InNoeWFtb2wuYnVzaW5lc3NAZ21haWwuY29tIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3MzQ3NzU2MDAsImV4cCI6MTkyNjMxMTYwMH0.tcfst795fmX9bqATzfWBf4VyqhK_5hKnaH7t-Ed9Pp0"

    print("=== Testing Document Retrieval Fix ===")

    # Test the endpoint
    url = "http://localhost:8000/api/v1/documents/user"
    headers = {
        'Authorization': f'Bearer {test_token}',
        'Content-Type': 'application/json'
    }

    print(f"\n1. Testing with JWT token:")
    print(f"   URL: {url}")
    print(f"   Headers: {headers}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Success! Found {len(data)} documents")
            if data:
                for doc in data:
                    print(f"     - {doc.get('original_file_name', 'Unknown')} ({doc.get('file_type', 'unknown')})")
            else:
                print("     No documents found")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ✗ Exception: {e}")

    # Test without token for comparison
    print(f"\n2. Testing without JWT token (should fail):")
    try:
        response = requests.get(url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 401:
            print(f"   ✓ Correctly requires authentication")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")

    # Test backend health
    print(f"\n3. Testing backend health:")
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print(f"   ✓ Backend is running")
        else:
            print(f"   ✗ Backend not responding correctly")
    except Exception as e:
        print(f"   ✗ Backend not accessible: {e}")

if __name__ == "__main__":
    test_document_retrieval()