"""
Teacher service for managing teacher dashboard and course oversight.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.services.metrics_service import MetricsService
from app.services.config_service import config_service

logger = logging.getLogger("app.teacher")


class TeacherService:
    """Service for managing teacher dashboard and course oversight."""
    
    def __init__(self):
        self.metrics_service = MetricsService()
        self.logger = logger
    
    def get_teacher_dashboard(self, db: Session) -> Dict[str, Any]:
        """
        Get comprehensive teacher dashboard data.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with teacher dashboard data
        """
        try:
            self.logger.info("Getting teacher dashboard data")
            
            # Get all courses
            courses = db.query(Course).all()
            
            # Get course summaries
            course_summaries = []
            for course in courses:
                course_summary = self._get_course_summary(course.id, db)
                course_summaries.append(course_summary)
            
            # Get risk students across all courses
            risk_students = self._get_risk_students_all_courses(db)
            
            # Get system metrics
            system_metrics = self.metrics_service.get_system_metrics(db)
            
            return {
                "courses": course_summaries,
                "risk_students": risk_students,
                "system_metrics": system_metrics,
                "generated_at": config_service.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting teacher dashboard: {e}")
            return {"error": str(e)}
    
    def get_course_details(self, course_id: int, db: Session) -> Dict[str, Any]:
        """
        Get detailed information about a specific course.
        
        Args:
            course_id: Course ID
            db: Database session
            
        Returns:
            Dictionary with course details
        """
        try:
            self.logger.info(f"Getting course details for course: {course_id}")
            
            # Get course
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return {"error": "Course not found"}
            
            # Get course summary
            course_summary = self._get_course_summary(course_id, db)
            
            # Get all students in this course
            students = self._get_course_students(course_id, db)
            
            # Get risk students for this course
            risk_students = self._get_risk_students_for_course(course_id, db)
            
            # Get recent activity
            recent_activity = self._get_course_recent_activity(course_id, db)
            
            return {
                "course": course,
                "summary": course_summary,
                "students": students,
                "risk_students": risk_students,
                "recent_activity": recent_activity,
                "generated_at": config_service.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting course details: {e}")
            return {"error": str(e)}
    
    def _get_course_summary(self, course_id: int, db: Session) -> Dict[str, Any]:
        """Get summary statistics for a course."""
        try:
            # Get total students in course
            total_students = db.query(Student).join(TaskCompletion).filter(
                TaskCompletion.course_id == course_id
            ).distinct().count()
            
            # Get total tasks
            total_tasks = db.query(Task).filter(Task.course_id == course_id).count()
            
            # Get attendance statistics
            total_attendance_records = db.query(Attendance).filter(
                Attendance.course_id == course_id
            ).count()
            attended_records = db.query(Attendance).filter(
                and_(Attendance.course_id == course_id, Attendance.attended == True)
            ).count()
            
            # Get task completion statistics
            total_completions = db.query(TaskCompletion).filter(
                TaskCompletion.course_id == course_id
            ).count()
            completed_tasks = db.query(TaskCompletion).filter(
                and_(TaskCompletion.course_id == course_id, TaskCompletion.status == "Выполнено")
            ).count()
            
            # Get overdue tasks
            current_time = config_service.now()
            overdue_tasks = db.query(TaskCompletion).filter(
                and_(
                    TaskCompletion.course_id == course_id,
                    TaskCompletion.deadline.isnot(None),
                    TaskCompletion.deadline < current_time,
                    TaskCompletion.status != "Выполнено"
                )
            ).count()
            
            # Get upcoming deadlines
            upcoming_deadlines = self.metrics_service.get_upcoming_deadlines(7, db)
            course_upcoming = [d for d in upcoming_deadlines if d.get("course_id") == course_id]
            
            return {
                "course_id": course_id,
                "total_students": total_students,
                "total_tasks": total_tasks,
                "attendance_rate": (attended_records / total_attendance_records * 100) if total_attendance_records > 0 else 0,
                "completion_rate": (completed_tasks / total_completions * 100) if total_completions > 0 else 0,
                "overdue_tasks": overdue_tasks,
                "upcoming_deadlines": len(course_upcoming)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting course summary: {e}")
            return {"course_id": course_id, "error": str(e)}
    
    def _get_course_students(self, course_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get all students in a course with their progress."""
        try:
            # Get students in course
            students = db.query(Student).join(TaskCompletion).filter(
                TaskCompletion.course_id == course_id
            ).distinct().all()
            
            student_data = []
            for student in students:
                # Get student progress for this course
                progress = self.metrics_service.calculate_student_progress(student.id, db)
                
                # Filter course-specific data
                course_data = None
                if "courses" in progress:
                    course_data = next((c for c in progress["courses"] if c["course_name"] == db.query(Course).filter(Course.id == course_id).first().name), None)
                
                student_data.append({
                    "student_id": student.id,
                    "student_name": student.name or f"Студент {student.id}",
                    "attendance_rate": course_data["attendance_progress"] if course_data else 0,
                    "completion_rate": course_data["task_progress"] if course_data else 0,
                    "overall_progress": progress.get("overall_progress", 0),
                    "status": self._get_student_status(course_data)
                })
            
            return student_data
            
        except Exception as e:
            self.logger.error(f"Error getting course students: {e}")
            return []
    
    def _get_risk_students_all_courses(self, db: Session) -> List[Dict[str, Any]]:
        """Get risk students across all courses."""
        try:
            risk_students = []
            
            # Get all courses
            courses = db.query(Course).all()
            
            for course in courses:
                course_risk_students = self._get_risk_students_for_course(course.id, db)
                for student in course_risk_students:
                    student["course_name"] = course.name
                    student["course_id"] = course.id
                risk_students.extend(course_risk_students)
            
            # Sort by risk level and limit
            risk_students.sort(key=lambda x: x["risk_score"], reverse=True)
            return risk_students[:20]  # Top 20 risk students
            
        except Exception as e:
            self.logger.error(f"Error getting risk students: {e}")
            return []
    
    def _get_risk_students_for_course(self, course_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get risk students for a specific course."""
        try:
            risk_students = []
            
            # Get students in course
            students = db.query(Student).join(TaskCompletion).filter(
                TaskCompletion.course_id == course_id
            ).distinct().all()
            
            for student in students:
                # Get student progress
                progress = self.metrics_service.calculate_student_progress(student.id, db)
                
                # Find course-specific data
                course_data = None
                if "courses" in progress:
                    course_data = next((c for c in progress["courses"] if c["course_name"] == db.query(Course).filter(Course.id == course_id).first().name), None)
                
                if course_data:
                    # Calculate risk score
                    risk_score = self._calculate_risk_score(course_data, progress)
                    
                    if risk_score > 50:  # High risk threshold
                        risk_students.append({
                            "student_id": student.id,
                            "student_name": student.name or f"Студент {student.id}",
                            "attendance_rate": course_data["attendance_progress"],
                            "completion_rate": course_data["task_progress"],
                            "overdue_tasks": self._count_overdue_tasks(student.id, course_id, db),
                            "risk_score": risk_score,
                            "risk_factors": self._get_risk_factors(course_data, progress)
                        })
            
            return risk_students
            
        except Exception as e:
            self.logger.error(f"Error getting risk students for course: {e}")
            return []
    
    def _get_course_recent_activity(self, course_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get recent activity for a course."""
        try:
            # Get recent task completions
            recent_completions = db.query(TaskCompletion).join(Task).filter(
                and_(
                    TaskCompletion.course_id == course_id,
                    TaskCompletion.completed_at.isnot(None),
                    TaskCompletion.completed_at >= config_service.now() - timedelta(days=7)
                )
            ).order_by(desc(TaskCompletion.completed_at)).limit(10).all()
            
            activity = []
            for completion in recent_completions:
                activity.append({
                    "type": "task_completion",
                    "student_id": completion.student_id,
                    "task_name": completion.task.name,
                    "timestamp": completion.completed_at,
                    "status": completion.status
                })
            
            return activity
            
        except Exception as e:
            self.logger.error(f"Error getting course recent activity: {e}")
            return []
    
    def _get_student_status(self, course_data: Optional[Dict[str, Any]]) -> str:
        """Get student status based on course data."""
        if not course_data:
            return "unknown"
        
        attendance_rate = course_data.get("attendance_progress", 0)
        completion_rate = course_data.get("task_progress", 0)
        
        if attendance_rate < 50 or completion_rate < 30:
            return "high_risk"
        elif attendance_rate < 70 or completion_rate < 60:
            return "medium_risk"
        else:
            return "good"
    
    def _calculate_risk_score(self, course_data: Dict[str, Any], progress: Dict[str, Any]) -> float:
        """Calculate risk score for a student."""
        try:
            attendance_rate = course_data.get("attendance_progress", 0)
            completion_rate = course_data.get("task_progress", 0)
            overall_progress = progress.get("overall_progress", 0)
            
            # Risk factors
            attendance_risk = max(0, 100 - attendance_rate) * 0.4
            completion_risk = max(0, 100 - completion_rate) * 0.4
            overall_risk = max(0, 100 - overall_progress) * 0.2
            
            return min(100, attendance_risk + completion_risk + overall_risk)
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return 0
    
    def _count_overdue_tasks(self, student_id: str, course_id: int, db: Session) -> int:
        """Count overdue tasks for a student in a course."""
        try:
            current_time = config_service.now()
            overdue_count = db.query(TaskCompletion).filter(
                and_(
                    TaskCompletion.student_id == student_id,
                    TaskCompletion.course_id == course_id,
                    TaskCompletion.deadline.isnot(None),
                    TaskCompletion.deadline < current_time,
                    TaskCompletion.status != "Выполнено"
                )
            ).count()
            
            return overdue_count
            
        except Exception as e:
            self.logger.error(f"Error counting overdue tasks: {e}")
            return 0
    
    def _get_risk_factors(self, course_data: Dict[str, Any], progress: Dict[str, Any]) -> List[str]:
        """Get list of risk factors for a student."""
        factors = []
        
        attendance_rate = course_data.get("attendance_progress", 0)
        completion_rate = course_data.get("task_progress", 0)
        overall_progress = progress.get("overall_progress", 0)
        
        if attendance_rate < 50:
            factors.append("Низкая посещаемость")
        if completion_rate < 30:
            factors.append("Низкое выполнение заданий")
        if overall_progress < 40:
            factors.append("Общий низкий прогресс")
        
        return factors
