"""
Celery application for background task processing.
Handles grant searches, application generation, and automated workflows.
"""

import logging
from celery import Celery
from celery.schedules import crontab
from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# Create Celery application
celery_app = Celery(
    "grant_finder_tasks",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=[
        "tasks.application_generator",
        "tasks.grant_search",
        "tasks.maintenance",
        "tasks.cleanup_expired_grants"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task time limits (10 minute hard limit, 9 minute soft limit)
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    worker_disable_rate_limits=False,

    # Task routing
    task_routes={
        "tasks.application_generator.*": {"queue": "applications"},
        "tasks.grant_search.*": {"queue": "searches"},
        "tasks.maintenance.*": {"queue": "maintenance"}
    },

    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},

    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,

    # Beat schedule (for periodic tasks)
    beat_schedule={
        # Run scheduled grant searches every 6 hours
        "scheduled-grant-searches": {
            "task": "tasks.grant_search.run_scheduled_searches",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        },

        # Reset monthly usage counters on the 1st of each month at midnight
        "reset-monthly-usage": {
            "task": "tasks.maintenance.reset_monthly_usage_counters",
            "schedule": crontab(minute=0, hour=0, day_of_month=1),  # 1st of month
        },

        # Send usage warnings daily at 9 AM
        "check-usage-limits": {
            "task": "tasks.maintenance.check_and_warn_usage_limits",
            "schedule": crontab(minute=0, hour=9),  # Daily at 9 AM
        },

        # Clean up expired embeddings weekly
        "cleanup-expired-embeddings": {
            "task": "tasks.maintenance.cleanup_expired_embeddings",
            "schedule": crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2 AM
        },

        # Generate weekly reports for active users
        "weekly-user-reports": {
            "task": "tasks.maintenance.send_weekly_reports",
            "schedule": crontab(minute=0, hour=10, day_of_week=1),  # Monday 10 AM
        },

        # Clean up expired grants weekly
        "cleanup-expired-grants": {
            "task": "tasks.cleanup_expired_grants.cleanup_expired_grants",
            "schedule": crontab(day_of_week='sunday', hour=3, minute=0),  # Sunday 3 AM
        }
    },
)

# Task configuration
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

logger.info("Celery application configured with Redis broker")
logger.info(f"Broker URL: {settings.REDIS_URL}")
logger.info(f"Result backend: {settings.celery_backend}")
