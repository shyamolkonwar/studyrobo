"""
Enhanced LLM wrapper with Supabase integration
Replaces ChromaDB and service account tools with Supabase-based alternatives
Supports dynamic LLM provider selection (OpenAI, Mistral)
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.llm_factory import get_llm_provider
from app.core.chat_memory import get_conversation_history, add_message, format_conversation_for_llm
from app.tools.search_tools import get_study_material, get_study_material_tool
from app.tools.career_tools import get_career_insights, get_career_insights_tool
from app.tools.attendance_tools_supabase import mark_attendance, get_attendance_records, mark_attendance_tool, get_attendance_records_tool
from app.tools.email_tools_supabase import get_unread_emails, draft_email, get_unread_emails_tool, draft_email_tool
from app.tools.calendar_tools_supabase import get_upcoming_events, create_calendar_event, get_upcoming_events_tool, create_calendar_event_tool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        "email": ["email", "gmail", "inbox", "draft", "send", "message", "unread", "check"],
        "calendar": ["calendar", "schedule", "event", "meeting", "appointment", "agenda", "today", "tomorrow", "week", "upcoming", "create", "add", "book", "remind"]
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
        "calendar": "You are a helpful scheduling assistant. You have access to tools that can fetch upcoming calendar events and create new events using Google Calendar. Use the get_upcoming_events tool to check schedules and agendas, and use the create_calendar_event tool to schedule new meetings, study sessions, or appointments. Help students stay organized and on top of their commitments.",
        "general": "You are a helpful student mentor assistant that provides guidance on various academic and personal topics. Be supportive, informative, and encouraging."
    }

    return prompts.get(intent, prompts["general"])

async def execute_tool(tool_name: str, tool_args: Dict[str, Any], google_access_token: Optional[str] = None, user_id: Optional[int] = None, google_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute the appropriate tool function based on tool name.
    """
    try:
        if tool_name == "get_study_material":
            logger.info(f"🔍 RAG SYSTEM ACTIVATED: Searching study materials for query: '{tool_args.get('query', '')}'")
            return await get_study_material(tool_args.get("query", ""), google_id)
        elif tool_name == "get_career_insights":
            logger.info(f"💼 CAREER TOOL USED: Getting insights for field: '{tool_args.get('field', '')}'")
            return await get_career_insights(tool_args.get("field", ""))
        elif tool_name == "mark_attendance":
            logger.info(f"📝 ATTENDANCE TOOL USED: Marking attendance for course: '{tool_args.get('course_name', '')}'")
            # Now requires user_id instead of student_name
            if not user_id:
                return {
                    "success": False,
                    "error": "User ID is required for attendance marking",
                    "message": "Please ensure you're logged in to mark attendance"
                }
            return mark_attendance(
                user_id=str(user_id),
                course_name=tool_args.get("course_name", "")
            )
        elif tool_name == "get_attendance_records":
            logger.info(f"📊 ATTENDANCE RECORDS TOOL USED: Retrieving records for course: '{tool_args.get('course_name')}'")
            # New tool for retrieving attendance records
            if not user_id:
                return {
                    "success": False,
                    "error": "User ID is required for attendance records",
                    "message": "Please ensure you're logged in to view attendance"
                }
            return get_attendance_records(
                user_id=str(user_id),
                course_name=tool_args.get("course_name")
            )
        elif tool_name == "get_unread_emails":
            logger.info(f"📧 EMAIL TOOL USED: Fetching unread emails (max: {tool_args.get('max_results', 10)})")
            # Now uses stored refresh token from database
            if not google_id:
                return {
                    "success": False,
                    "error": "User authentication required",
                    "message": "Please log in to access email functionality."
                }
            return await get_unread_emails(
                user_id=google_id,
                max_results=tool_args.get("max_results", 10)
            )
        elif tool_name == "draft_email":
            logger.info(f"✉️ EMAIL DRAFT TOOL USED: Drafting email to: '{tool_args.get('to', '')}', subject: '{tool_args.get('subject', '')}'")
            # Now requires google_access_token instead of user_id
            if not google_access_token:
                return {
                    "success": False,
                    "error": "Google access token is required",
                    "message": "To draft an email, I'll need your Google OAuth access token. Could you please ensure that I have the necessary permissions to access your Gmail account?"
                }
            return await draft_email(
                google_access_token=google_access_token,
                to=tool_args.get("to", ""),
                subject=tool_args.get("subject", ""),
                body=tool_args.get("body", "")
            )
        elif tool_name == "get_upcoming_events":
            logger.info(f"📅 CALENDAR TOOL USED: Fetching upcoming events (max: {tool_args.get('max_results', 10)})")
            if not google_id:
                return {
                    "success": False,
                    "error": "User authentication required",
                    "message": "Please log in to access calendar functionality."
                }
            return await get_upcoming_events(
                user_id=google_id,
                max_results=tool_args.get("max_results", 10)
            )
        elif tool_name == "create_calendar_event":
            logger.info(f"📝 CALENDAR EVENT TOOL USED: Creating event '{tool_args.get('title', '')}'")
            if not google_id:
                return {
                    "success": False,
                    "error": "User authentication required",
                    "message": "Please log in to create calendar events."
                }
            return await create_calendar_event(
                user_id=google_id,
                title=tool_args.get("title", ""),
                start_time=tool_args.get("start_time", ""),
                end_time=tool_args.get("end_time", ""),
                description=tool_args.get("description", ""),
                location=tool_args.get("location", "")
            )
        else:
            logger.warning(f"⚠️ UNKNOWN TOOL REQUESTED: {tool_name}")
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "message": f"Tool {tool_name} is not available"
            }

    except Exception as e:
        logger.error(f"❌ TOOL EXECUTION ERROR for {tool_name}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Error executing {tool_name}: {str(e)}"
        }

