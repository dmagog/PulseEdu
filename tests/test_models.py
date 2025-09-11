"""
Tests for data models.
"""
import pytest
from datetime import datetime

from app.models.student import Student, Course, Task, Lesson, Attendance, TaskCompletion
from app.models.user import User, Role, UserRole
from app.models.cluster import StudentCluster


class TestStudentModel:
    """Test Student model."""
    
    def test_student_creation(self, test_db_session, sample_student):
        """Test student creation and retrieval."""
        retrieved_student = test_db_session.query(Student).filter(
            Student.id == "test_student_001"
        ).first()
        
        assert retrieved_student is not None
        assert retrieved_student.name == "Тестовый Студент"
        assert retrieved_student.email == "test@example.com"
        assert retrieved_student.group_id == "Группа А"
    
    def test_student_required_fields(self, test_db_session):
        """Test that required fields are enforced."""
        student = Student(
            id="test_student_002",
            name="Еще один студент"
            # email и другие поля отсутствуют
        )
        test_db_session.add(student)
        test_db_session.commit()
        
        retrieved = test_db_session.query(Student).filter(
            Student.id == "test_student_002"
        ).first()
        
        assert retrieved is not None
        assert retrieved.name == "Еще один студент"


class TestCourseModel:
    """Test Course model."""
    
    def test_course_creation(self, test_db_session, sample_course):
        """Test course creation and retrieval."""
        retrieved_course = test_db_session.query(Course).filter(
            Course.id == 1
        ).first()
        
        assert retrieved_course is not None
        assert retrieved_course.name == "Тестовый курс"
        assert retrieved_course.description == "Описание тестового курса"
    
    def test_course_tasks_relationship(self, test_db_session, sample_course, sample_task):
        """Test relationship between course and tasks."""
        # sample_task уже связан с sample_course через course_id
        retrieved_course = test_db_session.query(Course).filter(
            Course.id == 1
        ).first()
        
        assert retrieved_course is not None
        
        # Проверяем, что можем получить задачи курса
        tasks = test_db_session.query(Task).filter(
            Task.course_id == retrieved_course.id
        ).all()
        
        assert len(tasks) == 1
        assert tasks[0].name == "Тестовое задание"


class TestTaskModel:
    """Test Task model."""
    
    def test_task_creation(self, test_db_session, sample_task):
        """Test task creation and retrieval."""
        retrieved_task = test_db_session.query(Task).filter(
            Task.id == 1
        ).first()
        
        assert retrieved_task is not None
        assert retrieved_task.name == "Тестовое задание"
        assert retrieved_task.description == "Описание тестового задания"
        assert retrieved_task.course_id == 1
        assert retrieved_task.deadline == "2024-12-31 23:59:59"


class TestLessonModel:
    """Test Lesson model."""
    
    def test_lesson_creation(self, test_db_session, sample_lesson):
        """Test lesson creation and retrieval."""
        retrieved_lesson = test_db_session.query(Lesson).filter(
            Lesson.id == 1
        ).first()
        
        assert retrieved_lesson is not None
        assert retrieved_lesson.title == "Тестовый урок"
        assert retrieved_lesson.lesson_number == 1
        assert retrieved_lesson.course_id == 1
        assert retrieved_lesson.date == "2024-01-15 10:00:00"


class TestAttendanceModel:
    """Test Attendance model."""
    
    def test_attendance_creation(self, test_db_session, sample_student, sample_lesson):
        """Test attendance creation and retrieval."""
        attendance = Attendance(
            student_id=sample_student.id,
            lesson_id=sample_lesson.id,
            course_id=1,
            attended=True
        )
        test_db_session.add(attendance)
        test_db_session.commit()
        
        retrieved_attendance = test_db_session.query(Attendance).filter(
            Attendance.student_id == sample_student.id,
            Attendance.lesson_id == sample_lesson.id
        ).first()
        
        assert retrieved_attendance is not None
        assert retrieved_attendance.attended is True
        assert retrieved_attendance.course_id == 1


class TestTaskCompletionModel:
    """Test TaskCompletion model."""
    
    def test_task_completion_creation(self, test_db_session, sample_student, sample_task):
        """Test task completion creation and retrieval."""
        completion = TaskCompletion(
            student_id=sample_student.id,
            task_id=sample_task.id,
            course_id=1,
            status="Выполнено",
            completed_at=datetime.now()
        )
        test_db_session.add(completion)
        test_db_session.commit()
        
        retrieved_completion = test_db_session.query(TaskCompletion).filter(
            TaskCompletion.student_id == sample_student.id,
            TaskCompletion.task_id == sample_task.id
        ).first()
        
        assert retrieved_completion is not None
        assert retrieved_completion.status == "Выполнено"
        assert retrieved_completion.course_id == 1
        assert retrieved_completion.completed_at is not None


class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self, test_db_session, sample_user):
        """Test user creation and retrieval."""
        retrieved_user = test_db_session.query(User).filter(
            User.user_id == "test_user_001"
        ).first()
        
        assert retrieved_user is not None
        assert retrieved_user.email == "user@example.com"
        assert retrieved_user.login == "testuser"
        assert retrieved_user.display_name == "Тестовый Пользователь"
        assert retrieved_user.is_active is True


class TestRoleModel:
    """Test Role model."""
    
    def test_role_creation(self, test_db_session, sample_role):
        """Test role creation and retrieval."""
        retrieved_role = test_db_session.query(Role).filter(
            Role.role_name == "test_role"
        ).first()
        
        assert retrieved_role is not None
        assert retrieved_role.role_name == "test_role"
        assert retrieved_role.description == "Тестовая роль"


class TestStudentClusterModel:
    """Test StudentCluster model."""
    
    def test_student_cluster_creation(self, test_db_session, sample_student):
        """Test student cluster creation and retrieval."""
        cluster = StudentCluster(
            student_id=sample_student.id,
            course_id=1,
            cluster_label="A",
            cluster_score=0.85,
            attendance_rate=95.5,
            completion_rate=88.0,
            overall_progress=91.5
        )
        test_db_session.add(cluster)
        test_db_session.commit()
        
        retrieved_cluster = test_db_session.query(StudentCluster).filter(
            StudentCluster.student_id == sample_student.id,
            StudentCluster.course_id == 1
        ).first()
        
        assert retrieved_cluster is not None
        assert retrieved_cluster.cluster_label == "A"
        assert retrieved_cluster.cluster_score == 0.85
        assert retrieved_cluster.attendance_rate == 95.5
        assert retrieved_cluster.completion_rate == 88.0
        assert retrieved_cluster.overall_progress == 91.5
