"""
Learning process import service for processing learning_process.xlsx files.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.student import Student, Course, Task, TaskCompletion
from app.models.import_models import ImportJob, ImportErrorLog

logger = logging.getLogger("app.learning_import")


class LearningImportService:
    """Service for importing learning process data from Excel files."""
    
    def process_learning_file(self, file_path: str, job_id: str, db: Session) -> Dict[str, Any]:
        """
        Process learning process Excel file and import data.
        
        Args:
            file_path: Path to Excel file
            job_id: Import job ID
            db: Database session
            
        Returns:
            Dictionary with import results
        """
        try:
            logger.info(f"Starting learning process import for job {job_id}")
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_cols = ['Студент_ID', 'Курс']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Get or create course
            course_name = df['Курс'].iloc[0]  # Assume all rows have same course
            course = self._get_or_create_course(course_name, db)
            
            # Find task columns (not time or deadline columns)
            task_cols = self._get_task_columns(df.columns)
            logger.info(f"Found {len(task_cols)} task columns")
            
            # Create tasks if they don't exist
            tasks = self._create_tasks(course.id, task_cols, df, db)
            
            # Process each student
            imported_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    student_id = self._clean_student_id(row['Студент_ID'])
                    
                    # Get or create student
                    student = self._get_or_create_student(student_id, db)
                    
                    # Process task completions
                    for task_col in task_cols:
                        task = tasks.get(task_col)
                        if task:
                            status = row[task_col]
                            completed_at = self._get_completion_time(df.columns, task_col, row)
                            deadline = self._get_deadline(df.columns, task_col, row)
                            
                            # Check if completion record already exists
                            existing = db.query(TaskCompletion).filter(
                                TaskCompletion.student_id == student.id,
                                TaskCompletion.task_id == task.id
                            ).first()
                            
                            if not existing:
                                completion = TaskCompletion(
                                    student_id=student.id,
                                    course_id=course.id,
                                    task_id=task.id,
                                    status=str(status) if pd.notna(status) else "Не выполнено",
                                    completed_at=completed_at,
                                    deadline=deadline
                                )
                                db.add(completion)
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    self._log_error(job_id, index + 1, None, "processing", str(e), str(row.to_dict()), db)
                    logger.error(f"Error processing student row {index + 1}: {e}")
            
            db.commit()
            
            logger.info(f"Learning process import completed: {imported_count} students, {error_count} errors")
            
            return {
                "total_rows": len(df),
                "imported_students": imported_count,
                "error_count": error_count,
                "tasks_created": len(tasks)
            }
            
        except Exception as e:
            logger.error(f"Learning process import failed for job {job_id}: {e}")
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
    
    def _get_task_columns(self, columns: List[str]) -> List[str]:
        """Get task columns (exclude time and deadline columns)."""
        task_cols = []
        for col in columns:
            if (not col.startswith('Время выполнения') and 
                not col.startswith('Дедлайн') and 
                col not in ['Студент_ID', 'Курс', 'Дорожная карта курса']):
                task_cols.append(col)
        return task_cols
    
    def _create_tasks(self, course_id: int, task_cols: List[str], df: pd.DataFrame, db: Session) -> Dict[str, Task]:
        """Create tasks for the course."""
        tasks = {}
        
        for task_col in task_cols:
            # Check if task already exists
            existing_task = db.query(Task).filter(
                Task.course_id == course_id,
                Task.name == task_col
            ).first()
            
            if existing_task:
                tasks[task_col] = existing_task
            else:
                # Determine task type based on name
                task_type = self._determine_task_type(task_col)
                
                # Get deadline from the first row (assuming all students have same deadlines)
                deadline = self._get_deadline_from_first_row(df.columns, task_col, df)
                
                task = Task(
                    course_id=course_id,
                    name=task_col,
                    task_type=task_type,
                    deadline=deadline
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                tasks[task_col] = task
        
        return tasks
    
    def _determine_task_type(self, task_name: str) -> str:
        """Determine task type based on name."""
        task_name_lower = task_name.lower()
        if 'лекция' in task_name_lower:
            return 'lecture'
        elif 'тест' in task_name_lower:
            return 'test'
        elif 'задание' in task_name_lower:
            return 'assignment'
        else:
            return 'other'
    
    def _get_deadline_from_first_row(self, columns: List[str], task_col: str, df: pd.DataFrame) -> Optional[datetime]:
        """Get deadline for a task from the first row."""
        # Find the deadline column that corresponds to this task
        task_index = list(columns).index(task_col)
        
        # Look for deadline column after this task
        for i in range(task_index + 1, len(columns)):
            if columns[i].startswith('Дедлайн'):
                deadline_value = df[columns[i]].iloc[0]
                if pd.notna(deadline_value):
                    return deadline_value
                break
        
        return None
    
    def _get_completion_time(self, columns: List[str], task_col: str, row: pd.Series) -> Optional[datetime]:
        """Get completion time for a task."""
        task_index = list(columns).index(task_col)
        
        # Look for time column after this task
        for i in range(task_index + 1, len(columns)):
            if columns[i].startswith('Время выполнения'):
                time_value = row[columns[i]]
                if pd.notna(time_value):
                    return time_value
                break
        
        return None
    
    def _get_deadline(self, columns: List[str], task_col: str, row: pd.Series) -> Optional[datetime]:
        """Get deadline for a task."""
        task_index = list(columns).index(task_col)
        
        # Look for deadline column after this task
        for i in range(task_index + 1, len(columns)):
            if columns[i].startswith('Дедлайн'):
                deadline_value = row[columns[i]]
                if pd.notna(deadline_value):
                    return deadline_value
                break
        
        return None
    
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