def extract_career_field(message: str) -> str:
    """
    Extract career field from user message.
    """
    message_lower = message.lower()

    # Common career fields to look for
    career_fields = [
        "computer science", "software engineering", "data science", "machine learning",
        "artificial intelligence", "web development", "mobile development", "devops",
        "cybersecurity", "blockchain", "cloud computing", "it", "programming",
        "engineering", "medicine", "law", "finance", "marketing", "design",
        "business", "accounting", "teaching", "research"
    ]

    for field in career_fields:
        if field in message_lower:
            return field

    # Default fallback
    return "technology"

def extract_course_name(message: str) -> str:
    """
    Extract course name from attendance-related messages.
    """
    message_lower = message.lower()

    # Look for course names or subjects
    courses = [
        "computer science", "mathematics", "physics", "chemistry", "biology",
        "english", "history", "geography", "economics", "psychology",
        "data structures", "algorithms", "database", "web development",
        "machine learning", "artificial intelligence"
    ]

    for course in courses:
        if course in message_lower:
            return course

    # Look for course codes after keywords like "for", "in", etc.
    import re

    # Pattern to find course codes like CS101, MATH201, etc.
    course_code_pattern = r'\b([A-Z]{2,4}\d{2,4}|[A-Z]{2,}\s*\d{2,})\b'
    course_codes = re.findall(course_code_pattern, message)
    if course_codes:
        return course_codes[0].upper()

    # Look for words after "for" or "in"
    for_pattern = r'\bfor\s+(\w+)'
    in_pattern = r'\bin\s+(\w+)'

    for_match = re.search(for_pattern, message_lower)
    if for_match:
        word = for_match.group(1)
        if len(word) > 2 and word not in ["my", "the", "a", "an"]:
            return word.title()

    in_match = re.search(in_pattern, message_lower)
    if in_match:
        word = in_match.group(1)
        if len(word) > 2 and word not in ["my", "the", "a", "an"]:
            return word.title()

    # Try to extract words that might be course names (but avoid common words)
    words = message_lower.split()
    excluded_words = ["mark", "attendance", "present", "here", "class", "course", "check", "my", "the", "for", "in", "and", "or", "but", "with"]

    for word in words:
        if len(word) >= 3 and word not in excluded_words and not word.isdigit():
            # Check if it looks like a course code (letters followed by numbers)
            if re.match(r'^[a-zA-Z]+\d+$', word):
                return word.upper()
            # Or if it's a reasonable course name
            elif len(word) <= 20:  # Reasonable length limit
                return word.title()

    return ""  # Return empty string instead of "General" to indicate no specific course

def extract_email_details(message: str) -> Dict[str, Any]:
    """
    Extract email details from draft email messages.
    """
    # Simple extraction - in production this could use NLP
    message_lower = message.lower()

    # Default values
    details = {
        "to": "",
        "subject": "",
        "body": message  # Use the full message as body if we can't parse better
    }

    # Try to extract recipient (look for email addresses or names)
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, message)
    if emails:
        details["to"] = emails[0]

    # Try to extract subject (look for "subject:" or similar)
    subject_match = re.search(r'subject:?\s*([^\n]+)', message_lower)
    if subject_match:
        details["subject"] = subject_match.group(1).strip()

    return details

