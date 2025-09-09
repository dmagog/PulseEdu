"""
Database engine configuration.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger("app.database")


def create_database_engine() -> Engine:
    """
    Create and configure SQLAlchemy engine for PostgreSQL.
    
    Returns:
        Configured SQLAlchemy engine
    """
    database_url = os.getenv("DB_URL", "postgresql://pulseedu:pulseedu@localhost:5432/pulseedu")
    
    logger.info(f"Creating database engine for: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    engine = create_engine(
        database_url,
        # Connection pool settings
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        # Echo SQL queries in development
        echo=os.getenv("DB_ECHO", "false").lower() == "true"
    )
    
    return engine


# Global engine instance
engine = create_database_engine()
