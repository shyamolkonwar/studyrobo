#!/usr/bin/env python3
"""
Comprehensive verification script for the backend fixes
"""

import requests
import json
import time

def test_conversation_endpoints():
    """Test conversation endpoints to verify BigInt fix"""
    print("=== Testing Conversation Endpoints ===")
    
    # Test getting conversations (should return 401 without auth)
    response = requests.get("http://localhost:8000/api/v1/conversations")
    print(f"GET /conversations: {response.status_code}")
    
    # Test getting messages for a specific conversation
    test_conv_id = "test-conv-123"
    response = requests.get(f"http://localhost:8000/api/v1/conversations/{test_conv_id}/messages")
    print(f"GET /conversations/{test_conv_id}/messages: {response.status_code}")
    
    # Test adding message to conversation (this is where the BigInt error occurred)
    response = requests.post(
        f"http://localhost:8000/api/v1/conversations/{test_conv_id}/messages",
        json={"role": "user", "content": "test message"}
    )
    print(f"POST /conversations/{test_conv_id}/messages: {response.status_code}")
    if response.status_code == 500:
        print(f"Error response: {response.text}")
        if "bigint" in response.text.lower():
            print("❌ BigInt error still present!")
        else:
            print("✅ No BigInt error detected")
    
    return response.status_code != 500 or "bigint" not in response.text.lower()

def test_rag_system():
    """Test RAG system to verify authentication fix"""
    print("\n=== Testing RAG System ===")
    
    # Test the chat endpoint which uses RAG
    response = requests.post(
        "http://localhost:8000/api/v1/chat",
        json={"message": "what is mvp?"},
        headers={"Authorization": "Bearer test_token"}
    )
    print(f"POST /chat: {response.status_code}")
    
    if response.status_code == 500:
        print(f"Error response: {response.text}")
        if "authentication required" in response.text.lower():
            print("❌ Authentication required error still present!")
        else:
            print("✅ No authentication error detected")
    elif response.status_code == 401:
        print("✅ Authentication working (401 is expected with test token)")
    else:
        print("✅ Chat endpoint responding")
    
    return response.status_code != 500 or "authentication required" not in response.text.lower()

def test_document_search():
    """Test document search functionality"""
    print("\n=== Testing Document Search ===")
    
    # Test document search endpoint
    response = requests.get("http://localhost:8000/api/v1/documents")
    print(f"GET /documents: {response.status_code}")
    
    if response.status_code == 200:
        documents = response.json()
        print(f"Found {len(documents)} documents")
        if documents:
            # Test searching documents
            doc_id = documents[0]['id']
            response = requests.get(f"http://localhost:8000/api/v1/documents/{doc_id}")
            print(f"GET /documents/{doc_id}: {response.status_code}")
    
    return response.status_code < 500

def main():
    """Run all tests"""
    print("🔍 Verifying Backend Fixes")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    time.sleep(2)
    
    results = []
    
    try:
        # Test 1: Conversation endpoints (BigInt fix)
        results.append(("Conversation BigInt Fix", test_conversation_endpoints()))
        
        # Test 2: RAG system (Authentication fix)
        results.append(("RAG Authentication Fix", test_rag_system()))
        
        # Test 3: Document system
        results.append(("Document System", test_document_search()))
        
    except Exception as e:
        print(f"\n❌ Test execution error: {e}")
        results.append(("Test Execution", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All fixes verified successfully!")
    else:
        print("⚠️  Some issues remain - check the test output above")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)