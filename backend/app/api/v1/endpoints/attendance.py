import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.api.v1.endpoints.auth.google import verify_supabase_token
from app.tools.attendance_tools_supabase import get_attendance_summary

router = APIRouter()

# Set up logger for attendance endpoints
logger = logging.getLogger(__name__)

@router.post("/mark")
async def mark_attendance_endpoint(
    request: Dict[str, str],
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Mark attendance for a course.
    """
    logger.info(f"Mark attendance endpoint called for user: {user.get('google_id', 'unknown')}, request: {request}")

    try:
        course_name = request.get('course_name')
        if not course_name:
            logger.warning("course_name is required but not provided")
            raise HTTPException(status_code=400, detail="course_name is required")

        logger.debug(f"Marking attendance for course: {course_name}")

        # Get user's internal ID from Google ID
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('id').eq('google_id', user["google_id"]).single().execute()

        # Handle response format
        if isinstance(user_data, dict) and user_data.get('data'):
            user_info = user_data['data']
        else:
            user_info = None

        if not user_info:
            logger.error(f"User not found for google_id: {user['google_id']}")
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_info['id']
        logger.debug(f"Retrieved user_id: {user_id} for google_id: {user['google_id']}")

        # Mark attendance using the tool
        from app.tools.attendance_tools_supabase import mark_attendance
        logger.debug(f"Calling mark_attendance tool for user_id: {user_id}, course: {course_name}")
        result = mark_attendance(course_name, str(user_id))
        logger.debug(f"Mark attendance result: {result}")

        if not result['success']:
            logger.error(f"Failed to mark attendance: {result['error']}")
            raise HTTPException(status_code=500, detail=result['error'])

        logger.info(f"Successfully marked attendance for user {user_id}, course {course_name}")
        return {
            "message": result['message'],
            "attendance_data": result['attendance_data']
        }

    except HTTPException:
        logger.exception("HTTPException in mark attendance endpoint")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in mark attendance endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to mark attendance: {str(e)}")

@router.get("/target")
async def get_attendance_target(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get the user's target attendance percentage.
    """
    logger.info(f"Get attendance target endpoint called for user: {user.get('google_id', 'unknown')}")

    try:
        # Get user's target from database
        logger.debug(f"Querying target_attendance for google_id: {user['google_id']}")
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('target_attendance').eq('google_id', user["google_id"]).single().execute()

        # Handle response format
        if isinstance(user_data, dict) and user_data.get('data'):
            user_info = user_data['data']
        else:
            user_info = None

        if not user_info:
            logger.error(f"User not found for google_id: {user['google_id']}")
            raise HTTPException(status_code=404, detail="User not found")

        target_attendance = float(user_info['target_attendance'] or 75.0)
        logger.info(f"Retrieved target_attendance: {target_attendance} for user {user['google_id']}")

        return {
            "target_attendance": target_attendance
        }

    except HTTPException:
        logger.exception("HTTPException in get attendance target endpoint")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get attendance target endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get attendance target: {str(e)}")

@router.post("/target")
async def set_attendance_target(
    request: Dict[str, float],
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Set the user's target attendance percentage.
    """
    logger.info(f"Set attendance target endpoint called for user: {user.get('google_id', 'unknown')}, request: {request}")

    try:
        target_attendance = request.get('target_attendance')
        if target_attendance is None or not (0 <= target_attendance <= 100):
            logger.warning(f"Invalid target_attendance value: {target_attendance}")
            raise HTTPException(status_code=400, detail="target_attendance must be between 0 and 100")

        logger.debug(f"Setting target_attendance to {target_attendance} for google_id: {user['google_id']}")

        # Update user's target in database
        from app.core.supabase_client import supabase
        result = supabase.table('users').update({
            'target_attendance': target_attendance
        }).eq('google_id', user["google_id"]).execute()

        if not result.data:
            logger.error(f"User not found for google_id: {user['google_id']}")
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"Successfully set target_attendance to {target_attendance} for user {user['google_id']}")
        return {
            "message": f"Target attendance set to {target_attendance}%",
            "target_attendance": target_attendance
        }

    except HTTPException:
        logger.exception("HTTPException in set attendance target endpoint")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in set attendance target endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to set attendance target: {str(e)}")

@router.get("/records")
async def get_attendance_records(
    course_name: str = None,
    user: Dict[str, Any] = Depends(verify_supabase_token)
):
    """
    Get attendance records for the user, optionally filtered by course.
    """
    logger.info(f"Get attendance records endpoint called for user: {user.get('google_id', 'unknown')}, course_filter: {course_name}")

    try:
        # Get user's internal ID from Google ID
        logger.debug(f"Querying user data for google_id: {user['google_id']}")
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('id').eq('google_id', user["google_id"]).single().execute()

        # Handle response format
        if isinstance(user_data, dict) and user_data.get('data'):
            user_info = user_data['data']
        else:
            user_info = None

        if not user_info:
            logger.error(f"User not found for google_id: {user['google_id']}")
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_info['id']
        logger.debug(f"Retrieved user_id: {user_id} for google_id: {user['google_id']}")

        # Get attendance records
        from app.tools.attendance_tools_supabase import get_attendance_records
        logger.debug(f"Calling get_attendance_records for user_id: {user_id}, course_name: {course_name}")
        records_result = get_attendance_records(str(user_id), course_name)
        logger.debug(f"Attendance records result: {records_result}")

        if not records_result['success']:
            logger.error(f"Failed to get attendance records: {records_result['error']}")
            raise HTTPException(status_code=500, detail=records_result['error'])

        logger.info(f"Successfully retrieved {records_result.get('total_records', 0)} attendance records for user {user_id}")
        return records_result

    except HTTPException:
        logger.exception("HTTPException in get attendance records endpoint")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get attendance records endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get attendance records: {str(e)}")

@router.get("/stats")
async def get_attendance_stats(user: Dict[str, Any] = Depends(verify_supabase_token)):
    """
    Get attendance statistics for the user.
    """
    logger.info(f"Attendance stats endpoint called for user: {user.get('google_id', 'unknown')}")

    try:
        # Get user's internal ID from Google ID
        logger.debug(f"Querying user data for google_id: {user['google_id']}")
        from app.core.supabase_client import supabase
        user_data = supabase.table('users').select('id, target_attendance').eq('google_id', user["google_id"]).single().execute()

        logger.debug(f"User data query result: {user_data}")

        # Handle response format
        if isinstance(user_data, dict) and user_data.get('data'):
            user_info = user_data['data']
            logger.debug(f"User data: {user_info}")
        else:
            user_info = None
            logger.warning(f"Unexpected user_data format: {user_data}")

        if not user_info:
            logger.error(f"User not found for google_id: {user['google_id']}")
            raise HTTPException(status_code=404, detail="User not found")

        user_id = user_info['id']
        target_attendance = float(user_info['target_attendance'] or 75.0)
        logger.info(f"Retrieved user_id: {user_id}, target_attendance: {target_attendance}")

        # Get attendance summary
        logger.debug(f"Calling get_attendance_summary for user_id: {user_id}")
        summary_result = get_attendance_summary(str(user_id))
        logger.debug(f"Attendance summary result: {summary_result}")

        if not summary_result['success']:
            logger.error(f"Failed to get attendance summary: {summary_result['error']}")
            raise HTTPException(status_code=500, detail=summary_result['error'])

        # Calculate overall stats
        total_attendance = sum(course['total_attendance'] for course in summary_result['summary'])
        total_courses = len(summary_result['summary'])
        logger.info(f"Total attendance: {total_attendance}, Total courses: {total_courses}")

        # For demo purposes, assume 15 classes per course for percentage calculation
        # In a real app, this would be configurable per course
        assumed_classes_per_course = 15
        total_possible = total_courses * assumed_classes_per_course
        attendance_percentage = (total_attendance / total_possible * 100) if total_possible > 0 else 0
        logger.debug(f"Calculated stats - total_possible: {total_possible}, attendance_percentage: {attendance_percentage}")

        # Calculate total missed and allowed absences
        total_missed = total_possible - total_attendance
        allowed_missed = int((100 - target_attendance) / 100 * total_possible)
        allowed_absences_left = max(0, allowed_missed - total_missed)
        logger.debug(f"Absence calculations - total_missed: {total_missed}, allowed_missed: {allowed_missed}, allowed_absences_left: {allowed_absences_left}")

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

        logger.info(f"Successfully calculated attendance stats for user {user_id}")
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
        logger.exception("HTTPException in attendance stats endpoint")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in attendance stats endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get attendance stats: {str(e)}")

@router.get("/health")
async def attendance_health_check():
    """Health check for attendance service."""
    return {"status": "healthy", "service": "attendance"}
