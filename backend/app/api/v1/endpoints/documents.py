from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, Form
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import os
import tempfile
import uuid
from app.core.config import settings
from app.core.supabase_client import get_supabase_client, supabase
from supabase import create_client, Client
from app.api.v1.endpoints.auth.google import verify_supabase_token
import httpx
import io
from pypdf import PdfReader
from docx import Document
import openai
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

router = APIRouter()

# Simple text splitter implementation
class SimpleTextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[str]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            if end > len(text):
                end = len(text)

            chunks.append(text[start:end])
            start = end - self.chunk_overlap

            if start >= len(text):
                break

        return chunks

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return f"[PDF Document] - Error extracting text: {str(e)}"

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return f"[DOCX Document] - Error extracting text: {str(e)}"

def generate_embeddings(text: str, openai_api_key: str) -> list[float]:
    """Generate embeddings for text using OpenAI"""
    try:
        if not text.strip():
            print("No text content to embed")
            return []

        # Split text into chunks
        splitter = SimpleTextSplitter(1000, 200)
        chunks = splitter.split_text(text)
        print(f"Split text into {len(chunks)} chunks")

        # Limit to first 5 chunks to avoid rate limits and long processing
        chunks = chunks[:5] if len(chunks) > 5 else chunks

        # Generate embeddings for chunks
        chunk_embeddings = []
        client = openai.OpenAI(api_key=openai_api_key)

        for i, chunk in enumerate(chunks):
            print(f"Generating embedding for chunk {i+1}/{len(chunks)}")
            response = client.embeddings.create(
                input=chunk,
                model='text-embedding-3-small'
            )
            chunk_embeddings.append(response.data[0].embedding)

        # Average the embeddings
        if chunk_embeddings:
            embedding_dim = len(chunk_embeddings[0])
            embedding = [0.0] * embedding_dim
            for chunk_embedding in chunk_embeddings:
                for i in range(embedding_dim):
                    embedding[i] += chunk_embedding[i]
            for i in range(embedding_dim):
                embedding[i] /= len(chunk_embeddings)
            print(f"Successfully generated embedding with {embedding_dim} dimensions")
            return embedding

        return []
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return []

def get_user_id(google_id: str) -> int:
    """Get user ID from Google ID - assumes user already exists"""
    try:
        # Get existing user
        result = supabase.table('users').select('id').eq('google_id', google_id).execute()

        if result['data'] and len(result['data']) > 0:
            return result['data'][0]['id']
        else:
            raise Exception(f"User with google_id {google_id} not found in database")

    except Exception as e:
        raise Exception(f"Failed to get user: {str(e)}")