async def process_tool_results(tool_results: List[Dict], intent: str, original_message: str, conversation_context: str = "") -> str:
    """
    Process tool results and generate appropriate response.
    Warn user if no relevant information found.
    """
    if not tool_results:
        return "I apologize, but I couldn't process your request. Please try again."

    tool_result = tool_results[0]  # We only execute one tool per intent
    tool_name = tool_result["tool_name"]
    result = tool_result["tool_result"]

    # Handle case where result might be a string (error) instead of dict
    if isinstance(result, str):
        return f"I encountered an error while processing your request: {result}"

    # Check if tool execution was successful
    if not result.get("success", False):
        error_msg = result.get("error", "Unknown error")
        return f"I encountered an error while processing your request: {error_msg}"

    # Process results based on tool type
    if tool_name == "get_study_material":
        context = result.get("context", "")
        message = result.get("message", "")

        # Check if no relevant materials were found
        if "No relevant study materials found" in context:
            return f"I searched through your uploaded study materials but couldn't find relevant information for '{original_message}'. Please try rephrasing your question or upload relevant documents that contain information about this topic."

        # Check if there was an error
        if not result.get("success", False):
            return f"I encountered an error while searching study materials: {result.get('error', 'Unknown error')}"

        # Use LLM to synthesize an answer based on the retrieved context
        try:
            llm_provider = get_llm_provider()

            synthesis_prompt = f"""Based on the following information from the user's study materials, please provide a comprehensive and well-structured answer to their question: "{original_message}"

Study Materials Context:
{context}

Please synthesize this information into a clear, helpful answer. Focus on being accurate, comprehensive, and directly addressing the user's question. If the context doesn't fully answer the question, mention what additional information might be needed."""

            # Get LLM response using the synthesis prompt
            synthesis_response = await llm_provider.create_completion(
                messages=[{"role": "user", "content": synthesis_prompt}],
                tools=[],  # No tools needed for synthesis
                tool_choice=None,
                max_tokens=1500,
                temperature=0.3
            )

            # Extract the answer from the response
            answer = synthesis_response['choices'][0]['message']['content']

            # Add a note about the source
            answer += "\n\n*This answer is based on information from your uploaded study materials. If you need more details or have additional questions, feel free to ask!*"

            return answer

        except Exception as e:
            logger.error(f"Error synthesizing answer with LLM: {str(e)}")
            # Fallback to raw context if LLM synthesis fails
            response = f"Based on your study materials, here's what I found:\n\n{context}\n\n"
            response += "If this doesn't fully answer your question, please provide more details or upload additional study materials."
            return response

    elif tool_name == "get_career_insights":
        insights = result.get("insights", {})
        extracted_content = result.get("extracted_content", "")

        if not insights and not extracted_content:
            field = extract_career_field(original_message)
            return f"I couldn't find specific career insights for '{field}'. Please try a different career field or provide more details about your interests."

        # If we have extracted content, use LLM to synthesize a comprehensive answer
        if extracted_content and len(extracted_content.strip()) > 100:
            try:
                llm_provider = get_llm_provider()

                synthesis_prompt = f"""Based on the following career insights and market information, please provide a comprehensive and well-structured answer to the user's career question: "{original_message}"

Career Information Context:
{extracted_content[:4000]}  # Limit context to avoid token limits

Please synthesize this information into a clear, helpful career advice response. Focus on:
- Current job market trends and demand
- Salary expectations and growth opportunities
- Required skills and qualifications
- Realistic career advice and next steps
- Be encouraging and practical

If the context doesn't fully answer the question, provide general guidance based on the field mentioned."""

                # Get LLM response using the synthesis prompt
                synthesis_response = await llm_provider.create_completion(
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    tools=[],  # No tools needed for synthesis
                    tool_choice=None,
                    max_tokens=1200,
                    temperature=0.3
                )

                # Extract the answer from the response
                answer = synthesis_response['choices'][0]['message']['content']

                # Add a note about the source
                answer += "\n\n*This career advice is based on current market data and industry insights. Career opportunities can vary by location and individual circumstances.*"

                return answer

            except Exception as e:
                logger.error(f"Error synthesizing career answer with LLM: {str(e)}")
                # Fall back to basic insights if LLM synthesis fails

        # Fallback to basic insights formatting
        insights_list = insights.get("insights", [])
        if insights_list:
            response = "Here are some career insights I found:\n\n"
            for insight in insights_list[:5]:  # Limit to 5 insights
                title = insight.get("title", "")
                summary = insight.get("summary", "")
                source = insight.get("source", "")
                if title and summary:
                    response += f"**{title}**\n{summary}\n"
                    if source and source != "industry_standard" and source != "market_analysis":
                        response += f"*Source: {source}*\n"
                    response += "\n"
        else:
            field = extract_career_field(original_message)
            response = f"I found some general career information for '{field}', but detailed insights are limited. Consider exploring specific sub-fields or current market trends."

    elif tool_name == "mark_attendance":
        message = result.get("message", "")
        if "success" in message.lower():
            course_name = extract_course_name(original_message)
            response = f"✅ Attendance marked successfully for {course_name}!"
        else:
            response = f"There was an issue marking your attendance: {message}"

    elif tool_name == "get_attendance_records":
        records = result.get("records", [])
        if not records:
            response = "I couldn't find any attendance records for you. Make sure you've marked attendance for some classes first."
        else:
            response = "Here are your attendance records:\n\n"
            for record in records[:10]:  # Limit to 10 records
                course = record.get("course_name", "Unknown")
                date = record.get("marked_at", "Unknown")
                response += f"• {course} - {date}\n"
            if len(records) > 10:
                response += f"\n(Showing 10 most recent out of {len(records)} records)"

    elif tool_name == "get_unread_emails":
        emails = result.get("emails", [])
        if not emails:
            response = "You have no unread emails in your inbox."
        else:
            response = f"You have {len(emails)} unread email(s):\n\n"
            for i, email in enumerate(emails[:5], 1):  # Limit to 5 emails
                subject = email.get("subject", "No Subject")
                sender = email.get("from", "Unknown")
                snippet = email.get("snippet", "")[:100]
                response += f"{i}. **{subject}** from {sender}\n   {snippet}...\n\n"
            if len(emails) > 5:
                response += f"(Showing 5 most recent out of {len(emails)} emails)"

    elif tool_name == "draft_email":
        draft_id = result.get("draft_id")
        draft_url = result.get("draft_url")
        if draft_id:
            response = f"✅ Email draft created successfully!\n\nYou can review and send it here: {draft_url}"
        else:
            response = f"There was an issue creating your email draft: {result.get('message', 'Unknown error')}"

    elif tool_name == "get_upcoming_events":
        events = result.get("events", [])
        if not events:
            response = "You have no upcoming events in your calendar."
        else:
            response = f"You have {len(events)} upcoming event(s):\n\n"
            for i, event in enumerate(events[:5], 1):  # Limit to 5 events
                title = event.get("summary", "No Title")
                start_time = event.get("start", "Unknown time")
                location = event.get("location", "")
                location_str = f" at {location}" if location else ""
                response += f"{i}. **{title}** - {start_time}{location_str}\n"
            if len(events) > 5:
                response += f"\n(Showing 5 most recent out of {len(events)} events)"

    elif tool_name == "create_calendar_event":
        event_id = result.get("event_id")
        html_link = result.get("html_link")
        if event_id:
            response = f"✅ {result.get('message', 'Event created successfully!')}\n\nYou can view it here: {html_link}"
        else:
            response = f"There was an issue creating your calendar event: {result.get('message', 'Unknown error')}"

    else:
        response = f"Tool executed successfully, but I don't know how to format the response for {tool_name}."

    return response

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
        draft_email_tool,
        get_upcoming_events_tool,
        create_calendar_event_tool
    ]

