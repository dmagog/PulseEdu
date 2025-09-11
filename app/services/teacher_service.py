"""
Teacher service for managing teacher dashboard and course oversight.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as SQLAlchemySession
from sqlmodel import Session, and_, desc, func, select

from app.models.cluster import StudentCluster
from app.models.student import Attendance, Course, Student, Task, TaskCompletion
from app.services.config_service import config_service
from app.services.metrics_service import MetricsService

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
                "generated_at": config_service.now(),
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
                "generated_at": config_service.now(),
            }

        except Exception as e:
            self.logger.error(f"Error getting course details: {e}")
            return {"error": str(e)}

    def _get_course_summary(self, course_id: int, db: Session) -> Dict[str, Any]:
        """Get summary statistics for a course."""
        try:
            # Get course information
            course = db.query(Course).filter(Course.id == course_id).first()
            course_name = course.name if course else f"Курс #{course_id}"

            # Get total students in course
            total_students = (
                db.query(Student).join(TaskCompletion).filter(TaskCompletion.course_id == course_id).distinct().count()
            )

            # Get unique groups in course
            unique_groups = (
                db.query(Student.group_id)
                .join(TaskCompletion)
                .filter(and_(TaskCompletion.course_id == course_id, Student.group_id.isnot(None)))
                .distinct()
                .count()
            )

            # Get total tasks
            total_tasks = db.query(Task).filter(Task.course_id == course_id).count()

            # Get attendance statistics
            total_attendance_records = db.query(Attendance).filter(Attendance.course_id == course_id).count()
            attended_records = (
                db.query(Attendance).filter(and_(Attendance.course_id == course_id, Attendance.attended == True)).count()
            )

            # Get task completion statistics
            total_completions = db.query(TaskCompletion).filter(TaskCompletion.course_id == course_id).count()
            completed_tasks = (
                db.query(TaskCompletion)
                .filter(and_(TaskCompletion.course_id == course_id, TaskCompletion.status == "Выполнено"))
                .count()
            )

            # Get overdue tasks
            current_time = config_service.now()
            overdue_tasks = (
                db.query(TaskCompletion)
                .filter(
                    and_(
                        TaskCompletion.course_id == course_id,
                        TaskCompletion.deadline.isnot(None),
                        TaskCompletion.deadline < current_time,
                        TaskCompletion.status != "Выполнено",
                    )
                )
                .count()
            )

            # Get upcoming deadlines
            upcoming_deadlines = self.metrics_service.get_upcoming_deadlines(7, db)
            course_upcoming = [d for d in upcoming_deadlines if d.get("course_id") == course_id]

            return {
                "course_id": course_id,
                "course_name": course_name,
                "total_students": total_students,
                "total_groups": unique_groups,
                "total_tasks": total_tasks,
                "attendance_rate": (attended_records / total_attendance_records * 100) if total_attendance_records > 0 else 0,
                "completion_rate": (completed_tasks / total_completions * 100) if total_completions > 0 else 0,
                "overdue_tasks": overdue_tasks,
                "upcoming_deadlines": len(course_upcoming),
            }

        except Exception as e:
            self.logger.error(f"Error getting course summary: {e}")
            return {"course_id": course_id, "error": str(e)}

    def _get_course_students(self, course_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get all students in a course with their progress."""
        try:
            # Get students in course
            students = db.query(Student).join(TaskCompletion).filter(TaskCompletion.course_id == course_id).distinct().all()

            student_data = []
            for student in students:
                # Get student progress for this course
                progress = self.metrics_service.calculate_student_progress(student.id, db)

                # Filter course-specific data
                course_data = None
                if "courses" in progress:
                    course_data = next(
                        (
                            c
                            for c in progress["courses"]
                            if c["course_name"] == db.query(Course).filter(Course.id == course_id).first().name
                        ),
                        None,
                    )

                # Get cluster information
                cluster = (
                    db.query(StudentCluster)
                    .filter(and_(StudentCluster.student_id == student.id, StudentCluster.course_id == course_id))
                    .first()
                )

                student_data.append(
                    {
                        "student_id": student.id,
                        "student_name": student.name or f"Студент {student.id}",
                        "attendance_rate": course_data["attendance_progress"] if course_data else 0,
                        "completion_rate": course_data["task_progress"] if course_data else 0,
                        "overall_progress": progress.get("overall_progress", 0),
                        "status": self._get_student_status(course_data),
                        "cluster_label": cluster.cluster_label if cluster else None,
                        "cluster_score": cluster.cluster_score if cluster else None,
                    }
                )

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

    def get_teacher_courses(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get teacher courses data.

        Args:
            db: Database session

        Returns:
            List of course data
        """
        try:
            self.logger.info("Getting teacher courses")

            # Mock courses data
            courses = [
                {
                    "id": "1",
                    "name": "Программирование на Python",
                    "description": "Основы программирования на языке Python",
                    "status": "active",
                    "semester": "1",
                    "student_count": 25,
                    "task_count": 12,
                    "avg_progress": 78,
                    "start_date": "2024-01-15",
                    "end_date": "2024-05-15",
                    "duration": 120,
                },
                {
                    "id": "2",
                    "name": "Веб-разработка",
                    "description": "Создание веб-приложений с использованием современных технологий",
                    "status": "active",
                    "semester": "2",
                    "student_count": 20,
                    "task_count": 15,
                    "avg_progress": 65,
                    "start_date": "2024-02-01",
                    "end_date": "2024-06-01",
                    "duration": 100,
                },
                {
                    "id": "3",
                    "name": "Базы данных",
                    "description": "Проектирование и управление базами данных",
                    "status": "upcoming",
                    "semester": "3",
                    "student_count": 18,
                    "task_count": 10,
                    "avg_progress": 0,
                    "start_date": "2024-03-01",
                    "end_date": "2024-07-01",
                    "duration": 80,
                },
            ]

            return courses

        except Exception as e:
            self.logger.error(f"Error getting teacher courses: {e}")
            return []

    def get_teacher_students(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get teacher students data with clustering information.

        Args:
            db: Database session

        Returns:
            List of student data
        """
        try:
            self.logger.info("Getting teacher students with clustering data")

            # Get all students with their cluster assignments
            students_query = db.query(Student).all()
            students = []

            for student in students_query:
                # Get cluster assignment for this student
                cluster = db.query(StudentCluster).filter(StudentCluster.student_id == student.id).first()

                # Get student's courses
                student_courses = (
                    db.query(Course).join(Attendance).filter(Attendance.student_id == student.id).distinct().all()
                )

                # Also get courses from TaskCompletion
                task_courses = (
                    db.query(Course).join(TaskCompletion).filter(TaskCompletion.student_id == student.id).distinct().all()
                )

                # Combine and deduplicate courses by ID
                all_courses_dict = {}
                for course in student_courses + task_courses:
                    all_courses_dict[course.id] = course
                all_courses = list(all_courses_dict.values())

                # Calculate progress and attendance
                progress = self._calculate_student_progress(student.id, db)
                attendance = self._calculate_student_attendance(student.id, db)

                # Determine status based on progress and attendance
                if progress >= 80 and attendance >= 85:
                    status = "excellent"
                elif progress < 50 or attendance < 60:
                    status = "at_risk"
                else:
                    status = "active"

                student_data = {
                    "id": student.id,
                    "name": student.name,
                    "email": student.email,
                    "group_id": student.group_id,  # Добавляем номер группы студента
                    "courses": [{"name": course.name} for course in all_courses],
                    "course_ids": [str(course.id) for course in all_courses],
                    "cluster_group": cluster.cluster_label if cluster else None,
                    "overall_progress": progress,
                    "attendance_rate": attendance,
                    "status": status,
                }

                students.append(student_data)

            return students

        except Exception as e:
            self.logger.error(f"Error getting teacher students: {e}")
            # Fallback to mock data if there's an error
            return [
                {
                    "id": "01",
                    "name": "Иванов Иван Иванович",
                    "email": "ivanov@example.com",
                    "courses": [{"name": "Программирование"}, {"name": "Веб-разработка"}],
                    "course_ids": ["1", "2"],
                    "cluster_group": "A",
                    "overall_progress": 85,
                    "attendance_rate": 92,
                    "status": "excellent",
                },
                {
                    "id": "02",
                    "name": "Петров Петр Петрович",
                    "email": "petrov@example.com",
                    "courses": [{"name": "Программирование"}],
                    "course_ids": ["1"],
                    "cluster_group": "B",
                    "overall_progress": 72,
                    "attendance_rate": 78,
                    "status": "active",
                },
                {
                    "id": "03",
                    "name": "Сидоров Сидор Сидорович",
                    "email": "sidorov@example.com",
                    "courses": [{"name": "Веб-разработка"}],
                    "course_ids": ["2"],
                    "cluster_group": "C",
                    "overall_progress": 45,
                    "attendance_rate": 55,
                    "status": "at_risk",
                },
            ]

    def get_teacher_analytics(self, db: Session) -> Dict[str, Any]:
        """
        Get teacher analytics data.

        Args:
            db: Database session

        Returns:
            Dictionary with analytics data
        """
        try:
            self.logger.info("Getting teacher analytics")

            # Mock analytics data
            analytics = {
                "avg_progress": 74,
                "progress_change": 5.2,
                "avg_attendance": 82,
                "attendance_change": 3.1,
                "completed_tasks": 45,
                "total_tasks": 60,
                "at_risk_students": 3,
                "at_risk_percentage": 12.5,
                "excellent_students": 8,
                "good_students": 15,
            }

            return analytics

        except Exception as e:
            self.logger.error(f"Error getting teacher analytics: {e}")
            return {}

    def get_course_analytics(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get course analytics data.

        Args:
            db: Database session

        Returns:
            List of course analytics
        """
        try:
            self.logger.info("Getting course analytics")

            # Mock course analytics data
            course_analytics = [
                {
                    "name": "Программирование на Python",
                    "code": "PYTHON-101",
                    "student_count": 25,
                    "avg_progress": 78,
                    "avg_attendance": 85,
                    "completed_tasks": 18,
                    "total_tasks": 20,
                    "at_risk_count": 2,
                    "at_risk_percentage": 8.0,
                    "rating": 4.2,
                },
                {
                    "name": "Веб-разработка",
                    "code": "WEB-201",
                    "student_count": 20,
                    "avg_progress": 65,
                    "avg_attendance": 78,
                    "completed_tasks": 15,
                    "total_tasks": 18,
                    "at_risk_count": 4,
                    "at_risk_percentage": 20.0,
                    "rating": 3.8,
                },
                {
                    "name": "Базы данных",
                    "code": "DB-301",
                    "student_count": 18,
                    "avg_progress": 0,
                    "avg_attendance": 0,
                    "completed_tasks": 0,
                    "total_tasks": 12,
                    "at_risk_count": 0,
                    "at_risk_percentage": 0.0,
                    "rating": 0.0,
                },
            ]

            return course_analytics

        except Exception as e:
            self.logger.error(f"Error getting course analytics: {e}")
            return []

    def get_teacher_schedule(self, db: Session) -> Dict[str, Any]:
        """
        Get teacher schedule data.

        Args:
            db: Database session

        Returns:
            Dictionary with schedule data
        """
        try:
            self.logger.info("Getting teacher schedule")

            # Mock schedule data
            schedule = {
                "time_slots": [
                    {"time": "09:00"},
                    {"time": "10:30"},
                    {"time": "12:00"},
                    {"time": "13:30"},
                    {"time": "15:00"},
                    {"time": "16:30"},
                ],
                "lessons": {
                    "monday": {
                        "09:00": {
                            "id": "1",
                            "course_name": "Программирование",
                            "room": "А-101",
                            "group": "Группа 1",
                            "color": "#007bff",
                        },
                        "12:00": {
                            "id": "2",
                            "course_name": "Веб-разработка",
                            "room": "Б-202",
                            "group": "Группа 2",
                            "color": "#28a745",
                        },
                    },
                    "tuesday": {
                        "10:30": {
                            "id": "3",
                            "course_name": "Базы данных",
                            "room": "В-303",
                            "group": "Группа 1",
                            "color": "#ffc107",
                        }
                    },
                    "wednesday": {
                        "09:00": {
                            "id": "4",
                            "course_name": "Программирование",
                            "room": "А-101",
                            "group": "Группа 2",
                            "color": "#007bff",
                        }
                    },
                    "thursday": {
                        "13:30": {
                            "id": "5",
                            "course_name": "Веб-разработка",
                            "room": "Б-202",
                            "group": "Группа 1",
                            "color": "#28a745",
                        }
                    },
                    "friday": {
                        "15:00": {
                            "id": "6",
                            "course_name": "Базы данных",
                            "room": "В-303",
                            "group": "Группа 2",
                            "color": "#ffc107",
                        }
                    },
                },
            }

            return schedule

        except Exception as e:
            self.logger.error(f"Error getting teacher schedule: {e}")
            return {"time_slots": [], "lessons": {}}

    def get_upcoming_lessons(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get upcoming lessons for teacher.

        Args:
            db: Database session

        Returns:
            List of upcoming lessons
        """
        try:
            self.logger.info("Getting upcoming lessons")

            # Mock upcoming lessons data
            upcoming_lessons = [
                {
                    "id": "1",
                    "course_name": "Программирование на Python",
                    "topic": "Основы ООП",
                    "date": "2024-01-15",
                    "time": "09:00",
                    "room": "А-101",
                    "group": "Группа 1",
                },
                {
                    "id": "2",
                    "course_name": "Веб-разработка",
                    "topic": "React компоненты",
                    "date": "2024-01-15",
                    "time": "12:00",
                    "room": "Б-202",
                    "group": "Группа 2",
                },
                {
                    "id": "3",
                    "course_name": "Базы данных",
                    "topic": "SQL запросы",
                    "date": "2024-01-16",
                    "time": "10:30",
                    "room": "В-303",
                    "group": "Группа 1",
                },
            ]

            return upcoming_lessons

        except Exception as e:
            self.logger.error(f"Error getting upcoming lessons: {e}")
            return []

    def get_schedule_stats(self, db: Session) -> Dict[str, Any]:
        """
        Get schedule statistics for teacher.

        Args:
            db: Database session

        Returns:
            Dictionary with schedule statistics
        """
        try:
            self.logger.info("Getting schedule stats")

            # Mock schedule stats data
            schedule_stats = {"weekly_lessons": 12, "weekly_hours": 18, "active_courses": 3, "groups_count": 2}

            return schedule_stats

        except Exception as e:
            self.logger.error(f"Error getting schedule stats: {e}")
            return {}

    def _get_risk_students_for_course(self, course_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get risk students for a specific course."""
        try:
            risk_students = []

            # Get students in course
            students = db.query(Student).join(TaskCompletion).filter(TaskCompletion.course_id == course_id).distinct().all()

            for student in students:
                # Get student progress
                progress = self.metrics_service.calculate_student_progress(student.id, db)

                # Find course-specific data
                course_data = None
                if "courses" in progress:
                    course_data = next(
                        (
                            c
                            for c in progress["courses"]
                            if c["course_name"] == db.query(Course).filter(Course.id == course_id).first().name
                        ),
                        None,
                    )

                if course_data:
                    # Calculate risk score
                    risk_score = self._calculate_risk_score(course_data, progress)

                    if risk_score > 50:  # High risk threshold
                        risk_students.append(
                            {
                                "student_id": student.id,
                                "student_name": student.name or f"Студент {student.id}",
                                "attendance_rate": course_data["attendance_progress"],
                                "completion_rate": course_data["task_progress"],
                                "overdue_tasks": self._count_overdue_tasks(student.id, course_id, db),
                                "risk_score": risk_score,
                                "risk_factors": self._get_risk_factors(course_data, progress),
                            }
                        )

            return risk_students

        except Exception as e:
            self.logger.error(f"Error getting risk students for course: {e}")
            return []

    def _get_course_recent_activity(self, course_id: int, db: Session) -> List[Dict[str, Any]]:
        """Get recent activity for a course."""
        try:
            # Get recent task completions
            recent_completions = (
                db.query(TaskCompletion)
                .join(Task)
                .filter(
                    and_(
                        TaskCompletion.course_id == course_id,
                        TaskCompletion.completed_at.isnot(None),
                        TaskCompletion.completed_at >= config_service.now() - timedelta(days=7),
                    )
                )
                .order_by(desc(TaskCompletion.completed_at))
                .limit(10)
                .all()
            )

            activity = []
            for completion in recent_completions:
                activity.append(
                    {
                        "type": "task_completion",
                        "student_id": completion.student_id,
                        "task_name": completion.task.name,
                        "timestamp": completion.completed_at,
                        "status": completion.status,
                    }
                )

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
            overdue_count = (
                db.query(TaskCompletion)
                .filter(
                    and_(
                        TaskCompletion.student_id == student_id,
                        TaskCompletion.course_id == course_id,
                        TaskCompletion.deadline.isnot(None),
                        TaskCompletion.deadline < current_time,
                        TaskCompletion.status != "Выполнено",
                    )
                )
                .count()
            )

            return overdue_count

        except Exception as e:
            self.logger.error(f"Error counting overdue tasks: {e}")
            return 0

    def _calculate_student_progress(self, student_id: str, db: SQLAlchemySession) -> float:
        """Calculate overall progress for a student."""
        try:
            # Get all task completions for the student
            completions = db.query(TaskCompletion).filter(TaskCompletion.student_id == student_id).all()

            if not completions:
                return 0.0

            # Calculate completion rate - only count tasks that are not "missing"
            assigned_tasks = [c for c in completions if c.status != "missing"]
            total_tasks = len(assigned_tasks)
            completed_tasks = sum(1 for c in assigned_tasks if c.status == "Выполнено")

            if total_tasks == 0:
                return 0.0

            progress = (completed_tasks / total_tasks) * 100
            result = round(progress, 1)

            return result

        except Exception as e:
            self.logger.error(f"Error calculating student progress: {e}")
            return 0.0

    def _calculate_student_attendance(self, student_id: str, db: SQLAlchemySession) -> float:
        """Calculate attendance rate for a student."""
        try:
            # Get all attendance records for the student
            attendances = db.query(Attendance).filter(Attendance.student_id == student_id).all()

            if not attendances:
                return 0.0

            # Calculate attendance rate
            total_lessons = len(attendances)
            attended_lessons = sum(1 for a in attendances if a.attended == True)

            return round((attended_lessons / total_lessons) * 100, 1)

        except Exception as e:
            self.logger.error(f"Error calculating student attendance: {e}")
            return 0.0

    def _calculate_student_completion_rate(self, student_id: str, db: SQLAlchemySession) -> float:
        """Calculate task completion rate for a student."""
        try:
            # Get all task completions for the student
            completions = db.query(TaskCompletion).filter(TaskCompletion.student_id == student_id).all()

            if not completions:
                return 0.0

            # Calculate completion rate - only count tasks that are not "missing"
            assigned_tasks = [c for c in completions if c.status != "missing"]
            total_tasks = len(assigned_tasks)
            completed_tasks = sum(1 for c in assigned_tasks if c.status == "Выполнено")

            if total_tasks == 0:
                return 0.0

            return round((completed_tasks / total_tasks) * 100, 1)

        except Exception as e:
            self.logger.error(f"Error calculating student completion rate: {e}")
            return 0.0

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

    def get_teacher_assignments(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get all assignments for teacher.

        Args:
            db: Database session

        Returns:
            List of assignment dictionaries
        """
        try:
            self.logger.info("Getting teacher assignments")

            # Get all tasks (assignments) from all courses
            tasks = db.query(Task).all()

            assignments = []
            for task in tasks:
                # Get course name
                course = db.query(Course).filter(Course.id == task.course_id).first()
                course_name = course.name if course else f"Курс #{task.course_id}"

                # Get completion statistics
                completions = db.query(TaskCompletion).filter(TaskCompletion.task_id == task.id).all()

                student_count = len(completions)
                completed_count = sum(1 for c in completions if c.status == "Выполнено")
                completion_rate = round((completed_count / student_count * 100), 1) if student_count > 0 else 0

                assignments.append(
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "course_id": task.course_id,
                        "course_name": course_name,
                        "student_count": student_count,
                        "completion_rate": completion_rate,
                        "due_date": task.due_date.strftime("%d.%m.%Y") if task.due_date else "Не указано",
                        "created_at": task.created_at.strftime("%d.%m.%Y") if task.created_at else "Не указано",
                        "status": "active",  # Simplified status for now
                    }
                )

            return assignments

        except Exception as e:
            self.logger.error(f"Error getting teacher assignments: {e}")
            return []

    def get_assignments_stats(self, db: Session) -> Dict[str, Any]:
        """
        Get assignment statistics for teacher.

        Args:
            db: Database session

        Returns:
            Dictionary with assignment statistics
        """
        try:
            self.logger.info("Getting assignment statistics")

            # Get all tasks
            total_tasks = db.query(Task).count()

            # Get completion statistics
            all_completions = db.query(TaskCompletion).all()
            total_submissions = len(all_completions)
            completed_submissions = sum(1 for c in all_completions if c.status == "Выполнено")

            avg_completion = round((completed_submissions / total_submissions * 100), 1) if total_submissions > 0 else 0

            return {
                "total_assignments": total_tasks,
                "active_assignments": total_tasks,  # Simplified - all are considered active
                "pending_submissions": total_submissions - completed_submissions,
                "avg_completion": avg_completion,
            }

        except Exception as e:
            self.logger.error(f"Error getting assignment statistics: {e}")
            return {"total_assignments": 0, "active_assignments": 0, "pending_submissions": 0, "avg_completion": 0}