@router.get("/user")
async def get_user_documents(
    user: Dict[str, Any] = Depends(verify_supabase_token),
    supabase_client: Client = Depends(get_supabase_client),
    authorization: Optional[str] = Header(None)
):
    """Get all documents for the current user"""
    try:
        google_id = user["google_id"]
        email = user.get("email", "")

        # Get user
        user_id = get_user_id(google_id)
        print(f"DEBUG: Authenticated user - google_id: {google_id}, email: {email}")
        print(f"DEBUG: Mapped to internal user_id: {user_id}")

        # Use service role client directly with proper user filtering for reliable access
        # This bypasses RLS issues while still maintaining security by filtering by user_id
        print(f"DEBUG: Using service role client with user_id filtering")
        from app.core.supabase_client import get_supabase_service_client
        service_supabase = get_supabase_service_client()

        documents = service_supabase.table('documents').select('*').eq('user_id', user_id).execute()
        print(f"DEBUG: Service role found {len(documents.data) if hasattr(documents, 'data') and documents.data else 0} documents")

        # Verify the documents belong to the authenticated user (double security check)
        if hasattr(documents, 'data') and documents.data:
            filtered_docs = [doc for doc in documents.data if doc['user_id'] == user_id]
            print(f"DEBUG: After security verification, returning {len(filtered_docs)} documents")
            return filtered_docs
        else:
            print("DEBUG: No documents found in service role query")
            return []

    except Exception as e:
        print(f"DEBUG: Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    course_name: str = Form(...),
    user: Dict[str, Any] = Depends(verify_supabase_token),
    supabase_client: Client = Depends(get_supabase_client)
):
    """Upload a document, extract text, chunk it, generate embeddings, and save to database"""
    try:
        # Validate file type
        allowed_types = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not allowed. Only PDF and DOCX files are supported."
            )

        # Get user info
        google_id = user["google_id"]
        user_id = get_user_id(google_id)

        # Read file content
        file_content = await file.read()

        # Create unique file path for storage
        file_extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"{google_id}/{unique_filename}"

        # Upload file to Supabase Storage
        try:
            service_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            storage_response = service_supabase.storage.from_('user-documents').upload(
                path=file_path,
                file=file_content,
                file_options={
                    'content-type': file.content_type,
                    'upsert': False
                }
            )
            if not storage_response:
                raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

        # Extract text from file
        if file_extension == 'pdf':
            full_text = extract_text_from_pdf(file_content)
        elif file_extension == 'docx':
            full_text = extract_text_from_docx(file_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        if not full_text.strip():
            raise HTTPException(status_code=400, detail="No text content could be extracted from the file")

        # Split text into chunks using LangChain
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            length_function=len
        )
        chunks = text_splitter.split_text(full_text)
        print(f"Split text into {len(chunks)} chunks")

        # Generate embeddings for each chunk
        if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        embeddings = []

        for i, chunk in enumerate(chunks):
            print(f"Generating embedding for chunk {i+1}/{len(chunks)}")
            response = client.embeddings.create(
                input=chunk,
                model="text-embedding-3-small"
            )
            embeddings.append(response.data[0].embedding)

        # Prepare data for insertion
        data_to_insert = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            data_to_insert.append({
                "user_id": user_id,
                "content": chunk,
                "embedding": embedding,
                "course_name": course_name,
                "original_file_name": file.filename,
                "file_path": file_path,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })

        # Insert all chunks into documents table
        service_supabase.table("documents").insert(data_to_insert).execute()

        return {
            "message": "File processed and saved successfully",
            "chunks_created": len(chunks),
            "filename": file.filename,
            "course_name": course_name
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
):
    """Delete a document and its file from storage"""
    try:
        # Get user info
        google_id = user["google_id"]
        email = user.get("email", "")

        # Get user
        user_id = get_user_id(google_id)

        # Get document info
        doc_data = supabase.table('documents').select('file_path, user_id').eq('id', document_id).single().execute()
        
        # Handle both dictionary and object response formats for doc_data
        if isinstance(doc_data, dict):
            doc_info = doc_data.get('data')
        elif hasattr(doc_data, 'data'):
            doc_info = doc_data.data
        else:
            doc_info = None
            
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        # Verify document belongs to user
        if doc_info['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")

        file_path = doc_info['file_path']

        # Delete from storage
        if file_path:
            try:
                supabase.storage.from_('user-documents').remove([file_path])
            except Exception as e:
                print(f"Failed to delete file from storage: {str(e)}")

        # Delete from database
        supabase.table('documents').delete().eq('id', document_id).execute()

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
):
    """Get a specific document"""
    try:
        # Get user info
        google_id = user["google_id"]
        email = user.get("email", "")

        # Get user
        user_id = get_user_id(google_id)

        # Get document
        doc_data = supabase.table('documents').select('*').eq('id', document_id).single().execute()
        
        # Handle both dictionary and object response formats for doc_data
        if isinstance(doc_data, dict):
            doc_info = doc_data.get('data')
        elif hasattr(doc_data, 'data'):
            doc_info = doc_data.data
        else:
            doc_info = None
            
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        # Verify document belongs to user or is global
        if doc_info['user_id'] != user_id and doc_info['user_id'] is not None:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")

        return doc_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
