"""
User and authentication models.
"""

from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.admin import AdminSetting


class User(SQLModel, table=True):
    """User model."""

    __tablename__ = "users"

    user_id: str = Field(primary_key=True, max_length=50)
    email: str = Field(unique=True, max_length=255)
    login: str = Field(unique=True, max_length=100)
    display_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    roles: List["UserRole"] = Relationship(back_populates="user")


class Role(SQLModel, table=True):
    """Role model."""

    __tablename__ = "roles"

    role_id: str = Field(primary_key=True, max_length=50)
    name: str = Field(unique=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    users: List["UserRole"] = Relationship(back_populates="role")


class UserRole(SQLModel, table=True):
    """User-Role association model."""

    __tablename__ = "user_roles"

    user_id: str = Field(foreign_key="users.user_id", primary_key=True)
    role_id: str = Field(foreign_key="roles.role_id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[str] = Field(default=None, max_length=50)

    # Relationships
    user: User = Relationship(back_populates="roles")
    role: Role = Relationship(back_populates="users")


class UserAuthLog(SQLModel, table=True):
    """User authentication log for audit."""

    __tablename__ = "user_auth_log"

    log_id: int = Field(primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    login: str = Field(max_length=100)
    outcome: str = Field(max_length=20)  # 'success' or 'fail'
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    reason: Optional[str] = Field(default=None, max_length=200)
    user_id: Optional[str] = Field(default=None, max_length=50)


class UserCourseAssignment(SQLModel, table=True):
    """User-Course assignment model for staff monitoring courses."""

    __tablename__ = "user_course_assignments"

    assignment_id: int = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", max_length=50)
    course_id: int = Field(foreign_key="courses.id")
    assignment_type: str = Field(max_length=20)  # 'teacher', 'rop', 'monitor'
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)

    # Relationships
    user: User = Relationship()
    course: "Course" = Relationship()


# Import Course to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.student import Course
