"""
Session management service.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from itsdangerous import URLSafeTimedSerializer

from app.database.session import get_session
from app.models.user import User

logger = logging.getLogger("app.session")


class SessionService:
    """Service for managing user sessions."""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or "pulseedu-secret-key-change-in-production"
        self.serializer = URLSafeTimedSerializer(self.secret_key)
        self.logger = logger
        self._sessions: Dict[str, Dict[str, Any]] = {}  # In-memory session storage

    def create_session(self, user: User) -> str:
        """
        Create a new session for user.

        Args:
            user: User object

        Returns:
            Session token
        """
        try:
            # Generate session token
            session_token = secrets.token_urlsafe(32)

            # Create session data
            session_data = {
                "user_id": user.user_id,
                "login": user.login,
                "email": user.email,
                "display_name": user.display_name,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            }

            # Store session in memory (in production, use Redis or database)
            self._sessions[session_token] = session_data

            self.logger.info(f"Created session for user {user.login}")
            return session_token

        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise

    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by token.

        Args:
            session_token: Session token

        Returns:
            Session data or None if invalid/expired
        """
        try:
            if not session_token:
                return None

            # Check in-memory storage
            session_data = self._sessions.get(session_token)
            if not session_data:
                return None

            # Check expiration
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if datetime.utcnow() > expires_at:
                self.logger.info(f"Session expired for user {session_data.get('login')}")
                del self._sessions[session_token]
                return None

            return session_data

        except Exception as e:
            self.logger.error(f"Error getting session: {e}")
            return None

    def get_user_from_session(self, session_token: str) -> Optional[User]:
        """
        Get user object from session token.

        Args:
            session_token: Session token

        Returns:
            User object or None
        """
        try:
            session_data = self.get_session(session_token)
            if not session_data:
                return None

            # Get database session
            db = next(get_session())

            # Find user
            user = db.query(User).filter(User.user_id == session_data["user_id"]).first()
            return user

        except Exception as e:
            self.logger.error(f"Error getting user from session: {e}")
            return None

    def destroy_session(self, session_token: str) -> bool:
        """
        Destroy session.

        Args:
            session_token: Session token

        Returns:
            True if session destroyed, False otherwise
        """
        try:
            if session_token in self._sessions:
                user_login = self._sessions[session_token].get("login", "unknown")
                del self._sessions[session_token]
                self.logger.info(f"Destroyed session for user {user_login}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error destroying session: {e}")
            return False

    def refresh_session(self, session_token: str) -> Optional[str]:
        """
        Refresh session expiration.

        Args:
            session_token: Current session token

        Returns:
            New session token or None if refresh failed
        """
        try:
            session_data = self.get_session(session_token)
            if not session_data:
                return None

            # Create new session with extended expiration
            user = self.get_user_from_session(session_token)
            if not user:
                return None

            # Destroy old session
            self.destroy_session(session_token)

            # Create new session
            new_token = self.create_session(user)
            return new_token

        except Exception as e:
            self.logger.error(f"Error refreshing session: {e}")
            return None

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            current_time = datetime.utcnow()
            expired_tokens = []

            for token, session_data in self._sessions.items():
                expires_at = datetime.fromisoformat(session_data["expires_at"])
                if current_time > expires_at:
                    expired_tokens.append(token)

            for token in expired_tokens:
                del self._sessions[token]

            if expired_tokens:
                self.logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

            return len(expired_tokens)

        except Exception as e:
            self.logger.error(f"Error cleaning up sessions: {e}")
            return 0

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


# Global session service instance
session_service = SessionService()
