"""
Authentication routes.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.user import User, Role, UserRole, UserAuthLog
from app.services.session_service import session_service
from worker.auth_tasks import (
    log_auth_attempt_task,
    create_user_session_task,
    destroy_user_session_task,
    assign_default_role_task
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app.auth")

# Templates
templates = Jinja2Templates(directory="app/ui/templates")


def log_auth_attempt(
    db: Session,
    login: str,
    outcome: str,
    request: Request,
    user_id: Optional[str] = None,
    reason: Optional[str] = None
) -> None:
    """
    Log authentication attempt for audit using Celery worker.
    
    Args:
        db: Database session
        login: User login
        outcome: 'success' or 'fail'
        request: FastAPI request object
        user_id: User ID if successful
        reason: Failure reason if failed
    """
    try:
        # Send task to auth worker
        log_auth_attempt_task.delay(
            login=login,
            outcome=outcome,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            user_id=user_id,
            reason=reason
        )
        logger.info(f"Auth log task queued: {login} - {outcome}")
    except Exception as e:
        logger.error(f"Failed to queue auth log task: {e}")
        # Fallback to direct logging if worker is unavailable
        try:
            auth_log = UserAuthLog(
                login=login,
                outcome=outcome,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                reason=reason,
                user_id=user_id
            )
            db.add(auth_log)
            db.commit()
            logger.info(f"Auth log recorded directly: {login} - {outcome}")
        except Exception as fallback_e:
            logger.error(f"Failed to log auth attempt directly: {fallback_e}")
            try:
                db.rollback()
            except:
                pass


def get_or_create_user(db: Session, login: str, email: Optional[str] = None) -> User:
    """
    Get existing user or create new one.
    
    Args:
        db: Database session
        login: User login
        email: User email (optional)
        
    Returns:
        User object
    """
    # Try to find existing user
    user = db.query(User).filter(User.login == login).first()
    
    if not user:
        # Create new user
        user_id = f"user_{login}_{int(datetime.utcnow().timestamp())}"
        email = email or f"{login}@pulseedu.local"
        
        user = User(
            user_id=user_id,
            login=login,
            email=email,
            display_name=login,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Assign default role (student) using worker
        try:
            assign_default_role_task.delay(user.user_id, "student")
            logger.info(f"Default role assignment queued for user {login}")
        except Exception as e:
            logger.error(f"Failed to queue role assignment: {e}")
            # Fallback to direct assignment
            default_role = db.query(Role).filter(Role.role_name == "student").first()
            if default_role:
                user_role = UserRole(
                    user_id=user.user_id,
                    role_id=default_role.role_id
                )
                db.add(user_role)
                db.commit()
                logger.info(f"Default role assigned directly to user {login}")
        
        logger.info(f"Created new user: {login}")
    
    return user


@router.post("/verify")
async def verify_auth(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session)
) -> RedirectResponse:
    """
    Verify authentication (fake implementation).
    
    Accepts any login and password combination.
    Creates user if doesn't exist.
    """
    logger.info(f"Auth attempt for login: {login}")
    
    try:
        # Fake authentication - accept any login/password
        if not login or not password:
            log_auth_attempt(db, login, "fail", request, reason="empty_credentials")
            raise HTTPException(status_code=400, detail="Login and password required")
        
        # Get or create user
        user = get_or_create_user(db, login)
        
        # Log successful authentication
        log_auth_attempt(db, login, "success", request, user_id=user.user_id)
        
        # Create session
        session_token = session_service.create_session(user)
        
        # Create response with session cookie
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=24*60*60,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error for {login}: {e}")
        log_auth_attempt(db, login, "fail", request, reason="system_error")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """
    Beautiful login page.
    """
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "title": "Вход в систему"
    })


@router.get("/verify")
async def auth_form() -> str:
    """
    Simple authentication form (for testing) - redirect to new login page.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PulseEdu - Авторизация</title>
        <meta http-equiv="refresh" content="0; url=/auth/login">
    </head>
    <body>
        <p>Перенаправление на страницу входа...</p>
        <script>window.location.href = '/auth/login';</script>
    </body>
    </html>
    """


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """
    Logout user and destroy session.
    """
    try:
        # Get session token from cookie
        session_token = request.cookies.get("session_token")
        
        if session_token:
            # Get user info before destroying session
            session_data = session_service.get_session(session_token)
            user_id = session_data.get("user_id") if session_data else None
            
            # Destroy session using worker
            try:
                destroy_user_session_task.delay(session_token, user_id)
                logger.info(f"Session destruction queued for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to queue session destruction: {e}")
                # Fallback to direct destruction
                session_service.destroy_session(session_token)
                logger.info(f"Session destroyed directly for user {user_id}")
        
        # Create response and clear cookie
        response = RedirectResponse(url="/auth/login", status_code=303)
        response.delete_cookie("session_token")
        
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return RedirectResponse(url="/auth/login", status_code=303)