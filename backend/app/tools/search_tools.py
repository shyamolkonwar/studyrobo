from typing import Dict, Any
from app.core.db_client import search_documents as db_search_documents
import openai
from app.core.config import settings

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
        # Check if OpenAI API key is available
        if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "query": query,
                "message": "RAG search is not available - OpenAI API key not configured"
            }

        # Create query embedding using OpenAI
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding

        # Search using database function with user filtering
        matches = db_search_documents(query_embedding, match_threshold=0.3, match_count=4, google_id=user_id)

        if not matches or len(matches) == 0:
            return {
                "success": True,
                "context": "No relevant study materials found for your query.",
                "query": query,
                "message": f"No relevant study materials found for: {query}"
            }

        # Format results for LLM consumption
        context_parts = []
        for match in matches:
            content = match.get('content', '')[:800]  # Limit content length
            similarity = match.get('similarity', 0)
            file_name = match.get('file_name', 'Unknown document')
            is_global = match.get('is_global', False)

            source_type = "Course Material" if is_global else "Your Document"
            context_parts.append(f"From {source_type} ({file_name}) - Relevance: {similarity:.3f}:\n{content}\n")

        context = "\n".join(context_parts)

        return {
            "success": True,
            "context": context,
            "query": query,
            "message": f"Found {len(matches)} relevant study materials for: {query}"
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
