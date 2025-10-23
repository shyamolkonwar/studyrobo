import os
import json
import urllib.parse
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.tools.email_tools import token_store

router = APIRouter()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

@router.get("/google")
async def google_login():
    """
    Redirect user to Google OAuth 2.0 authorization page.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Construct the authorization URL
    redirect_uri = "http://localhost:3000/auth/google/callback"
    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote_plus(redirect_uri)}"
        f"&response_type=code"
        f"&scope={' '.join(scopes)}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return RedirectResponse(url=auth_url)

@router.get("/google/callback")
async def google_callback(code: Optional[str] = None, error: Optional[str] = None):
    """
    Handle Google OAuth callback and exchange code for tokens.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    try:
        # Exchange authorization code for tokens
        import requests
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:3000/auth/google/callback"
        }

        response = requests.post(token_url, data=data)
        token_data = response.json()

        if "error" in token_data:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_data['error']}")

        # Store tokens (in production, this should be encrypted and stored securely)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        # For demo purposes, store in memory with a simple user ID
        user_id = "default_user"
        token_store[user_id] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": token_data.get("expires_in", 3600),
            "created_at": "2024-01-01T00:00:00Z"  # Fixed timestamp for demo
        }

        return RedirectResponse(url=f"http://localhost:3000/auth/success?user_id={user_id}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")

@router.get("/tokens/{user_id}")
async def get_tokens(user_id: str):
    """
    Retrieve stored tokens for a user (for testing/demo purposes).

    Args:
        user_id (str): User identifier

    Returns:
        Dict[str, Any]: Token information
    """
    tokens = token_store.get(user_id)
    if not tokens:
        raise HTTPException(status_code=404, detail="Tokens not found for user")

    return {
        "user_id": user_id,
        "tokens": tokens,
        "status": "active"
    }

@router.delete("/tokens/{user_id}")
async def revoke_tokens(user_id: str):
    """
    Revoke and remove stored tokens for a user.

    Args:
        user_id (str): User identifier

    Returns:
        Dict[str, Any]: Revocation status
    """
    if user_id in token_store:
        del token_store[user_id]
        return {
            "message": f"Tokens revoked for user {user_id}",
            "status": "revoked"
        }
    else:
        raise HTTPException(status_code=404, detail="Tokens not found for user")

@router.get("/check/{user_id}")
async def check_auth_status(user_id: str):
    """
    Check authentication status for a user.

    Args:
        user_id (str): User identifier

    Returns:
        Dict[str, Any]: Authentication status
    """
    tokens = token_store.get(user_id)
    if not tokens:
        return {
            "authenticated": False,
            "user_id": user_id,
            "message": "No tokens found"
        }

    # In production, you would validate the token with Google here
    return {
        "authenticated": True,
        "user_id": user_id,
        "message": "Authentication valid"
    }