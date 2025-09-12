"""
ROP (Руководитель образовательной программы) routes for program analytics.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.student import Attendance, Course, Student, Task, TaskCompletion
from app.services.rop_service import ROPService

router = APIRouter(prefix="/rop", tags=["rop"])
logger = logging.getLogger("app.rop")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")

# Initialize ROP service
rop_service = ROPService()


@router.get("/", response_class=HTMLResponse)
async def rop_dashboard(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
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

        return templates.TemplateResponse(
            "rop/dashboard.html", {"request": request, "title": "Дашборд РОП", "dashboard": dashboard_data}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading ROP dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/course/{course_id}", response_class=HTMLResponse)
async def course_analytics(course_id: int, request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
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

        return templates.TemplateResponse(
            "rop/course.html",
            {
                "request": request,
                "title": f"Аналитика курса: {course.name}",
                "course": course,
                "trends_7d": trends_7d,
                "trends_30d": trends_30d,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading course analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/dashboard")
async def get_rop_dashboard_api(db: Session = Depends(get_session)) -> Dict[str, Any]:
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
        return {"status": "success", "data": dashboard_data}

    except Exception as e:
        logger.error(f"Error getting ROP dashboard API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/trends/{days}")
async def get_trends_api(days: int, db: Session = Depends(get_session)) -> Dict[str, Any]:
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
        return {"status": "success", "data": trends_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trends API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/course/{course_id}/trends/{days}")
async def get_course_trends_api(course_id: int, days: int, db: Session = Depends(get_session)) -> Dict[str, Any]:
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
        return {"status": "success", "data": trends_data}

    except Exception as e:
        logger.error(f"Error getting course trends API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/programs", response_class=HTMLResponse)
async def rop_programs(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    """
    ROP programs page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTML response with ROP programs
    """
    logger.info("ROP programs page requested")

    try:
        # Get ROP programs data
        programs = rop_service.get_rop_programs(db)

        return templates.TemplateResponse(
            "rop/programs.html", {"request": request, "title": "Образовательные программы", "programs": programs}
        )

    except Exception as e:
        logger.error(f"Error loading ROP programs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trends", response_class=HTMLResponse)
async def rop_trends(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    """
    ROP trends page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTML response with ROP trends
    """
    logger.info("ROP trends page requested")

    try:
        # Get ROP trends data
        trends = rop_service.get_rop_trends(db)
        programs = rop_service.get_rop_programs(db)
        predictions = rop_service.get_quality_predictions(db)

        return templates.TemplateResponse(
            "rop/trends.html",
            {
                "request": request,
                "title": "Тренды и прогнозы",
                "trends": trends,
                "programs": programs,
                "predictions": predictions,
                "enrollment_dates": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн"],
                "enrollment_values": [120, 135, 142, 158, 165, 172],
                "completion_dates": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн"],
                "completion_values": [85, 87, 89, 91, 88, 92],
                "program_names": ["Программирование", "Веб-разработка", "Базы данных"],
                "performance_values": [4.2, 3.8, 4.0],
                "grades_distribution": {"excellent": 35, "good": 45, "satisfactory": 18, "unsatisfactory": 2},
            },
        )

    except Exception as e:
        logger.error(f"Error loading ROP trends: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/quality", response_class=HTMLResponse)
async def rop_quality(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    """
    ROP quality page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTML response with ROP quality
    """
    logger.info("ROP quality page requested")

    try:
        # Get ROP quality data
        quality = rop_service.get_quality_metrics(db)
        quality_dimensions = rop_service.get_quality_dimensions(db)
        quality_issues = rop_service.get_quality_issues(db)
        quality_recommendations = rop_service.get_quality_recommendations(db)
        improvement_plans = rop_service.get_improvement_plans(db)
        programs = rop_service.get_rop_programs(db)

        return templates.TemplateResponse(
            "rop/quality.html",
            {
                "request": request,
                "title": "Качество образования",
                "quality": quality,
                "quality_dimensions": quality_dimensions,
                "quality_issues": quality_issues,
                "quality_recommendations": quality_recommendations,
                "improvement_plans": improvement_plans,
                "quality_dimensions_names": [dim["name"] for dim in quality_dimensions],
                "quality_dimensions_scores": [dim["score"] for dim in quality_dimensions],
                "quality_trend_dates": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн"],
                "quality_trend_values": [4.1, 4.2, 4.3, 4.4, 4.3, 4.5],
                "program_names": [program["name"] for program in programs],
                "program_quality_scores": [program["quality_score"] for program in programs],
            },
        )

    except Exception as e:
        logger.error(f"Error loading ROP quality: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
