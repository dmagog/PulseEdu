"""
Celery tasks for PulseEdu.
"""
import logging

from worker.celery_app import celery_app

logger = logging.getLogger("worker.tasks")

@celery_app.task
def dummy_task():
    """
    Dummy task for testing Celery setup.
    """
    logger.info("Dummy task executed")
    return "Task completed successfully"
