"""
Celery configuration and task definitions
"""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "cotai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.services.tasks.document_processing",
        "app.services.tasks.tender_analysis",
        "app.services.tasks.notifications",
        "app.services.tasks.cloud_storage",
        "app.services.tasks.team_notifications",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    "app.services.tasks.document_processing.*": {"queue": "document_processing"},
    "app.services.tasks.tender_analysis.*": {"queue": "analysis"},
    "app.services.tasks.notifications.*": {"queue": "notifications"},
    "app.services.tasks.cloud_storage.*": {"queue": "cloud_storage"},
    "app.services.tasks.team_notifications.*": {"queue": "team_notifications"},
}

# Periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "check-new-tenders": {
        "task": "app.services.tasks.tender_analysis.check_new_tenders",
        "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours
    },
    "send-daily-digest": {
        "task": "app.services.tasks.notifications.send_daily_digest",
        "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    "cleanup-old-files": {
        "task": "app.services.tasks.document_processing.cleanup_old_files",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "backup-daily-files": {
        "task": "app.services.tasks.cloud_storage.backup_files_to_cloud",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "send-team-daily-digest": {
        "task": "app.services.tasks.team_notifications.send_daily_team_digest",
        "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    "cleanup-old-cloud-files": {
        "task": "app.services.tasks.cloud_storage.cleanup_old_cloud_files",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Weekly on Sunday at 4 AM
    },
}
