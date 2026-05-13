"""Celery application for timetable background work (reminders, etc.)."""
import os

from celery import Celery
from celery.schedules import crontab


CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@rabbitmq:5672//",
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://redis:6379/2",
)


celery_app = Celery(
    "timetable",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["tasks"],
)

celery_app.conf.update(
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)


# Beat schedule: scan every minute for lessons starting in ~15 minutes.
celery_app.conf.beat_schedule = {
    "scan-upcoming-lessons-every-minute": {
        "task": "tasks.scan_upcoming_lessons",
        "schedule": crontab(minute="*"),
    },
}
