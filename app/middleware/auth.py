"""
Authentication and authorization middleware.
"""
import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.services.rbac_service import RBACService
from app.services.session_service import session_service

logger = logging.getLogger("app.auth_middleware")


class AuthMiddleware:
    """Middleware for handling authentication and authorization."""
    
    def __init__(self):
        self.rbac_service = RBACService()
        self.logger = logger
    
    def require_role(self, required_role: str, resource: str, action: str = "read"):
        """
        Decorator to require specific role for route access.
        
        Args:
            required_role: Required role name
            resource: Resource name for permission check
            action: Action name for permission check
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # Extract request and session from kwargs
                request = None
                db = None
                
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                    elif isinstance(arg, Session):
                        db = arg
                
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                    elif isinstance(value, Session):
                        db = value
                
                if not request or not db:
                    raise HTTPException(status_code=500, detail="Request or database session not found")
                
                # Get user ID from session/cookie (simplified for now)
                user_id = self._get_user_id_from_request(request)
                
                if not user_id:
                    return self._redirect_to_login(request)
                
                # Check permission
                if not self.rbac_service.has_permission(user_id, resource, action, db):
                    return self._redirect_to_unauthorized(request)
                
                # Call original function
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_permission(self, resource: str, action: str = "read"):
        """
        Decorator to require specific permission for route access.
        
        Args:
            resource: Resource name for permission check
            action: Action name for permission check
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # Extract request and session from kwargs
                request = None
                db = None
                
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                    elif isinstance(arg, Session):
                        db = arg
                
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                    elif isinstance(value, Session):
                        db = value
                
                # If no db session found, create one
                if not db:
                    from app.database.session import get_session
                    db = next(get_session())
                
                if not request:
                    raise HTTPException(status_code=500, detail="Request not found")
                
                # Get user ID from session/cookie (simplified for now)
                user_id = self._get_user_id_from_request(request)
                
                if not user_id:
                    return self._redirect_to_login(request)
                
                # Check permission
                if not self.rbac_service.has_permission(user_id, resource, action, db):
                    return self._redirect_to_unauthorized(request)
                
                # Call original function
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def _get_user_id_from_request(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request using session.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User ID or None
        """
        try:
            # Get session token from cookie
            session_token = request.cookies.get("session_token")
            if not session_token:
                return None
            
            # Get session data
            session_data = session_service.get_session(session_token)
            if not session_data:
                return None
            
            return session_data.get("user_id")
            
        except Exception as e:
            self.logger.error(f"Error getting user ID from request: {e}")
            return None
    
    def _redirect_to_login(self, request: Request) -> RedirectResponse:
        """Redirect to login page."""
        return RedirectResponse(url="/auth/login", status_code=302)
    
    def _redirect_to_unauthorized(self, request: Request) -> RedirectResponse:
        """Redirect to unauthorized page."""
        return RedirectResponse(url="/unauthorized", status_code=302)


# Global middleware instance
auth_middleware = AuthMiddleware()


# Real permission decorators
def require_admin(func: Callable):
    """Require admin role."""
    return auth_middleware.require_permission("system.manage", "write")(func)


def require_operator(func: Callable):
    """Require operator role."""
    return auth_middleware.require_permission("import.upload", "write")(func)


def require_student_access(func: Callable):
    """Require student access."""
    return auth_middleware.require_permission("student.view", "read")(func)


def require_teacher_access(func: Callable):
    """Require teacher access."""
    return auth_middleware.require_permission("teacher.view", "read")(func)


def require_rop_access(func: Callable):
    """Require ROP access."""
    return auth_middleware.require_permission("rop.view", "read")(func)


def require_import_access(func: Callable):
    """Require import access."""
    return auth_middleware.require_permission("import.upload", "write")(func)
