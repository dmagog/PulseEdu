"""
Admin routes for system configuration.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.config_service import config_service

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("app.admin")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")


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
