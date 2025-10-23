from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from app.core.supabase_client import supabase
from app.core.db_client import get_user_by_google_id, create_user

router = APIRouter()

async def verify_supabase_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Verify Supabase JWT token and return user information.

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        Dict containing user information

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "")

    try:
        # Verify the JWT token with Supabase
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "user_id": user.user.id,
            "email": user.user.email,
            "google_id": user.user.user_metadata.get("provider_id") if user.user.user_metadata else None
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

@router.get("/me")
async def get_current_user(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get current authenticated user information.
    """
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "google_id": user["google_id"]
    }

@router.post("/sync-user")
async def sync_user_with_database(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Sync Supabase user with our custom database.
    Creates user record if it doesn't exist.
    """
    try:
        google_id = user["google_id"]
        email = user["email"]

        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found in user metadata")

        # Check if user exists in our database
        existing_user = get_user_by_google_id(google_id)

        if not existing_user:
            # Create new user
            db_user = create_user(google_id, email, email.split("@")[0])  # Use email prefix as name
            return {
                "message": "User created successfully",
                "user_id": db_user["id"],
                "google_id": google_id
            }
        else:
            return {
                "message": "User already exists",
                "user_id": existing_user["id"],
                "google_id": google_id
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync user: {str(e)}")

@router.post("/google-tokens")
async def store_google_tokens(
    token_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Store Google OAuth tokens for a user.
    This should be called after successful Google OAuth in the frontend.
    """
    try:
        # For now, store in a simple in-memory store (replace with database storage)
        from app.tools.email_tools import token_store

        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Store tokens with Google ID as key
        token_store[google_id] = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in", 3600),
            "created_at": "2024-01-01T00:00:00Z"  # Should be current timestamp
        }

        return {"message": "Tokens stored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store tokens: {str(e)}")

@router.get("/google-tokens")
async def get_google_tokens(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get Google OAuth tokens for the authenticated user.
    """
    try:
        from app.tools.email_tools import token_store

        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        tokens = token_store.get(google_id)
        if not tokens:
            raise HTTPException(status_code=404, detail="Tokens not found")

        return {
            "access_token": tokens.get("access_token"),
            "expires_in": tokens.get("expires_in")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tokens: {str(e)}")

@router.get("/health")
async def auth_health_check():
    """Health check for auth service."""
    return {"status": "healthy", "service": "auth"}
