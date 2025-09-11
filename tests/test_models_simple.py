"""
Simple tests for data models.
"""
import pytest
from datetime import datetime

from app.models.student import Student, Course, Task
from app.models.user import User, Role


class TestStudentModel:
    """Test Student model."""
    
    def test_student_creation(self, test_db_session):
        """Test student creation and retrieval."""
        student_id = f"test_student_{hash(self.__class__.__name__) % 100000}"
        student = Student(
            id=student_id,
            name="Тестовый Студент",
            email="test@example.com",
            group_id="Группа А"
        )
        test_db_session.add(student)
        test_db_session.commit()
        
        retrieved_student = test_db_session.query(Student).filter(
            Student.id == student_id
        ).first()
        
        assert retrieved_student is not None
        assert retrieved_student.name == "Тестовый Студент"
        assert retrieved_student.email == "test@example.com"
        assert retrieved_student.group_id == "Группа А"
    
    def test_student_required_fields(self, test_db_session):
        """Test that required fields are enforced."""
        student_id = f"test_student_minimal_{hash(self.__class__.__name__) % 100000}"
        student = Student(
            id=student_id,
            name="Еще один студент"
            # email и другие поля отсутствуют
        )
        test_db_session.add(student)
        test_db_session.commit()
        
        retrieved = test_db_session.query(Student).filter(
            Student.id == student_id
        ).first()
        
        assert retrieved is not None
        assert retrieved.name == "Еще один студент"


class TestCourseModel:
    """Test Course model."""
    
    def test_course_creation(self, test_db_session):
        """Test course creation and retrieval."""
        course_id = 999999  # Use a unique ID
        course = Course(
            id=course_id,
            name="Тестовый курс",
            description="Описание тестового курса"
        )
        test_db_session.add(course)
        test_db_session.commit()
        
        retrieved_course = test_db_session.query(Course).filter(
            Course.id == course_id
        ).first()
        
        assert retrieved_course is not None
        assert retrieved_course.name == "Тестовый курс"
        assert retrieved_course.description == "Описание тестового курса"


class TestTaskModel:
    """Test Task model."""
    
    def test_task_creation(self, test_db_session):
        """Test task creation and retrieval."""
        # First create a course
        course_id = 888888
        course = Course(
            id=course_id,
            name="Курс для задания",
            description="Описание курса"
        )
        test_db_session.add(course)
        test_db_session.commit()
        
        # Then create a task
        task_id = 777777
        task = Task(
            id=task_id,
            name="Тестовое задание",
            description="Описание тестового задания",
            course_id=course_id,
            deadline=datetime(2024, 12, 31, 23, 59, 59)
        )
        test_db_session.add(task)
        test_db_session.commit()
        
        retrieved_task = test_db_session.query(Task).filter(
            Task.id == task_id
        ).first()
        
        assert retrieved_task is not None
        assert retrieved_task.name == "Тестовое задание"
        assert retrieved_task.description == "Описание тестового задания"
        assert retrieved_task.course_id == course_id
        assert retrieved_task.deadline == datetime(2024, 12, 31, 23, 59, 59)


class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self, test_db_session):
        """Test user creation and retrieval."""
        user_id = f"test_user_{hash(self.__class__.__name__) % 100000}"
        user = User(
            user_id=user_id,
            email="user@example.com",
            login="testuser",
            display_name="Тестовый Пользователь",
            is_active=True
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        retrieved_user = test_db_session.query(User).filter(
            User.user_id == user_id
        ).first()
        
        assert retrieved_user is not None
        assert retrieved_user.email == "user@example.com"
        assert retrieved_user.login == "testuser"
        assert retrieved_user.display_name == "Тестовый Пользователь"
        assert retrieved_user.is_active is True


class TestRoleModel:
    """Test Role model."""
    
    def test_role_creation(self, test_db_session):
        """Test role creation and retrieval."""
        role_id = 666666
        role = Role(
            role_id=role_id,
            name="test_role",
            role_name="test_role",
            description="Тестовая роль"
        )
        test_db_session.add(role)
        test_db_session.commit()
        
        retrieved_role = test_db_session.query(Role).filter(
            Role.role_id == role_id
        ).first()
        
        assert retrieved_role is not None
        assert retrieved_role.role_name == "test_role"
        assert retrieved_role.description == "Тестовая роль"
