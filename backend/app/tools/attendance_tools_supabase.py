"""
Attendance tools using database
Replaces Google Sheets integration with database table storage
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from app.core.db_client import mark_attendance as db_mark_attendance, execute_query
from app.core.supabase_client import supabase

def mark_attendance(course_name: str, user_id: str) -> Dict[str, Any]:
    """
    Mark attendance for a specific course and user using database.

    This function records attendance data in database and returns confirmation.
    Much faster and more reliable than Google Sheets integration.

    Args:
        course_name (str): Name of the course (e.g., "CS101", "Math201")
        user_id (str): The user's UUID from Supabase Auth

    Returns:
        Dict[str, Any]: Confirmation of attendance marking
    """
    try:
        # Convert user_id string to int for database (assuming it's a numeric ID)
        try:
            user_id_int = int(user_id)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid user_id format: {user_id}. Must be numeric.",
                "course": course_name,
                "user_id": user_id
            }

        # Mark attendance in database
        db_mark_attendance(user_id_int, course_name)

        # Get current timestamp
        timestamp = datetime.now().isoformat()

        return {
            "success": True,
            "message": f"Successfully marked attendance for course {course_name}",
            "attendance_data": {
                "user_id": user_id,
                "course": course_name,
                "marked_at": timestamp,
                "status": "Present"
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error marking attendance: {str(e)}",
            "course": course_name,
            "user_id": user_id
        }

def get_attendance_records(user_id: str, course_name: str = None) -> Dict[str, Any]:
    """
    Retrieve attendance records for a specific user from database.

    Args:
        user_id (str): The user's ID (will be converted to int)
        course_name (str, optional): Filter by course name

    Returns:
        Dict[str, Any]: Attendance records
    """
    try:
        # Convert user_id to int
        try:
            user_id_int = int(user_id)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid user_id format: {user_id}. Must be numeric.",
                "records": [],
                "user_id": user_id
            }

        # Build query
        if course_name:
            query = "SELECT id, user_id, course_name, marked_at FROM attendance WHERE user_id = %s AND course_name = %s ORDER BY marked_at DESC"
            params = (user_id_int, course_name)
        else:
            query = "SELECT id, user_id, course_name, marked_at FROM attendance WHERE user_id = %s ORDER BY marked_at DESC"
            params = (user_id_int,)

        # Execute query
        result = execute_query(query, params)

        # Format records
        records = []
        if result:
            for record in result:
                records.append({
                    "id": record['id'],
                    "course_name": record['course_name'],
                    "marked_at": str(record['marked_at']),
                    "date": str(record['marked_at']).split(' ')[0] if ' ' in str(record['marked_at']) else str(record['marked_at'])
                })

        return {
            "success": True,
            "records": records,
            "total_records": len(records),
            "user_id": user_id,
            "course_filter": course_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving attendance records: {str(e)}",
            "records": [],
            "user_id": user_id
        }

def get_attendance_summary(user_id: str) -> Dict[str, Any]:
    """
    Get a summary of attendance records grouped by course.

    Args:
        user_id (str): The user's UUID from Supabase Auth

    Returns:
        Dict[str, Any]: Attendance summary by course
    """
    try:
        # Get all attendance records for the user
        attendance_result = get_attendance_records(user_id)

        if not attendance_result['success']:
            return attendance_result

        records = attendance_result['records']

        # Group by course
        course_summary = {}
        for record in records:
            course = record['course_name']
            if course not in course_summary:
                course_summary[course] = {
                    'course_name': course,
                    'total_attendance': 0,
                    'last_marked': None,
                    'attendance_dates': []
                }

            course_summary[course]['total_attendance'] += 1
            course_summary[course]['attendance_dates'].append(record['date'])

            # Update last marked date if this is more recent
            if (course_summary[course]['last_marked'] is None or
                record['marked_at'] > course_summary[course]['last_marked']):
                course_summary[course]['last_marked'] = record['marked_at']

        # Convert to list and sort by course name
        summary_list = list(course_summary.values())
        summary_list.sort(key=lambda x: x['course_name'])

        return {
            "success": True,
            "summary": summary_list,
            "total_courses": len(summary_list),
            "total_attendance_events": len(records),
            "user_id": user_id
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating attendance summary: {str(e)}",
            "summary": [],
            "user_id": user_id
        }

# Tool definitions for OpenAI function calling
mark_attendance_tool = {
    "type": "function",
    "function": {
        "name": "mark_attendance",
        "description": "Mark attendance for a specific course using the user's ID. Records student presence in Supabase database quickly and reliably.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's UUID from Supabase Auth"
                },
                "course_name": {
                    "type": "string",
                    "description": "The name of the course (e.g., 'CS101', 'Math201', 'Physics101')"
                }
            },
            "required": ["user_id", "course_name"]
        }
    }
}

get_attendance_records_tool = {
    "type": "function",
    "function": {
        "name": "get_attendance_records",
        "description": "Retrieve attendance records for a user from Supabase, optionally filtered by course name.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's UUID from Supabase Auth"
                },
                "course_name": {
                    "type": "string",
                    "description": "Filter records by course name (optional)"
                }
            },
            "required": ["user_id"]
        }
    }
}

get_attendance_summary_tool = {
    "type": "function",
    "function": {
        "name": "get_attendance_summary",
        "description": "Get a summary of attendance records grouped by course for a user.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's UUID from Supabase Auth"
                }
            },
            "required": ["user_id"]
        }
    }
}
