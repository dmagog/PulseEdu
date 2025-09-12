"""
Fixed tests for service classes with correct method signatures.
"""

from datetime import datetime

from app.services.metrics_service import MetricsService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService


class TestStudentService:
    """Test StudentService."""

    def test_get_student_assignments_empty(self, isolated_db_session):
        """Test getting assignments for student with no courses."""
        service = StudentService()
        assignments = service.get_student_assignments("nonexistent_student", isolated_db_session)

        assert assignments == []

    def test_get_student_assignments_with_data(self, isolated_db_session):
        """Test getting assignments for student with courses."""
        # Create test data
        import uuid
        student_id = f"test_student_{uuid.uuid4().hex[:8]}"
        course_id = int(datetime.now().timestamp()) % 1000000
        task_id = int(datetime.now().timestamp()) % 1000000

        # Create student
        from app.models.student import Student

        student = Student(id=student_id, name="Тестовый Студент")
        isolated_db_session.add(student)
        isolated_db_session.flush()  # Force SQLAlchemy to process the student first

        # Create course
        from app.models.student import Course

        course = Course(id=course_id, name="Тестовый курс")
        isolated_db_session.add(course)
        isolated_db_session.flush()  # Force SQLAlchemy to process the course

        # Create task
        from app.models.student import Task

        task = Task(id=task_id, name="Тестовое задание", course_id=course_id)
        isolated_db_session.add(task)
        isolated_db_session.flush()  # Force SQLAlchemy to process the task

        # Create task completion
        from app.models.student import TaskCompletion

        completion = TaskCompletion(student_id=student_id, task_id=task_id, course_id=course_id, status="Выполнено")
        isolated_db_session.add(completion)
        isolated_db_session.commit()

        service = StudentService()
        assignments = service.get_student_assignments(student_id, isolated_db_session)

        assert len(assignments) >= 1
        # Check that we found the assignment
        assignment_found = any(a["title"] == "Тестовое задание" for a in assignments)
        assert assignment_found


class TestTeacherService:
    """Test TeacherService."""

    def test_get_teacher_students_empty(self, isolated_db_session):
        """Test getting students for teacher with no courses."""
        service = TeacherService()
        students = service.get_teacher_students(isolated_db_session)

        assert students == []

    def test_get_teacher_dashboard(self, isolated_db_session):
        """Test getting teacher dashboard data."""
        service = TeacherService()
        dashboard = service.get_teacher_dashboard(isolated_db_session)

        assert isinstance(dashboard, dict)
        # Should have basic dashboard structure
        assert "risk_students" in dashboard
        assert "courses" in dashboard
        assert "system_metrics" in dashboard


class TestMetricsService:
    """Test MetricsService."""

    def test_calculate_student_progress_empty(self, isolated_db_session):
        """Test calculating progress for student with no data."""
        service = MetricsService()
        progress = service.calculate_student_progress("nonexistent_student", isolated_db_session)

        assert isinstance(progress, dict)
        # For non-existent student, should return error
        assert "error" in progress
        assert progress["error"] == "Student not found"

    def test_calculate_student_progress_with_data(self, isolated_db_session):
        """Test calculating progress for student with completed tasks."""
        # Create test data
        import uuid
        student_id = f"test_student_{uuid.uuid4().hex[:8]}"
        course_id = int(datetime.now().timestamp()) % 1000000
        task_id = int(datetime.now().timestamp()) % 1000000

        # Create student
        from app.models.student import Student

        student = Student(id=student_id, name="Тестовый Студент")
        isolated_db_session.add(student)
        isolated_db_session.flush()  # Force SQLAlchemy to process the student first

        # Create course
        from app.models.student import Course

        course = Course(id=course_id, name="Тестовый курс")
        isolated_db_session.add(course)
        isolated_db_session.flush()  # Force SQLAlchemy to process the course

        # Create task
        from app.models.student import Task

        task = Task(id=task_id, name="Тестовое задание", course_id=course_id)
        isolated_db_session.add(task)
        isolated_db_session.flush()  # Force SQLAlchemy to process the task

        # Create task completion
        from app.models.student import TaskCompletion

        completion = TaskCompletion(student_id=student_id, task_id=task_id, course_id=course_id, status="Выполнено")
        isolated_db_session.add(completion)
        isolated_db_session.commit()

        service = MetricsService()
        progress = service.calculate_student_progress(student_id, isolated_db_session)

        assert isinstance(progress, dict)
        assert "overall_progress" in progress
        assert "courses" in progress
        # Check that we have course data with completed tasks
        assert len(progress["courses"]) >= 1
        course_data = progress["courses"][0]
        assert "completed_tasks" in course_data
        assert course_data["completed_tasks"] >= 1
