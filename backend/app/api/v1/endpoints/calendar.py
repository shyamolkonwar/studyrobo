"""
Calendar API endpoints for Google Calendar integration
Provides endpoints for fetching upcoming events and managing calendar data
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.api.v1.endpoints.auth.google import verify_supabase_token
from app.tools.calendar_tools_supabase import get_upcoming_events, check_google_connection

router = APIRouter()

@router.get("/agenda")
async def get_agenda(
    user: Dict[str, Any] = Depends(verify_supabase_token)
) -> Dict[str, Any]:
    """
    Get user's upcoming calendar events for the dashboard agenda widget.

    This endpoint fetches the next 10 upcoming events and formats them
    for display in the dashboard "Today's Schedule" widget.
    """
    try:
        # Get user information from verified token
        google_id = user.get("google_id")

        if not google_id:
            raise HTTPException(
                status_code=400,
                detail="Google ID not found. Please ensure you logged in with Google."
            )

        # Check if user has Google connected
        connection_status = check_google_connection(google_id)
        if not connection_status.get("connected"):
            return {
                "events": [],
                "connected": False,
                "message": "Google Calendar not connected"
            }

        # Fetch upcoming events
        result = await get_upcoming_events(google_id, max_results=10)

        if not result.get("success"):
            return {
                "events": [],
                "connected": True,
                "error": result.get("error", "Failed to fetch events")
            }

        # Format events for dashboard display
        events = result.get("events", [])
        formatted_events = []

        for event in events[:6]:  # Limit to 6 for dashboard display
            # Parse the start time for display
            start_time = event.get("start", "")
            display_time = "TBD"

            if start_time:
                try:
                    # Handle ISO format (2023-10-25T14:30:00Z)
                    if "T" in start_time:
                        # Parse datetime
                        from datetime import datetime
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        display_time = dt.strftime("%I:%M %p").lstrip('0')  # Remove leading zero
                    else:
                        # All-day event
                        display_time = "All Day"
                except:
                    display_time = "TBD"

            formatted_events.append({
                "id": event.get("id", ""),
                "title": event.get("summary", "No Title"),
                "time": display_time,
                "location": event.get("location", ""),
                "description": event.get("description", ""),
                "is_all_day": event.get("is_all_day", False),
                "htmlLink": event.get("htmlLink", "")
            })

        return {
            "events": formatted_events,
            "connected": True,
            "total_count": len(events),
            "message": f"Found {len(formatted_events)} upcoming events"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching agenda: {str(e)}"
        )

@router.get("/calendar/status")
async def get_calendar_status(
    user: Dict[str, Any] = Depends(verify_supabase_token)
) -> Dict[str, Any]:
    """
    Check the status of user's Google Calendar connection.
    """
    try:
        google_id = user.get("google_id")

        if not google_id:
            return {
                "connected": False,
                "message": "User not authenticated with Google"
            }

        connection_status = check_google_connection(google_id)
        return connection_status

    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "message": "Error checking calendar connection"
        }
