"""
Pytest configuration and fixtures for PulseEdu tests.
"""

import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import get_session
from app.main import app
from app.models.student import Course, Lesson, Student, Task
from app.models.user import Role, User


@pytest.fixture(scope="session")
def test_db_url():
    """Create a test database URL."""
    return "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Create a test database engine."""
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create a test session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_db_session(test_engine, test_session_factory):
    """Create a test database session."""
    # Create tables
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(bind=test_engine)

    session = test_session_factory()
    try:
        yield session
        # Clean up after each test
        session.rollback()
    finally:
        session.close()


@pytest.fixture(scope="function")
def isolated_db_session(test_engine):
    """Create an isolated database session for each test."""
    import os

    # Create a new in-memory database for each test
    import tempfile

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import SQLModel

    # Create temporary database file
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create engine for this test
    engine = create_engine(f"sqlite:///{temp_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        # Clean up temp file
        try:
            os.unlink(temp_db)
        except:
            pass


@pytest.fixture
def client(test_db_session):
    """Create a test client with database dependency override."""

    def override_get_session():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_session

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_student(test_db_session):
    """Create a sample student for testing."""
    import uuid

    student_id = f"test_student_{uuid.uuid4().hex[:8]}"
    student = Student(id=student_id, name="Тестовый Студент", email="test@example.com", group_id="Группа А")
    test_db_session.add(student)
    test_db_session.commit()
    test_db_session.refresh(student)
    return student


@pytest.fixture
def sample_course(test_db_session):
    """Create a sample course for testing."""
    import uuid

    course_id = uuid.uuid4().int % 1000000  # Generate unique course ID
    course = Course(id=course_id, name="Тестовый курс", description="Описание тестового курса")
    test_db_session.add(course)
    test_db_session.commit()
    test_db_session.refresh(course)
    return course


@pytest.fixture
def sample_task(test_db_session, sample_course):
    """Create a sample task for testing."""
    import uuid

    task_id = uuid.uuid4().int % 1000000  # Generate unique task ID
    task = Task(
        id=task_id,
        name="Тестовое задание",
        description="Описание тестового задания",
        course_id=sample_course.id,
        deadline="2024-12-31 23:59:59",
    )
    test_db_session.add(task)
    test_db_session.commit()
    test_db_session.refresh(task)
    return task


@pytest.fixture
def sample_lesson(test_db_session, sample_course):
    """Create a sample lesson for testing."""
    import uuid

    lesson_id = uuid.uuid4().int % 1000000  # Generate unique lesson ID
    lesson = Lesson(
        id=lesson_id, title="Тестовый урок", lesson_number=1, course_id=sample_course.id, date="2024-01-15 10:00:00"
    )
    test_db_session.add(lesson)
    test_db_session.commit()
    test_db_session.refresh(lesson)
    return lesson


@pytest.fixture
def sample_user(test_db_session):
    """Create a sample user for testing."""
    user = User(
        user_id="test_user_001",
        email="user@example.com",
        login="testuser",
        display_name="Тестовый Пользователь",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def sample_role(test_db_session):
    """Create a sample role for testing."""
    import uuid

    role_id = uuid.uuid4().int % 1000000  # Generate unique role ID
    role = Role(role_id=role_id, role_name="test_role", description="Тестовая роль")
    test_db_session.add(role)
    test_db_session.commit()
    test_db_session.refresh(role)
    return role
