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
    create_conversation,
    get_user_conversations,
    delete_conversation as db_delete_conversation,
    update_conversation_title,
    get_messages_by_conversation,
    add_message_to_conversation
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

@router.post("/conversations", response_model=Dict[str, str])
async def create_new_conversation(
    conversation: ConversationCreate,
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Create a new conversation for the authenticated user.
    """
    try:
        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Create conversation in database
        conversation_id = create_conversation(google_id, conversation.title)

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
        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Get conversations from database
        conversations = get_user_conversations(google_id)

        return conversations
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
        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Delete conversation from database (includes ownership check)
        db_delete_conversation(conversation_id, google_id)

        return {"message": "Conversation deleted successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Conversation not found")
        elif "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation: ConversationCreate,
    conversation_id: str = Path(..., description="Conversation ID to update"),
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Update conversation title.
    """
    try:
        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Update conversation title in database (includes ownership check)
        update_conversation_title(conversation_id, google_id, conversation.title)

        return {"message": "Conversation updated successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Conversation not found")
        elif "access denied" in str(e).lower():
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update conversation: {str(e)}"
        )



@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str = Path(..., description="Conversation ID"),
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Get all messages for a specific conversation.
    """
    try:
        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Get messages with ownership check
        messages = get_messages_by_conversation(conversation_id, google_id)

        # If no messages returned, check if conversation exists
        if not messages:
            # Check if conversation exists at all
            from app.core.db_client import execute_query
            conv_check = execute_query("SELECT id FROM conversations WHERE id = %s", (conversation_id,))
            if not conv_check:
                raise HTTPException(status_code=404, detail="Conversation not found")
            # If conversation exists but no messages returned, user doesn't own it
            # (empty conversation is still valid - return empty list)
            return []

        return messages
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
        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Add message to conversation (includes ownership check)
        add_message_to_conversation(conversation_id, "user", message.content)

        return {"message": "Message added successfully"}
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="Conversation not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add message: {str(e)}"
        )

@router.get("/conversations/health")
async def conversations_health_check():
    """Health check for conversations service."""
    return {"status": "healthy", "service": "conversations"}
