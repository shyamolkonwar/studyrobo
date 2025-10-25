#!/usr/bin/env python3
"""
Test script to verify the fixes for the backend issues
"""

import requests
import json

# Test the conversation endpoints
print("Testing conversation endpoints...")

# Test getting conversations
response = requests.get("http://localhost:8000/api/v1/conversations")
print(f"GET /conversations: {response.status_code}")
if response.status_code == 200:
    conversations = response.json()
    print(f"Found {len(conversations)} conversations")
    
    # Test getting messages for each conversation
    for conv in conversations[:2]:  # Test first 2 conversations
        conv_id = conv['id']
        print(f"\nTesting conversation {conv_id}...")
        
        # Get messages
        response = requests.get(f"http://localhost:8000/api/v1/conversations/{conv_id}/messages")
        print(f"GET /conversations/{conv_id}/messages: {response.status_code}")
        
        if response.status_code == 200:
            messages = response.json()
            print(f"Found {len(messages)} messages")
        else:
            print(f"Error: {response.text}")

print("\nTesting RAG system...")
# Test the RAG search functionality
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={"message": "what is mvp?"},
    headers={"Authorization": "Bearer test_token"}
)
print(f"POST /chat: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print("Chat response received successfully")
else:
    print(f"Chat error: {response.text}")

print("\nAll tests completed!")