"""
Celery application configuration for email worker.
"""
import os
from celery import Celery

# Create Celery app for email worker
celery_app = Celery(
    "pulseedu_email",
    broker=os.getenv("RABBITMQ_URL", "amqp://pulseedu:pulseedu@localhost:5672//"),
    backend=None,
    include=[
        "worker.email_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s',
    task_annotations={
        '*': {
            'rate_limit': '100/m',
        }
    }
)

# Queue configuration
celery_app.conf.task_routes = {
    'worker.email_tasks.*': {'queue': 'email'},
    'email.*': {'queue': 'email'},
}
