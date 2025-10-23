"""
Conversation management endpoints for StudyRobo
Handles creating, listing, and deleting conversations
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List, Dict, Any
from pydantic import BaseModel
from app.api.v1.endpoints.auth.google import verify_supabase_token
from app.core.db_client import (
    create_user,
    get_user_by_google_id,
    get_messages,  # Use existing functions for now
    add_message
)

router = APIRouter()

class ConversationCreate(BaseModel):
    title: str = "New Chat"

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int

class MessageCreate(BaseModel):
    content: str

# In-memory storage for conversations (temporary fix)
# This will be cleared on server restart, but allows testing
_conversations_store: Dict[str, Dict[str, Any]] = {}

@router.post("/conversations", response_model=Dict[str, str])
async def create_new_conversation(
    conversation: ConversationCreate,
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Create a new conversation for the authenticated user.
    """
    try:
        # Create a simple conversation ID
        import uuid
        conversation_id = str(uuid.uuid4())

        # Store in memory (temporary fix)
        _conversations_store[conversation_id] = {
            'user_google_id': user["google_id"],
            'title': conversation.title,
            'created_at': 'now()',
            'message_count': 0
        }

        return {"conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Get all conversations for the authenticated user.
    """
    try:
        # Return user's conversations from in-memory store (temporary fix)
        user_conversations = []
        for conv_id, conv_data in _conversations_store.items():
            if conv_data['user_google_id'] == user["google_id"]:
                user_conversations.append({
                    "id": conv_id,
                    "title": conv_data['title'],
                    "created_at": conv_data['created_at'],
                    "message_count": conv_data['message_count']
                })

        return user_conversations
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list conversations: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str = Path(..., description="Conversation ID to delete"),
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Delete a conversation and all its messages.
    """
    try:
        # Check if user owns this conversation
        if conversation_id not in _conversations_store:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if _conversations_store[conversation_id]['user_google_id'] != user["google_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete conversation
        del _conversations_store[conversation_id]
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str = Path(..., description="Conversation ID to update"),
    conversation: ConversationCreate = None,
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Update conversation title.
    """
    try:
        # Check if user owns this conversation
        if conversation_id not in _conversations_store:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if _conversations_store[conversation_id]['user_google_id'] != user["google_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update conversation
        _conversations_store[conversation_id]['title'] = conversation.title
        return {"message": "Conversation updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update conversation: {str(e)}"
        )

# In-memory message storage for conversations (temporary fix)
_conversation_messages: Dict[str, List[Dict[str, Any]]] = {}

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str = Path(..., description="Conversation ID"),
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Get all messages for a specific conversation.
    """
    try:
        # Check if user owns this conversation
        if conversation_id not in _conversations_store:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if _conversations_store[conversation_id]['user_google_id'] != user["google_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Return messages for this conversation
        messages = _conversation_messages.get(conversation_id, [])
        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "created_at": msg["created_at"]
            }
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get messages: {str(e)}"
        )

@router.post("/conversations/{conversation_id}/messages")
async def add_message_endpoint(
    message: MessageCreate,
    conversation_id: str = Path(..., description="Conversation ID"),
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Add a new message to a conversation.
    """
    try:
        # Check if user owns this conversation
        if conversation_id not in _conversations_store:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if _conversations_store[conversation_id]['user_google_id'] != user["google_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Add message
        from datetime import datetime
        new_message = {
            "role": "user",
            "content": message.content,
            "created_at": datetime.now().isoformat()
        }

        if conversation_id not in _conversation_messages:
            _conversation_messages[conversation_id] = []

        _conversation_messages[conversation_id].append(new_message)

        # Update message count
        _conversations_store[conversation_id]['message_count'] += 1

        return {"message": "Message added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add message: {str(e)}"
        )

@router.get("/conversations/health")
async def conversations_health_check():
    """Health check for conversations service."""
    return {"status": "healthy", "service": "conversations"}