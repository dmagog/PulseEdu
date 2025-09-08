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
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Enhanced logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s',
    task_annotations={
        '*': {
            'rate_limit': '100/m',  # Rate limiting
        }
    }
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
    # Import and data processing tasks
    'worker.tasks.process_import_job': {'queue': 'ingest'},
    'worker.tasks.*': {'queue': 'ingest'},
    
    # Clustering tasks
    'worker.cluster_tasks.*': {'queue': 'cluster'},
    
    # Beat tasks (periodic)
    'worker.beat_tasks.*': {'queue': 'beat'},
    
    # Future tasks
    'worker.auth_tasks.*': {'queue': 'auth'},
    'email.*': {'queue': 'email'},
    'worker.llm_tasks.*': {'queue': 'llm'},
}
