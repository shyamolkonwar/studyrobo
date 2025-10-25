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

@router.get("/target")
async def get_attendance_target(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get the user's target attendance percentage.
    """
    try:
        # Get user's target from database
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('target_attendance').eq('google_id', user["google_id"]).single()

        # Handle both dictionary and object response formats
        if isinstance(user_data, dict):
            user_info = user_data.get('data')
        elif hasattr(user_data, 'data'):
            user_info = user_data.data
        else:
            user_info = None

        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "target_attendance": float(user_info['target_attendance'] or 75.0)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance target: {str(e)}")

@router.post("/target")
async def set_attendance_target(
    request: Dict[str, float],
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Set the user's target attendance percentage.
    """
    try:
        target_attendance = request.get('target_attendance')
        if target_attendance is None or not (0 <= target_attendance <= 100):
            raise HTTPException(status_code=400, detail="target_attendance must be between 0 and 100")

        # Update user's target in database
        from app.core.supabase_client import supabase
        result = supabase.table('users').update({
            'target_attendance': target_attendance
        }).eq('google_id', user["google_id"]).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "message": f"Target attendance set to {target_attendance}%",
            "target_attendance": target_attendance
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set attendance target: {str(e)}")

@router.get("/records")
async def get_attendance_records(
    course_name: str = None,
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Get attendance records for the user, optionally filtered by course.
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

        # Get attendance records
        from app.tools.attendance_tools_supabase import get_attendance_records
        records_result = get_attendance_records(str(user_id), course_name)

        if not records_result['success']:
            raise HTTPException(status_code=500, detail=records_result['error'])

        return records_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance records: {str(e)}")

@router.get("/stats")
async def get_attendance_stats(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get attendance statistics for the user.
    """
    try:
        # Get user's internal ID from Google ID
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('id, target_attendance').eq('google_id', user["google_id"]).single()

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
        target_attendance = float(user_info['target_attendance'] or 75.0)

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

        # Calculate total missed and allowed absences
        total_missed = total_possible - total_attendance
        allowed_missed = int((100 - target_attendance) / 100 * total_possible)
        allowed_absences_left = max(0, allowed_missed - total_missed)

        # Calculate course breakdown with percentages and status
        course_breakdown = []
        for course in summary_result['summary']:
            course_percentage = (course['total_attendance'] / assumed_classes_per_course * 100) if assumed_classes_per_course > 0 else 0
            course_missed = assumed_classes_per_course - course['total_attendance']
            course_allowed_missed = int((100 - target_attendance) / 100 * assumed_classes_per_course)
            course_allowed_left = max(0, course_allowed_missed - course_missed)

            status = "Safe" if course_percentage >= target_attendance else "At Risk"

            course_breakdown.append({
                "course_name": course['course_name'],
                "percentage": round(course_percentage, 1),
                "ratio": f"{course['total_attendance']} / {assumed_classes_per_course}",
                "status": status,
                "allowed_absences_left": course_allowed_left
            })

        return {
            "target_attendance": target_attendance,
            "overall_percentage": round(attendance_percentage, 1),
            "total_attended": total_attendance,
            "total_possible": total_possible,
            "total_missed": total_missed,
            "allowed_absences_left": allowed_absences_left,
            "courses": course_breakdown
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attendance stats: {str(e)}")

@router.get("/health")
async def attendance_health_check():
    """Health check for attendance service."""
    return {"status": "healthy", "service": "attendance"}
