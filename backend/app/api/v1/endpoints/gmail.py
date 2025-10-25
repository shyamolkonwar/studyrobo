from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.api.v1.endpoints.auth.google import verify_supabase_token
from app.tools.email_tools_supabase import check_gmail_connection

router = APIRouter()

@router.get("/info")
async def get_gmail_info(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get Gmail connection information for the user.
    """
    try:
        # Check if user has Gmail connected
        connection_info = check_gmail_connection(user["google_id"])

        if not connection_info["connected"]:
            raise HTTPException(status_code=404, detail="Gmail not connected")

        return {
            "connected": True,
            "email": connection_info.get("email"),
            "connected_at": connection_info.get("connected_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Gmail info: {str(e)}")

@router.get("/health")
async def gmail_health_check():
    """Health check for Gmail service."""
    return {"status": "healthy", "service": "gmail"}
