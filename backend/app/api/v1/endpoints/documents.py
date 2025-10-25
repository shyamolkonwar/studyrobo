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

router = APIRouter()

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

        # Trigger document processing via Edge Function
        try:
            edge_function_url = f"{settings.SUPABASE_URL}/functions/v1/process-document"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    edge_function_url,
                    json={
                        "documentId": document_id,
                        "filePath": file_path
                    },
                    headers={
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )

                if response.status_code != 200:
                    print(f"Edge function response: {response.status_code} - {response.text}")
                    # Don't fail the upload if processing fails, just log it
                    # The document will remain in "Processing..." state
        except Exception as e:
            print(f"Failed to trigger document processing: {str(e)}")
            # Don't fail the upload, just log the error

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
