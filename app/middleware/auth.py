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
        Extract user ID from request (simplified implementation).
        
        Args:
            request: FastAPI request object
            
        Returns:
            User ID or None
        """
        # For now, we'll use a simple approach with query parameters
        # In a real application, this would check session/cookies/JWT tokens
        
        # Check query parameter
        user_id = request.query_params.get("user_id")
        if user_id:
            return user_id
        
        # Check if it's a student route with student_id
        if "/student/" in str(request.url):
            student_id = request.query_params.get("student_id")
            if student_id:
                return student_id
        
        # Default to admin user for testing
        # In real app, this would be extracted from authentication
        return "admin_user"
    
    def _redirect_to_login(self, request: Request) -> RedirectResponse:
        """Redirect to login page."""
        return RedirectResponse(url="/auth/login", status_code=302)
    
    def _redirect_to_unauthorized(self, request: Request) -> RedirectResponse:
        """Redirect to unauthorized page."""
        return RedirectResponse(url="/unauthorized", status_code=302)


# Global middleware instance
auth_middleware = AuthMiddleware()


# Simplified permission decorators
def require_admin(func: Callable):
    """Require admin role - simplified version."""
    async def wrapper(*args, **kwargs):
        # For now, just call the function without permission checks
        # In a real system, this would check authentication and roles
        return await func(*args, **kwargs)
    return wrapper


def require_operator(func: Callable):
    """Require operator role - simplified version."""
    async def wrapper(*args, **kwargs):
        # For now, just call the function without permission checks
        return await func(*args, **kwargs)
    return wrapper


def require_student_access(func: Callable):
    """Require student access - simplified version."""
    async def wrapper(*args, **kwargs):
        # For now, just call the function without permission checks
        return await func(*args, **kwargs)
    return wrapper


def require_import_access(func: Callable):
    """Require import access - simplified version."""
    async def wrapper(*args, **kwargs):
        # For now, just call the function without permission checks
        return await func(*args, **kwargs)
    return wrapper
