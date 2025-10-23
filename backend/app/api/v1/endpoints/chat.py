from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse
from app.core.enhanced_llm_wrapper import get_llm_response_with_all_tools

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    reply = await get_llm_response_with_all_tools(request.message)
    return ChatResponse(reply=reply)