"""
ROP (Руководитель образовательной программы) service for program analytics.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.student import Student, Course, Task, Attendance, TaskCompletion
from app.services.metrics_service import MetricsService
from app.services.config_service import config_service

logger = logging.getLogger("app.rop")


class ROPService:
    """Service for ROP dashboard and program analytics."""
    
    def __init__(self):
        self.metrics_service = MetricsService()
        self.logger = logger
    
    def get_rop_dashboard(self, db: Session) -> Dict[str, Any]:
        """
        Get comprehensive ROP dashboard data.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with ROP dashboard data
        """
        try:
            self.logger.info("Getting ROP dashboard data")
            
            # Get program summary
            program_summary = self._get_program_summary(db)
            
            # Get trends data
            trends_7d = self._get_trends_data(7, db)
            trends_30d = self._get_trends_data(30, db)
            
            # Get risk analysis
            risk_analysis = self._get_risk_analysis(db)
            
            # Get course performance
            course_performance = self._get_course_performance(db)
            
            return {
                "program_summary": program_summary,
                "trends_7d": trends_7d,
                "trends_30d": trends_30d,
                "risk_analysis": risk_analysis,
                "course_performance": course_performance,
                "generated_at": config_service.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ROP dashboard: {e}")
            return {"error": str(e)}
    
    def _get_program_summary(self, db: Session) -> Dict[str, Any]:
        """Get program-level summary statistics."""
        try:
            # Get total counts
            total_students = db.query(Student).count()
            total_courses = db.query(Course).count()
            total_tasks = db.query(Task).count()
            
            # Get completion statistics
            total_completions = db.query(TaskCompletion).count()
            completed_tasks = db.query(TaskCompletion).filter(
                TaskCompletion.status == "Выполнено"
            ).count()
            
            # Get attendance statistics
            total_attendance = db.query(Attendance).count()
            attended_lessons = db.query(Attendance).filter(
                Attendance.attended == True
            ).count()
            
            # Get overdue tasks
            current_time = config_service.now()
            overdue_tasks = db.query(TaskCompletion).filter(
                and_(
                    TaskCompletion.deadline.isnot(None),
                    TaskCompletion.deadline < current_time,
                    TaskCompletion.status != "Выполнено"
                )
            ).count()
            
            # Get upcoming deadlines
            upcoming_deadlines = self.metrics_service.get_upcoming_deadlines(7, db)
            
            # Calculate percentages
            completion_rate = (completed_tasks / total_completions * 100) if total_completions > 0 else 0
            attendance_rate = (attended_lessons / total_attendance * 100) if total_attendance > 0 else 0
            overdue_rate = (overdue_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                "total_students": total_students,
                "total_courses": total_courses,
                "total_tasks": total_tasks,
                "completion_rate": completion_rate,
                "attendance_rate": attendance_rate,
                "overdue_rate": overdue_rate,
                "overdue_tasks": overdue_tasks,
                "upcoming_deadlines": len(upcoming_deadlines)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting program summary: {e}")
            return {"error": str(e)}
    
    def _get_trends_data(self, days: int, db: Session) -> Dict[str, Any]:
        """Get trends data for specified number of days."""
        try:
            end_date = config_service.now()
            start_date = end_date - timedelta(days=days)
            
            # Get daily completion trends
            daily_completions = []
            daily_attendance = []
            daily_overdue = []
            
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                next_date = current_date + timedelta(days=1)
                
                # Completions for this day
                completions = db.query(TaskCompletion).filter(
                    and_(
                        TaskCompletion.completed_at >= current_date,
                        TaskCompletion.completed_at < next_date,
                        TaskCompletion.status == "Выполнено"
                    )
                ).count()
                
                # Attendance for this day
                attendance = db.query(Attendance).filter(
                    and_(
                        Attendance.created_at >= current_date,
                        Attendance.created_at < next_date,
                        Attendance.attended == True
                    )
                ).count()
                
                # Overdue tasks for this day
                overdue = db.query(TaskCompletion).filter(
                    and_(
                        TaskCompletion.deadline >= current_date,
                        TaskCompletion.deadline < next_date,
                        TaskCompletion.status != "Выполнено"
                    )
                ).count()
                
                daily_completions.append(completions)
                daily_attendance.append(attendance)
                daily_overdue.append(overdue)
            
            return {
                "days": days,
                "dates": [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)],
                "completions": daily_completions,
                "attendance": daily_attendance,
                "overdue": daily_overdue,
                "total_completions": sum(daily_completions),
                "total_attendance": sum(daily_attendance),
                "total_overdue": sum(daily_overdue)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting trends data: {e}")
            return {"error": str(e)}
    
    def _get_risk_analysis(self, db: Session) -> Dict[str, Any]:
        """Get risk analysis across all programs."""
        try:
            # Get all students with their progress
            students = db.query(Student).all()
            
            risk_categories = {
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "good": 0
            }
            
            risk_factors = {
                "low_attendance": 0,
                "low_completion": 0,
                "overdue_tasks": 0,
                "no_activity": 0
            }
            
            for student in students:
                progress = self.metrics_service.calculate_student_progress(student.id, db)
                
                if "error" not in progress:
                    overall_progress = progress.get("overall_progress", 0)
                    attendance_rate = progress.get("attendance", {}).get("percentage", 0)
                    completion_rate = progress.get("tasks", {}).get("percentage", 0)
                    
                    # Categorize risk level
                    if overall_progress < 30:
                        risk_categories["high_risk"] += 1
                    elif overall_progress < 60:
                        risk_categories["medium_risk"] += 1
                    elif overall_progress < 80:
                        risk_categories["low_risk"] += 1
                    else:
                        risk_categories["good"] += 1
                    
                    # Identify risk factors
                    if attendance_rate < 50:
                        risk_factors["low_attendance"] += 1
                    if completion_rate < 30:
                        risk_factors["low_completion"] += 1
                    
                    # Check for overdue tasks
                    current_time = config_service.now()
                    overdue_count = db.query(TaskCompletion).filter(
                        and_(
                            TaskCompletion.student_id == student.id,
                            TaskCompletion.deadline.isnot(None),
                            TaskCompletion.deadline < current_time,
                            TaskCompletion.status != "Выполнено"
                        )
                    ).count()
                    
                    if overdue_count > 0:
                        risk_factors["overdue_tasks"] += 1
                    
                    # Check for no recent activity
                    week_ago = current_time - timedelta(days=7)
                    recent_activity = db.query(TaskCompletion).filter(
                        and_(
                            TaskCompletion.student_id == student.id,
                            TaskCompletion.completed_at >= week_ago
                        )
                    ).count()
                    
                    if recent_activity == 0:
                        risk_factors["no_activity"] += 1
            
            return {
                "risk_categories": risk_categories,
                "risk_factors": risk_factors,
                "total_students": len(students)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting risk analysis: {e}")
            return {"error": str(e)}
    
    def _get_course_performance(self, db: Session) -> List[Dict[str, Any]]:
        """Get performance metrics for each course."""
        try:
            courses = db.query(Course).all()
            course_performance = []
            
            for course in courses:
                # Get course statistics
                total_students = db.query(Student).join(TaskCompletion).filter(
                    TaskCompletion.course_id == course.id
                ).distinct().count()
                
                total_tasks = db.query(Task).filter(Task.course_id == course.id).count()
                
                # Get completion rate
                total_completions = db.query(TaskCompletion).filter(
                    TaskCompletion.course_id == course.id
                ).count()
                completed_tasks = db.query(TaskCompletion).filter(
                    and_(
                        TaskCompletion.course_id == course.id,
                        TaskCompletion.status == "Выполнено"
                    )
                ).count()
                
                # Get attendance rate
                total_attendance = db.query(Attendance).filter(
                    Attendance.course_id == course.id
                ).count()
                attended_lessons = db.query(Attendance).filter(
                    and_(
                        Attendance.course_id == course.id,
                        Attendance.attended == True
                    )
                ).count()
                
                # Get overdue tasks
                current_time = config_service.now()
                overdue_tasks = db.query(TaskCompletion).filter(
                    and_(
                        TaskCompletion.course_id == course.id,
                        TaskCompletion.deadline.isnot(None),
                        TaskCompletion.deadline < current_time,
                        TaskCompletion.status != "Выполнено"
                    )
                ).count()
                
                completion_rate = (completed_tasks / total_completions * 100) if total_completions > 0 else 0
                attendance_rate = (attended_lessons / total_attendance * 100) if total_attendance > 0 else 0
                overdue_rate = (overdue_tasks / total_tasks * 100) if total_tasks > 0 else 0
                
                course_performance.append({
                    "course_id": course.id,
                    "course_name": course.name,
                    "total_students": total_students,
                    "total_tasks": total_tasks,
                    "completion_rate": completion_rate,
                    "attendance_rate": attendance_rate,
                    "overdue_rate": overdue_rate,
                    "overdue_tasks": overdue_tasks,
                    "performance_score": (completion_rate + attendance_rate - overdue_rate) / 2
                })
            
            # Sort by performance score
            course_performance.sort(key=lambda x: x["performance_score"], reverse=True)
            
            return course_performance
            
        except Exception as e:
            self.logger.error(f"Error getting course performance: {e}")
            return []
    
    def get_course_trends(self, course_id: int, days: int, db: Session) -> Dict[str, Any]:
        """Get trends data for a specific course."""
        try:
            end_date = config_service.now()
            start_date = end_date - timedelta(days=days)
            
            daily_data = []
            
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                next_date = current_date + timedelta(days=1)
                
                # Course-specific completions
                completions = db.query(TaskCompletion).join(Task).filter(
                    and_(
                        TaskCompletion.course_id == course_id,
                        TaskCompletion.completed_at >= current_date,
                        TaskCompletion.completed_at < next_date,
                        TaskCompletion.status == "Выполнено"
                    )
                ).count()
                
                # Course-specific attendance
                attendance = db.query(Attendance).filter(
                    and_(
                        Attendance.course_id == course_id,
                        Attendance.created_at >= current_date,
                        Attendance.created_at < next_date,
                        Attendance.attended == True
                    )
                ).count()
                
                daily_data.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "completions": completions,
                    "attendance": attendance
                })
            
            return {
                "course_id": course_id,
                "days": days,
                "daily_data": daily_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting course trends: {e}")
            return {"error": str(e)}

    def get_rop_programs(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get ROP programs data.
        
        Args:
            db: Database session
            
        Returns:
            List of program data
        """
        try:
            self.logger.info("Getting ROP programs")
            
            # Mock programs data
            programs = [
                {
                    "id": "1",
                    "name": "Программирование и информационные технологии",
                    "description": "Бакалаврская программа по программированию",
                    "status": "active",
                    "level": "bachelor",
                    "level_name": "Бакалавриат",
                    "student_count": 150,
                    "course_count": 25,
                    "semesters": 8,
                    "completion_rate": 78,
                    "start_date": "2023-09-01",
                    "end_date": "2027-06-30",
                    "quality_score": 4.2
                },
                {
                    "id": "2",
                    "name": "Веб-разработка и дизайн",
                    "description": "Магистерская программа по веб-разработке",
                    "status": "active",
                    "level": "master",
                    "level_name": "Магистратура",
                    "student_count": 45,
                    "course_count": 12,
                    "semesters": 4,
                    "completion_rate": 85,
                    "start_date": "2023-09-01",
                    "end_date": "2025-06-30",
                    "quality_score": 4.5
                },
                {
                    "id": "3",
                    "name": "Анализ данных и машинное обучение",
                    "description": "Специализированная программа по анализу данных",
                    "status": "planning",
                    "level": "specialist",
                    "level_name": "Специалитет",
                    "student_count": 0,
                    "course_count": 15,
                    "semesters": 5,
                    "completion_rate": 0,
                    "start_date": "2024-09-01",
                    "end_date": "2029-06-30",
                    "quality_score": 0
                }
            ]
            
            return programs
            
        except Exception as e:
            self.logger.error(f"Error getting ROP programs: {e}")
            return []

    def get_rop_trends(self, db: Session) -> Dict[str, Any]:
        """
        Get ROP trends data.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with trends data
        """
        try:
            self.logger.info("Getting ROP trends")
            
            # Mock trends data
            trends = {
                "enrollment_growth": 12.5,
                "performance_improvement": 8.3,
                "satisfaction_score": 4.3,
                "employment_rate": 89
            }
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting ROP trends: {e}")
            return {}

    def get_quality_predictions(self, db: Session) -> Dict[str, Any]:
        """
        Get quality predictions data.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with predictions data
        """
        try:
            self.logger.info("Getting quality predictions")
            
            # Mock predictions data
            predictions = {
                "enrollment_growth": 15,
                "enrollment_forecast": 180,
                "graduation_rate": 82,
                "graduation_forecast": 125,
                "employment_rate": 92,
                "employment_forecast": 115
            }
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error getting quality predictions: {e}")
            return {}

    def get_quality_metrics(self, db: Session) -> Dict[str, Any]:
        """
        Get quality metrics data.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with quality metrics
        """
        try:
            self.logger.info("Getting quality metrics")
            
            # Mock quality metrics data
            quality = {
                "overall_rating": 4.3,
                "satisfaction_score": 87,
                "employment_rate": 89,
                "improvement_rate": 12.5
            }
            
            return quality
            
        except Exception as e:
            self.logger.error(f"Error getting quality metrics: {e}")
            return {}

    def get_quality_dimensions(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get quality dimensions data.
        
        Args:
            db: Database session
            
        Returns:
            List of quality dimensions
        """
        try:
            self.logger.info("Getting quality dimensions")
            
            # Mock quality dimensions data
            quality_dimensions = [
                {
                    "name": "Содержание программы",
                    "description": "Актуальность и полнота учебного плана",
                    "score": 4.5
                },
                {
                    "name": "Качество преподавания",
                    "description": "Квалификация и методика преподавателей",
                    "score": 4.2
                },
                {
                    "name": "Инфраструктура",
                    "description": "Оборудование и учебные помещения",
                    "score": 4.0
                },
                {
                    "name": "Поддержка студентов",
                    "description": "Консультации и помощь в обучении",
                    "score": 4.3
                },
                {
                    "name": "Практическая подготовка",
                    "description": "Стажировки и проектная работа",
                    "score": 4.1
                },
                {
                    "name": "Трудоустройство",
                    "description": "Помощь в поиске работы",
                    "score": 4.4
                }
            ]
            
            return quality_dimensions
            
        except Exception as e:
            self.logger.error(f"Error getting quality dimensions: {e}")
            return []

    def get_quality_issues(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get quality issues data.
        
        Args:
            db: Database session
            
        Returns:
            List of quality issues
        """
        try:
            self.logger.info("Getting quality issues")
            
            # Mock quality issues data
            quality_issues = [
                {
                    "title": "Недостаток современного оборудования",
                    "description": "Требуется обновление компьютерных классов"
                },
                {
                    "title": "Низкая активность студентов",
                    "description": "Снижение участия в практических занятиях"
                }
            ]
            
            return quality_issues
            
        except Exception as e:
            self.logger.error(f"Error getting quality issues: {e}")
            return []

    def get_quality_recommendations(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get quality recommendations data.
        
        Args:
            db: Database session
            
        Returns:
            List of quality recommendations
        """
        try:
            self.logger.info("Getting quality recommendations")
            
            # Mock quality recommendations data
            quality_recommendations = [
                {
                    "title": "Внедрить интерактивные методы обучения",
                    "description": "Использовать больше практических заданий и проектов"
                },
                {
                    "title": "Улучшить обратную связь",
                    "description": "Регулярно собирать отзывы студентов и анализировать их"
                }
            ]
            
            return quality_recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting quality recommendations: {e}")
            return []

    def get_improvement_plans(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get improvement plans data.
        
        Args:
            db: Database session
            
        Returns:
            List of improvement plans
        """
        try:
            self.logger.info("Getting improvement plans")
            
            # Mock improvement plans data
            improvement_plans = [
                {
                    "area": "Инфраструктура",
                    "action": "Обновить компьютерные классы",
                    "responsible": "Технический отдел",
                    "deadline": "2024-06-30",
                    "status": "in_progress"
                },
                {
                    "area": "Методика обучения",
                    "action": "Внедрить проектное обучение",
                    "responsible": "Кафедра программирования",
                    "deadline": "2024-09-01",
                    "status": "planned"
                },
                {
                    "area": "Поддержка студентов",
                    "action": "Создать центр карьеры",
                    "responsible": "Отдел по работе со студентами",
                    "deadline": "2024-03-31",
                    "status": "completed"
                }
            ]
            
            return improvement_plans
            
        except Exception as e:
            self.logger.error(f"Error getting improvement plans: {e}")
            return []
