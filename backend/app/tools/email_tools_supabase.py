"""
Email tools for Gmail API integration using Google OAuth tokens
Replaces service account authentication with OAuth token-based approach
"""

import os
import json
import asyncio
from typing import Dict, Any, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
import aiofiles

async def get_unread_emails(google_access_token: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Fetch unread emails from Gmail using Google OAuth access token.

    Args:
        google_access_token (str): Google OAuth access token from Supabase auth
        max_results (int): Maximum number of emails to fetch (default: 10)

    Returns:
        Dict[str, Any]: Unread emails with metadata
    """
    try:
        # Create credentials from the access token
        creds = Credentials(
            token=google_access_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )

        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Get unread messages
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=max_results
        ).execute()

        # Process messages
        emails = []
        if 'messages' in results:
            for message in results['messages'][:5]:  # Limit to 5 emails for readability
                # Get message details
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata'
                ).execute()

                # Extract headers
                headers = {}
                for header in msg.get('payload', {}).get('headers', []):
                    name = header.get('name', '').lower()
                    if name == 'subject':
                        headers['subject'] = header.get('value', '')
                    elif name == 'from':
                        headers['from'] = header.get('value', '')
                    elif name == 'date':
                        headers['date'] = header.get('value', '')

                emails.append({
                    'id': message['id'],
                    'snippet': msg.get('snippet', ''),
                    'subject': headers.get('subject', 'No Subject'),
                    'from': headers.get('from', 'Unknown'),
                    'date': headers.get('date', 'Unknown'),
                    'threadId': message.get('threadId', ''),
                    'labelIds': message.get('labelIds', []),
                    'is_important': 'IMPORTANT' in str(message.get('labelIds', []))
                })

        return {
            "success": True,
            "emails": emails,
            "total_count": len(results.get('messages', [])),
            "message": f"Found {len(emails)} unread emails",
            "fetched_at": "current_timestamp"  # You can add actual timestamp if needed
        }

    except Exception as e:
        error_message = str(e)

        # Check for common authentication errors
        if "invalid_grant" in error_message or "unauthorized" in error_message.lower():
            return {
                "success": False,
                "error": "Token expired or invalid. Please re-authenticate with Google.",
                "emails": [],
                "auth_required": True,
                "message": "Please log in again to access your Gmail"
            }
        else:
            return {
                "success": False,
                "error": error_message,
                "emails": [],
                "message": f"Error fetching emails: {error_message}"
            }

async def draft_email(google_access_token: str, to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Draft a new email using Gmail API with Google OAuth token.

    Args:
        google_access_token (str): Google OAuth access token from Supabase auth
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content

    Returns:
        Dict[str, Any]: Draft creation result
    """
    try:
        # Create credentials from the access token
        creds = Credentials(
            token=google_access_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/gmail.compose']
        )

        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)

        # Create email message
        message = {
            'raw': create_message(to, subject, body)
        }

        # Create draft
        draft = service.users().drafts().create(
            userId='me',
            body=message
        ).execute()

        return {
            "success": True,
            "draft_id": draft.get('id', ''),
            "message": f"Draft created: {subject}",
            "to": to,
            "subject": subject,
            "draft_url": f"https://mail.google.com/mail/u/0/#drafts/{draft.get('id', '')}"
        }

    except Exception as e:
        error_message = str(e)

        # Check for common authentication errors
        if "invalid_grant" in error_message or "unauthorized" in error_message.lower():
            return {
                "success": False,
                "error": "Token expired or invalid. Please re-authenticate with Google.",
                "draft_id": None,
                "message": "Please log in again to create email drafts"
            }
        else:
            return {
                "success": False,
                "error": error_message,
                "draft_id": None,
                "message": f"Error creating draft: {error_message}"
            }

def create_message(to: str, subject: str, body: str) -> str:
    """Create a raw email message for Gmail API."""
    from email.mime.text import MIMEText
    import base64

    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject

    # Encode the message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return raw

def get_email_categories(emails: List[Dict]) -> Dict[str, Any]:
    """
    Categorize emails based on content and headers.

    Args:
        emails (List[Dict]): List of email dictionaries

    Returns:
        Dict[str, Any]: Categorized email summary
    """
    try:
        categories = {
            'urgent': [],
            'academic': [],
            'promotions': [],
            'general': []
        }

        for email in emails:
            subject = email.get('subject', '').lower()
            from_addr = email.get('from', '').lower()
            snippet = email.get('snippet', '').lower()

            # Categorize based on keywords
            if any(keyword in subject for keyword in ['urgent', 'asap', 'important', 'deadline']):
                categories['urgent'].append(email)
            elif any(keyword in from_addr for keyword in ['university', 'professor', '教务', 'student']):
                categories['academic'].append(email)
            elif any(keyword in snippet for keyword in ['sale', 'discount', 'offer', 'promotion']):
                categories['promotions'].append(email)
            else:
                categories['general'].append(email)

        return {
            'success': True,
            'total_emails': len(emails),
            'categories': categories,
            'summary': {
                'urgent_count': len(categories['urgent']),
                'academic_count': len(categories['academic']),
                'promotion_count': len(categories['promotions']),
                'general_count': len(categories['general'])
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'categories': {}
        }

# Tool definitions for OpenAI function calling
get_unread_emails_tool = {
    "type": "function",
    "function": {
        "name": "get_unread_emails",
        "description": "Fetch unread emails from Gmail using the user's Google OAuth token. Returns emails with subject, sender, date, and priority information.",
        "parameters": {
            "type": "object",
            "properties": {
                "google_access_token": {
                    "type": "string",
                    "description": "The user's Google OAuth access token obtained from Supabase authentication"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of emails to fetch (default: 10)",
                    "default": 10
                }
            },
            "required": ["google_access_token"]
        }
    }
}

draft_email_tool = {
    "type": "function",
    "function": {
        "name": "draft_email",
        "description": "Draft a new email using Gmail API with the user's Google OAuth token. Requires recipient, subject, and body.",
        "parameters": {
            "type": "object",
            "properties": {
                "google_access_token": {
                    "type": "string",
                    "description": "The user's Google OAuth access token obtained from Supabase authentication"
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                }
            },
            "required": ["google_access_token", "to", "subject", "body"]
        }
    }
}