"""
Email tasks for sending notifications.
"""
import logging
from datetime import datetime
from celery import Celery
from app.database.session import get_db_session
from app.services.email_service import EmailService
from app.models.import_models import ImportJob
from app.models.user import User
from worker.celery_app import celery_app

logger = logging.getLogger("worker.email_tasks")
email_service = EmailService()

@celery_app.task(name="email.send_import_completion")
def send_import_completion_email(job_id: str, user_email: str):
    """
    Send email notification about import completion.
    
    Args:
        job_id: Import job ID
        user_email: User email address
    """
    logger.info(f"Sending import completion email for job: {job_id} to {user_email}")
    
    try:
        with get_db_session() as db:
            # Get job details
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if not job:
                logger.error(f"Import job not found: {job_id}")
                return {"status": "error", "message": "Job not found"}
            
            # Prepare job details
            job_details = {
                "total_rows": job.processed_rows,
                "imported_students": job.processed_rows,  # Assuming each row is a student
                "lessons_created": 0,  # This would need to be calculated from the import
                "error_count": job.error_rows,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "app_base_url": "http://localhost:8000"  # TODO: Get from config
            }
            
            # Send email
            success = email_service.send_import_completion(job_id, user_email, job_details)
            
            if success:
                logger.info(f"Import completion email sent successfully for job: {job_id}")
                return {"status": "success", "message": "Email sent successfully"}
            else:
                logger.error(f"Failed to send import completion email for job: {job_id}")
                return {"status": "error", "message": "Failed to send email"}
                
    except Exception as e:
        logger.error(f"Error sending import completion email: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="email.send_import_error")
def send_import_error_email(job_id: str, user_email: str, error_message: str):
    """
    Send email notification about import error.
    
    Args:
        job_id: Import job ID
        user_email: User email address
        error_message: Error message
    """
    logger.info(f"Sending import error email for job: {job_id} to {user_email}")
    
    try:
        # Send email
        success = email_service.send_import_error(
            job_id, 
            user_email, 
            error_message
        )
        
        if success:
            logger.info(f"Import error email sent successfully for job: {job_id}")
            return {"status": "success", "message": "Email sent successfully"}
        else:
            logger.error(f"Failed to send import error email for job: {job_id}")
            return {"status": "error", "message": "Failed to send email"}
            
    except Exception as e:
        logger.error(f"Error sending import error email: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="email.send_deadline_reminder")
def send_deadline_reminder_email(student_email: str, task_name: str, deadline: str, course_name: str):
    """
    Send email reminder about approaching deadline.
    
    Args:
        student_email: Student email address
        task_name: Task name
        deadline: Deadline date
        course_name: Course name
    """
    logger.info(f"Sending deadline reminder email to {student_email} for task: {task_name}")
    
    try:
        # Send email
        success = email_service.send_deadline_reminder(
            student_email,
            task_name,
            deadline,
            course_name
        )
        
        if success:
            logger.info(f"Deadline reminder email sent successfully to {student_email}")
            return {"status": "success", "message": "Email sent successfully"}
        else:
            logger.error(f"Failed to send deadline reminder email to {student_email}")
            return {"status": "error", "message": "Failed to send email"}
            
    except Exception as e:
        logger.error(f"Error sending deadline reminder email: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="email.send_metrics_update")
def send_metrics_update_email(user_email: str, update_summary: dict):
    """
    Send email notification about metrics update.
    
    Args:
        user_email: User email address
        update_summary: Summary of metrics update
    """
    logger.info(f"Sending metrics update email to {user_email}")
    
    try:
        # Add timestamp
        update_summary["updated_at"] = datetime.utcnow().isoformat()
        update_summary["app_base_url"] = "http://localhost:8000"  # TODO: Get from config
        
        # Send email
        success = email_service.send_metrics_update(user_email, update_summary)
        
        if success:
            logger.info(f"Metrics update email sent successfully to {user_email}")
            return {"status": "success", "message": "Email sent successfully"}
        else:
            logger.error(f"Failed to send metrics update email to {user_email}")
            return {"status": "error", "message": "Failed to send email"}
            
    except Exception as e:
        logger.error(f"Error sending metrics update email: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="email.send_bulk_notifications")
def send_bulk_notifications(notification_type: str, recipients: list, data: dict):
    """
    Send bulk notifications to multiple recipients.
    
    Args:
        notification_type: Type of notification (import_completion, deadline_reminder, etc.)
        recipients: List of email addresses
        data: Notification data
    """
    logger.info(f"Sending bulk {notification_type} notifications to {len(recipients)} recipients")
    
    results = []
    for recipient in recipients:
        try:
            if notification_type == "import_completion":
                result = send_import_completion_email.delay(
                    data.get("job_id"),
                    recipient
                )
            elif notification_type == "deadline_reminder":
                result = send_deadline_reminder_email.delay(
                    recipient,
                    data.get("task_name"),
                    data.get("deadline"),
                    data.get("course_name")
                )
            elif notification_type == "metrics_update":
                result = send_metrics_update_email.delay(
                    recipient,
                    data
                )
            else:
                logger.error(f"Unknown notification type: {notification_type}")
                continue
                
            results.append({"recipient": recipient, "task_id": result.id})
            
        except Exception as e:
            logger.error(f"Error queuing notification for {recipient}: {e}")
            results.append({"recipient": recipient, "error": str(e)})
    
    logger.info(f"Bulk notifications queued: {len(results)} tasks")
    return {"status": "success", "queued_tasks": results}

