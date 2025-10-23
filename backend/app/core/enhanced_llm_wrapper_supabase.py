"""
Enhanced LLM wrapper with Supabase integration
Replaces ChromaDB and service account tools with Supabase-based alternatives
Supports dynamic LLM provider selection (OpenAI, Mistral)
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.llm_factory import get_llm_provider
from app.core.chat_memory import get_conversation_history, add_message, format_conversation_for_llm
from app.tools.search_tools import get_study_material, get_study_material_tool
from app.tools.career_tools import get_career_insights, get_career_insights_tool
from app.tools.attendance_tools_supabase import mark_attendance, get_attendance_records, mark_attendance_tool, get_attendance_records_tool
from app.tools.email_tools_supabase import get_unread_emails, draft_email, get_unread_emails_tool, draft_email_tool

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
        "attendance": "You are a helpful academic assistant. You have access to tools that can mark student attendance and retrieve attendance records using Supabase. Use the mark_attendance tool when students need to record their presence in class. Be efficient and provide clear confirmations.",
        "email": "You are a helpful communication assistant. You have access to tools that can fetch unread emails and draft new messages using Google OAuth tokens. Use the get_unread_emails tool to check for important messages, and use the draft_email tool to compose new emails. Help students manage their inbox efficiently.",
        "general": "You are a helpful student mentor assistant that provides guidance on various academic and personal topics. Be supportive, informative, and encouraging."
    }

    return prompts.get(intent, prompts["general"])

async def execute_tool(tool_name: str, tool_args: Dict[str, Any], google_access_token: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute the appropriate tool function based on tool name.
    """
    try:
        if tool_name == "get_study_material":
            return await get_study_material(tool_args.get("query", ""))
        elif tool_name == "get_career_insights":
            return await get_career_insights(tool_args.get("field", ""))
        elif tool_name == "mark_attendance":
            # Now requires user_id instead of student_name
            if not user_id:
                return {
                    "success": False,
                    "error": "User ID is required for attendance marking",
                    "message": "Please ensure you're logged in to mark attendance"
                }
            return await mark_attendance(
                user_id=user_id,
                course_name=tool_args.get("course_name", "")
            )
        elif tool_name == "get_attendance_records":
            # New tool for retrieving attendance records
            if not user_id:
                return {
                    "success": False,
                    "error": "User ID is required for attendance records",
                    "message": "Please ensure you're logged in to view attendance"
                }
            return await get_attendance_records(
                user_id=user_id,
                course_name=tool_args.get("course_name")
            )
        elif tool_name == "get_unread_emails":
            # Now requires google_access_token instead of user_id
            if not google_access_token:
                return {
                    "success": False,
                    "error": "Google access token is required",
                    "message": "Please ensure you're logged in with Google to access emails"
                }
            return await get_unread_emails(
                google_access_token=google_access_token,
                max_results=tool_args.get("max_results", 10)
            )
        elif tool_name == "draft_email":
            # Now requires google_access_token instead of user_id
            if not google_access_token:
                return {
                    "success": False,
                    "error": "Google access token is required",
                    "message": "Please ensure you're logged in with Google to draft emails"
                }
            return await draft_email(
                google_access_token=google_access_token,
                to=tool_args.get("to", ""),
                subject=tool_args.get("subject", ""),
                body=tool_args.get("body", "")
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
        get_attendance_records_tool,  # Added new tool
        get_unread_emails_tool,
        draft_email_tool
    ]

async def get_llm_response_with_supabase(
    message: str,
    google_access_token: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """
    Enhanced LLM response function with Supabase integration and chat memory.
    Supports dynamic LLM provider selection (OpenAI, Mistral).

    This function:
    1. Retrieves conversation history from Supabase
    2. Detects user intent based on message content
    3. Creates appropriate system prompt with context
    4. Provides all relevant tools to the selected LLM
    5. Executes tool calls when requested by the LLM
    6. Stores conversation in Supabase
    7. Returns formatted responses
    """
    try:
        # Get the configured LLM provider
        llm_provider = get_llm_provider()

        # Store user message in chat memory
        if user_id:
            add_message(user_id, 'user', message)

        # Get conversation history for context
        conversation_context = ""
        if user_id:
            conversation_context = format_conversation_for_llm(user_id, limit=10)

        # Detect user intent
        intent = detect_intent(message)

        # Create appropriate system prompt
        system_prompt = create_system_prompt(intent)

        # Add conversation context to system prompt if available
        if conversation_context and conversation_context != "No previous conversation history.":
            system_prompt += f"\n\nRecent conversation context:\n{conversation_context}"

        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {"role": "user", "content": message}
        ]

        # Get tools - only for OpenAI since Mistral doesn't support tool calling yet
        tools = []
        if settings.LLM_PROVIDER == "openai":
            tools = get_all_tools()

        # Create completion with the selected LLM
        response = await llm_provider.create_completion(
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
            max_tokens=1000,
            temperature=0.3
        )

        assistant_message = response['choices'][0]['message']

        # Handle tool calls (only for OpenAI)
        if assistant_message.get('tool_calls') and settings.LLM_PROVIDER == "openai":
            tool_results = []
            for tool_call in assistant_message['tool_calls']:
                tool_name = tool_call['function']['name']
                tool_args = json.loads(tool_call['function']['arguments'])

                # Execute the tool with additional parameters
                tool_result = await execute_tool(
                    tool_name,
                    tool_args,
                    google_access_token=google_access_token,
                    user_id=user_id
                )

                tool_results.append({
                    "tool_call_id": tool_call['id'],
                    "tool_name": tool_name,
                    "tool_result": tool_result
                })

                # Create tool result message
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                }

                # Send tool result back to LLM for final response
                final_messages = messages + [assistant_message, tool_message]
                final_response = await llm_provider.create_completion(
                    messages=final_messages,
                    max_tokens=800,
                    temperature=0.3
                )

                assistant_reply = final_response['choices'][0]['message']['content']

                # Store AI response in chat memory
                if user_id:
                    add_message(user_id, 'ai', assistant_reply)

                return assistant_reply

        # If no tool was called, return the regular response
        assistant_reply = assistant_message.get('content', '')

        # Store AI response in chat memory
        if user_id:
            add_message(user_id, 'ai', assistant_reply)

        return assistant_reply

    except Exception as e:
        error_message = f"Error: {str(e)}"

        # Store error in chat memory if user_id is available
        if user_id:
            add_message(user_id, 'ai', error_message)

        return error_message

# Backward compatibility function
async def get_llm_response_with_all_tools(message: str) -> str:
    """
    Legacy function for backward compatibility.
    """
    return await get_llm_response_with_supabase(message)
