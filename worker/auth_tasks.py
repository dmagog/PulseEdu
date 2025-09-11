"""
Authentication tasks for Celery worker.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from celery import Celery
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.user import User, UserAuthLog, Role, UserRole
from app.services.rbac_service import RBACService
from app.services.session_service import session_service

logger = logging.getLogger("worker.auth")

# Import celery app
from worker.celery_auth import celery_app


@celery_app.task(bind=True, name='worker.auth_tasks.log_auth_attempt')
def log_auth_attempt_task(
    self,
    login: str,
    outcome: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    user_id: Optional[str] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log authentication attempt asynchronously.
    
    Args:
        login: User login
        outcome: 'success' or 'fail'
        ip_address: Client IP address
        user_agent: Client user agent
        user_id: User ID if successful
        reason: Failure reason if failed
        
    Returns:
        Task result
    """
    try:
        logger.info(f"Logging auth attempt: {login} - {outcome}")
        
        # Get database session
        db = next(get_session())
        
        # Create auth log entry
        auth_log = UserAuthLog(
            login=login,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=reason,
            user_id=user_id
        )
        
        db.add(auth_log)
        db.commit()
        
        logger.info(f"Auth log recorded: {login} - {outcome}")
        
        return {
            "status": "success",
            "message": f"Auth attempt logged for {login}",
            "outcome": outcome
        }
        
    except Exception as e:
        logger.error(f"Error logging auth attempt: {e}")
        try:
            db.rollback()
        except:
            pass
        
        return {
            "status": "error",
            "message": str(e),
            "outcome": outcome
        }


@celery_app.task(bind=True, name='worker.auth_tasks.create_user_session')
def create_user_session_task(
    self,
    user_id: str,
    login: str,
    email: str,
    display_name: str
) -> Dict[str, Any]:
    """
    Create user session asynchronously.
    
    Args:
        user_id: User ID
        login: User login
        email: User email
        display_name: User display name
        
    Returns:
        Task result with session token
    """
    try:
        logger.info(f"Creating session for user: {login}")
        
        # Create user object for session
        user = User(
            user_id=user_id,
            login=login,
            email=email,
            display_name=display_name,
            is_active=True
        )
        
        # Create session
        session_token = session_service.create_session(user)
        
        logger.info(f"Session created for user {login}")
        
        return {
            "status": "success",
            "message": f"Session created for {login}",
            "session_token": session_token,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error creating user session: {e}")
        
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id
        }


@celery_app.task(bind=True, name='worker.auth_tasks.destroy_user_session')
def destroy_user_session_task(
    self,
    session_token: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Destroy user session asynchronously.
    
    Args:
        session_token: Session token to destroy
        user_id: User ID (optional, for logging)
        
    Returns:
        Task result
    """
    try:
        logger.info(f"Destroying session for user: {user_id or 'unknown'}")
        
        # Destroy session
        success = session_service.destroy_session(session_token)
        
        if success:
            logger.info(f"Session destroyed for user {user_id or 'unknown'}")
            return {
                "status": "success",
                "message": f"Session destroyed for user {user_id or 'unknown'}"
            }
        else:
            logger.warning(f"Session not found for user {user_id or 'unknown'}")
            return {
                "status": "warning",
                "message": f"Session not found for user {user_id or 'unknown'}"
            }
        
    except Exception as e:
        logger.error(f"Error destroying user session: {e}")
        
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id
        }


@celery_app.task(bind=True, name='worker.auth_tasks.assign_default_role')
def assign_default_role_task(
    self,
    user_id: str,
    role_name: str = "student"
) -> Dict[str, Any]:
    """
    Assign default role to user asynchronously.
    
    Args:
        user_id: User ID
        role_name: Role name to assign (default: student)
        
    Returns:
        Task result
    """
    try:
        logger.info(f"Assigning role {role_name} to user {user_id}")
        
        # Get database session
        db = next(get_session())
        
        # Use RBAC service to assign role
        rbac_service = RBACService()
        success = rbac_service.assign_role_to_user(user_id, role_name, db)
        
        if success:
            logger.info(f"Role {role_name} assigned to user {user_id}")
            return {
                "status": "success",
                "message": f"Role {role_name} assigned to user {user_id}",
                "user_id": user_id,
                "role": role_name
            }
        else:
            logger.error(f"Failed to assign role {role_name} to user {user_id}")
            return {
                "status": "error",
                "message": f"Failed to assign role {role_name} to user {user_id}",
                "user_id": user_id,
                "role": role_name
            }
        
    except Exception as e:
        logger.error(f"Error assigning default role: {e}")
        try:
            db.rollback()
        except:
            pass
        
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id,
            "role": role_name
        }


@celery_app.task(bind=True, name='worker.auth_tasks.cleanup_expired_sessions')
def cleanup_expired_sessions_task(self) -> Dict[str, Any]:
    """
    Clean up expired sessions periodically.
    
    Returns:
        Task result
    """
    try:
        logger.info("Starting cleanup of expired sessions")
        
        # Clean up expired sessions
        cleaned_count = session_service.cleanup_expired_sessions()
        
        logger.info(f"Cleaned up {cleaned_count} expired sessions")
        
        return {
            "status": "success",
            "message": f"Cleaned up {cleaned_count} expired sessions",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")
        
        return {
            "status": "error",
            "message": str(e),
            "cleaned_count": 0
        }


@celery_app.task(bind=True, name='worker.auth_tasks.audit_user_activity')
def audit_user_activity_task(
    self,
    user_id: str,
    activity_type: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Audit user activity asynchronously.
    
    Args:
        user_id: User ID
        activity_type: Type of activity (login, logout, access_denied, etc.)
        details: Additional details about the activity
        
    Returns:
        Task result
    """
    try:
        logger.info(f"Auditing activity for user {user_id}: {activity_type}")
        
        # Get database session
        db = next(get_session())
        
        # Create audit log entry
        audit_log = UserAuthLog(
            login=f"user_{user_id}",
            outcome="audit",
            reason=f"{activity_type}: {details or 'No details'}",
            user_id=user_id
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Activity audited for user {user_id}: {activity_type}")
        
        return {
            "status": "success",
            "message": f"Activity audited for user {user_id}",
            "activity_type": activity_type,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error auditing user activity: {e}")
        try:
            db.rollback()
        except:
            pass
        
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id,
            "activity_type": activity_type
        }
