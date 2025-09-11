"""
Student service for managing student data and progress.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.student import Student, Course, Task, Attendance, TaskCompletion, Lesson
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
    
    def get_course_details_for_student(self, student_id: str, course_id: int, db: Session) -> Dict[str, Any]:
        """
        Get detailed course information for a student including lessons and assignments.
        
        Args:
            student_id: Student ID
            course_id: Course ID
            db: Database session
            
        Returns:
            Dictionary with course details including lessons and assignments
        """
        try:
            logger.info(f"Getting course details for student: {student_id}, course: {course_id}")
            
            # Get course information
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return {"error": "Course not found"}
            
            # Get all lessons for this course with attendance data
            lessons_query = db.query(Attendance, Lesson).join(Lesson, Attendance.lesson_id == Lesson.id).filter(
                and_(Attendance.course_id == course_id, Attendance.student_id == student_id)
            ).order_by(Lesson.date).all()
            
            # Get all tasks/assignments for this course
            tasks = db.query(Task).filter(Task.course_id == course_id).order_by(Task.created_at).all()
            
            # Get task completions for this student
            task_completions = db.query(TaskCompletion).filter(
                and_(TaskCompletion.course_id == course_id, TaskCompletion.student_id == student_id)
            ).all()
            
            # Create a mapping of task_id to completion status
            completion_map = {tc.task_id: tc for tc in task_completions}
            
            # Process lessons data
            lessons_data = []
            for attendance, lesson in lessons_query:
                lessons_data.append({
                    "id": lesson.id,
                    "lesson_name": lesson.title or f"Занятие {lesson.lesson_number}",
                    "lesson_date": lesson.date.strftime('%d.%m.%Y') if lesson.date else "Не указано",
                    "lesson_time": lesson.date.strftime('%H:%M') if lesson.date else "Не указано",
                    "attended": attendance.attended,
                    "status": "Посещено" if attendance.attended else "Пропущено",
                    "status_class": "success" if attendance.attended else "danger"
                })
            
            # Process tasks/assignments data
            assignments_data = []
            for task in tasks:
                completion = completion_map.get(task.id)
                if completion:
                    status = completion.status
                    # Change "missing" to more user-friendly "Отправлено"
                    if status == "missing":
                        status = "Отправлено"
                        status_class = "info"  # Blue color for "sent for review"
                    elif status == "Выполнено":
                        status_class = "success"
                    elif status == "В процессе":
                        status_class = "warning"
                    else:
                        status_class = "danger"
                    completion_date = completion.completed_at.strftime('%d.%m.%Y') if completion.completed_at else None
                else:
                    status = "Не назначено"
                    status_class = "secondary"
                    completion_date = None
                
                # Determine if task is overdue
                is_overdue = False
                # Use deadline from task_completions if available, otherwise from tasks
                effective_deadline = completion.deadline if completion and completion.deadline else task.deadline
                
                if effective_deadline and completion:
                    # Task is overdue only if deadline has passed AND task is not completed
                    # Consider "missing" as completed since it was submitted
                    is_completed = completion.status in ["Выполнено", "missing"]
                    is_overdue = (effective_deadline < datetime.now()) and not is_completed
                elif effective_deadline and not completion:
                    # Task is overdue if deadline has passed AND task is not assigned/completed
                    is_overdue = effective_deadline < datetime.now()
                
                assignments_data.append({
                    "id": task.id,
                    "title": task.name or f"Задание #{task.id}",
                    "description": f"Тип: {task.task_type}" if task.task_type else "Описание не указано",
                    "deadline": effective_deadline.strftime('%d.%m.%Y') if effective_deadline else "Не указано",
                    "status": status,
                    "status_class": status_class,
                    "completion_date": completion_date,
                    "is_overdue": is_overdue
                })
            
            # Calculate course statistics
            total_lessons = len(lessons_data)
            attended_lessons = sum(1 for lesson_data in lessons_data if lesson_data['attended'])
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if completion_map.get(task.id, {}).status == "Выполнено")
            
            return {
                "course": course,
                "lessons": lessons_data,
                "assignments": assignments_data,
                "statistics": {
                    "total_lessons": total_lessons,
                    "attended_lessons": attended_lessons,
                    "attendance_rate": (attended_lessons / total_lessons * 100) if total_lessons > 0 else 0,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting course details for student: {e}")
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

    def get_detailed_progress(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get detailed progress data for each course.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of course progress details
        """
        try:
            logger.info(f"Getting detailed progress for student: {student_id}")
            
            # Get student courses
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return []
            
            courses = db.query(Course).join(Student.courses).filter(Student.id == student_id).all()
            
            progress_details = []
            for course in courses:
                # Calculate course-specific metrics
                attendance_rate = self._calculate_course_attendance(student_id, course.id, db)
                task_completion = self._calculate_course_task_completion(student_id, course.id, db)
                
                progress_details.append({
                    "id": course.id,
                    "name": course.name,
                    "progress": int((attendance_rate + task_completion) / 2),
                    "attendance": attendance_rate,
                    "tasks_completed": task_completion,
                    "tasks_total": 10,  # Mock data
                    "grade": "A" if attendance_rate > 80 and task_completion > 80 else "B" if attendance_rate > 60 and task_completion > 60 else "C"
                })
            
            return progress_details
            
        except Exception as e:
            logger.error(f"Error getting detailed progress: {e}")
            return []

    def get_student_assignments(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get student assignments from all courses.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of assignments from all student courses
        """
        try:
            logger.info(f"Getting assignments for student: {student_id}")
            
            # Get all courses for the student through attendances and task completions
            # Get courses from attendances
            courses_from_attendance = db.query(Course).join(Lesson, Course.id == Lesson.course_id).join(
                Attendance, Lesson.id == Attendance.lesson_id
            ).filter(Attendance.student_id == student_id).distinct().all()
            
            # Get courses from task completions
            courses_from_tasks = db.query(Course).join(Task, Course.id == Task.course_id).join(
                TaskCompletion, Task.id == TaskCompletion.task_id
            ).filter(TaskCompletion.student_id == student_id).distinct().all()
            
            # Combine and deduplicate courses
            all_courses = courses_from_attendance + courses_from_tasks
            unique_courses = {}
            for course in all_courses:
                unique_courses[course.id] = course
            student_courses = list(unique_courses.values())
            
            if not student_courses:
                logger.info(f"No courses found for student: {student_id}")
                return []
            
            assignments = []
            
            # Get tasks from all student courses
            for course in student_courses:
                # Get all tasks for this course
                tasks = db.query(Task).filter(Task.course_id == course.id).all()
                
                for task in tasks:
                    # Get task completion status for this student
                    completion = db.query(TaskCompletion).filter(
                        TaskCompletion.student_id == student_id,
                        TaskCompletion.task_id == task.id
                    ).first()
                    
                    # Determine status
                    if completion:
                        status = completion.status
                        if status == "missing":
                            status = "Отправлено"
                        elif status == "Выполнено":
                            status = "completed"
                        elif status == "Не выполнено":
                            status = "pending"
                        else:
                            status = "in_progress"
                        
                        completion_date = completion.completed_at.strftime('%d.%m.%Y') if completion.completed_at else None
                    else:
                        status = "pending"
                        completion_date = None
                    
                    # Determine if overdue
                    is_overdue = False
                    effective_deadline = completion.deadline if completion and completion.deadline else task.deadline
                    
                    if effective_deadline:
                        if completion:
                            is_completed = completion.status in ["Выполнено", "missing"]
                            is_overdue = (effective_deadline < datetime.now()) and not is_completed
                        else:
                            is_overdue = effective_deadline < datetime.now()
                    
                    # Determine priority based on deadline proximity
                    priority = "low"
                    if effective_deadline:
                        days_until_deadline = (effective_deadline - datetime.now()).days
                        if days_until_deadline < 0:
                            priority = "high"  # Overdue
                        elif days_until_deadline <= 3:
                            priority = "high"
                        elif days_until_deadline <= 7:
                            priority = "medium"
                    
                    assignment_data = {
                        "id": str(task.id),
                        "title": task.name,
                        "description": f"Тип: {task.task_type}" if task.task_type else "Описание не указано",
                        "course_id": str(course.id),
                        "course_name": course.name,
                        "due_date": effective_deadline.strftime('%d.%m.%Y') if effective_deadline else "Не указан",
                        "due_date_raw": effective_deadline.isoformat() if effective_deadline else None,
                        "status": status,
                        "priority": priority,
                        "is_overdue": is_overdue,
                        "completion_date": completion_date,
                        "task_type": task.task_type
                    }
                    
                    assignments.append(assignment_data)
            
            # Sort assignments: overdue first, then by deadline, then by priority
            assignments.sort(key=lambda x: (
                not x["is_overdue"],  # Overdue first
                x["due_date_raw"] or "9999-12-31",  # Then by deadline
                {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3)  # Then by priority
            ))
            
            logger.info(f"Found {len(assignments)} assignments for student {student_id}")
            return assignments
            
        except Exception as e:
            logger.error(f"Error getting assignments: {e}")
            return []

    def get_student_courses(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get student courses.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of courses
        """
        try:
            logger.info(f"Getting courses for student: {student_id}")
            
            # Get student courses from database
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return []
            
            courses = db.query(Course).join(Student.courses).filter(Student.id == student_id).all()
            
            return [{"id": course.id, "name": course.name} for course in courses]
            
        except Exception as e:
            logger.error(f"Error getting courses: {e}")
            return []

    def get_student_schedule(self, student_id: str, db: Session) -> Dict[str, Any]:
        """
        Get student schedule.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            Schedule data
        """
        try:
            logger.info(f"Getting schedule for student: {student_id}")
            
            # Mock schedule data
            schedule = {
                "time_slots": [
                    {"time": "09:00"},
                    {"time": "10:30"},
                    {"time": "12:00"},
                    {"time": "13:30"},
                    {"time": "15:00"},
                    {"time": "16:30"}
                ],
                "lessons": {
                    "monday": {
                        "09:00": {
                            "course_name": "Программирование",
                            "room": "А-101",
                            "teacher": "Иванов И.И.",
                            "color": "#007bff"
                        }
                    },
                    "tuesday": {
                        "10:30": {
                            "course_name": "Веб-разработка",
                            "room": "Б-202",
                            "teacher": "Петров П.П.",
                            "color": "#28a745"
                        }
                    },
                    "wednesday": {
                        "12:00": {
                            "course_name": "Базы данных",
                            "room": "В-303",
                            "teacher": "Сидоров С.С.",
                            "color": "#ffc107"
                        }
                    }
                }
            }
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error getting schedule: {e}")
            return {"time_slots": [], "lessons": {}}

    def get_upcoming_events(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get upcoming events for student.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of upcoming events
        """
        try:
            logger.info(f"Getting upcoming events for student: {student_id}")
            
            # Mock events data
            events = [
                {
                    "title": "Экзамен по программированию",
                    "description": "Итоговый экзамен по курсу программирования",
                    "date": "2024-01-25",
                    "time": "10:00",
                    "type": "exam"
                },
                {
                    "title": "Дедлайн курсовой работы",
                    "description": "Сдача курсовой работы по веб-разработке",
                    "date": "2024-01-20",
                    "time": "23:59",
                    "type": "deadline"
                }
            ]
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []

    def get_student_recommendations(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get student recommendations.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of recommendations
        """
        try:
            logger.info(f"Getting recommendations for student: {student_id}")
            
            # Mock recommendations data
            recommendations = [
                {
                    "id": "1",
                    "title": "Улучшить посещаемость",
                    "description": "Рекомендуется повысить посещаемость занятий для улучшения успеваемости",
                    "category": "study",
                    "category_name": "Учеба",
                    "priority": "high",
                    "created_at": "2024-01-10"
                },
                {
                    "id": "2",
                    "title": "Изучить дополнительные материалы",
                    "description": "Для углубления знаний рекомендуется изучить дополнительные материалы по программированию",
                    "category": "study",
                    "category_name": "Учеба",
                    "priority": "medium",
                    "created_at": "2024-01-08"
                }
            ]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []

    def get_recommendation_history(self, student_id: str, db: Session) -> List[Dict[str, Any]]:
        """
        Get recommendation history for student.
        
        Args:
            student_id: Student ID
            db: Database session
            
        Returns:
            List of recommendation history items
        """
        try:
            logger.info(f"Getting recommendation history for student: {student_id}")
            
            # Mock history data
            history = [
                {
                    "id": "1",
                    "title": "Составить план обучения",
                    "status": "applied",
                    "date": "2024-01-05"
                },
                {
                    "id": "2",
                    "title": "Обратиться к преподавателю",
                    "status": "dismissed",
                    "date": "2024-01-03"
                }
            ]
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting recommendation history: {e}")
            return []

    def _calculate_course_attendance(self, student_id: str, course_id: str, db: Session) -> int:
        """Calculate attendance rate for a specific course."""
        try:
            # Mock calculation
            return 85
        except Exception as e:
            logger.error(f"Error calculating course attendance: {e}")
            return 0

    def _calculate_course_task_completion(self, student_id: str, course_id: str, db: Session) -> int:
        """Calculate task completion rate for a specific course."""
        try:
            # Mock calculation
            return 75
        except Exception as e:
            logger.error(f"Error calculating course task completion: {e}")
            return 0
    
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
