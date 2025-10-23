import os
import json
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.tools.search_tools import get_study_material, get_study_material_tool
from app.tools.career_tools import get_career_insights, get_career_insights_tool
from app.tools.attendance_tools import mark_attendance, mark_attendance_tool
from app.tools.email_tools import get_unread_emails, draft_email, get_unread_emails_tool, draft_email_tool

# Initialize OpenAI client
client = None
if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def detect_intent(message: str) -> str:
    """
    Detect the user's intent based on keywords in the message.
    """
    message_lower = message.lower()

    # Define intent categories with their associated tools
    intents = {
        "study": ["study", "learn", "explain", "what is", "help me understand", "exam", "topic", "concept", "algorithm", "syllabus", "material", "notes", "homework", "assignment"],
        "career": ["career", "job", "salary", "work", "employment", "profession", "field", "market", "opportunity", "growth"],
        "attendance": ["attendance", "present", "absent", "mark", "class", "course"],
        "email": ["email", "gmail", "inbox", "draft", "send", "message", "unread", "check"]
    }

    # Check for each intent category
    for intent, keywords in intents.items():
        if any(keyword in message_lower for keyword in keywords):
            return intent

    return "general"

def create_system_prompt(intent: str) -> str:
    """
    Create an appropriate system prompt based on detected intent.
    """
    prompts = {
        "study": "You are a helpful student mentor assistant. You have access to a tool that can search through study materials and documents. Use the get_study_material tool when students ask about academic topics, concepts, or need help with studying. Provide comprehensive answers based on the retrieved materials.",
        "career": "You are a helpful career guidance assistant. You have access to a tool that can search for career insights and job market information. Use the get_career_insights tool when students ask about career prospects, job trends, salary information, or professional development. Provide helpful and realistic career advice.",
        "attendance": "You are a helpful academic assistant. You have access to a tool that can mark student attendance in courses. Use the mark_attendance tool when students need to record their presence in class. Be efficient and provide clear confirmations.",
        "email": "You are a helpful communication assistant. You have access to tools that can fetch unread emails and draft new messages. Use the get_unread_emails tool to check for important messages, and use the draft_email tool to compose new emails. Help students manage their inbox efficiently.",
        "general": "You are a helpful student mentor assistant that provides guidance on various academic and personal topics. Be supportive, informative, and encouraging."
    }

    return prompts.get(intent, prompts["general"])

async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the appropriate tool function based on tool name.
    """
    try:
        if tool_name == "get_study_material":
            return await get_study_material(tool_args.get("query", ""))
        elif tool_name == "get_career_insights":
            return await get_career_insights(tool_args.get("field", ""))
        elif tool_name == "mark_attendance":
            return await mark_attendance(
                tool_args.get("course_name", ""),
                tool_args.get("student_name", "")
            )
        elif tool_name == "get_unread_emails":
            return await get_unread_emails(tool_args.get("user_id", "default"))
        elif tool_name == "draft_email":
            return await draft_email(
                tool_args.get("to", ""),
                tool_args.get("subject", ""),
                tool_args.get("body", ""),
                tool_args.get("user_id", "default")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "message": f"Tool {tool_name} is not available"
            }

    except Exception as e:
        return {
            "success": False,
                "error": str(e),
                "message": f"Error executing {tool_name}: {str(e)}"
            }

def get_all_tools() -> List[Dict[str, Any]]:
    """
    Return all available tools for function calling.
    """
    return [
        get_study_material_tool,
        get_career_insights_tool,
        mark_attendance_tool,
        get_unread_emails_tool,
        draft_email_tool
    ]

async def get_llm_response_with_all_tools(message: str) -> str:
    """
    Enhanced LLM response function with comprehensive tool integration.

    This function:
    1. Detects user intent based on message content
    2. Creates appropriate system prompt
    3. Provides all relevant tools to OpenAI
    4. Executes tool calls when requested by OpenAI
    5. Formats responses appropriately
    """
    # Mock response if no API key is configured
    if not client:
        intent = detect_intent(message)
        return f"Hi! I received your message: '{message}'. This appears to be about {intent}. This is a mock response since no OpenAI API key is configured. Please add your OpenAI API key to the backend/.env file to get real AI responses."

    try:
        # Detect user intent
        intent = detect_intent(message)

        # Create appropriate system prompt
        system_prompt = create_system_prompt(intent)

        # Prepare tools for function calling
        tools = get_all_tools()

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {"role": "user", "content": message}
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=1000,
            temperature=0.3
        )

        assistant_message = response.choices[0].message

        # Handle tool calls
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                # Execute the tool
                tool_result = await execute_tool(tool_name, tool_args)

                # Create tool result message
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                }

                # Send tool result back to OpenAI for final response
                final_response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                        assistant_message,
                        tool_message
                    ],
                    max_tokens=800,
                    temperature=0.3
                )

                return final_response.choices[0].message.content

        # If no tool was called, return the regular response
        return assistant_message.content

    except Exception as e:
        return f"Error: {str(e)}"