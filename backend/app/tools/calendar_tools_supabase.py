"""
Calendar tools for Google Calendar API integration using Google OAuth tokens
Provides functionality to fetch upcoming events and create new calendar events
"""

import os
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
import requests

async def get_upcoming_events(user_id: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Fetch upcoming calendar events from Google Calendar using stored refresh token.

    Args:
        user_id (str): User ID (Google ID UUID) to look up stored tokens
        max_results (int): Maximum number of events to fetch (default: 10)

    Returns:
        Dict[str, Any]: Upcoming events with metadata
    """
    try:
        # Get Supabase client to query user_connections table
        from app.core.supabase_client import supabase

        # Query the user's Google connection using Google ID (UUID)
        response = supabase.table('user_connections').select('*').eq('user_id', user_id).eq('app_name', 'google').single().execute()

        if not response.get('data'):
            return {
                "success": False,
                "error": "Google not connected",
                "message": "Please connect your Google account first to access calendar features.",
                "events": [],
                "auth_required": True
            }

        connection = response['data']

        # Get the refresh token (simplified version - in production this would be decrypted)
        refresh_token = connection['refresh_token']

        # Exchange refresh token for access token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        token_response = requests.post(token_url, data=data)
        token_data = token_response.json()

        if "error" in token_data:
            return {
                "success": False,
                "error": f"Token refresh failed: {token_data['error']}",
                "message": "Failed to refresh Google access token. Please reconnect your account.",
                "events": [],
                "auth_required": True
            }

        access_token = token_data["access_token"]

        # Create credentials from the access token
        creds = Credentials(
            token=access_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )

        # Build Calendar service
        service = build('calendar', 'v3', credentials=creds)

        # Get upcoming events
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = []
        for event in events_result.get('items', []):
            # Parse start and end times
            start = event.get('start', {})
            end = event.get('end', {})

            # Handle both dateTime and date formats
            if 'dateTime' in start:
                start_time = start['dateTime']
                end_time = end['dateTime']
            else:
                # All-day event
                start_time = start.get('date', '')
                end_time = end.get('date', '')

            events.append({
                'id': event.get('id', ''),
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': start_time,
                'end': end_time,
                'location': event.get('location', ''),
                'status': event.get('status', ''),
                'htmlLink': event.get('htmlLink', ''),
                'is_all_day': 'dateTime' not in start
            })

        return {
            "success": True,
            "events": events,
            "total_count": len(events),
            "message": f"Found {len(events)} upcoming events",
            "fetched_at": now.isoformat()
        }

    except Exception as e:
        error_message = str(e)

        # Check for common authentication errors
        if "invalid_grant" in error_message or "unauthorized" in error_message.lower():
            return {
                "success": False,
                "error": "Token expired or invalid. Please re-authenticate with Google.",
                "events": [],
                "auth_required": True,
                "message": "Please log in again to access your calendar"
            }
        else:
            return {
                "success": False,
                "error": error_message,
                "events": [],
                "message": f"Error fetching calendar events: {error_message}"
            }

async def create_calendar_event(user_id: str, title: str, start_time: str, end_time: str, description: str = "", location: str = "") -> Dict[str, Any]:
    """
    Create a new calendar event using Google Calendar API with stored refresh token.

    Args:
        user_id (str): User ID (Google ID UUID) to look up stored tokens
        title (str): Event title
        start_time (str): Start time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
        end_time (str): End time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
        description (str): Event description (optional)
        location (str): Event location (optional)

    Returns:
        Dict[str, Any]: Event creation result
    """
    try:
        # Get Supabase client to query user_connections table
        from app.core.supabase_client import supabase

        # Query the user's Google connection using Google ID (UUID)
        response = supabase.table('user_connections').select('*').eq('user_id', user_id).eq('app_name', 'google').single().execute()

        if not response.get('data'):
            return {
                "success": False,
                "error": "Google not connected",
                "message": "Please connect your Google account first to create calendar events.",
                "auth_required": True
            }

        connection = response['data']

        # Get the refresh token
        refresh_token = connection['refresh_token']

        # Exchange refresh token for access token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        token_response = requests.post(token_url, data=data)
        token_data = token_response.json()

        if "error" in token_data:
            return {
                "success": False,
                "error": f"Token refresh failed: {token_data['error']}",
                "message": "Failed to refresh Google access token. Please reconnect your account.",
                "auth_required": True
            }

        access_token = token_data["access_token"]

        # Create credentials from the access token
        creds = Credentials(
            token=access_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/calendar.events']
        )

        # Build Calendar service
        service = build('calendar', 'v3', credentials=creds)

        # Create event body
        event_body = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',  # You might want to get user's timezone from profile
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        # Create the event
        created_event = service.events().insert(
            calendarId='primary',
            body=event_body
        ).execute()

        return {
            "success": True,
            "event_id": created_event.get('id', ''),
            "html_link": created_event.get('htmlLink', ''),
            "message": f"Event '{title}' has been created successfully.",
            "event_details": {
                "title": title,
                "start": start_time,
                "end": end_time,
                "description": description,
                "location": location
            }
        }

    except Exception as e:
        error_message = str(e)

        # Check for common authentication errors
        if "invalid_grant" in error_message or "unauthorized" in error_message.lower():
            return {
                "success": False,
                "error": "Token expired or invalid. Please re-authenticate with Google.",
                "message": "Please log in again to create calendar events",
                "auth_required": True
            }
        else:
            return {
                "success": False,
                "error": error_message,
                "message": f"Error creating calendar event: {error_message}"
            }

def check_google_connection(user_id: str) -> Dict[str, Any]:
    """
    Check if a user has Google connected for calendar access.

    Args:
        user_id (str): User ID (Google ID UUID)

    Returns:
        Dict[str, Any]: Connection status
    """
    try:
        # Get Supabase client to query user_connections table
        from app.core.supabase_client import supabase

        # Query the user's Google connection using Google ID (UUID)
        response = supabase.table('user_connections').select('*').eq('user_id', user_id).eq('app_name', 'google').single().execute()

        if not response.get('data'):
            return {
                "connected": False,
                "message": "Google not connected"
            }

        connection = response['data']

        return {
            "connected": True,
            "email": connection.get('email'),
            "connected_at": connection.get('created_at'),
            "message": "Google connected (Calendar & Gmail access)"
        }

    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "message": "Error checking Google connection"
        }

# Tool definitions for OpenAI function calling
get_upcoming_events_tool = {
    "type": "function",
    "function": {
        "name": "get_upcoming_events",
        "description": "Fetch upcoming calendar events from the user's Google Calendar. Returns events with title, time, location, and other details.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of events to fetch (default: 10)",
                    "default": 10
                }
            },
            "required": []
        }
    }
}

create_calendar_event_tool = {
    "type": "function",
    "function": {
        "name": "create_calendar_event",
        "description": "Create a new event in the user's Google Calendar. Requires title, start time, and end time in ISO 8601 format.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Event title or summary"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
                },
                "description": {
                    "type": "string",
                    "description": "Event description (optional)",
                    "default": ""
                },
                "location": {
                    "type": "string",
                    "description": "Event location (optional)",
                    "default": ""
                }
            },
            "required": ["title", "start_time", "end_time"]
        }
    }
}
