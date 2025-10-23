import os
import json
import asyncio
from typing import Dict, Any, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
import aiofiles

# Simple in-memory storage for demo (in production, use a proper database)
token_store = {}

async def get_unread_emails(user_id: str = "default") -> Dict[str, Any]:
    """
    Fetch unread emails from Gmail using stored OAuth tokens.

    Args:
        user_id (str): User identifier (defaults to "default")

    Returns:
        Dict[str, Any]: Unread emails with metadata
    """
    try:
        # Check if user has stored OAuth token
        user_tokens = token_store.get(user_id)
        if not user_tokens:
            return {
                "success": False,
                "error": "User not authenticated. Please authenticate first.",
                "emails": [],
                "auth_required": True
            }

        # Create Gmail API client
        if 'refresh_token' in user_tokens and 'access_token' in user_tokens:
            creds = Credentials(
                token=user_tokens['access_token'],
                refresh_token=user_tokens['refresh_token'],
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
                maxResults=10
            ).execute()

            # Process messages
            emails = []
            if 'messages' in results:
                for message in results['messages'][:5]:  # Limit to 5 emails
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
                "user_id": user_id
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "emails": [],
                "message": f"Error fetching emails: {str(e)}"
            }

async def draft_email(to: str, subject: str, body: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Draft a new email using Gmail API.

    Args:
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content
        user_id (str): User identifier

    Returns:
        Dict[str, Any]: Draft creation result
    """
    try:
        # Check if user has stored OAuth token
        user_tokens = token_store.get(user_id)
        if not user_tokens:
            return {
                "success": False,
                "error": "User not authenticated. Please authenticate first.",
                "draft_id": None
            }

        # Create Gmail API client
        if 'refresh_token' in user_tokens and 'access_token' in user_tokens:
            creds = Credentials(
                token=user_tokens['access_token'],
                refresh_token=user_tokens['refresh_token'],
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
                "user_id": user_id
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "draft_id": None,
                "message": f"Error creating draft: {str(e)}"
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
        "description": "Fetch unread emails from Gmail. Returns emails with subject, sender, date, and priority information.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User identifier (defaults to 'default')",
                    "default": "default"
                }
            },
            "required": []
        }
    }
}

draft_email_tool = {
    "type": "function",
    "function": {
        "name": "draft_email",
        "description": "Draft a new email using Gmail API. Requires recipient, subject, and body.",
        "parameters": {
            "type": "object",
            "properties": {
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
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier (defaults to 'default')",
                    "default": "default"
                }
            },
            "required": ["to", "subject", "body"]
        }
    }
}