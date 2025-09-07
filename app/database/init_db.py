"""
Database initialization script.
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.engine import engine
from app.database.session import SessionLocal
from app.models.user import Role

logger = logging.getLogger("app.database")


def init_roles(db: Session) -> None:
    """
    Initialize default roles in the database.
    
    Args:
        db: Database session
    """
    default_roles = [
        {"role_id": "student", "name": "student", "description": "Студент"},
        {"role_id": "teacher", "name": "teacher", "description": "Преподаватель"},
        {"role_id": "rop", "name": "rop", "description": "Руководитель образовательной программы"},
        {"role_id": "data_operator", "name": "data_operator", "description": "Оператор данных"},
        {"role_id": "admin", "name": "admin", "description": "Администратор системы"},
    ]
    
    for role_data in default_roles:
        existing_role = db.query(Role).filter(Role.role_id == role_data["role_id"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.add(role)
            logger.info(f"Created role: {role_data['name']}")
        else:
            logger.debug(f"Role already exists: {role_data['name']}")
    
    db.commit()


def init_database() -> None:
    """
    Initialize database with default data.
    """
    logger.info("Initializing database...")
    
    # Create tables
    from app.models.user import User, Role, UserRole, UserAuthLog
    from app.models.admin import AdminSetting
    from sqlmodel import SQLModel
    
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created")
    
    # Initialize default data
    db = SessionLocal()
    try:
        init_roles(db)
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
