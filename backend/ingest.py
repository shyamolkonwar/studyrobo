import os
import glob
from typing import List
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# Configuration
DATA_DIR = "data"
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "study_materials"

def load_documents() -> List[str]:
    """Load all text documents from the data directory."""
    documents = []
    file_paths = glob.glob(os.path.join(DATA_DIR, "*.txt"))

    print(f"Found {len(file_paths)} documents in {DATA_DIR}/")

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Add filename as reference
                filename = os.path.basename(file_path)
                documents.append(f"Source: {filename}\n\n{content}")
                print(f"Loaded: {filename}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return documents

def split_documents(documents: List[str]) -> List[str]:
    """Split documents into chunks for better embedding."""
    chunks = []
    chunk_size = 500
    overlap = 50

    for doc in documents:
        # Simple text splitting by paragraphs and then by character count
        paragraphs = doc.split('\n\n')

        for paragraph in paragraphs:
            if len(paragraph) <= chunk_size:
                chunks.append(paragraph)
            else:
                # Split long paragraphs into smaller chunks
                for i in range(0, len(paragraph), chunk_size - overlap):
                    chunk = paragraph[i:i + chunk_size]
                    if chunk.strip():
                        chunks.append(chunk)

    print(f"Split into {len(chunks)} chunks")
    return chunks

def create_embeddings_and_store(chunks: List[str]):
    """Create embeddings and store in ChromaDB."""
    # Initialize the embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    # Create embeddings
    print("Creating embeddings...")
    embeddings = embedding_model.encode(chunks)

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # Delete existing collection if it exists
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print("Deleted existing collection")
    except:
        pass

    # Create new collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Add documents to collection
    print("Adding documents to ChromaDB...")
    collection.add(
        embeddings=[embedding.tolist() for embedding in embeddings],
        documents=chunks,
        ids=[str(i) for i in range(len(chunks))],
        metadatas=[{"source": f"chunk_{i}"} for i in range(len(chunks))]
    )

    print(f"Successfully added {len(chunks)} documents to ChromaDB")
    print(f"Collection '{COLLECTION_NAME}' created with {collection.count()} documents")

def main():
    """Main function to ingest documents."""
    print("Starting document ingestion...")

    # Load documents
    documents = load_documents()
    if not documents:
        print("No documents found to ingest!")
        return

    # Split documents into chunks
    chunks = split_documents(documents)

    # Create embeddings and store in ChromaDB
    create_embeddings_and_store(chunks)

    print("\nDocument ingestion completed successfully!")
    print(f"Database saved to: {CHROMA_DB_PATH}")

if __name__ == "__main__":
    main()