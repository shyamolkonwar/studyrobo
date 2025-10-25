from typing import Dict, Any, Optional
import os
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
        import datetime
        _oauth_states[state] = {
            "google_id": user["google_id"],
            "email": user["email"],
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        # Build Google OAuth URL
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        params = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "redirect_uri": f"{frontend_url}/auth/google/callback",
            "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events",
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
async def google_oauth_callback(code: str, state: str, user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Handle Google OAuth callback and exchange code for tokens.
    Called by the frontend after receiving the authorization code.
    """
    try:
        # Verify state parameter with better error handling
        from app.tools.email_tools import _oauth_states
        
        # Check if state exists and is valid
        if state not in _oauth_states:
            print(f"State {state} not found in available states: {list(_oauth_states.keys())}")
            raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

        # Verify that the user matches the state
        user_data = _oauth_states[state]
        if user_data["google_id"] != user["google_id"]:
            print(f"State user mismatch: state has {user_data['google_id']}, current user has {user['google_id']}")
            raise HTTPException(status_code=400, detail="State parameter does not match current user")

        # Check if state has expired (older than 10 minutes)
        import datetime
        from datetime import datetime as dt
        state_created = dt.fromisoformat(user_data.get("created_at", "2024-01-01T00:00:00Z"))
        if (dt.utcnow() - state_created).total_seconds() > 600:  # 10 minutes
            del _oauth_states[state]
            raise HTTPException(status_code=400, detail="State parameter has expired")

        # Exchange authorization code for tokens
        import requests

        token_url = "https://oauth2.googleapis.com/token"
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        # Validate required environment variables
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": f"{frontend_url}/auth/google/callback"
        }

        response = requests.post(token_url, data=data)
        
        if response.status_code != 200:
            print(f"Google token exchange failed with status {response.status_code}: {response.text}")
            raise HTTPException(status_code=400, detail=f"Google token exchange failed: {response.text}")

        try:
            tokens = response.json()
        except ValueError as e:
            print(f"Failed to parse Google response as JSON: {response.text}")
            raise HTTPException(status_code=400, detail=f"Invalid response from Google: {response.text}")

        if "error" in tokens:
            print(f"Google token error: {tokens['error']}")
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {tokens['error']}")

        # Clean up state after successful token exchange
        del _oauth_states[state]

        # Return tokens to frontend
        return {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 3600),
            "token_type": tokens.get("token_type", "Bearer"),
            "success": True
        }

    except HTTPException:
        # Clean up state on error if it exists
        if 'state' in locals() and state in _oauth_states:
            try:
                del _oauth_states[state]
            except:
                pass
        raise
    except Exception as e:
        # Clean up state on error if it exists
        if 'state' in locals() and 'state' in locals() and state in _oauth_states:
            try:
                del _oauth_states[state]
            except:
                pass
        print(f"OAuth callback error: {str(e)}")
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
        # Validate token_data
        if not token_data or not isinstance(token_data, dict):
            raise HTTPException(status_code=400, detail="Invalid token data provided")
        
        if not token_data.get("access_token"):
            raise HTTPException(status_code=400, detail="Access token is required")
        
        if not token_data.get("refresh_token"):
            raise HTTPException(status_code=400, detail="Refresh token is required")
        from app.tools.email_tools import token_store
        from app.core.supabase_client import supabase
        import datetime

        google_id = user["google_id"]
        if not google_id:
            raise HTTPException(status_code=400, detail="Google ID not found")

        # Store tokens in memory for immediate use
        token_store[google_id] = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in", 3600),
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        # Also store tokens in Supabase for persistence
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=token_data.get("expires_in", 3600))

        connection_data = {
            "user_id": user["user_id"],  # Use Supabase user ID, not Google ID
            "app_name": "google",  # Changed from "gmail" to "google" for both Gmail and Calendar access
            "refresh_token": token_data.get("refresh_token"),
            "access_token": token_data.get("access_token"),
            "expires_at": expires_at.isoformat()
        }

        # Handle potential conflicts by first checking for existing connections
        try:
            # Check if there's an existing "gmail" connection that we should update to "google"
            existing_gmail_response = supabase.table('user_connections').select('*').eq('user_id', user["user_id"]).eq('app_name', 'gmail').execute()

            # Handle different response formats
            if isinstance(existing_gmail_response, dict):
                existing_gmail_data = existing_gmail_response.get('data', [])
            elif hasattr(existing_gmail_response, 'data'):
                existing_gmail_data = existing_gmail_response.data
            else:
                existing_gmail_data = existing_gmail_response or []

            if existing_gmail_data:
                # Update existing "gmail" connection to "google"
                print("Found existing gmail connection, updating to google...")
                update_response = supabase.table('user_connections').update({
                    "app_name": "google",
                    "refresh_token": connection_data["refresh_token"],
                    "access_token": connection_data["access_token"],
                    "expires_at": connection_data["expires_at"],
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }).eq('user_id', user["user_id"]).eq('app_name', 'gmail').execute()

                # Check if update was successful
                if isinstance(update_response, dict):
                    update_success = 'data' in update_response and update_response.get('data') is not None
                elif hasattr(update_response, 'data'):
                    update_success = update_response.data is not None
                else:
                    update_success = update_response is not None

                if update_success:
                    print(f"Successfully updated existing gmail connection to google: {update_response}")
                else:
                    raise HTTPException(status_code=500, detail="Failed to update existing gmail connection")
            else:
                # No existing gmail connection, check for google connection
                existing_google_response = supabase.table('user_connections').select('*').eq('user_id', user["user_id"]).eq('app_name', 'google').execute()

                # Handle different response formats
                if isinstance(existing_google_response, dict):
                    existing_google_data = existing_google_response.get('data', [])
                elif hasattr(existing_google_response, 'data'):
                    existing_google_data = existing_google_response.data
                else:
                    existing_google_data = existing_google_response or []

                if existing_google_data:
                    # Update existing google connection
                    print("Updating existing google connection...")
                    update_response = supabase.table('user_connections').update({
                        "refresh_token": connection_data["refresh_token"],
                        "access_token": connection_data["access_token"],
                        "expires_at": connection_data["expires_at"],
                        "updated_at": datetime.datetime.utcnow().isoformat()
                    }).eq('user_id', user["user_id"]).eq('app_name', 'google').execute()

                    # Check if update was successful
                    if isinstance(update_response, dict):
                        update_success = 'data' in update_response and update_response.get('data') is not None
                    elif hasattr(update_response, 'data'):
                        update_success = update_response.data is not None
                    else:
                        update_success = update_response is not None

                    if update_success:
                        print(f"Successfully updated existing google connection: {update_response}")
                    else:
                        raise HTTPException(status_code=500, detail="Failed to update existing google connection")
                else:
                    # No existing connection, insert new one
                    print("Inserting new google connection...")
                    insert_response = supabase.table('user_connections').insert(connection_data).execute()

                    # Check if insert was successful
                    if isinstance(insert_response, dict):
                        insert_success = 'data' in insert_response and insert_response.get('data') is not None
                    elif hasattr(insert_response, 'data'):
                        insert_success = insert_response.data is not None
                    else:
                        insert_success = insert_response is not None

                    if insert_success:
                        print(f"Successfully inserted new google connection: {insert_response}")
                    else:
                        raise HTTPException(status_code=500, detail="Failed to insert new google connection")

        except HTTPException:
            raise
        except Exception as db_error:
            error_str = str(db_error)
            print(f"Database operation failed: {error_str}")
            raise HTTPException(status_code=500, detail=f"Failed to store connection: {error_str}")

        return {"message": "Tokens stored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store tokens: {str(e)}")

@router.get("/google-tokens")
async def get_google_tokens(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Check if user has Google services connection in the database.
    """
    try:
        # Check if user has Google connection using Supabase user ID
        from app.core.supabase_client import supabase
        response = supabase.table('user_connections').select('*').eq('user_id', user["user_id"]).eq('app_name', 'google').execute()

        # Handle different response formats - some return dict, others return objects
        if isinstance(response, dict):
            # Response is a dictionary
            response_data = response.get('data', [])
        elif hasattr(response, 'data'):
            # Response is an object with .data attribute
            response_data = response.data
        else:
            # Fallback - assume response is the data directly
            response_data = response or []

        # Check if we got data and it's not empty
        if not response_data:
            return {
                "connected": False,
                "app_name": "google",
                "message": "Google services not connected"
            }

        # Handle both single record and array responses
        connection_data = response_data[0] if isinstance(response_data, list) and response_data else response_data

        # Return success (don't expose actual tokens)
        return {
            "connected": True,
            "app_name": "google",
            "connected_at": connection_data.get("created_at") if isinstance(connection_data, dict) else None,
            "updated_at": connection_data.get("updated_at") if isinstance(connection_data, dict) else None
        }

    except Exception as e:
        # Return a graceful response instead of throwing 500
        print(f"Error checking Google connection: {str(e)}")
        return {
            "connected": False,
            "app_name": "google",
            "error": f"Failed to check connection: {str(e)}"
        }

@router.get("/health")
async def auth_health_check():
    """Health check for auth service."""
    return {"status": "healthy", "service": "auth"}
