import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

# Simple in-memory storage for demo (in production, use a proper database)
attendance_store = {}

def mark_attendance(course_name: str, student_name: str = None) -> Dict[str, Any]:
    """
    Mark attendance for a specific course and student.

    This function records attendance data in Google Sheets and returns confirmation.
    For demo purposes, also maintains local storage.

    Args:
        course_name (str): Name of the course (e.g., "CS101", "Math201")
        student_name (str, optional): Name of the student (if None, uses "default_student")

    Returns:
        Dict[str, Any]: Confirmation of attendance marking
    """
    try:
        # Get Google Sheets credentials
        if student_name is None:
            student_name = "default_student"

        # Try to connect to Google Sheets
        service_account_info = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")

        if service_account_info:
            # Parse the service account info
            try:
                creds_info = json.loads(service_account_info)
                scope = ['https://www.googleapis.com/auth/spreadsheets.readonly']
                creds = Credentials.from_service_account_info(creds_info, scopes=scope)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Invalid service account format: {str(e)}",
                    "course": course_name,
                    "student": student_name
                }

            # Authorize and open the spreadsheet
            gc = gspread.authorize(creds)
            sheet = gc.open_by_url(os.getenv("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/1ABC123/edit"))

            # Get current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Find or create the appropriate worksheet
            try:
                worksheet = sheet.worksheet(course_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=course_name, rows="100")

            # Find the next empty row
            try:
                row = len(worksheet.get_all_values()) + 1
            except:
                row = 1

            # Mark attendance
            worksheet.append_row([student_name, "Present", timestamp, course_name])

            # Also store locally for backup
            attendance_key = f"{course_name}_{student_name}"
            attendance_store[attendance_key] = {
                "student": student_name,
                "course": course_name,
                "date": timestamp,
                "status": "Present"
            }

            return {
                "success": True,
                "message": f"Successfully marked attendance for {student_name} in {course_name}",
                "attendance_data": {
                    "student": student_name,
                    "course": course_name,
                    "date": timestamp,
                    "status": "Present",
                    "sheet_url": os.getenv("GOOGLE_SHEET_URL", "Not configured")
                }
            }

        except Exception as e:
            # Fallback to local storage only
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            attendance_key = f"{course_name}_{student_name}"
            attendance_store[attendance_key] = {
                "student": student_name,
                "course": course_name,
                "date": timestamp,
                "status": "Present"
            }

            return {
                "success": True,
                "message": f"Attendance marked locally for {student_name} in {course_name}",
                "warning": "Google Sheets not available - using local storage",
                "attendance_data": {
                    "student": student_name,
                    "course": course_name,
                    "date": timestamp,
                    "status": "Present"
                }
            }

def get_attendance_records(course_name: str = None, student_name: str = None) -> Dict[str, Any]:
    """
    Retrieve attendance records for a specific course or student.

    Args:
        course_name (str, optional): Filter by course name
        student_name (str, optional): Filter by student name

    Returns:
        Dict[str, Any]: Attendance records
    """
    try:
        records = []

        # Filter attendance records
        for key, record in attendance_store.items():
            if course_name and course_name.lower() not in key.lower():
                continue
            if student_name and student_name.lower() not in record.get('student', '').lower():
                continue

            records.append({
                "key": key,
                "student": record.get('student'),
                "course": record.get('course'),
                "date": record.get('date'),
                "status": record.get('status')
            })

        return {
            "success": True,
            "records": records,
            "total_records": len(records),
            "filter_applied": {
                "course": course_name,
                "student": student_name
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "records": []
        }

# Tool definition for OpenAI function calling
mark_attendance_tool = {
    "type": "function",
    "function": {
        "name": "mark_attendance",
        "description": "Mark attendance for a specific course. Records student presence in Google Sheets or local storage if Sheets is not available.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_name": {
                    "type": "string",
                    "description": "The name of the course (e.g., 'CS101', 'Math201', 'Physics101')"
                },
                "student_name": {
                    "type": "string",
                    "description": "The name of the student (optional, defaults to 'default_student')"
                }
            },
            "required": ["course_name"]
        }
    }
}

get_attendance_records_tool = {
    "type": "function",
    "function": {
        "name": "get_attendance_records",
        "description": "Retrieve attendance records filtered by course name or student name.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_name": {
                    "type": "string",
                    "description": "Filter records by course name (optional)"
                },
                "student_name": {
                    "type": "string",
                    "description": "Filter records by student name (optional)"
                }
            },
            "required": []
        }
    }
}