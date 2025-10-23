from fastapi import APIRouter
from app.api.v1.endpoints import chat_supabase
from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(chat_supabase.router, tags=["chat"])
api_router.include_router(auth.google.router, prefix="/auth", tags=["authentication"])
