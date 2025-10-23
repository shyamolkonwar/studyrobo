"""
Database-based RAG retriever
Uses PostgreSQL vector database
"""

import os
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.db_client import search_documents as db_search_documents, insert_document

# Configuration
# Note: Using OpenAI's embedding dimension (1536) - adjust if using different model
EMBEDDING_DIMENSION = 1536

# Global variables for caching
_embedding_model = None

def get_embedding_model():
    """Get or create embedding model."""
    global _embedding_model
    if _embedding_model is None:
        # Note: Using a model that produces 1536-dimensional embeddings to match OpenAI
        # You might want to use OpenAI's embeddings API for consistency
        _embedding_model = SentenceTransformer('all-mpnet-base-v2')  # This produces 768-dim vectors
        # For production, consider using OpenAI's embedding API:
        # from openai import OpenAI
        # client = OpenAI()
        # def get_embedding(text):
        #     return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding
    return _embedding_model

def search_documents(query: str, match_threshold: float = 0.75, match_count: int = 5) -> str:
    """
    Search for relevant documents in database using vector similarity.

    Args:
        query (str): The search query
        match_threshold (float): Similarity threshold for matches (default: 0.75)
        match_count (int): Number of results to return (default: 5)

    Returns:
        str: Formatted context block with relevant documents
    """
    try:
        # Get embedding model
        embedding_model = get_embedding_model()

        # Create query embedding
        query_embedding = embedding_model.encode(query)

        # Pad or truncate embedding to match expected dimension (1536)
        if len(query_embedding) < EMBEDDING_DIMENSION:
            # Pad with zeros
            query_embedding = np.pad(query_embedding, (0, EMBEDDING_DIMENSION - len(query_embedding)))
        elif len(query_embedding) > EMBEDDING_DIMENSION:
            # Truncate
            query_embedding = query_embedding[:EMBEDDING_DIMENSION]

        # Search using database function
        try:
            matches = db_search_documents(query_embedding.tolist(), match_threshold, match_count)
        except Exception as e:
            print(f"Error searching documents: {e}")
            return "Error searching study materials: Vector search function not available. Please ensure the database setup script has been run."

        # Format results
        if not matches or len(matches) == 0:
            return "No relevant study materials found for your query."

        context_parts = []
        for i, match in enumerate(matches):
            content = match.get('content', '')
            similarity = match.get('similarity', 0)
            context_parts.append(f"Document {i+1} (Similarity: {similarity:.3f}):\n{content}\n")

        # Join all relevant documents
        context = "\n".join(context_parts)

        return f"Based on the following study materials:\n\n{context}\nPlease use this information to answer the user's question."

    except Exception as e:
        print(f"Error searching documents: {e}")
        return f"Error searching study materials: {str(e)}"

def add_document(content: str, course_name: str = "General") -> bool:
    """
    Add a document to the vector database.

    Args:
        content (str): The document content
        course_name (str): The course name for categorization

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        embedding_model = get_embedding_model()

        # Create embedding
        embedding = embedding_model.encode(content)

        # Pad or truncate embedding to match expected dimension
        if len(embedding) < EMBEDDING_DIMENSION:
            embedding = np.pad(embedding, (0, EMBEDDING_DIMENSION - len(embedding)))
        elif len(embedding) > EMBEDDING_DIMENSION:
            embedding = embedding[:EMBEDDING_DIMENSION]

        # Insert document
        insert_document(content, course_name, embedding.tolist())

        return True

    except Exception as e:
        print(f"Error adding document: {e}")
        return False

def test_search():
    """Test function to verify the search functionality."""
    test_queries = [
        "What is bubble sort?",
        "When is the midterm exam?",
        "What topics are covered in computer science 101?",
        "What is the time complexity of QuickSort?"
    ]

    print("Testing Supabase document search...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = search_documents(query)
        print(f"Result preview: {result[:200]}...")

if __name__ == "__main__":
    test_search()
