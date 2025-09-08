"""
Attendance import service for processing attendance.xlsx files.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.student import Student, Course, Lesson, Attendance
from app.models.import_models import ImportJob, ImportErrorLog

logger = logging.getLogger("app.attendance_import")


class AttendanceImportService:
    """Service for importing attendance data from Excel files."""
    
    def process_attendance_file(self, file_path: str, job_id: str, db: Session) -> Dict[str, Any]:
        """
        Process attendance Excel file and import data.
        
        Args:
            file_path: Path to Excel file
            job_id: Import job ID
            db: Database session
            
        Returns:
            Dictionary with import results
        """
        try:
            logger.info(f"Starting attendance import for job {job_id}")
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_cols = ['Студент', 'Курс']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Get or create course
            course_name = df['Курс'].iloc[0]  # Assume all rows have same course
            course = self._get_or_create_course(course_name, db)
            
            # Get lesson columns
            lesson_cols = [col for col in df.columns if col.startswith('Занятие')]
            logger.info(f"Found {len(lesson_cols)} lesson columns")
            
            # Create lessons if they don't exist
            lessons = self._create_lessons(course.id, lesson_cols, db)
            
            # Process each student
            imported_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    student_id = self._clean_student_id(row['Студент'])
                    
                    # Get or create student
                    student = self._get_or_create_student(student_id, db)
                    
                    # Process attendance for each lesson
                    for lesson_col in lesson_cols:
                        lesson_number = self._extract_lesson_number(lesson_col)
                        lesson = lessons.get(lesson_number)
                        
                        if lesson:
                            attended = bool(row[lesson_col])
                            
                            # Check if attendance record already exists
                            existing = db.query(Attendance).filter(
                                Attendance.student_id == student.id,
                                Attendance.lesson_id == lesson.id
                            ).first()
                            
                            if not existing:
                                attendance = Attendance(
                                    student_id=student.id,
                                    course_id=course.id,
                                    lesson_id=lesson.id,
                                    attended=attended
                                )
                                db.add(attendance)
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    self._log_error(job_id, index + 1, None, "processing", str(e), str(row.to_dict()), db)
                    logger.error(f"Error processing student row {index + 1}: {e}")
            
            db.commit()
            
            logger.info(f"Attendance import completed: {imported_count} students, {error_count} errors")
            
            return {
                "total_rows": len(df),
                "imported_students": imported_count,
                "error_count": error_count,
                "lessons_created": len(lessons)
            }
            
        except Exception as e:
            logger.error(f"Attendance import failed for job {job_id}: {e}")
            self._log_error(job_id, 0, None, "import", str(e), None, db)
            raise
    
    def _clean_student_id(self, student_id: str) -> str:
        """Clean student ID by removing 'id_' prefix if present."""
        if student_id.startswith('id_'):
            return student_id[3:]  # Remove 'id_' prefix
        return student_id
    
    def _get_or_create_course(self, course_name: str, db: Session) -> Course:
        """Get or create course."""
        course = db.query(Course).filter(Course.name == course_name).first()
        if not course:
            course = Course(name=course_name)
            db.add(course)
            db.commit()
            db.refresh(course)
        return course
    
    def _get_or_create_student(self, student_id: str, db: Session) -> Student:
        """Get or create student."""
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            student = Student(id=student_id)
            db.add(student)
            db.commit()
            db.refresh(student)
        return student
    
    def _create_lessons(self, course_id: int, lesson_cols: List[str], db: Session) -> Dict[int, Lesson]:
        """Create lessons for the course."""
        lessons = {}
        
        for lesson_col in lesson_cols:
            lesson_number = self._extract_lesson_number(lesson_col)
            
            # Check if lesson already exists
            existing_lesson = db.query(Lesson).filter(
                Lesson.course_id == course_id,
                Lesson.lesson_number == lesson_number
            ).first()
            
            if existing_lesson:
                lessons[lesson_number] = existing_lesson
            else:
                lesson = Lesson(
                    course_id=course_id,
                    lesson_number=lesson_number,
                    title=lesson_col
                )
                db.add(lesson)
                db.commit()
                db.refresh(lesson)
                lessons[lesson_number] = lesson
        
        return lessons
    
    def _extract_lesson_number(self, lesson_col: str) -> int:
        """Extract lesson number from column name like 'Занятие 1'."""
        try:
            # Extract number from "Занятие N"
            parts = lesson_col.split()
            if len(parts) >= 2:
                return int(parts[1])
            return 1
        except (ValueError, IndexError):
            return 1
    
    def _log_error(self, job_id: str, row_number: int, column_name: str, 
                   error_type: str, error_message: str, cell_value: str, db: Session):
        """Log import error to database."""
        try:
            error = ImportErrorLog(
                job_id=job_id,
                row_number=row_number,
                column_name=column_name,
                error_type=error_type,
                error_message=error_message,
                cell_value=cell_value
            )
            db.add(error)
            db.commit()
            
            logger.warning(f"Import error logged: {error_type} at row {row_number}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to log import error: {e}")
            db.rollback()
