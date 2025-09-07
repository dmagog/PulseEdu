"""
ROP (Руководитель образовательной программы) routes for program analytics.
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
from app.services.rop_service import ROPService

router = APIRouter(prefix="/rop", tags=["rop"])
logger = logging.getLogger("app.rop")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize ROP service
rop_service = ROPService()


@router.get("/", response_class=HTMLResponse)
async def rop_dashboard(
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    ROP dashboard with program analytics and trends.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with ROP dashboard
    """
    logger.info("ROP dashboard requested")
    
    try:
        # Get ROP dashboard data
        dashboard_data = rop_service.get_rop_dashboard(db)
        
        if "error" in dashboard_data:
            raise HTTPException(status_code=500, detail=dashboard_data["error"])
        
        return templates.TemplateResponse("rop/dashboard.html", {
            "request": request,
            "title": "Дашборд РОП",
            "dashboard": dashboard_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading ROP dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/course/{course_id}", response_class=HTMLResponse)
async def course_analytics(
    course_id: int,
    request: Request,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    Course analytics page with trends and performance metrics.
    
    Args:
        course_id: Course ID
        request: FastAPI request object
        db: Database session
        
    Returns:
        HTML response with course analytics
    """
    logger.info(f"Course analytics requested for course: {course_id}")
    
    try:
        # Get course
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Get course trends
        trends_7d = rop_service.get_course_trends(course_id, 7, db)
        trends_30d = rop_service.get_course_trends(course_id, 30, db)
        
        return templates.TemplateResponse("rop/course.html", {
            "request": request,
            "title": f"Аналитика курса: {course.name}",
            "course": course,
            "trends_7d": trends_7d,
            "trends_30d": trends_30d
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading course analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/dashboard")
async def get_rop_dashboard_api(
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for ROP dashboard data.
    
    Args:
        db: Database session
        
    Returns:
        JSON with ROP dashboard data
    """
    logger.info("ROP dashboard API requested")
    
    try:
        dashboard_data = rop_service.get_rop_dashboard(db)
        return {
            "status": "success",
            "data": dashboard_data
        }
        
    except Exception as e:
        logger.error(f"Error getting ROP dashboard API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/trends/{days}")
async def get_trends_api(
    days: int,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for trends data.
    
    Args:
        days: Number of days for trends (7 or 30)
        db: Database session
        
    Returns:
        JSON with trends data
    """
    logger.info(f"Trends API requested for {days} days")
    
    try:
        if days not in [7, 30]:
            raise HTTPException(status_code=400, detail="Days must be 7 or 30")
        
        trends_data = rop_service._get_trends_data(days, db)
        return {
            "status": "success",
            "data": trends_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trends API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/course/{course_id}/trends/{days}")
async def get_course_trends_api(
    course_id: int,
    days: int,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    API endpoint for course-specific trends data.
    
    Args:
        course_id: Course ID
        days: Number of days for trends
        db: Database session
        
    Returns:
        JSON with course trends data
    """
    logger.info(f"Course trends API requested for course {course_id}, {days} days")
    
    try:
        trends_data = rop_service.get_course_trends(course_id, days, db)
        return {
            "status": "success",
            "data": trends_data
        }
        
    except Exception as e:
        logger.error(f"Error getting course trends API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
