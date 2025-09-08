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
        "worker.tasks",
        "worker.beat_tasks",
        "worker.cluster_tasks",
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
    'recalculate-metrics': {
        'task': 'worker.beat_tasks.recalculate_all_metrics',
        'schedule': 300.0,  # Every 5 minutes
    },
    'check-deadlines': {
        'task': 'worker.beat_tasks.check_deadlines',
        'schedule': 60.0,  # Every minute
    },
    'update-task-statuses': {
        'task': 'worker.beat_tasks.update_task_statuses',
        'schedule': 180.0,  # Every 3 minutes
    },
    'daily-report': {
        'task': 'worker.beat_tasks.generate_daily_report',
        'schedule': 86400.0,  # Every 24 hours
    },
    'periodic-cluster-update': {
        'task': 'worker.cluster_tasks.periodic_cluster_update',
        'schedule': 3600.0,  # Every hour
    },
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
