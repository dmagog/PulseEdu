"""
Student and course models.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Student(SQLModel, table=True):
    """Student model."""

    __tablename__ = "students"

    id: Optional[str] = Field(default=None, primary_key=True, max_length=20)  # id_01, id_02, etc.
    name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    group_id: Optional[str] = Field(default=None, max_length=50)  # Группа студента
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    attendances: List["Attendance"] = Relationship(back_populates="student")
    task_completions: List["TaskCompletion"] = Relationship(back_populates="student")

    def __init__(self, **data):
        super().__init__(**data)
        # Manually set id if provided
        if 'id' in data and data['id'] is not None:
            object.__setattr__(self, 'id', data['id'])


class Course(SQLModel, table=True):
    """Course model."""

    __tablename__ = "courses"

    id: int = Field(primary_key=True)
    name: str = Field(max_length=500)  # "Онлайн курс: от замысла до воплощения"
    description: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    attendances: List["Attendance"] = Relationship(back_populates="course")
    task_completions: List["TaskCompletion"] = Relationship(back_populates="course")
    tasks: List["Task"] = Relationship(back_populates="course")


class Lesson(SQLModel, table=True):
    """Lesson model for attendance tracking."""

    __tablename__ = "lessons"

    id: int = Field(primary_key=True)
    course_id: int = Field(foreign_key="courses.id")
    lesson_number: int = Field()  # 1, 2, 3, etc.
    title: str = Field(max_length=255)  # "Занятие 1", "Занятие 2", etc.
    date: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    course: Course = Relationship()
    attendances: List["Attendance"] = Relationship(back_populates="lesson")


class Task(SQLModel, table=True):
    """Task model for learning process tracking."""

    __tablename__ = "tasks"

    id: int = Field(primary_key=True)
    course_id: int = Field(foreign_key="courses.id")
    name: str = Field(max_length=500)  # "Лекция 1.1. Начинаем с «Зачем?»..."
    task_type: Optional[str] = Field(default=None, max_length=50)  # "lecture", "test", "assignment"
    deadline: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    course: Course = Relationship(back_populates="tasks")
    completions: List["TaskCompletion"] = Relationship(back_populates="task")


class Attendance(SQLModel, table=True):
    """Attendance record model."""

    __tablename__ = "attendances"

    id: int = Field(primary_key=True)
    student_id: str = Field(foreign_key="students.id")
    course_id: int = Field(foreign_key="courses.id")
    lesson_id: int = Field(foreign_key="lessons.id")
    attended: bool = Field()  # True (1) or False (0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    student: Student = Relationship(back_populates="attendances")
    course: Course = Relationship(back_populates="attendances")
    lesson: Lesson = Relationship(back_populates="attendances")


class TaskCompletion(SQLModel, table=True):
    """Task completion record model."""

    __tablename__ = "task_completions"

    id: int = Field(primary_key=True)
    student_id: str = Field(foreign_key="students.id")
    course_id: int = Field(foreign_key="courses.id")
    task_id: int = Field(foreign_key="tasks.id")
    status: str = Field(max_length=20)  # "Выполнено", "Не выполнено"
    completed_at: Optional[datetime] = Field(default=None)
    deadline: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    student: Student = Relationship(back_populates="task_completions")
    course: Course = Relationship(back_populates="task_completions")
    task: Task = Relationship(back_populates="completions")
