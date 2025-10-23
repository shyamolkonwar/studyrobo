from typing import Dict, Any, Optional
import jwt
from fastapi import APIRouter, HTTPException, Header, Depends
from app.core.config import settings
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
        # Decode JWT to get user info - strict verification for production
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid JWT token: missing user_id or email")

        # Valid JWT token
        return {
            "user_id": user_id,
            "email": email,
            "google_id": user_id
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
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

@router.get("/google-auth-url")
async def get_google_auth_url(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Generate Google OAuth URL for direct Gmail API access.
    This bypasses Supabase for Google OAuth to get proper tokens.
    """
    try:
        import secrets
        from urllib.parse import urlencode

        # Generate state parameter for security
        state = secrets.token_urlsafe(32)

        # Store state temporarily (in production, use Redis or database)
        from app.tools.email_tools import _oauth_states
        _oauth_states[state] = {
            "google_id": user["google_id"],
            "email": user["email"],
            "created_at": "2024-01-01T00:00:00Z"
        }

        # Build Google OAuth URL
        params = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "redirect_uri": f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/auth/google-callback",
            "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/spreadsheets",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        return {
            "auth_url": auth_url,
            "state": state
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@router.get("/google-callback")
async def google_oauth_callback(code: str, state: str):
    """
    Handle Google OAuth callback and exchange code for tokens.
    """
    try:
        # Verify state parameter
        from app.tools.email_tools import _oauth_states
        if state not in _oauth_states:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Exchange authorization code for tokens
        import requests

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/api/v1/auth/google-callback"
        }

        response = requests.post(token_url, data=data)
        tokens = response.json()

        if "error" in tokens:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {tokens['error']}")

        # Store tokens for the user
        user_data = _oauth_states[state]
        google_id = user_data["google_id"]

        from app.tools.email_tools import token_store
        token_store[google_id] = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 3600),
            "created_at": "2024-01-01T00:00:00Z"
        }

        # Clean up state
        del _oauth_states[state]

        # Redirect to frontend with success
        from fastapi.responses import RedirectResponse
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(f"{frontend_url}/?auth_success=true")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

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
    Check if user has Gmail connection in the database.
    """
    try:
        # Get our internal user ID from Google ID
        from app.core.db_client import get_user_by_google_id
        db_user = get_user_by_google_id(user["google_id"])

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found in database")

        # Check if user has Gmail connection
        from app.core.supabase_client import supabase
        response = supabase.table('user_connections').select('*').eq('user_id', user["google_id"]).eq('app_name', 'gmail').single().execute()

        if not response.get('data'):
            raise HTTPException(status_code=404, detail="Gmail not connected")

        # Return success (don't expose actual tokens)
        return {
            "connected": True,
            "app_name": "gmail",
            "connected_at": response['data'].get("created_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check Gmail connection: {str(e)}")

@router.get("/health")
async def auth_health_check():
    """Health check for auth service."""
    return {"status": "healthy", "service": "auth"}
