"""
Celery tasks for PulseEdu.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from celery import Celery
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.models.import_models import ImportJob, ImportErrorLog
from app.services.import_service import ImportService

from worker.celery_app import celery_app

logger = logging.getLogger("worker.tasks")

# Initialize import service
import_service = ImportService()


@celery_app.task
def dummy_task():
    """
    Dummy task for testing Celery setup.
    """
    logger.info("Dummy task executed")
    return "Task completed successfully"


@celery_app.task(bind=True)
def process_import_job(self, job_id: str):
    """
    Process import job in background.
    
    Args:
        job_id: Import job ID to process
    """
    logger.info(f"Starting import job processing: {job_id}")
    
    try:
        with get_db_session() as db:
            # Get import job
            job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
            if not job:
                logger.error(f"Import job not found: {job_id}")
                return
            
            # Update status to processing
            job.status = "processing"
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Process the file
            result = import_service.parse_excel(job.filename, job_id, db)
            
            # Update job with results
            job.processed_rows = result["total_rows"]
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            
            # Count errors
            error_count = db.query(ImportErrorLog).filter(ImportErrorLog.job_id == job_id).count()
            job.error_rows = error_count
            
            # Create errors summary
            if error_count > 0:
                errors = db.query(ImportErrorLog).filter(ImportErrorLog.job_id == job_id).all()
                errors_summary = []
                for error in errors:
                    errors_summary.append({
                        "row": error.row_number,
                        "column": error.column_name,
                        "type": error.error_type,
                        "message": error.error_message
                    })
                job.errors_json = str(errors_summary)
            
            db.commit()
            
            # Cleanup file
            import_service.cleanup_file(job.filename)
            
            # Trigger clustering after successful import
            try:
                from worker.cluster_tasks import cluster_students_after_import
                cluster_students_after_import.delay(job_id)
                logger.info(f"Clustering task triggered for import job: {job_id}")
            except Exception as cluster_error:
                logger.warning(f"Failed to trigger clustering: {cluster_error}")
            
            # Send email notification about successful import
            try:
                from worker.email_tasks import send_import_completion_email
                # TODO: Get user email from job or user context
                user_email = "admin@pulseedu.local"  # Default for now
                send_import_completion_email.delay(job_id, user_email)
                logger.info(f"Import completion email triggered for job: {job_id}")
            except Exception as email_error:
                logger.warning(f"Failed to trigger import completion email: {email_error}")
            
            logger.info(f"Import job completed: {job_id} - {job.processed_rows} rows, {job.error_rows} errors")
            
    except Exception as e:
        logger.error(f"Import job failed: {job_id} - {e}")
        
        # Send email notification about import error
        try:
            from worker.email_tasks import send_import_error_email
            user_email = "admin@pulseedu.local"  # Default for now
            send_import_error_email.delay(job_id, user_email, str(e))
            logger.info(f"Import error email triggered for job: {job_id}")
        except Exception as email_error:
            logger.warning(f"Failed to trigger import error email: {email_error}")
        
        # Update job status to failed
        try:
            with get_db_session() as db:
                job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
                if job:
                    job.status = "failed"
                    job.completed_at = datetime.utcnow()
                    job.errors_json = str(e)
                    db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
        
        # Re-raise exception for Celery
        raise self.retry(exc=e, countdown=60, max_retries=3)
