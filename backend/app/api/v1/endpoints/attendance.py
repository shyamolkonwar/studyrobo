from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.api.v1.endpoints.auth.google import verify_supabase_token
from app.tools.attendance_tools_supabase import get_attendance_summary

router = APIRouter()

@router.post("/mark")
async def mark_attendance_endpoint(
    request: Dict[str, str],
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Mark attendance for a course.
    """
    try:
        course_name = request.get('course_name')
        if not course_name:
            raise HTTPException(status_code=400, detail="course_name is required")

        # Get user's internal ID from Google ID
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('id').eq('google_id', user["google_id"]).single()
        
        # Handle both dictionary and object response formats
        if isinstance(user_data, dict):
            user_info = user_data.get('data')
        elif hasattr(user_data, 'data'):
            user_info = user_data.data
        else:
            user_info = None
            
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_info['id']

        # Mark attendance using the tool
        from app.tools.attendance_tools_supabase import mark_attendance
        result = mark_attendance(course_name, str(user_id))

        if not result['success']:
            raise HTTPException(status_code=500, detail=result['error'])

        return {
            "message": result['message'],
            "attendance_data": result['attendance_data']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark attendance: {str(e)}")

@router.get("/stats")
async def get_attendance_stats(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get attendance statistics for the user.
    """
    try:
        # Get user's internal ID from Google ID
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('id').eq('google_id', user["google_id"]).single()
        
        # Handle both dictionary and object response formats
        if isinstance(user_data, dict):
            user_info = user_data.get('data')
        elif hasattr(user_data, 'data'):
            user_info = user_data.data
        else:
            user_info = None
            
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_info['id']

        # Get attendance summary
        summary_result = get_attendance_summary(str(user_id))

        if not summary_result['success']:
            raise HTTPException(status_code=500, detail=summary_result['error'])

        # Calculate overall stats
        total_attendance = sum(course['total_attendance'] for course in summary_result['summary'])
        total_courses = len(summary_result['summary'])

        # For demo purposes, assume 15 classes per course for percentage calculation
        # In a real app, this would be configurable per course
        assumed_classes_per_course = 15
        total_possible = total_courses * assumed_classes_per_course
        attendance_percentage = (total_attendance / total_possible * 100) if total_possible > 0 else 0

        return {
            "total_attendance": total_attendance,
            "total_courses": total_courses,
            "attendance_percentage": round(attendance_percentage, 1),
            "courses": summary_result['summary']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance stats: {str(e)}")

@router.get("/health")
async def attendance_health_check():
    """Health check for attendance service."""
    return {"status": "healthy", "service": "attendance"}
