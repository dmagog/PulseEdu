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
from sqlalchemy import func, and_, case

from app.database.session import get_session
from app.models.student import Student, Course, Task, Attendance, TaskCompletion, Lesson
from app.services.teacher_service import TeacherService
from app.services.cluster_service import ClusterService
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/teacher", tags=["teacher"])
logger = logging.getLogger("app.teacher")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize services
teacher_service = TeacherService()
cluster_service = ClusterService()
rbac_service = RBACService()


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
    Detailed course view with students and progress, grouped by student groups.
    
    Args:
        course_id: Course ID
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with course details
    """
    logger.info(f"Course details requested for course: {course_id}")
    
    try:
        # Get course information
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Get students grouped by group_id with real data (simplified approach)
        students_by_group = {}
        
        try:
            # Get all students first
            all_students = db.query(Student).all()
            
            for student in all_students:
                group_id = student.group_id or "Без группы"
                if group_id not in students_by_group:
                    students_by_group[group_id] = []
                
                # Simplified progress calculation for now
                # TODO: Implement real calculations when data structure is stable
                attendance_rate = 75.0  # Mock data
                completion_rate = 80.0  # Mock data
                overall_progress = (attendance_rate + completion_rate) / 2
                
                students_by_group[group_id].append({
                    'student': student,
                    'attendance_rate': round(attendance_rate, 1),
                    'completion_rate': round(completion_rate, 1),
                    'overall_progress': round(overall_progress, 1),
                    'status': 'high_risk' if overall_progress < 40 else 'medium_risk' if overall_progress < 70 else 'good'
                })
        except Exception as e:
            logger.warning(f"Error loading students: {e}")
            students_by_group = {"Без группы": []}
        
        # Calculate real course statistics
        total_lessons = db.query(Lesson).filter(Lesson.course_id == course_id).count()
        total_tasks = db.query(Task).filter(Task.course_id == course_id).count()
        
        # Get cluster data if available
        cluster_groups = {}
        try:
            clusters = cluster_service.get_course_clusters(course_id, db)
            for cluster in clusters:
                if cluster.cluster_label not in cluster_groups:
                    cluster_groups[cluster.cluster_label] = []
                cluster_groups[cluster.cluster_label].append({
                    "student_id": cluster.student_id,
                    "cluster_score": cluster.cluster_score,
                    "attendance_rate": cluster.attendance_rate,
                    "completion_rate": cluster.completion_rate,
                    "overall_progress": cluster.overall_progress
                })
        except Exception as e:
            logger.warning(f"Could not load cluster data: {e}")
            cluster_groups = {}
        
        return templates.TemplateResponse("teacher/course_simple.html", {
            "request": request,
            "title": f"Курс: {course.name}",
            "course": course,
            "students_by_group": students_by_group,
            "total_lessons": total_lessons,
            "total_tasks": total_tasks,
            "cluster_groups": cluster_groups
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


@router.get("/api/course/{course_id}/clusters")
async def get_course_clusters_api(
    course_id: int,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for course clusters.
    
    Args:
        course_id: Course ID
        db: Database session
        
    Returns:
        JSON with course clusters
    """
    logger.info(f"Course clusters API requested for course: {course_id}")
    
    try:
        clusters = cluster_service.get_course_clusters(course_id, db)
        
        # Group clusters by label
        cluster_groups = {}
        for cluster in clusters:
            if cluster.cluster_label not in cluster_groups:
                cluster_groups[cluster.cluster_label] = []
            
            cluster_groups[cluster.cluster_label].append({
                "student_id": cluster.student_id,
                "cluster_score": cluster.cluster_score,
                "attendance_rate": cluster.attendance_rate,
                "completion_rate": cluster.completion_rate,
                "overall_progress": cluster.overall_progress,
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None
            })
        
        return {
            "status": "success",
            "data": {
                "course_id": course_id,
                "clusters": cluster_groups,
                "total_clusters": len(clusters)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting course clusters API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/recommendations", response_class=HTMLResponse)
async def teacher_recommendations(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher recommendations management page.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with recommendations management page
    """
    logger.info("Teacher recommendations page requested")
    
    try:
        return templates.TemplateResponse(
            "teacher/recommendations.html",
            {
                "request": request,
                "title": "Управление рекомендациями"
            }
        )
        
    except Exception as e:
        logger.error(f"Error rendering teacher recommendations page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/courses", response_class=HTMLResponse)
async def teacher_courses(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher courses page.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with teacher courses
    """
    logger.info("Teacher courses page requested")
    
    try:
        # Get teacher courses data
        courses = teacher_service.get_teacher_courses(db)
        
        return templates.TemplateResponse("teacher/courses.html", {
            "request": request,
            "title": "Мои курсы",
            "courses": courses
        })
        
    except Exception as e:
        logger.error(f"Error loading teacher courses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/students", response_class=HTMLResponse)
async def teacher_students(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher students page.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with teacher students
    """
    logger.info("Teacher students page requested")
    
    try:
        # Get teacher students data
        students = teacher_service.get_teacher_students(db)
        courses = teacher_service.get_teacher_courses(db)
        
        return templates.TemplateResponse("teacher/students.html", {
            "request": request,
            "title": "Мои студенты",
            "students": students,
            "courses": courses
        })
        
    except Exception as e:
        logger.error(f"Error loading teacher students: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics", response_class=HTMLResponse)
async def teacher_analytics(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher analytics page.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with teacher analytics
    """
    logger.info("Teacher analytics page requested")
    
    try:
        # Get teacher analytics data
        analytics = teacher_service.get_teacher_analytics(db)
        courses = teacher_service.get_teacher_courses(db)
        course_analytics = teacher_service.get_course_analytics(db)
        
        return templates.TemplateResponse("teacher/analytics.html", {
            "request": request,
            "title": "Аналитика",
            "analytics": analytics,
            "courses": courses,
            "course_analytics": course_analytics,
            "course_names": [course["name"] for course in course_analytics],
            "course_progress": [course["avg_progress"] for course in course_analytics],
            "attendance_dates": ["Неделя 1", "Неделя 2", "Неделя 3", "Неделя 4"],
            "attendance_values": [85, 88, 82, 90],
            "task_dates": ["Неделя 1", "Неделя 2", "Неделя 3", "Неделя 4"],
            "task_completion_values": [12, 18, 15, 22]
        })
        
    except Exception as e:
        logger.error(f"Error loading teacher analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
