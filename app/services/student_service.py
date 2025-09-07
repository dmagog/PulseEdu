"""
Student service for managing student data and progress.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.services.metrics_service import MetricsService

logger = logging.getLogger("app.student")


class StudentService:
    """Service for managing student data and progress calculations."""
    
    def __init__(self):
        self.metrics_service = MetricsService()
    
    def get_student_progress(self, student_id: str, db: Session) -> Dict[str, Any]:
        """
        Get comprehensive student progress data using MetricsService.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            Dictionary with student progress data
        """
        try:
            logger.info(f"Getting progress for student: {student_id}")
            
            # Use MetricsService for comprehensive progress calculation
            progress_data = self.metrics_service.calculate_student_progress(student_id, db)
            
            if "error" in progress_data:
                return progress_data
            
            # Add additional data for backward compatibility
            progress_data["attendance"] = progress_data.get("attendance", {})
            progress_data["completion"] = progress_data.get("tasks", {})
            progress_data["courses"] = progress_data.get("courses", [])
            
            return progress_data
            
        except Exception as e:
            logger.error(f"Error getting student progress: {e}")
            return {"error": str(e)}
    
    def get_activity_feed(self, student_id: str, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent activity feed for student.
        
        Args:
            student_id: Student ID
            db: Database session
            limit: Number of activities to return
            
        Returns:
            List of recent activities
        """
        try:
            logger.info(f"Getting activity feed for student: {student_id}")
            
            activities = []
            
            # Get recent task completions
            recent_completions = db.query(TaskCompletion).filter(
                and_(
                    TaskCompletion.student_id == student_id,
                    TaskCompletion.status == "Выполнено",
                    TaskCompletion.completed_at.isnot(None)
                )
            ).order_by(TaskCompletion.completed_at.desc()).limit(limit).all()
            
            for completion in recent_completions:
                activities.append({
                    "type": "task_completion",
                    "title": f"Выполнено задание: {completion.task.name[:50]}...",
                    "timestamp": completion.completed_at,
                    "icon": "check-circle",
                    "color": "success"
                })
            
            # Get recent attendance
            recent_attendance = db.query(Attendance).filter(
                and_(
                    Attendance.student_id == student_id,
                    Attendance.attended == True
                )
            ).order_by(Attendance.created_at.desc()).limit(5).all()
            
            for attendance in recent_attendance:
                activities.append({
                    "type": "attendance",
                    "title": f"Посещено занятие: {attendance.lesson.title}",
                    "timestamp": attendance.created_at,
                    "icon": "calendar-check",
                    "color": "info"
                })
            
            # Sort by timestamp and limit
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            return activities[:limit]
            
        except Exception as e:
            logger.error(f"Error getting activity feed: {e}")
            return []
    
    def get_upcoming_deadlines(self, student_id: str, db: Session, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Get upcoming deadlines for student using MetricsService.
        
        Args:
            student_id: Student ID
            db: Database session
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming deadlines
        """
        try:
            logger.info(f"Getting upcoming deadlines for student: {student_id}")
            
            # Get all upcoming deadlines from MetricsService
            all_deadlines = self.metrics_service.get_upcoming_deadlines(days_ahead, db)
            
            # Filter for specific student
            student_deadlines = [d for d in all_deadlines if d["student_id"] == student_id]
            
            # Convert urgency to UI classes
            for deadline in student_deadlines:
                if deadline["urgency"] == "critical":
                    deadline["urgency"] = "danger"
                elif deadline["urgency"] == "high":
                    deadline["urgency"] = "warning"
                else:
                    deadline["urgency"] = "info"
            
            return student_deadlines
            
        except Exception as e:
            logger.error(f"Error getting upcoming deadlines: {e}")
            return []
    
    def get_detailed_course_data(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get detailed course data for student.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of detailed course information
        """
        try:
            logger.info(f"Getting detailed course data for student: {student_id}")
            
            # Get courses for student
            courses = db.query(Course).join(TaskCompletion).filter(
                TaskCompletion.student_id == student_id
            ).distinct().all()
            
            course_data = []
            for course in courses:
                # Get course statistics
                total_tasks = db.query(Task).filter(Task.course_id == course.id).count()
                completed_tasks = db.query(TaskCompletion).filter(
                    and_(
                        TaskCompletion.student_id == student_id,
                        TaskCompletion.course_id == course.id,
                        TaskCompletion.status == "Выполнено"
                    )
                ).count()
                
                # Get attendance for this course
                total_lessons = db.query(Attendance).filter(
                    and_(
                        Attendance.student_id == student_id,
                        Attendance.course_id == course.id
                    )
                ).count()
                attended_lessons = db.query(Attendance).filter(
                    and_(
                        Attendance.student_id == student_id,
                        Attendance.course_id == course.id,
                        Attendance.attended == True
                    )
                ).count()
                
                course_data.append({
                    "course": course,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                    "total_lessons": total_lessons,
                    "attended_lessons": attended_lessons,
                    "attendance_percentage": (attended_lessons / total_lessons * 100) if total_lessons > 0 else 0
                })
            
            return course_data
            
        except Exception as e:
            logger.error(f"Error getting detailed course data: {e}")
            return []
    
    def _get_attendance_stats(self, student_id: str, db: Session) -> Dict[str, Any]:
        """Get attendance statistics for student."""
        total_attendance = db.query(Attendance).filter(Attendance.student_id == student_id).count()
        attended = db.query(Attendance).filter(
            and_(Attendance.student_id == student_id, Attendance.attended == True)
        ).count()
        
        return {
            "total": total_attendance,
            "attended": attended,
            "percentage": (attended / total_attendance * 100) if total_attendance > 0 else 0
        }
    
    def _get_completion_stats(self, student_id: str, db: Session) -> Dict[str, Any]:
        """Get task completion statistics for student."""
        total_tasks = db.query(TaskCompletion).filter(TaskCompletion.student_id == student_id).count()
        completed = db.query(TaskCompletion).filter(
            and_(TaskCompletion.student_id == student_id, TaskCompletion.status == "Выполнено")
        ).count()
        
        return {
            "total": total_tasks,
            "completed": completed,
            "percentage": (completed / total_tasks * 100) if total_tasks > 0 else 0
        }
    
    def _get_course_progress(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get course progress for student."""
        courses = db.query(Course).join(TaskCompletion).filter(
            TaskCompletion.student_id == student_id
        ).distinct().all()
        
        course_progress = []
        for course in courses:
            total_tasks = db.query(Task).filter(Task.course_id == course.id).count()
            completed_tasks = db.query(TaskCompletion).filter(
                and_(
                    TaskCompletion.student_id == student_id,
                    TaskCompletion.course_id == course.id,
                    TaskCompletion.status == "Выполнено"
                )
            ).count()
            
            course_progress.append({
                "course_name": course.name,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "progress_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            })
        
        return course_progress
    
    def _calculate_overall_progress(self, attendance_stats: Dict[str, Any], completion_stats: Dict[str, Any]) -> float:
        """Calculate overall progress score."""
        attendance_weight = 0.3
        completion_weight = 0.7
        
        overall = (
            attendance_stats.get("percentage", 0) * attendance_weight +
            completion_stats.get("percentage", 0) * completion_weight
        )
        
        return round(overall, 1)
