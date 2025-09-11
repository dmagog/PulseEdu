"""
Tests for service classes.
"""
import pytest
from datetime import datetime, timedelta

from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from app.services.metrics_service import MetricsService


class TestStudentService:
    """Test StudentService."""
    
    def test_get_student_assignments_empty(self, test_db_session):
        """Test getting assignments for student with no courses."""
        service = StudentService()
        assignments = service.get_student_assignments("nonexistent_student", test_db_session)
        
        assert assignments == []
    
    def test_get_student_assignments_with_data(self, test_db_session, sample_student, sample_course, sample_task):
        """Test getting assignments for student with courses."""
        # Создаем связь студента с курсом через TaskCompletion
        completion = TaskCompletion(
            student_id=sample_student.id,
            task_id=sample_task.id,
            course_id=sample_course.id,
            status="Выполнено"
        )
        test_db_session.add(completion)
        test_db_session.commit()
        
        service = StudentService()
        assignments = service.get_student_assignments(sample_student.id, test_db_session)
        
        assert len(assignments) == 1
        assert assignments[0]["title"] == "Тестовое задание"
        assert assignments[0]["course_name"] == "Тестовый курс"
        assert assignments[0]["status"] == "completed"
    
    def test_get_course_details_for_student(self, test_db_session, sample_student, sample_course, sample_lesson, sample_task):
        """Test getting course details for student."""
        # Создаем посещение
        attendance = Attendance(
            student_id=sample_student.id,
            lesson_id=sample_lesson.id,
            course_id=sample_course.id,
            attended=True
        )
        test_db_session.add(attendance)
        
        # Создаем выполнение задания
        completion = TaskCompletion(
            student_id=sample_student.id,
            task_id=sample_task.id,
            course_id=sample_course.id,
            status="Выполнено"
        )
        test_db_session.add(completion)
        test_db_session.commit()
        
        service = StudentService()
        course_details = service.get_course_details_for_student(sample_student.id, sample_course.id, test_db_session)
        
        assert course_details is not None
        assert course_details["course"].name == "Тестовый курс"
        assert len(course_details["lessons"]) == 1
        assert len(course_details["assignments"]) == 1


class TestTeacherService:
    """Test TeacherService."""
    
    def test_get_teacher_students_empty(self, test_db_session):
        """Test getting students for teacher with no courses."""
        service = TeacherService()
        students = service.get_teacher_students("nonexistent_teacher", test_db_session)
        
        assert students == []
    
    def test_calculate_student_attendance(self, test_db_session, sample_student, sample_lesson):
        """Test calculating student attendance."""
        # Создаем несколько посещений
        attendance1 = Attendance(
            student_id=sample_student.id,
            lesson_id=sample_lesson.id,
            course_id=1,
            attended=True
        )
        attendance2 = Attendance(
            student_id=sample_student.id,
            lesson_id=2,  # Другой урок
            course_id=1,
            attended=False
        )
        test_db_session.add_all([attendance1, attendance2])
        test_db_session.commit()
        
        service = TeacherService()
        attendance_rate = service._calculate_student_attendance(sample_student.id, 1, test_db_session)
        
        assert attendance_rate == 50.0  # 1 из 2 посещений
    
    def test_calculate_student_progress(self, test_db_session, sample_student, sample_task):
        """Test calculating student progress."""
        # Создаем выполнения заданий
        completion1 = TaskCompletion(
            student_id=sample_student.id,
            task_id=sample_task.id,
            course_id=1,
            status="Выполнено"
        )
        completion2 = TaskCompletion(
            student_id=sample_student.id,
            task_id=2,  # Другое задание
            course_id=1,
            status="В процессе"
        )
        test_db_session.add_all([completion1, completion2])
        test_db_session.commit()
        
        service = TeacherService()
        progress = service._calculate_student_progress(sample_student.id, test_db_session)
        
        assert progress == 50.0  # 1 из 2 заданий выполнено


class TestMetricsService:
    """Test MetricsService."""
    
    def test_calculate_progress_empty(self, test_db_session):
        """Test calculating progress for student with no data."""
        service = MetricsService()
        progress = service.calculate_progress("nonexistent_student", test_db_session)
        
        assert progress == 0.0
    
    def test_calculate_progress_with_data(self, test_db_session, sample_student, sample_task):
        """Test calculating progress for student with completed tasks."""
        completion = TaskCompletion(
            student_id=sample_student.id,
            task_id=sample_task.id,
            course_id=1,
            status="Выполнено"
        )
        test_db_session.add(completion)
        test_db_session.commit()
        
        service = MetricsService()
        progress = service.calculate_progress(sample_student.id, test_db_session)
        
        assert progress > 0.0
    
    def test_calculate_attendance_empty(self, test_db_session):
        """Test calculating attendance for student with no data."""
        service = MetricsService()
        attendance = service.calculate_attendance("nonexistent_student", test_db_session)
        
        assert attendance == 0.0
    
    def test_calculate_attendance_with_data(self, test_db_session, sample_student, sample_lesson):
        """Test calculating attendance for student with attendance records."""
        attendance = Attendance(
            student_id=sample_student.id,
            lesson_id=sample_lesson.id,
            course_id=1,
            attended=True
        )
        test_db_session.add(attendance)
        test_db_session.commit()
        
        service = MetricsService()
        attendance_rate = service.calculate_attendance(sample_student.id, test_db_session)
        
        assert attendance_rate > 0.0