async def get_llm_response_with_supabase(
    message: str,
    google_access_token: Optional[str] = None,
    user_id: Optional[int] = None,
    google_id: Optional[str] = None,
    conversation_id: Optional[str] = None
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
        if conversation_id:
            # Use conversation-specific history if available
            try:
                from app.core.db_client import get_messages_by_conversation
                messages = get_messages_by_conversation(conversation_id)
                # Format messages for LLM
                if messages:
                    conversation_context = "\n".join([
                        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                        for msg in messages[-10:]  # Last 10 messages
                    ])
            except:
                pass  # Fall back to user-based history if conversation-specific fails

        if not conversation_context and user_id:
            # Fallback to user-based history
            conversation_context = format_conversation_for_llm(user_id, limit=10)

        # Detect user intent
        intent = detect_intent(message)
        logger.info(f"🎯 INTENT DETECTED: '{intent}' for message: '{message[:50]}...'")

        # Force tool execution based on intent - never use direct LLM response
        tool_results = []

        if intent == "study":
            # Always use RAG for study queries
            logger.info("📚 STUDY INTENT: Forcing get_study_material tool")
            tool_result = await execute_tool(
                "get_study_material",
                {"query": message},
                google_access_token=google_access_token,
                user_id=user_id,
                google_id=google_id
            )
            tool_results.append({
                "tool_name": "get_study_material",
                "tool_result": tool_result
            })

        elif intent == "career":
            # Extract field from message for career insights
            field = extract_career_field(message)
            logger.info(f"💼 CAREER INTENT: Forcing get_career_insights tool for field: {field}")
            tool_result = await execute_tool(
                "get_career_insights",
                {"field": field},
                google_access_token=google_access_token,
                user_id=user_id,
                google_id=google_id
            )
            tool_results.append({
                "tool_name": "get_career_insights",
                "tool_result": tool_result
            })

        elif intent == "attendance":
            # Determine if user wants to mark attendance or get records
            if any(word in message.lower() for word in ["mark", "present", "here", "attending"]):
                # Extract course name from message
                course_name = extract_course_name(message)
                logger.info(f"📝 ATTENDANCE INTENT: Forcing mark_attendance tool for course: {course_name}")
                tool_result = await execute_tool(
                    "mark_attendance",
                    {"course_name": course_name},
                    google_access_token=google_access_token,
                    user_id=user_id,
                    google_id=google_id
                )
            else:
                # Default to getting attendance records
                course_name = extract_course_name(message) or ""
                logger.info(f"📊 ATTENDANCE INTENT: Forcing get_attendance_records tool for course: {course_name}")
                tool_result = await execute_tool(
                    "get_attendance_records",
                    {"course_name": course_name},
                    google_access_token=google_access_token,
                    user_id=user_id,
                    google_id=google_id
                )
            tool_results.append({
                "tool_name": "mark_attendance" if "mark" in message.lower() else "get_attendance_records",
                "tool_result": tool_result
            })

        elif intent == "email":
            # Determine if user wants to check emails or draft
            if any(word in message.lower() for word in ["draft", "write", "compose", "send"]):
                # Extract email details from message
                email_details = extract_email_details(message)
                logger.info(f"✉️ EMAIL INTENT: Forcing draft_email tool")
                tool_result = await execute_tool(
                    "draft_email",
                    email_details,
                    google_access_token=google_access_token,
                    user_id=user_id,
                    google_id=google_id
                )
            else:
                # Default to checking unread emails
                logger.info(f"📧 EMAIL INTENT: Forcing get_unread_emails tool")
                tool_result = await execute_tool(
                    "get_unread_emails",
                    {"max_results": 10},
                    google_access_token=google_access_token,
                    user_id=user_id,
                    google_id=google_id
                )
            tool_results.append({
                "tool_name": "draft_email" if any(word in message.lower() for word in ["draft", "write", "compose", "send"]) else "get_unread_emails",
                "tool_result": tool_result
            })

        elif intent == "calendar":
            # Determine if user wants to check events or create event
            if any(word in message.lower() for word in ["create", "add", "schedule", "book", "new"]):
                # For now, we'll need to extract event details from the message
                # In a production system, this could use more sophisticated NLP
                logger.info(f"📝 CALENDAR INTENT: Forcing create_calendar_event tool")
                # This is a simplified approach - in production you'd want better parsing
                tool_result = await execute_tool(
                    "create_calendar_event",
                    {
                        "title": "New Event",  # Would need better extraction
                        "start_time": "",  # Would need better extraction
                        "end_time": "",  # Would need better extraction
                        "description": message,
                        "location": ""
                    },
                    google_access_token=google_access_token,
                    user_id=user_id,
                    google_id=google_id
                )
            else:
                # Default to getting upcoming events
                logger.info(f"📅 CALENDAR INTENT: Forcing get_upcoming_events tool")
                tool_result = await execute_tool(
                    "get_upcoming_events",
                    {"max_results": 10},
                    google_access_token=google_access_token,
                    user_id=user_id,
                    google_id=google_id
                )
            tool_results.append({
                "tool_name": "create_calendar_event" if any(word in message.lower() for word in ["create", "add", "schedule", "book", "new"]) else "get_upcoming_events",
                "tool_result": tool_result
            })

        else:  # general intent
            # For general queries, try RAG first as fallback
            logger.info("🔍 GENERAL INTENT: Trying get_study_material tool as fallback")
            tool_result = await execute_tool(
                "get_study_material",
                {"query": message},
                google_access_token=google_access_token,
                user_id=user_id,
                google_id=google_id
            )
            tool_results.append({
                "tool_name": "get_study_material",
                "tool_result": tool_result
            })

        # Process tool results and generate response
        assistant_reply = await process_tool_results(tool_results, intent, message, conversation_context)

        # Store AI response in chat memory
        if user_id:
            add_message(user_id, 'ai', assistant_reply)

        return assistant_reply

    except Exception as e:
        error_message = f"Error: {str(e)}"
        logger.error(f"💥 LLM RESPONSE ERROR: {str(e)}")

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
