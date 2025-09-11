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
        
        # Calculate real course statistics
        total_lessons = db.query(Lesson).filter(Lesson.course_id == course_id).count()
        total_tasks = db.query(Task).filter(Task.course_id == course_id).count()
        
        # Get cluster data if available first
        cluster_groups = {}
        cluster_data_by_student = {}
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
                # Store cluster data by student ID for status assignment
                cluster_data_by_student[cluster.student_id] = cluster.cluster_label
            
            # Sort clusters by progress (descending), then by student ID (ascending)
            # Simplified sorting for now - can be enhanced later with names
            for cluster_label in cluster_groups:
                cluster_groups[cluster_label].sort(
                    key=lambda x: (-x['overall_progress'], x['student_id'])
                )
        except Exception as e:
            logger.warning(f"Could not load cluster data: {e}")
            cluster_groups = {}
            cluster_data_by_student = {}
        
        # Get students grouped by group_id with real data
        students_by_group = {}
        
        try:
            # Get all students first
            all_students = db.query(Student).all()
            
            for student in all_students:
                group_id = student.group_id or "Без группы"
                if group_id not in students_by_group:
                    students_by_group[group_id] = []
                
                # Get real progress data from teacher service
                attendance_rate = teacher_service._calculate_student_attendance(student.id, db)
                completion_rate = teacher_service._calculate_student_completion_rate(student.id, db)
                overall_progress = teacher_service._calculate_student_progress(student.id, db)
                
                # Determine status based on cluster data if available, otherwise use fallback
                if student.id in cluster_data_by_student:
                    cluster_label = cluster_data_by_student[student.id]
                    if cluster_label == 'A':
                        status = 'good'
                    elif cluster_label == 'B':
                        status = 'medium_risk'
                    else:
                        status = 'high_risk'
                else:
                    # Fallback to progress-based status
                    status = 'high_risk' if overall_progress < 40 else 'medium_risk' if overall_progress < 70 else 'good'
                
                students_by_group[group_id].append({
                    'student': student,
                    'attendance_rate': round(attendance_rate, 1),
                    'completion_rate': round(completion_rate, 1),
                    'overall_progress': round(overall_progress, 1),
                    'status': status
                })
            
            # Sort students within each group alphabetically by name
            for group_id in students_by_group:
                students_by_group[group_id].sort(
                    key=lambda x: (x['student'].name or x['student'].id).lower()
                )
                
        except Exception as e:
            logger.warning(f"Error loading students: {e}")
            students_by_group = {"Без группы": []}
        
        return templates.TemplateResponse("teacher/course_simple.html", {
            "request": request,
            "title": f"Курс: {course.name}",
            "course": course,
            "students_by_group": students_by_group,
            "total_lessons": total_lessons,
            "total_tasks": total_tasks,
            "cluster_groups": cluster_groups,
            "cluster_data_by_student": cluster_data_by_student
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading course details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Удален дублирующий маршрут /students


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


@router.get("/assignments", response_class=HTMLResponse)
async def teacher_assignments(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher assignments page.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with teacher assignments
    """
    logger.info("Teacher assignments page requested")
    
    try:
        # Get teacher assignments data
        assignments = teacher_service.get_teacher_assignments(db)
        courses = teacher_service.get_teacher_courses(db)
        assignments_stats = teacher_service.get_assignments_stats(db)
        
        return templates.TemplateResponse("teacher/assignments.html", {
            "request": request,
            "title": "Задания",
            "assignments": assignments,
            "courses": courses,
            "assignments_stats": assignments_stats
        })
        
    except Exception as e:
        logger.error(f"Error loading teacher assignments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/schedule", response_class=HTMLResponse)
async def teacher_schedule(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Teacher schedule page.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with teacher schedule
    """
    logger.info("Teacher schedule page requested")
    
    try:
        # Get teacher schedule data
        schedule = teacher_service.get_teacher_schedule(db)
        upcoming_lessons = teacher_service.get_upcoming_lessons(db)
        schedule_stats = teacher_service.get_schedule_stats(db)
        
        return templates.TemplateResponse("teacher/schedule.html", {
            "request": request,
            "title": "Мое расписание",
            "schedule": schedule,
            "upcoming_lessons": upcoming_lessons,
            "schedule_stats": schedule_stats
        })
        
    except Exception as e:
        logger.error(f"Error loading teacher schedule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
