"""
Enhanced chat endpoint with database integration
Uses Supabase JWT authentication for secure, personalized conversations
"""

from fastapi import APIRouter, HTTPException, Depends
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

        # Get our internal user ID from Google ID
        from app.core.db_client import get_user_by_google_id, create_user
        db_user = get_user_by_google_id(google_id)

        if not db_user:
            # Create user if they don't exist
            user_id = create_user(google_id, user["email"], user["email"].split("@")[0])["id"]
        else:
            user_id = db_user["id"]

        # Get Google access token for tools
        try:
            from app.api.v1.endpoints.auth.google import get_google_tokens
            # We need to get the token for this user
            # Since get_google_tokens is an endpoint, we'll access the token store directly
            from app.tools.email_tools import token_store
            google_token = token_store.get(google_id, {}).get("access_token")
        except:
            google_token = None

        # Add user message to history (support both old and new chat systems)
        if request.conversation_id:
            # New conversation-based system
            add_message_to_conversation(request.conversation_id, 'user', request.message)
        else:
            # Legacy system for backwards compatibility
            add_message(user_id, 'user', request.message)

        # Get AI response with user context
        reply = await get_llm_response_with_supabase(
            message=request.message,
            google_access_token=google_token,
            user_id=str(user_id),
            conversation_id=request.conversation_id
        )

        # Add AI message to history
        if request.conversation_id:
            # New conversation-based system
            add_message_to_conversation(request.conversation_id, 'ai', reply)
        else:
            # Legacy system for backwards compatibility
            add_message(user_id, 'ai', reply)

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

        # Get our internal user ID from Google ID
        from app.core.db_client import get_user_by_google_id, create_user
        db_user = get_user_by_google_id(google_id)

        if not db_user:
            # Create user if they don't exist
            user_id = create_user(google_id, user["email"], user["email"].split("@")[0])["id"]
        else:
            user_id = db_user["id"]
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
            user_id=None
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
