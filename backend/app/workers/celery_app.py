"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "news_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Make this app the process-wide default/current Celery app so task.delay()
# from API code does not fall back to the implicit AMQP default app.
celery_app.set_current()
celery_app.set_default()

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "app.workers.collectors",
    "app.workers.pipeline",
    "app.workers.publishers",
])

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "collect-telegram-posts": {
        "task": "app.workers.collectors.tasks.collect_telegram_posts",
        "schedule": crontab(minute=f"*/{settings.collection_interval_minutes}"),
    },
    "collect-rss-entries": {
        "task": "app.workers.collectors.tasks.collect_rss_entries",
        "schedule": crontab(minute=f"*/{settings.collection_interval_minutes}"),
    },
    "process-new-items": {
        "task": "app.workers.pipeline.tasks.process_new_items",
        "schedule": crontab(minute="*/5"),
    },
    "publish-scheduled-items": {
        "task": "app.workers.publishers.tasks.publish_scheduled_items",
        "schedule": crontab(minute="*/1"),
    },
    "auto-publish-approved-items": {
        "task": "app.workers.publishers.tasks.auto_publish_approved_items",
        "schedule": crontab(minute="*/1"),
    },
}
