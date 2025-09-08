"""
Home page routes.
"""
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request) -> HTMLResponse:
    """
    Главная страница с навигацией по ролям.
    """
    logger.info("Rendering home page")
    
    return templates.TemplateResponse("home.html", {
        "request": request,
        "title": "PulseEdu - Система мониторинга образовательного процесса"
    })
