import os
import json
from openai import AsyncOpenAI
from app.core.config import settings
from app.tools.search_tools import get_study_material, get_study_material_tool

# Initialize client only if API key is provided
client = None
if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def get_llm_response(message: str) -> str:
    # Require API key for production - no mock responses
    if not client:
        raise ValueError("No OpenAI API key configured. Please add your OpenAI API key to the backend/.env file.")

    try:
        # Check if the message might be asking for study materials
        study_keywords = ["study", "learn", "explain", "what is", "help me understand", "exam", "topic", "concept", "algorithm", "syllabus"]

        # Simple keyword-based tool calling (basic implementation)
        message_lower = message.lower()
        should_use_study_tool = any(keyword in message_lower for keyword in study_keywords)

        if should_use_study_tool:
            # Use the study material tool
            tool_result = get_study_material(message)

            if tool_result["success"]:
                # Enhanced prompt with retrieved context
                enhanced_message = f"""You are a helpful student mentor assistant. Answer the user's question based on the following study materials context.

Student Question: {message}

Study Materials Context:
{tool_result['context']}

Please provide a comprehensive answer based on the study materials above. If the context doesn't fully answer the question, you can supplement with general knowledge but make it clear what comes from the materials vs general knowledge."""

                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful student mentor assistant with access to study materials."},
                        {"role": "user", "content": enhanced_message}
                    ],
                    max_tokens=800,
                    temperature=0.3  # Lower temperature for more factual responses
                )
                return response.choices[0].message.content
            else:
                return f"Sorry, I encountered an error searching study materials: {tool_result.get('error', 'Unknown error')}"
        else:
            # Regular conversation without RAG
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

async def get_llm_response_with_functions(message: str) -> str:
    """Advanced version with proper OpenAI function calling."""
    # Require API key for production - no mock responses
    if not client:
        raise ValueError("No OpenAI API key configured. Please add your OpenAI API key to the backend/.env file.")

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful student mentor assistant. You have access to a tool that can search through study materials. Use the get_study_material tool when students ask about academic topics, concepts, or need help with studying."
                },
                {"role": "user", "content": message}
            ],
            tools=[get_study_material_tool],
            tool_choice="auto",
            max_tokens=800,
            temperature=0.3
        )

        message = response.choices[0].message

        # Check if the model called a function
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "get_study_material":
                # Parse the tool arguments
                args = json.loads(tool_call.function.arguments)
                tool_result = get_study_material(args["query"])

                # Send the tool result back to the model
                second_response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful student mentor assistant."},
                        {"role": "user", "content": message},
                        message,
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": json.dumps(tool_result)
                        }
                    ],
                    max_tokens=800,
                    temperature=0.3
                )
                return second_response.choices[0].message.content

        # If no function was called, return the regular response
        return message.content

    except Exception as e:
        return f"Error: {str(e)}"