import os
from typing import List
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# Configuration
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "study_materials"

# Global variables for caching
_client = None
_collection = None
_embedding_model = None

def get_client():
    """Get or create ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return _client

def get_collection():
    """Get or create ChromaDB collection."""
    global _collection
    if _collection is None:
        client = get_client()
        try:
            _collection = client.get_collection(name=COLLECTION_NAME)
        except Exception as e:
            print(f"Error getting collection '{COLLECTION_NAME}': {e}")
            return None
    return _collection

def get_embedding_model():
    """Get or create embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

def search_documents(query: str, n_results: int = 3) -> str:
    """
    Search for relevant documents in ChromaDB.

    Args:
        query (str): The search query
        n_results (int): Number of results to return (default: 3)

    Returns:
        str: Formatted context block with relevant documents
    """
    try:
        collection = get_collection()
        if collection is None:
            return "No study materials database available. Please run the ingestion script first."

        # Get embedding model
        embedding_model = get_embedding_model()

        # Create query embedding
        query_embedding = embedding_model.encode(query)

        # Search in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )

        # Format results
        if not results['documents'] or not results['documents'][0]:
            return "No relevant study materials found for your query."

        context_parts = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            context_parts.append(f"Document {i+1}:\n{doc}\n")

        # Join all relevant documents
        context = "\n".join(context_parts)

        return f"Based on the following study materials:\n\n{context}\nPlease use this information to answer the user's question."

    except Exception as e:
        print(f"Error searching documents: {e}")
        return f"Error searching study materials: {str(e)}"

def test_search():
    """Test function to verify the search functionality."""
    test_queries = [
        "What is bubble sort?",
        "When is the midterm exam?",
        "What topics are covered in computer science 101?",
        "What is the time complexity of QuickSort?"
    ]

    print("Testing document search...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = search_documents(query)
        print(f"Result preview: {result[:200]}...")

if __name__ == "__main__":
    test_search()