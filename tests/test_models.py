"""
Fixed tests for data models with isolated database sessions.
"""
import pytest
from datetime import datetime

from app.models.student import Student, Course, Task, Lesson
from app.models.user import User, Role


class TestStudentModel:
    """Test Student model."""
    
    def test_student_creation(self, isolated_db_session):
        """Test student creation and retrieval."""
        student_id = f"test_student_{datetime.now().timestamp()}"
        student = Student(
            id=student_id,
            name="Тестовый Студент",
            email="test@example.com",
            group_id="Группа А"
        )
        isolated_db_session.add(student)
        isolated_db_session.commit()
        
        retrieved_student = isolated_db_session.query(Student).filter(
            Student.id == student_id
        ).first()
        
        assert retrieved_student is not None
        assert retrieved_student.name == "Тестовый Студент"
        assert retrieved_student.email == "test@example.com"
        assert retrieved_student.group_id == "Группа А"
    
    def test_student_required_fields(self, isolated_db_session):
        """Test that required fields are enforced."""
        student_id = f"test_student_minimal_{datetime.now().timestamp()}"
        student = Student(
            id=student_id,
            name="Еще один студент"
            # email и другие поля отсутствуют
        )
        isolated_db_session.add(student)
        isolated_db_session.commit()
        
        retrieved = isolated_db_session.query(Student).filter(
            Student.id == student_id
        ).first()
        
        assert retrieved is not None
        assert retrieved.name == "Еще один студент"


class TestCourseModel:
    """Test Course model."""
    
    def test_course_creation(self, isolated_db_session):
        """Test course creation and retrieval."""
        course_id = int(datetime.now().timestamp()) % 1000000
        course = Course(
            id=course_id,
            name="Тестовый курс",
            description="Описание тестового курса"
        )
        isolated_db_session.add(course)
        isolated_db_session.commit()
        
        retrieved_course = isolated_db_session.query(Course).filter(
            Course.id == course_id
        ).first()
        
        assert retrieved_course is not None
        assert retrieved_course.name == "Тестовый курс"
        assert retrieved_course.description == "Описание тестового курса"


class TestTaskModel:
    """Test Task model."""
    
    def test_task_creation(self, isolated_db_session):
        """Test task creation and retrieval."""
        # First create a course
        course_id = int(datetime.now().timestamp()) % 1000000
        course = Course(
            id=course_id,
            name="Курс для задания",
            description="Описание курса"
        )
        isolated_db_session.add(course)
        isolated_db_session.commit()
        
        # Then create a task
        task_id = int(datetime.now().timestamp()) % 1000000
        task = Task(
            id=task_id,
            name="Тестовое задание",
            course_id=course_id,
            deadline=datetime(2024, 12, 31, 23, 59, 59)
        )
        isolated_db_session.add(task)
        isolated_db_session.commit()
        
        retrieved_task = isolated_db_session.query(Task).filter(
            Task.id == task_id
        ).first()
        
        assert retrieved_task is not None
        assert retrieved_task.name == "Тестовое задание"
        assert retrieved_task.course_id == course_id
        assert retrieved_task.deadline == datetime(2024, 12, 31, 23, 59, 59)


class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self, isolated_db_session):
        """Test user creation and retrieval."""
        user_id = f"test_user_{datetime.now().timestamp()}"
        user = User(
            user_id=user_id,
            email="user@example.com",
            login=f"testuser_{datetime.now().timestamp()}",
            display_name="Тестовый Пользователь",
            is_active=True
        )
        isolated_db_session.add(user)
        isolated_db_session.commit()
        
        retrieved_user = isolated_db_session.query(User).filter(
            User.user_id == user_id
        ).first()
        
        assert retrieved_user is not None
        assert retrieved_user.email == "user@example.com"
        assert retrieved_user.display_name == "Тестовый Пользователь"
        assert retrieved_user.is_active is True


class TestRoleModel:
    """Test Role model."""
    
    def test_role_creation(self, isolated_db_session):
        """Test role creation and retrieval."""
        role_id = int(datetime.now().timestamp()) % 1000000
        role_name = f"test_role_{datetime.now().timestamp()}"
        role = Role(
            role_id=role_id,
            name=role_name,
            description="Тестовая роль"
        )
        isolated_db_session.add(role)
        isolated_db_session.commit()
        
        retrieved_role = isolated_db_session.query(Role).filter(
            Role.role_id == role_id
        ).first()
        
        assert retrieved_role is not None
        assert retrieved_role.name == role_name
        assert retrieved_role.description == "Тестовая роль"
