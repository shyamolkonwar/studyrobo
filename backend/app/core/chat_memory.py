"""
Chat memory system using database
Stores and retrieves conversation history for persistent chat
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.db_client import get_messages, add_message as db_add_message, clear_messages

class ChatMemory:
    """
    Chat memory system that stores conversation history in database
    """

    def __init__(self):
        pass

    def add_message(self, user_id: int, role: str, content: str) -> bool:
        """
        Add a message to the conversation history.

        Args:
            user_id (int): The user's ID from database
            role (str): Either 'user' or 'ai'
            content (str): The message content

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db_add_message(user_id, role, content)
            return True
        except Exception as e:
            print(f"Error adding message: {e}")
            return False

    def get_conversation_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the conversation history for a user.

        Args:
            user_id (int): The user's ID from database
            limit (int): Maximum number of messages to retrieve (default: 50)

        Returns:
            List[Dict[str, Any]]: List of messages in chronological order
        """
        try:
            messages = get_messages(user_id)
            return messages[-limit:] if len(messages) > limit else messages
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
            return []

    def get_recent_messages(self, user_id: int, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent messages for context.

        Args:
            user_id (int): The user's ID from database
            count (int): Number of recent messages to retrieve (default: 10)

        Returns:
            List[Dict[str, Any]]: List of recent messages in chronological order
        """
        try:
            messages = get_messages(user_id)
            return messages[-count:] if len(messages) > count else messages
        except Exception as e:
            print(f"Error retrieving recent messages: {e}")
            return []

    def clear_conversation_history(self, user_id: int) -> bool:
        """
        Clear all conversation history for a user.

        Args:
            user_id (int): The user's ID from database

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            clear_messages(user_id)
            return True
        except Exception as e:
            print(f"Error clearing conversation history: {e}")
            return False

    def format_conversation_for_llm(self, user_id: int, limit: int = 20) -> str:
        """
        Format conversation history for inclusion in LLM context.

        Args:
            user_id (int): The user's ID from database
            limit (int): Maximum number of messages to include (default: 20)

        Returns:
            str: Formatted conversation history
        """
        messages = self.get_recent_messages(user_id, limit)

        if not messages:
            return "No previous conversation history."

        formatted_messages = []
        for message in messages:
            role = message['role'].upper()
            content = message['content']
            timestamp = message['created_at']

            formatted_messages.append(f"[{role}] ({timestamp}): {content}")

        return "\n".join(formatted_messages)

    def get_conversation_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get a summary of the conversation statistics.

        Args:
            user_id (int): The user's ID from database

        Returns:
            Dict[str, Any]: Conversation statistics
        """
        try:
            messages = get_messages(user_id)
            total_messages = len(messages)
            user_messages = len([m for m in messages if m['role'] == 'user'])
            ai_messages = len([m for m in messages if m['role'] == 'ai'])
            last_message_time = messages[-1]['created_at'] if messages else None

            return {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "last_message_time": last_message_time,
                "user_id": user_id
            }

        except Exception as e:
            return {
                "error": f"Error getting conversation summary: {str(e)}",
                "user_id": user_id
            }

# Global chat memory instance
chat_memory = ChatMemory()

# Helper functions for backward compatibility
def add_message(user_id: int, role: str, content: str) -> bool:
    """Add a message to chat history."""
    return chat_memory.add_message(user_id, role, content)

def get_conversation_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get conversation history for a user."""
    return chat_memory.get_conversation_history(user_id, limit)

def get_recent_messages(user_id: int, count: int = 10) -> List[Dict[str, Any]]:
    """Get recent messages for context."""
    return chat_memory.get_recent_messages(user_id, count)

def format_conversation_for_llm(user_id: int, limit: int = 20) -> str:
    """Format conversation for LLM context."""
    return chat_memory.format_conversation_for_llm(user_id, limit)
