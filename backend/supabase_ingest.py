"""
Database document ingestion script
Uses PostgreSQL vector database
"""

import os
import glob
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.db_client import insert_document, execute_query

# Configuration
DATA_DIR = "data"
EMBEDDING_DIMENSION = 1536  # Match the Supabase vector dimension

def load_documents() -> List[Dict[str, str]]:
    """Load all text documents from the data directory."""
    documents = []
    file_paths = glob.glob(os.path.join(DATA_DIR, "*.txt"))

    print(f"Found {len(file_paths)} documents in {DATA_DIR}/")

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Add filename as reference and extract course name from filename
                filename = os.path.basename(file_path)
                course_name = filename.replace('.txt', '').replace('_', ' ').title()
                documents.append({
                    'content': f"Source: {filename}\n\n{content}",
                    'course_name': course_name
                })
                print(f"Loaded: {filename} (Course: {course_name})")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return documents

def split_documents(documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Split documents into chunks for better embedding."""
    chunks = []
    chunk_size = 500
    overlap = 50

    for doc in documents:
        content = doc['content']
        course_name = doc['course_name']

        # Simple text splitting by paragraphs and then by character count
        paragraphs = content.split('\n\n')

        for paragraph in paragraphs:
            if len(paragraph) <= chunk_size:
                chunks.append({
                    'content': paragraph,
                    'course_name': course_name
                })
            else:
                # Split long paragraphs into smaller chunks
                for i in range(0, len(paragraph), chunk_size - overlap):
                    chunk = paragraph[i:i + chunk_size]
                    if chunk.strip():
                        chunks.append({
                            'content': chunk,
                            'course_name': course_name
                        })

    print(f"Split into {len(chunks)} chunks")
    return chunks

def create_embeddings_and_store(chunks: List[Dict[str, str]]):
    """Create embeddings and store in database."""
    try:
        # Initialize the embedding model
        # Note: Using a model that produces vectors, but we'll pad/truncate to match 1536 dimensions
        embedding_model = SentenceTransformer('all-mpnet-base-v2')  # 768 dimensions

        # Clear existing documents
        print("Clearing existing documents from database...")
        execute_query("DELETE FROM documents", fetch=False)

        # Process chunks
        total_processed = 0

        for i, chunk in enumerate(chunks):
            if (i + 1) % 10 == 0:
                print(f"Processing chunk {i + 1}/{len(chunks)}...")

            # Create embedding
            embedding = embedding_model.encode(chunk['content'])

            # Pad or truncate embedding to match expected dimension (1536)
            embedding_array = np.array(embedding)
            if len(embedding_array) < EMBEDDING_DIMENSION:
                # Pad with zeros
                embedding_padded = np.pad(embedding_array, (0, EMBEDDING_DIMENSION - len(embedding_array)))
            elif len(embedding_array) > EMBEDDING_DIMENSION:
                # Truncate
                embedding_padded = embedding_array[:EMBEDDING_DIMENSION]
            else:
                embedding_padded = embedding_array

            # Insert document
            try:
                insert_document(chunk['content'], chunk['course_name'], embedding_padded.tolist())
                total_processed += 1
            except Exception as e:
                print(f"Error inserting chunk {i + 1}: {e}")

        print(f"\nSuccessfully processed and stored {total_processed} document chunks in database")

        # Verify insertion
        count_result = execute_query("SELECT COUNT(*) as count FROM documents")
        if count_result:
            print(f"Total documents in database: {count_result[0]['count']}")
        else:
            print("Could not verify document count")

    except Exception as e:
        print(f"Error during embedding creation and storage: {e}")

def main():
    """Main function to ingest documents into Supabase."""
    print("Starting Supabase document ingestion...")

    # Load documents
    documents = load_documents()
    if not documents:
        print("No documents found to ingest!")
        return

    # Split documents into chunks
    chunks = split_documents(documents)

    # Create embeddings and store in Supabase
    create_embeddings_and_store(chunks)

    print("\nDocument ingestion completed successfully!")
    print("Documents are now available in Supabase vector database")

if __name__ == "__main__":
    main()
