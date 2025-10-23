"""
Enhanced chat endpoint with database integration
Accepts Google OAuth tokens and user IDs for secure, personalized conversations
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List, Dict, Any
from app.models.schemas import ChatRequest, ChatResponse
from app.core.enhanced_llm_wrapper_supabase import get_llm_response_with_supabase
from app.core.db_client import get_user_by_google_id, create_user, get_messages, add_message

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    x_google_token: Optional[str] = Header(None, description="Google OAuth access token"),
    x_user_id: Optional[str] = Header(None, description="User ID from database")
):
    """
    Enhanced chat endpoint that accepts Google OAuth tokens and user IDs.

    This endpoint:
    - Accepts Google access tokens from the frontend
    - Accepts user IDs from database
    - Provides personalized AI responses
    - Stores conversation history in database
    - Enables secure tool execution with user context
    """
    try:
        # Validate required headers
        if not x_google_token:
            raise HTTPException(
                status_code=401,
                detail="Missing Google OAuth token. Please ensure you're logged in with Google."
            )

        if not x_user_id:
            raise HTTPException(
                status_code=401,
                detail="Missing user ID. Please ensure you're authenticated."
            )

        # Clean the token (remove "Bearer " prefix if present)
        google_token = x_google_token.replace("Bearer ", "").strip()

        # Get user ID as int
        user_id = int(x_user_id)

        # Add user message to history
        add_message(user_id, 'user', request.message)

        # Get AI response with user context
        reply = await get_llm_response_with_supabase(
            message=request.message,
            google_access_token=google_token,
            user_id=str(user_id)  # Pass as str for compatibility
        )

        # Add AI message to history
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
    x_user_id: Optional[str] = Header(None, description="User ID from database")
) -> List[Dict[str, Any]]:
    """
    Get chat messages for a user.
    """
    try:
        if not x_user_id:
            raise HTTPException(
                status_code=401,
                detail="Missing user ID."
            )

        user_id = int(x_user_id)
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
