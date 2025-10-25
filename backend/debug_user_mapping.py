#!/usr/bin/env python3
"""
Debug the user ID mapping
"""

import os
import sys
sys.path.append('/Users/shyamolkonwar/Documents/studyrobo/backend')

from supabase import create_client
from app.core.config import settings

def debug_user_mapping():
    """Debug how user IDs are mapped"""

    print("=== Debugging User ID Mapping ===")

    # Use service role client
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    try:
        # Get all users
        users = client.table('users').select('*').execute()
        print(f"\nFound {len(users.data) if users.data else 0} users in database:")

        if users.data:
            for user in users.data:
                print(f"  ID: {user['id']}, Google ID: {user['google_id']}, Email: {user.get('email', 'N/A')}")

        # Get all documents
        docs = client.table('documents').select('*').execute()
        print(f"\nFound {len(docs.data) if docs.data else 0} documents in database:")

        if docs.data:
            for doc in docs.data:
                print(f"  Doc ID: {doc['id']}, User ID: {doc['user_id']}, File: {doc['original_file_name']}")

        # Check the specific user from the logs
        target_google_id = "bb816ebd-c28e-4644-b03a-c1fe38cc45cb"
        print(f"\nLooking for user with Google ID: {target_google_id}")

        user_data = client.table('users').select('*').eq('google_id', target_google_id).execute()
        if user_data.data:
            user = user_data.data[0]
            print(f"  Found user: ID={user['id']}, Google ID={user['google_id']}")

            # Check documents for this user
            docs = client.table('documents').select('*').eq('user_id', user['id']).execute()
            print(f"  Documents for this user: {len(docs.data) if docs.data else 0}")
            if docs.data:
                for doc in docs.data:
                    print(f"    - {doc['original_file_name']}")
        else:
            print(f"  User not found in database!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_user_mapping()