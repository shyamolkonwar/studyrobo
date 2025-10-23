"""
Script to ingest documents into Supabase pgvector database
Uses the DATABASE_URL to connect directly to Supabase PostgreSQL
"""

import os
import glob
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env file")

# Configuration
DATA_DIR = "data"
EMBEDDING_DIMENSION = 1536  # Match the vector dimension

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

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
    """Create embeddings and store in Supabase database."""
    try:
        # Initialize the embedding model
        embedding_model = SentenceTransformer('all-mpnet-base-v2')  # 768 dimensions

        # Clear existing documents
        print("Clearing existing documents from database...")
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM documents")
                conn.commit()

        # Process chunks in batches
        batch_size = 100  # Larger batch for efficiency
        total_processed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} chunks)...")

            # Create embeddings for batch
            texts = [chunk['content'] for chunk in batch]
            embeddings = embedding_model.encode(texts)

            # Prepare data for insertion
            data_to_insert = []
            for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                # Pad or truncate embedding to match expected dimension
                embedding_array = np.array(embedding)
                if len(embedding_array) < EMBEDDING_DIMENSION:
                    embedding_padded = np.pad(embedding_array, (0, EMBEDDING_DIMENSION - len(embedding_array)))
                elif len(embedding_array) > EMBEDDING_DIMENSION:
                    embedding_padded = embedding_array[:EMBEDDING_DIMENSION]
                else:
                    embedding_padded = embedding_array

                data_to_insert.append((
                    chunk['content'],
                    chunk['course_name'],
                    embedding_padded.tolist()
                ))

            # Insert batch using execute_values for efficiency
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(
                        cursor,
                        "INSERT INTO documents (content, course_name, embedding) VALUES %s",
                        data_to_insert
                    )
                    conn.commit()

            total_processed += len(data_to_insert)
            print(f"Inserted {len(data_to_insert)} documents")

        print(f"\nSuccessfully processed and stored {total_processed} document chunks in Supabase")

        # Verify insertion
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM documents")
                count = cursor.fetchone()[0]
                print(f"Total documents in database: {count}")

    except Exception as e:
        print(f"Error during embedding creation and storage: {e}")
        raise

def main():
    """Main function to ingest documents into Supabase."""
    print("Starting document ingestion into Supabase pgvector...")

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
    print("Documents are now available in Supabase pgvector database")

if __name__ == "__main__":
    main()
