"""
Authentication routes.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.user import User, Role, UserRole, UserAuthLog

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app.auth")


def log_auth_attempt(
    db: Session,
    login: str,
    outcome: str,
    request: Request,
    user_id: Optional[str] = None,
    reason: Optional[str] = None
) -> None:
    """
    Log authentication attempt for audit.
    
    Args:
        db: Database session
        login: User login
        outcome: 'success' or 'fail'
        request: FastAPI request object
        user_id: User ID if successful
        reason: Failure reason if failed
    """
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
        logger.info(f"Auth log recorded: {login} - {outcome}")
    except Exception as e:
        logger.error(f"Failed to log auth attempt: {e}")
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
        
        # Assign default role (student)
        default_role = db.query(Role).filter(Role.name == "student").first()
        if default_role:
            user_role = UserRole(
                user_id=user.user_id,
                role_id=default_role.role_id
            )
            db.add(user_role)
            db.commit()
        
        logger.info(f"Created new user: {login}")
    
    return user


@router.post("/verify")
async def verify_auth(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
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
        
        # In a real implementation, you would set a secure session cookie here
        # For now, we'll just return success
        
        return {
            "status": "success",
            "message": "Authentication successful",
            "user": {
                "user_id": user.user_id,
                "login": user.login,
                "email": user.email,
                "display_name": user.display_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error for {login}: {e}")
        log_auth_attempt(db, login, "fail", request, reason="system_error")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/verify")
async def auth_form() -> str:
    """
    Simple authentication form (for testing).
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PulseEdu - Авторизация</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h4>Вход в систему</h4>
                        </div>
                        <div class="card-body">
                            <form method="post" action="/auth/verify">
                                <div class="mb-3">
                                    <label for="login" class="form-label">Логин</label>
                                    <input type="text" class="form-control" id="login" name="login" required>
                                </div>
                                <div class="mb-3">
                                    <label for="password" class="form-label">Пароль</label>
                                    <input type="password" class="form-control" id="password" name="password" required>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Войти</button>
                            </form>
                            <div class="mt-3">
                                <small class="text-muted">
                                    <strong>Тестовый режим:</strong> любой логин и пароль будут приняты
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """