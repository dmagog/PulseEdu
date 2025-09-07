"""
Celery Beat tasks for periodic metric calculations and deadline monitoring.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import Celery
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.services.metrics_service import MetricsService
from app.services.config_service import config_service

from worker.celery_app import celery_app

logger = logging.getLogger("worker.beat_tasks")
metrics_service = MetricsService()


@celery_app.task
def recalculate_all_metrics():
    """
    Recalculate metrics for all students.
    This task runs periodically to ensure metrics are up to date.
    """
    logger.info("Starting periodic metrics recalculation")
    
    try:
        with get_db_session() as db:
            results = metrics_service.recalculate_all_students_progress(db)
            
            logger.info(f"Metrics recalculation completed: {results}")
            
            return {
                "status": "success",
                "results": results,
                "timestamp": config_service.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in recalculate_all_metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": config_service.now().isoformat()
        }


@celery_app.task
def check_deadlines():
    """
    Check for upcoming and overdue deadlines.
    This task runs frequently to monitor deadline status.
    """
    logger.info("Starting deadline check")
    
    try:
        with get_db_session() as db:
            # Get upcoming deadlines (next 7 days)
            upcoming_deadlines = metrics_service.get_upcoming_deadlines(7, db)
            
            # Get overdue tasks
            current_time = config_service.now()
            overdue_tasks = db.query(TaskCompletion).filter(
                and_(
                    TaskCompletion.deadline.isnot(None),
                    TaskCompletion.deadline < current_time,
                    TaskCompletion.status != "Выполнено"
                )
            ).count()
            
            # Log critical deadlines (due within 24 hours)
            critical_deadlines = [d for d in upcoming_deadlines if d["days_left"] <= 1]
            
            if critical_deadlines:
                logger.warning(f"Found {len(critical_deadlines)} critical deadlines")
                for deadline in critical_deadlines:
                    logger.warning(f"Critical deadline: Student {deadline['student_id']}, "
                                 f"Task: {deadline['task_name']}, "
                                 f"Due: {deadline['deadline']}")
            
            return {
                "status": "success",
                "upcoming_deadlines": len(upcoming_deadlines),
                "overdue_tasks": overdue_tasks,
                "critical_deadlines": len(critical_deadlines),
                "timestamp": config_service.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in check_deadlines: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": config_service.now().isoformat()
        }


@celery_app.task
def update_task_statuses():
    """
    Update task statuses based on current time and deadlines.
    This task runs to ensure task statuses are current.
    """
    logger.info("Starting task status update")
    
    try:
        with get_db_session() as db:
            # Get all task completions that might need status updates
            task_completions = db.query(TaskCompletion).filter(
                TaskCompletion.deadline.isnot(None)
            ).all()
            
            updated_count = 0
            for completion in task_completions:
                old_status = completion.status
                new_status = metrics_service.calculate_task_status(completion)
                
                # Update status if it changed
                if old_status != new_status:
                    completion.status = new_status
                    updated_count += 1
                    logger.debug(f"Updated task {completion.id} status: {old_status} -> {new_status}")
            
            db.commit()
            
            logger.info(f"Updated {updated_count} task statuses")
            
            return {
                "status": "success",
                "updated_count": updated_count,
                "total_checked": len(task_completions),
                "timestamp": config_service.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in update_task_statuses: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": config_service.now().isoformat()
        }


@celery_app.task
def generate_daily_report():
    """
    Generate daily system report.
    This task runs once per day to provide system overview.
    """
    logger.info("Generating daily system report")
    
    try:
        with get_db_session() as db:
            # Get system metrics
            system_metrics = metrics_service.get_system_metrics(db)
            
            # Get upcoming deadlines
            upcoming_deadlines = metrics_service.get_upcoming_deadlines(7, db)
            
            # Get recent activity (last 24 hours)
            yesterday = config_service.now() - timedelta(days=1)
            recent_completions = db.query(TaskCompletion).filter(
                TaskCompletion.completed_at >= yesterday
            ).count()
            
            report = {
                "date": config_service.now().date().isoformat(),
                "system_metrics": system_metrics,
                "upcoming_deadlines": len(upcoming_deadlines),
                "recent_completions": recent_completions,
                "generated_at": config_service.now().isoformat()
            }
            
            logger.info(f"Daily report generated: {report}")
            
            return {
                "status": "success",
                "report": report
            }
            
    except Exception as e:
        logger.error(f"Error in generate_daily_report: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": config_service.now().isoformat()
        }


# Import required models for the tasks
from app.models.student import TaskCompletion
from sqlalchemy import and_
