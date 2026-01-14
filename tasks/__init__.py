"""
Celery tasks for background job processing.
"""

from celery import Celery
from config.settings import Settings

settings = Settings()

# Initialize Celery app
celery_app = Celery(
    "grant_finder_tasks",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["tasks.application_generator"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

__all__ = ["celery_app"]
