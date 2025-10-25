"""
Conversation management endpoints for StudyRobo
Handles creating, listing, and deleting conversations
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List, Dict, Any
from pydantic import BaseModel
from app.api.v1.endpoints.auth.google import verify_supabase_token
from app.core.supabase_client import get_supabase_service_client

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

        # Get service client for admin operations
        service_client = get_supabase_service_client()

        # Ensure user exists in our database before creating conversation
        try:
            user_response = service_client.table('users').select('*').eq('google_id', google_id).execute()
            existing_user = user_response.data[0] if user_response.data else None
        except Exception as db_error:
            existing_user = None

        if not existing_user:
            # Create user record if it doesn't exist
            try:
                user_data = {
                    "google_id": google_id,
                    "email": user.get("email", ""),
                    "name": user.get("email", "").split("@")[0] if user.get("email") else ""
                }
                user_response = service_client.table('users').insert(user_data).execute()
                db_user = user_response.data[0] if user_response.data else None
            except Exception as create_error:
                raise HTTPException(status_code=500, detail=f"Failed to create user: {str(create_error)}")

        # Create conversation in database
        try:
            user_id = existing_user['id'] if existing_user else db_user['id']
            conversation_data = {
                "user_id": user_id,
                "title": conversation.title
            }
            conv_response = service_client.table('conversations').insert(conversation_data).execute()
            conversation_record = conv_response.data[0] if conv_response.data else None
            conversation_id = str(conversation_record['id']) if conversation_record else None
        except Exception as conv_error:
            raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(conv_error)}")

        return {"conversation_id": conversation_id}
    except HTTPException:
        raise
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

        # Get service client for admin operations
        service_client = get_supabase_service_client()

        # Ensure user exists in our database
        try:
            user_response = service_client.table('users').select('*').eq('google_id', google_id).execute()
            existing_user = user_response.data[0] if user_response.data else None
        except Exception as db_error:
            existing_user = None

        if not existing_user:
            # Create user record if it doesn't exist
            try:
                user_data = {
                    "google_id": google_id,
                    "email": user.get("email", ""),
                    "name": user.get("email", "").split("@")[0] if user.get("email") else ""
                }
                user_response = service_client.table('users').insert(user_data).execute()
                db_user = user_response.data[0] if user_response.data else None
            except Exception as create_error:
                raise HTTPException(status_code=500, detail=f"Failed to create user: {str(create_error)}")

        # Get conversations from database
        try:
            user_id = existing_user['id'] if existing_user else db_user['id']
            conv_response = service_client.table('conversations').select('id, title, created_at').eq('user_id', user_id).order('created_at', desc=True).execute()

            conversations = []
            if conv_response.data:
                for conv in conv_response.data:
                    # Count messages for each conversation
                    msg_response = service_client.table('messages').select('id', count='exact').eq('conversation_id', conv['id']).execute()
                    message_count = msg_response.count if hasattr(msg_response, 'count') else 0

                    conversations.append({
                        'id': str(conv['id']),
                        'title': conv['title'],
                        'created_at': conv['created_at'],
                        'message_count': message_count
                    })

        except Exception as conv_error:
            raise HTTPException(status_code=500, detail=f"Failed to fetch conversations: {str(conv_error)}")

        return conversations
    except HTTPException:
        raise
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

        # Get service client for admin operations
        service_client = get_supabase_service_client()

        # First verify user owns this conversation
        user_response = service_client.table('users').select('*').eq('google_id', google_id).execute()
        existing_user = user_response.data[0] if user_response.data else None

        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify conversation exists and belongs to user
        conv_response = service_client.table('conversations').select('*').eq('id', conversation_id).eq('user_id', existing_user['id']).execute()
        conversation = conv_response.data[0] if conv_response.data else None

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get messages for this conversation
        msg_response = service_client.table('messages').select('id, role, content, created_at').eq('conversation_id', conversation_id).order('created_at').execute()

        messages = []
        if msg_response.data:
            for msg in msg_response.data:
                messages.append({
                    'id': str(msg['id']),
                    'role': msg['role'],
                    'content': msg['content'],
                    'created_at': msg['created_at']
                })

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
