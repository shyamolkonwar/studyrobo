"""
Database client configuration for StudyRobo
Uses PostgreSQL with psycopg2 for all database operations
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    raise ValueError("Missing DATABASE_URL. Please set DATABASE_URL in your .env file.")

@contextmanager
def get_db_connection():
    """Get a database connection"""
    conn = psycopg2.connect(database_url)
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query: str, params: tuple = None, fetch: bool = True) -> Optional[List[Dict[str, Any]]]:
    """Execute a query and optionally fetch results"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            result = None
            if fetch:
                result = [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return result
    return None

def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Google ID"""
    query = "SELECT * FROM users WHERE google_id = %s"
    result = execute_query(query, (google_id,))
    return result[0] if result else None

def create_user(google_id: str, email: str, name: str) -> int:
    """Create a new user and return user_id"""
    query = "INSERT INTO users (google_id, email, name) VALUES (%s, %s, %s) RETURNING id"
    result = execute_query(query, (google_id, email, name), fetch=False)
    return result[0]['id'] if result else None

def get_messages(user_id: int) -> List[Dict[str, Any]]:
    """Get all messages for a user (legacy function for compatibility)"""
    query = "SELECT role, content, created_at FROM messages WHERE user_id = %s ORDER BY created_at"
    return execute_query(query, (user_id,)) or []

def get_messages_by_conversation(conversation_id: str, google_id: str = None) -> List[Dict[str, Any]]:
    """Get all messages for a specific conversation, optionally filtered by user ownership"""
    if google_id:
        # Check ownership and get messages
        query = """
        SELECT m.id, m.role, m.content, m.created_at::text as created_at
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE m.conversation_id = %s AND u.google_id = %s
        ORDER BY m.created_at
        """
        return execute_query(query, (conversation_id, google_id)) or []
    else:
        # Legacy behavior - get messages without ownership check
        query = "SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at"
        return execute_query(query, (conversation_id,)) or []

def add_message(user_id: int, role: str, content: str):
    """Add a message for a user (legacy function for compatibility)"""
    query = "INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)"
    execute_query(query, (user_id, role, content), fetch=False)

def add_message_to_conversation(conversation_id: str, role: str, content: str):
    """Add a message to a specific conversation"""
    # First get user_id from conversation
    user_query = "SELECT user_id FROM conversations WHERE id = %s"
    result = execute_query(user_query, (conversation_id,))
    if not result:
        raise ValueError(f"Conversation {conversation_id} not found")

    user_id = result[0]['user_id']
    
    # Validate that user_id is an integer (not a Google ID string)
    if not isinstance(user_id, int):
        # Try to convert to int, if it fails, we need to look up the correct user_id
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            # This might be a Google ID, try to find the corresponding user
            google_id = str(user_id)
            user_lookup = execute_query("SELECT id FROM users WHERE google_id = %s", (google_id,))
            if user_lookup:
                user_id = user_lookup[0]['id']
            else:
                raise ValueError(f"Invalid user_id in conversation {conversation_id}: {user_id}")
    
    query = "INSERT INTO messages (conversation_id, user_id, role, content) VALUES (%s, %s, %s, %s)"
    execute_query(query, (conversation_id, user_id, role, content), fetch=False)

def mark_attendance(user_id: int, course_name: str):
    """Mark attendance for a user"""
    query = "INSERT INTO attendance (user_id, course_name) VALUES (%s, %s)"
    execute_query(query, (user_id, course_name), fetch=False)

def insert_document(content: str, course_name: str, embedding: List[float]):
    """Insert a document with embedding"""
    query = "INSERT INTO documents (content, course_name, embedding) VALUES (%s, %s, %s)"
    execute_query(query, (content, course_name, embedding), fetch=False)

def search_documents(query_embedding: List[float], match_threshold: float = 0.3, match_count: int = 4, google_id: str = None) -> List[Dict[str, Any]]:
    """Search documents using direct SQL queries with user filtering"""
    try:
        if google_id:
            # Get user_id from google_id
            user_query = "SELECT id, course_name FROM users WHERE google_id = %s"
            user_result = execute_query(user_query, (google_id,))
            if not user_result:
                return []

            user_id = user_result[0]['id']
            user_course = user_result[0]['course_name']

            # Search with user filtering
            query = """
            SELECT
                id,
                content,
                1 - (embedding <=> %s::vector) as similarity,
                course_name,
                original_file_name as file_name,
                file_type,
                (user_id IS NULL) as is_global
            FROM documents
            WHERE 1 - (embedding <=> %s::vector) > %s
            AND (
                user_id = %s
                OR (user_id IS NULL AND course_name = %s)
                OR (user_id IS NULL AND course_name IS NULL)
            )
            ORDER BY similarity DESC
            LIMIT %s
            """
            return execute_query(query, (query_embedding, query_embedding, match_threshold, user_id, user_course, match_count)) or []
        else:
            # Fallback for no user context - search all documents
            query = """
            SELECT
                id,
                content,
                1 - (embedding <=> %s::vector) as similarity,
                course_name,
                original_file_name as file_name,
                file_type,
                (user_id IS NULL) as is_global
            FROM documents
            WHERE 1 - (embedding <=> %s::vector) > %s
            ORDER BY similarity DESC
            LIMIT %s
            """
            return execute_query(query, (query_embedding, query_embedding, match_threshold, match_count)) or []
    except Exception as e:
        print(f"Error in search_documents: {e}")
        return []

def clear_messages(user_id: int):
    """Clear all messages for a user"""
    query = "DELETE FROM messages WHERE user_id = %s"
    execute_query(query, (user_id,), fetch=False)

# Conversation management functions
def create_conversation(google_id: str, title: str = "New Chat") -> str:
    """Create a new conversation for a user and return the conversation ID"""
    print(f"DEBUG: create_conversation called with google_id: {google_id}, title: {title}")

    # First get user_id from google_id
    user_query = "SELECT id FROM users WHERE google_id = %s"
    print(f"DEBUG: Executing user lookup query: {user_query} with param: {google_id}")
    result = execute_query(user_query, (google_id,))
    print(f"DEBUG: User lookup result: {result}")

    if not result:
        print(f"DEBUG: No user found for Google ID: {google_id}")
        raise ValueError(f"User not found for Google ID: {google_id}")

    user_id = result[0]['id']
    print(f"DEBUG: Found user_id: {user_id}")

    # Create conversation
    conv_query = "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING id"
    print(f"DEBUG: Executing conversation insert query: {conv_query} with params: ({user_id}, {title})")
    result = execute_query(conv_query, (user_id, title))
    print(f"DEBUG: Conversation insert result: {result}")

    conversation_id = result[0]['id'] if result else None
    print(f"DEBUG: Returning conversation_id: {conversation_id}")
    return conversation_id

def get_user_conversations(google_id: str) -> List[Dict[str, Any]]:
    """Get all conversations for a user"""
    print(f"DEBUG: get_user_conversations called with google_id: {google_id}")

    query = """
    SELECT c.id, c.title, c.created_at::text as created_at,
           COUNT(m.id) as message_count
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    JOIN users u ON c.user_id = u.id
    WHERE u.google_id = %s
    GROUP BY c.id, c.title, c.created_at
    ORDER BY c.created_at DESC
    """
    print(f"DEBUG: Executing conversations query: {query} with param: {google_id}")
    result = execute_query(query, (google_id,)) or []
    print(f"DEBUG: Conversations query result: {result}")
    return result

def delete_conversation(conversation_id: str, google_id: str):
    """Delete a conversation and all its messages"""
    # Verify user owns the conversation
    verify_query = """
    SELECT 1 FROM conversations c
    JOIN users u ON c.user_id = u.id
    WHERE c.id = %s AND u.google_id = %s
    """
    result = execute_query(verify_query, (conversation_id, google_id))
    if not result:
        raise ValueError("Conversation not found or access denied")

    # Delete messages first, then conversation
    delete_messages_query = "DELETE FROM messages WHERE conversation_id = %s"
    delete_conv_query = "DELETE FROM conversations WHERE id = %s"

    execute_query(delete_messages_query, (conversation_id,), fetch=False)
    execute_query(delete_conv_query, (conversation_id,), fetch=False)

def update_conversation_title(conversation_id: str, google_id: str, title: str):
    """Update conversation title"""
    # Verify user owns the conversation
    verify_query = """
    SELECT 1 FROM conversations c
    JOIN users u ON c.user_id = u.id
    WHERE c.id = %s AND u.google_id = %s
    """
    result = execute_query(verify_query, (conversation_id, google_id))
    if not result:
        raise ValueError("Conversation not found or access denied")

    update_query = "UPDATE conversations SET title = %s WHERE id = %s"
    execute_query(update_query, (title, conversation_id), fetch=False)

def verify_google_token(google_access_token: str) -> Optional[dict]:
    """
    Verify Google OAuth token with Google's API
    In production, this validates the token and extracts user information
    """
    try:
        import requests

        # Verify token with Google's API
        response = requests.get(
            f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={google_access_token}"
        )

        if response.status_code == 200:
            user_data = response.json()
            return {
                "valid": True,
                "user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name")
            }
        else:
            return {"valid": False, "error": "Invalid token"}

    except Exception as e:
        print(f"Token verification error: {e}")
        return {"valid": False, "error": str(e)}
