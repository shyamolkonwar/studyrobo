from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
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
            return []

        # Split text into chunks
        splitter = SimpleTextSplitter(1000, 200)
        chunks = splitter.split_text(text)

        # Generate embeddings for chunks
        chunk_embeddings = []
        client = openai.OpenAI(api_key=openai_api_key)

        for chunk in chunks:
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
    user: Dict[str, Any] = Depends(verify_supabase_token),
    supabase_client: Client = Depends(get_supabase_client)
):
    """Upload a document to Supabase Storage and process it"""
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
        email = user.get("email", "")

        # Get user
        user_id = get_user_id(google_id)

        # Get user's course info
        user_data = supabase_client.table('users').select('course_name').eq('id', user_id).execute()
        
        # Handle both dictionary and object response formats
        if isinstance(user_data, dict):
            user_info = user_data.get('data', [])
        elif hasattr(user_data, 'data'):
            user_info = user_data.data
        else:
            user_info = []
            
        course_name = user_info[0].get('course_name', 'General') if user_info else 'General'

        # Create unique file path
        file_extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"{google_id}/{unique_filename}"

        # Determine file type
        if file_extension == 'pdf':
            file_type = 'pdf'
        elif file_extension == 'docx':
            file_type = 'docx'
        else:
            file_type = 'unknown'

        # Upload file to Supabase Storage
        try:
            # Read file content
            file_content = await file.read()

            # Upload to storage using service role (bypasses RLS)
            from supabase import create_client
            service_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            storage_response = service_supabase.storage.from_('user-documents').upload(
                path=file_path,
                file=file_content,
                file_options={
                    'content-type': file.content_type,
                    'upsert': False
                }
            )

            # Check if upload was successful (Supabase raises exception on failure)
            if not storage_response or hasattr(storage_response, 'status_code') and storage_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to upload file to storage")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

        # Try to get the uploaded document ID (should have been created by trigger)
        try:
            doc_data = supabase.table('documents').select('id').eq('file_path', file_path).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to query documents: {str(e)}")

        # Handle both dictionary and object response formats for doc_data
        if isinstance(doc_data, dict):
            doc_info = doc_data.get('data', [])
        elif hasattr(doc_data, 'data'):
            doc_info = doc_data.data
        else:
            doc_info = []
            
        if not doc_info or len(doc_info) == 0:
            # If no document record exists, create one manually using service role
            doc_insert = None
            try:
                doc_insert = supabase.table('documents').insert({
                    'content': '',  # Will be populated by the edge function
                    'file_path': file_path,
                    'user_id': user_id,
                    'course_name': course_name,
                    'original_file_name': file.filename,
                    'file_type': file_type,
                    'processing_status': 'processing'
                }).execute()
                print(f"DEBUG: Insert result: {doc_insert}")  # Debug logging
            except Exception as e:
                print(f"DEBUG: Insert exception: {str(e)}")  # Debug logging
                # Don't raise exception here - the insert might have succeeded despite the error
                # We'll try to query for the document below

            # Try to get the document ID - handle different response formats
            document_id = None
            if doc_insert:
                # Handle both dictionary and object response formats for doc_insert
                if isinstance(doc_insert, dict):
                    insert_data = doc_insert.get('data', [])
                elif hasattr(doc_insert, 'data'):
                    insert_data = doc_insert.data
                else:
                    insert_data = []
                    
                if insert_data and len(insert_data) > 0:
                    document_id = insert_data[0]['id']
                    print(f"DEBUG: Got ID from insert response: {document_id}")

            if document_id is None:
                # If we can't get the ID from response, query for the document we just created
                print("DEBUG: Querying for created document...")
                try:
                    doc_query = supabase.table('documents').select('id').eq('file_path', file_path).execute()
                    
                    # Handle both dictionary and object response formats for doc_query
                    if isinstance(doc_query, dict):
                        query_data = doc_query.get('data', [])
                    elif hasattr(doc_query, 'data'):
                        query_data = doc_query.data
                    else:
                        query_data = []
                        
                    if query_data and len(query_data) > 0:
                        document_id = query_data[0]['id']
                        print(f"DEBUG: Got ID from query: {document_id}")
                    else:
                        raise HTTPException(status_code=500, detail="Could not retrieve created document ID")
                except Exception as query_error:
                    print(f"DEBUG: Query failed: {str(query_error)}")
                    raise HTTPException(status_code=500, detail=f"Failed to query created document: {str(query_error)}")
        else:
            document_id = doc_info[0]['id']

        # Process the document directly
        try:
            # Extract text content from the file
            if file_extension == 'pdf':
                content = extract_text_from_pdf(file_content)
                if not content:
                    content = f"[PDF Document: {file.filename}] - No text content could be extracted from this PDF"
            elif file_extension == 'docx':
                content = extract_text_from_docx(file_content)
                if not content:
                    content = f"[DOCX Document: {file.filename}] - No text content could be extracted from this DOCX file"
            else:
                content = f"[Document: {file.filename}] - Unsupported file type: {file_extension}"

            # Generate embedding
            embedding = []
            if content and content.strip() and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                embedding = generate_embeddings(content, settings.OPENAI_API_KEY)

            # Update document with processed content and embedding
            update_data = {
                'content': content,
                'processing_status': 'completed'
            }
            if embedding:
                update_data['embedding'] = embedding

            supabase.table('documents').update(update_data).eq('id', document_id).execute()
            print(f"Document {document_id} processed successfully")

        except Exception as e:
            print(f"Failed to process document: {str(e)}")
            # Update status to failed but don't fail the upload
            try:
                supabase.table('documents').update({
                    'processing_status': 'failed',
                    'content': f"Error processing document: {str(e)}"
                }).eq('id', document_id).execute()
            except Exception as update_error:
                print(f"Failed to update document status: {str(update_error)}")

        return {
            "message": "Document uploaded successfully",
            "document_id": document_id,
            "filename": file.filename,
            "file_path": file_path
        }

    except HTTPException:
        raise
    except Exception as e:
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
