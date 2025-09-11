"""
Metrics service for calculating student progress and task statuses.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.student import Attendance, Course, Student, Task, TaskCompletion
from app.services.config_service import config_service

logger = logging.getLogger("app.metrics")


class MetricsService:
    """Service for calculating metrics, progress, and task statuses."""

    def __init__(self):
        self.logger = logger

    def calculate_task_status(self, task_completion: TaskCompletion) -> str:
        """
        Calculate task status based on completion and deadline.

        Args:
            task_completion: TaskCompletion object

        Returns:
            Status string: 'submitted', 'on_review', 'late', 'missing'
        """
        try:
            current_time = config_service.now()

            # If task is completed
            if task_completion.status == "Выполнено" and task_completion.completed_at:
                # Check if completed on time
                if task_completion.deadline and task_completion.completed_at > task_completion.deadline:
                    return "late"
                else:
                    return "submitted"

            # If task is in progress or submitted but not marked as completed
            elif task_completion.status in ["В процессе", "Отправлено"]:
                if task_completion.deadline and current_time > task_completion.deadline:
                    return "late"
                else:
                    return "on_review"

            # If task has deadline and it's past
            elif task_completion.deadline and current_time > task_completion.deadline:
                return "missing"

            # Default status
            else:
                return "on_review"

        except Exception as e:
            self.logger.error(f"Error calculating task status: {e}")
            return "missing"

    def calculate_student_progress(self, student_id: str, db: Session) -> Dict[str, Any]:
        """
        Calculate comprehensive student progress.

        Args:
            student_id: Student ID
            db: Database session

        Returns:
            Dictionary with progress metrics
        """
        try:
            self.logger.info(f"Calculating progress for student: {student_id}")

            # Get student
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return {"error": "Student not found"}

            # Calculate attendance metrics
            attendance_metrics = self._calculate_attendance_metrics(student_id, db)

            # Calculate task completion metrics
            task_metrics = self._calculate_task_metrics(student_id, db)

            # Calculate course-specific metrics
            course_metrics = self._calculate_course_metrics(student_id, db)

            # Calculate overall progress
            overall_progress = self._calculate_overall_progress(attendance_metrics, task_metrics)

            return {
                "student_id": student_id,
                "attendance": attendance_metrics,
                "tasks": task_metrics,
                "courses": course_metrics,
                "overall_progress": overall_progress,
                "calculated_at": config_service.now(),
            }

        except Exception as e:
            self.logger.error(f"Error calculating student progress: {e}")
            return {"error": str(e)}

    def recalculate_all_students_progress(self, db: Session) -> Dict[str, Any]:
        """
        Recalculate progress for all students.

        Args:
            db: Database session

        Returns:
            Summary of recalculation results
        """
        try:
            self.logger.info("Starting recalculation of all students progress")

            students = db.query(Student).all()
            results = {"total_students": len(students), "processed": 0, "errors": 0, "started_at": config_service.now()}

            for student in students:
                try:
                    progress = self.calculate_student_progress(student.id, db)
                    if "error" not in progress:
                        results["processed"] += 1
                    else:
                        results["errors"] += 1
                        self.logger.warning(f"Error calculating progress for student {student.id}: {progress['error']}")
                except Exception as e:
                    results["errors"] += 1
                    self.logger.error(f"Error processing student {student.id}: {e}")

            results["completed_at"] = config_service.now()
            results["duration_seconds"] = (results["completed_at"] - results["started_at"]).total_seconds()

            self.logger.info(f"Recalculation completed: {results}")
            return results

        except Exception as e:
            self.logger.error(f"Error in recalculate_all_students_progress: {e}")
            return {"error": str(e)}

    def get_upcoming_deadlines(self, days_ahead: int = 7, db: Session = None) -> List[Dict[str, Any]]:
        """
        Get upcoming deadlines for all students.

        Args:
            days_ahead: Number of days to look ahead
            db: Database session

        Returns:
            List of upcoming deadlines
        """
        try:
            current_time = config_service.now()
            future_date = current_time + timedelta(days=days_ahead)

            # Get upcoming deadlines
            upcoming = (
                db.query(TaskCompletion)
                .join(Task)
                .filter(
                    and_(
                        TaskCompletion.deadline.isnot(None),
                        TaskCompletion.deadline > current_time,
                        TaskCompletion.deadline <= future_date,
                        TaskCompletion.status != "Выполнено",
                    )
                )
                .order_by(TaskCompletion.deadline.asc())
                .all()
            )

            deadlines = []
            for completion in upcoming:
                days_left = (completion.deadline - current_time).days
                urgency = "critical" if days_left <= 1 else "high" if days_left <= 3 else "medium"

                deadlines.append(
                    {
                        "student_id": completion.student_id,
                        "task_name": completion.task.name,
                        "course_name": completion.task.course.name,
                        "deadline": completion.deadline,
                        "days_left": days_left,
                        "urgency": urgency,
                        "task_type": completion.task.task_type,
                    }
                )

            return deadlines

        except Exception as e:
            self.logger.error(f"Error getting upcoming deadlines: {e}")
            return []

    def _calculate_attendance_metrics(self, student_id: str, db: Session) -> Dict[str, Any]:
        """Calculate attendance metrics for student."""
        try:
            total_attendance = db.query(Attendance).filter(Attendance.student_id == student_id).count()
            attended = (
                db.query(Attendance).filter(and_(Attendance.student_id == student_id, Attendance.attended == True)).count()
            )

            return {
                "total": total_attendance,
                "attended": attended,
                "percentage": (attended / total_attendance * 100) if total_attendance > 0 else 0,
            }
        except Exception as e:
            self.logger.error(f"Error calculating attendance metrics: {e}")
            return {"total": 0, "attended": 0, "percentage": 0}

    def _calculate_task_metrics(self, student_id: str, db: Session) -> Dict[str, Any]:
        """Calculate task completion metrics for student."""
        try:
            total_tasks = db.query(TaskCompletion).filter(TaskCompletion.student_id == student_id).count()
            completed = (
                db.query(TaskCompletion)
                .filter(and_(TaskCompletion.student_id == student_id, TaskCompletion.status == "Выполнено"))
                .count()
            )

            # Calculate status breakdown
            status_counts = {}
            task_completions = db.query(TaskCompletion).filter(TaskCompletion.student_id == student_id).all()

            for completion in task_completions:
                status = self.calculate_task_status(completion)
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                "total": total_tasks,
                "completed": completed,
                "percentage": (completed / total_tasks * 100) if total_tasks > 0 else 0,
                "status_breakdown": status_counts,
            }
        except Exception as e:
            self.logger.error(f"Error calculating task metrics: {e}")
            return {"total": 0, "completed": 0, "percentage": 0, "status_breakdown": {}}

    def _calculate_course_metrics(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """Calculate course-specific metrics for student."""
        try:
            courses = db.query(Course).join(TaskCompletion).filter(TaskCompletion.student_id == student_id).distinct().all()

            course_metrics = []
            for course in courses:
                # Task metrics for this course
                total_tasks = db.query(Task).filter(Task.course_id == course.id).count()
                completed_tasks = (
                    db.query(TaskCompletion)
                    .filter(
                        and_(
                            TaskCompletion.student_id == student_id,
                            TaskCompletion.course_id == course.id,
                            TaskCompletion.status == "Выполнено",
                        )
                    )
                    .count()
                )

                # Attendance for this course
                total_lessons = (
                    db.query(Attendance)
                    .filter(and_(Attendance.student_id == student_id, Attendance.course_id == course.id))
                    .count()
                )
                attended_lessons = (
                    db.query(Attendance)
                    .filter(
                        and_(
                            Attendance.student_id == student_id, Attendance.course_id == course.id, Attendance.attended == True
                        )
                    )
                    .count()
                )

                course_metrics.append(
                    {
                        "course_name": course.name,
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks,
                        "task_progress": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                        "total_lessons": total_lessons,
                        "attended_lessons": attended_lessons,
                        "attendance_progress": (attended_lessons / total_lessons * 100) if total_lessons > 0 else 0,
                    }
                )

            return course_metrics

        except Exception as e:
            self.logger.error(f"Error calculating course metrics: {e}")
            return []

    def _calculate_overall_progress(self, attendance_metrics: Dict[str, Any], task_metrics: Dict[str, Any]) -> float:
        """Calculate overall progress score."""
        try:
            # Weighted average: 30% attendance, 70% task completion
            attendance_weight = 0.3
            task_weight = 0.7

            overall = (
                attendance_metrics.get("percentage", 0) * attendance_weight + task_metrics.get("percentage", 0) * task_weight
            )

            return round(overall, 1)
        except Exception as e:
            self.logger.error(f"Error calculating overall progress: {e}")
            return 0.0

    def get_system_metrics(self, db: Session) -> Dict[str, Any]:
        """
        Get system-wide metrics.

        Args:
            db: Database session

        Returns:
            Dictionary with system metrics
        """
        try:
            current_time = config_service.now()

            # Basic counts
            total_students = db.query(Student).count()
            total_courses = db.query(Course).count()
            total_tasks = db.query(Task).count()

            # Active students (with recent activity)
            week_ago = current_time - timedelta(days=7)
            active_students = (
                db.query(Student).join(TaskCompletion).filter(TaskCompletion.created_at >= week_ago).distinct().count()
            )

            # Overdue tasks
            overdue_tasks = (
                db.query(TaskCompletion)
                .filter(
                    and_(
                        TaskCompletion.deadline.isnot(None),
                        TaskCompletion.deadline < current_time,
                        TaskCompletion.status != "Выполнено",
                    )
                )
                .count()
            )

            # Upcoming deadlines
            upcoming_deadlines = self.get_upcoming_deadlines(7, db)

            return {
                "total_students": total_students,
                "active_students": active_students,
                "total_courses": total_courses,
                "total_tasks": total_tasks,
                "overdue_tasks": overdue_tasks,
                "upcoming_deadlines": len(upcoming_deadlines),
                "calculated_at": current_time,
            }

        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e)}
