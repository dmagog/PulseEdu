"""
Database session management.
"""
import logging
from typing import Generator
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.database.engine import engine

logger = logging.getLogger("app.database")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    
    Yields:
        Database session
    """
    session = SessionLocal()
    try:
        logger.debug("Database session created")
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        logger.debug("Database session closed")
        session.close()


@contextmanager
def get_db_session():
    """
    Context manager for database session.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
