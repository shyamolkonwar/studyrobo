from typing import Dict, Any
from app.rag.supabase_retriever import search_documents

async def get_study_material(query: str, user_id: str = None) -> Dict[str, Any]:
    """
    Search for information about course materials, exam topics, and study guides.

    This tool searches through the uploaded study materials to find relevant information
    about the student's query. It can help with exam preparation, understanding
    course concepts, and finding specific information from textbooks and syllabi.

    Args:
        query (str): The student's question or topic they want to study
        user_id (str): The user's Google ID for personalized search (optional)

    Returns:
        Dict[str, Any]: Search results with context information
    """
    try:
        # Search for relevant documents with user filtering
        context = search_documents(query, match_count=4, google_id=user_id)

        return {
            "success": True,
            "context": context,
            "query": query,
            "message": f"Found relevant study materials for: {query}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "message": f"Error searching study materials: {str(e)}"
        }

# Tool definition for OpenAI function calling
get_study_material_tool = {
    "type": "function",
    "function": {
        "name": "get_study_material",
        "description": "Use this tool to find information about course materials, exam topics, and study guides. Perfect for when students ask about specific subjects, concepts, or need help with exam preparation.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The specific topic or question the student wants to study (e.g., 'bubble sort algorithm', 'midterm exam dates', 'computer science fundamentals')"
                }
            },
            "required": ["query"]
        }
    }
}
