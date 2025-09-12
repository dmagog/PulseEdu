"""
Configuration service for reading settings from environment and database.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.admin import AdminSetting

logger = logging.getLogger("app.config")


class ConfigService:
    """Service for managing application configuration."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get setting value from database or environment.

        Priority: Database > Environment > Default
        """
        # First check cache
        if key in self._cache:
            return self._cache[key]

        # Try database first (will be implemented when DB is ready)
        # For now, fall back to environment
        value = os.getenv(key, default)

        # Cache the result
        self._cache[key] = value

        logger.debug(f"Retrieved setting {key}={value}")
        return value

    def set_setting(self, key: str, value: str, description: Optional[str] = None) -> None:
        """
        Set setting value in database.

        This will be implemented when database is ready.
        """
        # For now, just update cache
        self._cache[key] = value
        logger.info(f"Set setting {key}={value}")

    def now(self) -> datetime:
        """
        Get current time (real or fake based on APP_NOW_MODE).

        Returns:
            Current datetime (real or fake)
        """
        now_mode = self.get_setting("APP_NOW_MODE", "real")

        if now_mode == "fake":
            fake_now_str = self.get_setting("APP_FAKE_NOW")
            if fake_now_str:
                try:
                    # Parse YYYY-MM-DD format
                    fake_date = datetime.strptime(fake_now_str, "%Y-%m-%d")
                    logger.debug(f"Using fake time: {fake_date}")
                    return fake_date
                except ValueError:
                    logger.warning(f"Invalid APP_FAKE_NOW format: {fake_now_str}, using real time")

        # Return real time
        return datetime.now(timezone.utc)

    def is_fake_time_enabled(self) -> bool:
        """Check if fake time mode is enabled."""
        return self.get_setting("APP_NOW_MODE", "real") == "fake"

    def get_fake_time(self) -> Optional[datetime]:
        """Get fake time if enabled, None otherwise."""
        if not self.is_fake_time_enabled():
            return None

        fake_now_str = self.get_setting("APP_FAKE_NOW")
        if fake_now_str:
            try:
                return datetime.strptime(fake_now_str, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid APP_FAKE_NOW format: {fake_now_str}")

        return None


# Global instance
config_service = ConfigService()
