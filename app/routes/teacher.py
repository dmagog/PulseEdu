"""
Teacher routes for teacher dashboard and course management.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.services.teacher_service import TeacherService

router = APIRouter(prefix="/teacher", tags=["teacher"])
logger = logging.getLogger("app.teacher")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize teacher service
teacher_service = TeacherService()


@router.get("/", response_class=HTMLResponse)
async def teacher_dashboard(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher dashboard with course overview and risk students.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with teacher dashboard
    """
    logger.info("Teacher dashboard requested")
    
    try:
        # Get teacher dashboard data
        dashboard_data = teacher_service.get_teacher_dashboard(db)
        
        if "error" in dashboard_data:
            raise HTTPException(status_code=500, detail=dashboard_data["error"])
        
        return templates.TemplateResponse("teacher/dashboard.html", {
            "request": request,
            "title": "Панель преподавателя",
            "dashboard": dashboard_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading teacher dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/course/{course_id}", response_class=HTMLResponse)
async def course_details(
    course_id: int,
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Detailed course view with students and progress.
    
    Args:
        course_id: Course ID
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with course details
    """
    logger.info(f"Course details requested for course: {course_id}")
    
    try:
        # Get course details
        course_data = teacher_service.get_course_details(course_id, db)
        
        if "error" in course_data:
            raise HTTPException(status_code=404, detail=course_data["error"])
        
        return templates.TemplateResponse("teacher/course.html", {
            "request": request,
            "title": f"Курс: {course_data['course'].name}",
            "course_data": course_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading course details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/students", response_class=HTMLResponse)
async def students_overview(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Students overview with risk analysis.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with students overview
    """
    logger.info("Students overview requested")
    
    try:
        # Get all students with their progress
        students = db.query(Student).all()
        
        student_data = []
        for student in students:
            # Get student progress
            progress = teacher_service.metrics_service.calculate_student_progress(student.id, db)
            
            if "error" not in progress:
                student_data.append({
                    "student_id": student.id,
                    "student_name": student.name or f"Студент {student.id}",
                    "overall_progress": progress.get("overall_progress", 0),
                    "attendance_rate": progress.get("attendance", {}).get("percentage", 0),
                    "completion_rate": progress.get("tasks", {}).get("percentage", 0),
                    "courses_count": len(progress.get("courses", [])),
                    "status": "high_risk" if progress.get("overall_progress", 0) < 40 else "medium_risk" if progress.get("overall_progress", 0) < 70 else "good"
                })
        
        # Sort by overall progress
        student_data.sort(key=lambda x: x["overall_progress"])
        
        return templates.TemplateResponse("teacher/students.html", {
            "request": request,
            "title": "Обзор студентов",
            "students": student_data
        })
        
    except Exception as e:
        logger.error(f"Error loading students overview: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/dashboard")
async def get_teacher_dashboard_api(
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for teacher dashboard data.
    
    Args:
        db: Database session
        
    Returns:
        JSON with teacher dashboard data
    """
    logger.info("Teacher dashboard API requested")
    
    try:
        dashboard_data = teacher_service.get_teacher_dashboard(db)
        return {
            "status": "success",
            "data": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Error getting teacher dashboard API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/course/{course_id}")
async def get_course_details_api(
    course_id: int,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for course details.
    
    Args:
        course_id: Course ID
        db: Database session
        
    Returns:
        JSON with course details
    """
    logger.info(f"Course details API requested for course: {course_id}")
    
    try:
        course_data = teacher_service.get_course_details(course_id, db)
        return {
            "status": "success",
            "data": course_data
        }
        
    except Exception as e:
        logger.error(f"Error getting course details API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
