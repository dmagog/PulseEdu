"""
Admin routes for system configuration.
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_session
from app.services.config_service import config_service
from app.services.rbac_service import RBACService
from app.middleware.auth import require_admin
from app.models.import_models import ImportJob, ImportErrorLog
from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.models.llm_models import LLMCallLog, LLMRecommendation, LLMFeedback

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("app.admin")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")
rbac_service = RBACService()


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    """
    Admin dashboard with system metrics and overview.
    """
    logger.info("Admin dashboard requested")
    
    try:
        # Get system metrics
        metrics = {
            "total_students": db.query(Student).count(),
            "total_courses": db.query(Course).count(),
            "total_tasks": db.query(Task).count(),
            "total_import_jobs": db.query(ImportJob).count(),
            "recent_imports": db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(5).all(),
            "system_uptime": "N/A",  # Would be calculated in real system
            "active_users": db.query(Student).count()  # Simplified
        }
        
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "title": "Админ-панель",
            "metrics": metrics
        })
        
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "title": "Админ-панель",
            "error": str(e)
        })


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request) -> HTMLResponse:
    """
    Admin settings page for managing system configuration.
    """
    logger.info("Admin settings page requested")
    
    # Get current settings
    settings = {
        "APP_NOW_MODE": config_service.get_setting("APP_NOW_MODE", "real"),
        "APP_FAKE_NOW": config_service.get_setting("APP_FAKE_NOW", ""),
        "LLM_MAX_RECS": config_service.get_setting("LLM_MAX_RECS", "3"),
        "LLM_REC_MAX_CHARS": config_service.get_setting("LLM_REC_MAX_CHARS", "200"),
        "LLM_TIMEOUT_SECONDS": config_service.get_setting("LLM_TIMEOUT_SECONDS", "10"),
        "LLM_CACHE_TTL_HOURS": config_service.get_setting("LLM_CACHE_TTL_HOURS", "24"),
        # LLM Monitoring settings
        "LLM_MONITORING_ENABLED": config_service.get_setting("LLM_MONITORING_ENABLED", "true"),
        "LLM_ALERT_ERROR_RATE_PCT": config_service.get_setting("LLM_ALERT_ERROR_RATE_PCT", "10.0"),
        "LLM_ALERT_CONSECUTIVE_FAILS": config_service.get_setting("LLM_ALERT_CONSECUTIVE_FAILS", "5"),
        "LLM_ALERT_EMAIL_TO": config_service.get_setting("LLM_ALERT_EMAIL_TO", ""),
        "LLM_LOG_RETENTION_DAYS": config_service.get_setting("LLM_LOG_RETENTION_DAYS", "30"),
    }
    
    # Get current time info
    current_time = config_service.now()
    is_fake_time = config_service.is_fake_time_enabled()
    
    context = {
        "request": request,
        "settings": settings,
        "current_time": current_time,
        "is_fake_time": is_fake_time,
        "title": "Настройки системы"
    }
    
    return templates.TemplateResponse("admin/settings.html", context)


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    app_now_mode: str = Form(...),
    app_fake_now: str = Form(...),
    llm_max_recs: str = Form(...),
    llm_rec_max_chars: str = Form(...),
    llm_timeout_seconds: str = Form(...),
    llm_cache_ttl_hours: str = Form(...),
) -> HTMLResponse:
    """
    Update system settings.
    """
    logger.info(f"Updating settings: APP_NOW_MODE={app_now_mode}")
    
    # Update settings (for now just in cache, will be DB later)
    config_service.set_setting("APP_NOW_MODE", app_now_mode)
    config_service.set_setting("APP_FAKE_NOW", app_fake_now)
    config_service.set_setting("LLM_MAX_RECS", llm_max_recs)
    config_service.set_setting("LLM_REC_MAX_CHARS", llm_rec_max_chars)
    config_service.set_setting("LLM_TIMEOUT_SECONDS", llm_timeout_seconds)
    config_service.set_setting("LLM_CACHE_TTL_HOURS", llm_cache_ttl_hours)
    
    # Redirect back to settings page
    return HTMLResponse(
        content=f"""
        <html>
            <head>
                <meta http-equiv="refresh" content="0; url=/admin/settings">
                <title>Настройки обновлены</title>
            </head>
            <body>
                <p>Настройки обновлены. Перенаправление...</p>
                <script>window.location.href = '/admin/settings';</script>
            </body>
        </html>
        """,
        status_code=200
    )


@router.get("/import-jobs", response_class=HTMLResponse)
async def admin_import_jobs(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    """
    Admin page for viewing import jobs and their status.
    """
    logger.info("Admin import jobs page requested")
    
    try:
        # Get all import jobs with pagination
        import_jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(50).all()
        
        # Get import statistics
        stats = {
            "total_jobs": db.query(ImportJob).count(),
            "completed_jobs": db.query(ImportJob).filter(ImportJob.status == "completed").count(),
            "failed_jobs": db.query(ImportJob).filter(ImportJob.status == "failed").count(),
            "pending_jobs": db.query(ImportJob).filter(ImportJob.status == "pending").count(),
            "processing_jobs": db.query(ImportJob).filter(ImportJob.status == "processing").count()
        }
        
        return templates.TemplateResponse("admin/import_jobs.html", {
            "request": request,
            "title": "Журнал импорта",
            "import_jobs": import_jobs,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error loading import jobs: {e}")
        return templates.TemplateResponse("admin/import_jobs.html", {
            "request": request,
            "title": "Журнал импорта",
            "error": str(e)
        })


@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_session)) -> HTMLResponse:
    """
    Admin page for managing users and roles.
    """
    logger.info("Admin users page requested")
    
    try:
        # Get all users with their roles
        users = db.query(Student).all()
        roles = db.query(Role).all()
        
        # Get user role mappings
        user_roles = {}
        for user in users:
            user_roles[user.id] = rbac_service.get_user_roles(user.id, db)
        
        return templates.TemplateResponse("admin/users.html", {
            "request": request,
            "title": "Управление пользователями",
            "users": users,
            "roles": roles,
            "user_roles": user_roles
        })
        
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return templates.TemplateResponse("admin/users.html", {
            "request": request,
            "title": "Управление пользователями",
            "error": str(e)
        })


@router.get("/llm", response_class=HTMLResponse)
async def admin_llm_monitoring(
    request: Request,
    status: str = None,
    course_id: str = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_session)
) -> HTMLResponse:
    """
    LLM monitoring dashboard with call logs and statistics.
    """
    logger.info("LLM monitoring dashboard requested")
    
    try:
        # Get LLM statistics for last 24 hours
        from datetime import datetime, timedelta
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Total calls
        total_calls = db.query(LLMCallLog).filter(
            LLMCallLog.created_at >= last_24h
        ).count()
        
        # Successful calls
        successful_calls = db.query(LLMCallLog).filter(
            LLMCallLog.created_at >= last_24h,
            LLMCallLog.status == "success"
        ).count()
        
        # Failed calls
        failed_calls = db.query(LLMCallLog).filter(
            LLMCallLog.created_at >= last_24h,
            LLMCallLog.status.in_(["failed", "error"])
        ).count()
        
        # Calculate success rate
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Average response time
        avg_response_time = db.query(LLMCallLog).filter(
            LLMCallLog.created_at >= last_24h,
            LLMCallLog.response_time_ms.isnot(None)
        ).with_entities(
            func.avg(LLMCallLog.response_time_ms)
        ).scalar() or 0
        
        # Cache hit rate
        cached_calls = db.query(LLMCallLog).filter(
            LLMCallLog.created_at >= last_24h,
            LLMCallLog.status == "cached"
        ).count()
        
        cache_hit_rate = (cached_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Build query for call logs
        query = db.query(LLMCallLog).filter(LLMCallLog.created_at >= last_24h)
        
        # Apply filters
        if status:
            query = query.filter(LLMCallLog.status == status)
        if course_id:
            query = query.filter(LLMCallLog.course_id == course_id)
        
        # Get total count for pagination
        total_logs = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        call_logs = query.order_by(LLMCallLog.created_at.desc()).offset(offset).limit(per_page).all()
        
        # Calculate total pages
        total_pages = (total_logs + per_page - 1) // per_page
        
        # Get unique courses for filter dropdown
        courses = db.query(LLMCallLog.course_id).filter(
            LLMCallLog.course_id.isnot(None),
            LLMCallLog.created_at >= last_24h
        ).distinct().all()
        course_list = [course[0] for course in courses if course[0]]
        
        # Statistics summary
        stats = {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": round(success_rate, 1),
            "avg_response_time": round(avg_response_time, 0),
            "cache_hit_rate": round(cache_hit_rate, 1),
            "cached_calls": cached_calls
        }
        
        return templates.TemplateResponse("admin/llm_monitoring.html", {
            "request": request,
            "title": "Мониторинг LLM",
            "call_logs": call_logs,
            "stats": stats,
            "total_logs": total_logs,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "courses": course_list,
            "filters": {
                "status": status,
                "course_id": course_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error loading LLM monitoring: {e}")
        return templates.TemplateResponse("admin/llm_monitoring.html", {
            "request": request,
            "title": "Мониторинг LLM",
            "error": str(e)
        })


@router.get("/llm/export")
async def admin_llm_export_csv(
    status: str = None,
    course_id: str = None,
    db: Session = Depends(get_session)
) -> Response:
    """
    Export LLM call logs to CSV format.
    """
    logger.info("LLM CSV export requested")
    
    try:
        import csv
        import io
        from datetime import datetime, timedelta
        
        # Get data for last 24 hours
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Build query
        query = db.query(LLMCallLog).filter(LLMCallLog.created_at >= last_24h)
        
        # Apply filters
        if status:
            query = query.filter(LLMCallLog.status == status)
        if course_id:
            query = query.filter(LLMCallLog.course_id == course_id)
        
        # Get all matching records
        call_logs = query.order_by(LLMCallLog.created_at.desc()).all()
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Время',
            'Студент ID',
            'Курс ID',
            'Статус',
            'Время ответа (мс)',
            'Количество рекомендаций',
            'Модель',
            'Температура',
            'Макс токены',
            'Количество повторов',
            'Сообщение об ошибке',
            'Превью ответа'
        ])
        
        # Write data rows
        for log in call_logs:
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.student_id or '',
                log.course_id or '',
                log.status,
                log.response_time_ms or '',
                log.recommendations_count or '',
                log.model_used or '',
                log.temperature or '',
                log.max_tokens or '',
                log.retry_count,
                log.error_message or '',
                log.response_preview or ''
            ])
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"llm_logs_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting LLM logs: {e}")
        raise HTTPException(status_code=500, detail="Export failed")
