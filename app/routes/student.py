"""
Student routes for student dashboard and course management.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.services.student_service import StudentService

router = APIRouter(prefix="/student", tags=["student"])
logger = logging.getLogger("app.student")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize student service
student_service = StudentService()


@router.get("/", response_class=HTMLResponse)
async def student_dashboard(
    request: Request,
    student_id: str = Query(default="01", description="Student ID"),
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Student dashboard with course cards, activity feed, and deadlines.
    
    Args:
        request: FastAPI request object
        student_id: Student ID (default: "01" for testing)
        db: Database session
        
    Returns:
        HTML response with student dashboard
    """
    logger.info(f"Student dashboard requested for student: {student_id}")
    
    try:
        # Get student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get student progress and data
        progress_data = student_service.get_student_progress(student_id, db)
        activity_feed = student_service.get_activity_feed(student_id, db)
        upcoming_deadlines = student_service.get_upcoming_deadlines(student_id, db)
        
        return templates.TemplateResponse("student/dashboard.html", {
            "request": request,
            "title": f"Панель студента - {student_id}",
            "student": student,
            "progress": progress_data,
            "activity_feed": activity_feed,
            "deadlines": upcoming_deadlines
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading student dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/courses", response_class=HTMLResponse)
async def student_courses(
    request: Request,
    student_id: str = Query(default="01", description="Student ID"),
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Student courses page with detailed course information.
    
    Args:
        request: FastAPI request object
        student_id: Student ID
        db: Database session
        
    Returns:
        HTML response with student courses
    """
    logger.info(f"Student courses requested for student: {student_id}")
    
    try:
        # Get student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get detailed course data
        course_data = student_service.get_detailed_course_data(student_id, db)
        
        return templates.TemplateResponse("student/courses.html", {
            "request": request,
            "title": f"Курсы - {student_id}",
            "student": student,
            "courses": course_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading student courses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/progress", response_class=HTMLResponse)
async def student_progress(
    request: Request,
    student_id: str = Query(default="01", description="Student ID"),
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Student progress page with detailed analytics.
    
    Args:
        request: FastAPI request object
        student_id: Student ID
        db: Database session
        
    Returns:
        HTML response with student progress page
    """
    logger.info(f"Student progress page requested for student: {student_id}")
    
    try:
        # Get student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get progress data
        progress_data = student_service.get_student_progress(student_id, db)
        progress_details = student_service.get_detailed_progress(student_id, db)
        
        return templates.TemplateResponse("student/progress.html", {
            "request": request,
            "title": f"Прогресс - {student_id}",
            "student": student,
            "progress": progress_data,
            "progress_details": progress_details
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading student progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/assignments", response_class=HTMLResponse)
async def student_assignments(
    request: Request,
    student_id: str = Query(default="01", description="Student ID"),
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Student assignments page.
    
    Args:
        request: FastAPI request object
        student_id: Student ID
        db: Database session
        
    Returns:
        HTML response with student assignments
    """
    logger.info(f"Student assignments page requested for student: {student_id}")
    
    try:
        # Get student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get assignments and courses data
        assignments = student_service.get_student_assignments(student_id, db)
        courses = student_service.get_student_courses(student_id, db)
        
        return templates.TemplateResponse("student/assignments.html", {
            "request": request,
            "title": f"Задания - {student_id}",
            "student": student,
            "assignments": assignments,
            "courses": courses
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading student assignments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/schedule", response_class=HTMLResponse)
async def student_schedule(
    request: Request,
    student_id: str = Query(default="01", description="Student ID"),
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Student schedule page.
    
    Args:
        request: FastAPI request object
        student_id: Student ID
        db: Database session
        
    Returns:
        HTML response with student schedule
    """
    logger.info(f"Student schedule page requested for student: {student_id}")
    
    try:
        # Get student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get schedule data
        schedule = student_service.get_student_schedule(student_id, db)
        upcoming_events = student_service.get_upcoming_events(student_id, db)
        
        return templates.TemplateResponse("student/schedule.html", {
            "request": request,
            "title": f"Расписание - {student_id}",
            "student": student,
            "schedule": schedule,
            "upcoming_events": upcoming_events
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading student schedule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/recommendations", response_class=HTMLResponse)
async def student_recommendations(
    request: Request,
    student_id: str = Query(default="01", description="Student ID"),
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Student recommendations page.
    
    Args:
        request: FastAPI request object
        student_id: Student ID
        db: Database session
        
    Returns:
        HTML response with student recommendations
    """
    logger.info(f"Student recommendations page requested for student: {student_id}")
    
    try:
        # Get student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get recommendations data
        recommendations = student_service.get_student_recommendations(student_id, db)
        recommendation_history = student_service.get_recommendation_history(student_id, db)
        
        return templates.TemplateResponse("student/recommendations.html", {
            "request": request,
            "title": f"Рекомендации - {student_id}",
            "student": student,
            "recommendations": recommendations,
            "recommendation_history": recommendation_history
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading student recommendations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/progress/{student_id}")
async def get_student_progress_api(
    student_id: str,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for student progress data.
    
    Args:
        student_id: Student ID
        db: Database session
        
    Returns:
        JSON with student progress data
    """
    logger.info(f"Student progress API requested for student: {student_id}")
    
    try:
        progress_data = student_service.get_student_progress(student_id, db)
        return {
            "status": "success",
            "student_id": student_id,
            "data": progress_data
        }
        
    except Exception as e:
        logger.error(f"Error getting student progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
