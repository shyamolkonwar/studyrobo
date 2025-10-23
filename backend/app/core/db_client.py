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
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
    return None

def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Google ID"""
    query = "SELECT * FROM users WHERE google_id = %s"
    result = execute_query(query, (google_id,))
    return result[0] if result else None

def create_user(google_id: str, email: str, name: str) -> int:
    """Create a new user and return user_id"""
    query = "INSERT INTO users (google_id, email, name) VALUES (%s, %s, %s) RETURNING id"
    result = execute_query(query, (google_id, email, name))
    return result[0]['id'] if result else None

def get_messages(user_id: int) -> List[Dict[str, Any]]:
    """Get all messages for a user"""
    query = "SELECT role, content, created_at FROM messages WHERE user_id = %s ORDER BY created_at"
    return execute_query(query, (user_id,)) or []

def add_message(user_id: int, role: str, content: str):
    """Add a message for a user"""
    query = "INSERT INTO messages (user_id, role, content) VALUES (%s, %s, %s)"
    execute_query(query, (user_id, role, content), fetch=False)

def mark_attendance(user_id: int, course_name: str):
    """Mark attendance for a user"""
    query = "INSERT INTO attendance (user_id, course_name) VALUES (%s, %s)"
    execute_query(query, (user_id, course_name), fetch=False)

def insert_document(content: str, course_name: str, embedding: List[float]):
    """Insert a document with embedding"""
    query = "INSERT INTO documents (content, course_name, embedding) VALUES (%s, %s, %s)"
    execute_query(query, (content, course_name, embedding), fetch=False)

def search_documents(query_embedding: List[float], match_threshold: float = 0.75, match_count: int = 5) -> List[Dict[str, Any]]:
    """Search documents using vector similarity"""
    query = "SELECT id, content, 1 - (embedding <=> %s::vector) as similarity FROM documents WHERE 1 - (embedding <=> %s::vector) > %s ORDER BY similarity DESC LIMIT %s"
    return execute_query(query, (query_embedding, query_embedding, match_threshold, match_count)) or []

def clear_messages(user_id: int):
    """Clear all messages for a user"""
    query = "DELETE FROM messages WHERE user_id = %s"
    execute_query(query, (user_id,), fetch=False)

def verify_google_token(google_access_token: str) -> Optional[dict]:
    """
    Placeholder for Google token verification
    In production, verify with Google's API
    """
    try:
        # Placeholder - implement actual verification
        return {"valid": True, "user_id": "temp_user_id"}
    except Exception as e:
        print(f"Token verification error: {e}")
        return None
