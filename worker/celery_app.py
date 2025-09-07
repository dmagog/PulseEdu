"""
Celery application configuration.
"""
import os
from celery import Celery

# Create Celery app
celery_app = Celery(
    "pulseedu",
    broker=os.getenv("RABBITMQ_URL", "amqp://pulseedu:pulseedu@localhost:5672//"),
    backend=None,  # Disable result backend for now
    include=[
        "worker.tasks",  # Will be created in future iterations
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
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule (for periodic tasks)
celery_app.conf.beat_schedule = {
    # TODO: Add periodic tasks in future iterations
    # Example:
    # "check-deadlines": {
    #     "task": "worker.tasks.check_deadlines",
    #     "schedule": 60.0,  # Every minute
    # },
}

# Queue configuration
celery_app.conf.task_routes = {
    # TODO: Add queue routing in future iterations
    # Example:
    # "worker.tasks.auth.*": {"queue": "auth"},
    # "worker.tasks.ingest.*": {"queue": "ingest"},
    # "worker.tasks.email.*": {"queue": "email"},
    # "worker.tasks.llm.*": {"queue": "llm"},
    # "worker.tasks.cluster.*": {"queue": "cluster"},
}
