import os
from openai import AsyncOpenAI
from app.core.config import settings

# Initialize client only if API key is provided
client = None
if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def get_llm_response(message: str) -> str:
    # Mock response if no API key is configured
    if not client:
        return f"Hi! I received your message: '{message}'. This is a mock response since no OpenAI API key is configured. Please add your OpenAI API key to the backend/.env file to get real AI responses."

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful student mentor assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"