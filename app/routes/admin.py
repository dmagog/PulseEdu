"""
Admin routes for system configuration.
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.services.config_service import config_service
from app.services.rbac_service import RBACService
from app.middleware.auth import require_admin
from app.models.import_models import ImportJob, ImportError
from app.models.student import Student, Course, Task, Attendance, TaskCompletion

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
