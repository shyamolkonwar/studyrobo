"""
Enhanced chat endpoint with database integration
Uses Supabase JWT authentication for secure, personalized conversations
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Dict, Any
from app.models.schemas import ChatRequest, ChatResponse
from app.core.enhanced_llm_wrapper_supabase import get_llm_response_with_supabase
from app.core.db_client import get_messages, add_message, add_message_to_conversation
from app.api.v1.endpoints.auth.google import verify_supabase_token

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Enhanced chat endpoint that uses Supabase JWT authentication.

    This endpoint:
    - Verifies Supabase JWT tokens
    - Gets user information from verified token
    - Provides personalized AI responses
    - Stores conversation history in database
    - Enables secure tool execution with user context
    """
    try:
        # Get user information from verified token
        supabase_user_id = user["user_id"]
        google_id = user["google_id"]

        if not google_id:
            raise HTTPException(
                status_code=400,
                detail="Google ID not found. Please ensure you logged in with Google."
            )

        # Get user ID (user should already exist)
        from app.api.v1.endpoints.documents import get_user_id
        user_id = get_user_id(google_id)

        # Google tokens are now retrieved from the secure database storage

        # Add user message to history (new conversation-based system)
        if request.conversation_id:
            # New conversation-based system - only store messages with conversation_id
            add_message_to_conversation(request.conversation_id, 'user', request.message)
        else:
            # Legacy message system for backward compatibility
            # Try to use in-memory conversation store
            try:
                from app.api.v1.endpoints.conversations import _conversations_store

                # Find or create conversation for this user
                user_conversations = [
                    conv_id for conv_id, conv_data in _conversations_store.items()
                    if conv_data['user_google_id'] == user["google_id"]
                ]

                if user_conversations:
                    # Use most recent conversation
                    conversation_id = user_conversations[0]
                    add_message_to_conversation(conversation_id, 'user', request.message)
                else:
                    # Create new conversation and add message
                    import uuid
                    conversation_id = str(uuid.uuid4())
                    _conversations_store[conversation_id] = {
                        'user_google_id': user["google_id"],
                        'title': 'Chat',
                        'message_count': 0,
                        'created_at': 'now()'
                    }
                    add_message_to_conversation(conversation_id, 'user', request.message)
            except Exception as e:
                # Fallback to old system if conversation system fails
                # Use the integer user_id for message storage
                add_message(int(user_id), 'user', request.message)

        # Get AI response with user context
        reply = await get_llm_response_with_supabase(
            message=request.message,
            google_access_token=None,  # Tokens are now retrieved from secure database storage
            user_id=user_id,  # Use integer user_id for message storage
            google_id=user["google_id"],  # Use Google ID for tool execution
            conversation_id=request.conversation_id
        )

        # Add AI message to history
        if request.conversation_id:
            # New conversation-based system
            add_message_to_conversation(request.conversation_id, 'ai', reply)
        else:
            # Legacy system for backwards compatibility
            # Always use integer user_id for message storage
            add_message(int(user_id), 'ai', reply)

        return ChatResponse(reply=reply)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@router.get("/chat/messages")
async def get_chat_messages(
    user: Dict[str, Any] = Depends(verify_supabase_token)
) -> List[Dict[str, Any]]:
    """
    Get chat messages for the authenticated user.
    """
    try:
        google_id = user["google_id"]

        if not google_id:
            raise HTTPException(
                status_code=400,
                detail="Google ID not found. Please ensure you logged in with Google."
            )

        # Get user ID (user should already exist)
        from app.api.v1.endpoints.documents import get_user_id
        user_id = get_user_id(google_id)
        messages = get_messages(user_id)
        return messages

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving messages: {str(e)}"
        )

@router.get("/chat/health")
async def chat_health_check():
    """Health check endpoint for the chat service."""
    return {"status": "healthy", "service": "chat_supabase"}

@router.post("/chat/test")
async def test_chat_endpoint(request: ChatRequest):
    """
    Test chat endpoint that doesn't require authentication.
    Useful for testing the LLM integration without Supabase setup.
    """
    try:
        # Get AI response without user context (for testing only)
        reply = await get_llm_response_with_supabase(
            message=request.message,
            google_access_token=None,
            user_id=None,
            google_id=None
        )

        return ChatResponse(
            reply=reply,
            warning="This is a test response without user context or memory."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your test request: {str(e)}"
        )
