from fastapi import APIRouter
from app.api.v1.endpoints import chat_supabase, conversations, documents, gmail, attendance, calendar
from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(chat_supabase.router, tags=["chat"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(gmail.router, prefix="/gmail", tags=["gmail"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(auth.google.router, prefix="/auth", tags=["authentication"])
