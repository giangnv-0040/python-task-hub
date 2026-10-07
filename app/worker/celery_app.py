from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging as celery_setup_logging

from app.config import settings
from app.core.constants import (
    CELERY_BROKER_SOCKET_TIMEOUT_SECONDS,
    CELERY_PUBLISH_MAX_RETRIES,
    REMIND_DUE_TASKS_HOUR,
    REMIND_DUE_TASKS_MINUTE,
)
from app.core.logging import setup_logging

celery_app = Celery(
    "taskhub",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.celery_timezone,
    enable_utc=True,
    # Task gui mail khong ai doc ket qua -> khong ghi result vao Redis
    task_ignore_result=True,
    # .delay() goi tu request sau commit: broker chet thi fail nhanh (R41)
    task_publish_retry_policy={"max_retries": CELERY_PUBLISH_MAX_RETRIES},
    broker_transport_options={
        "socket_connect_timeout": CELERY_BROKER_SOCKET_TIMEOUT_SECONDS,
        "socket_timeout": CELERY_BROKER_SOCKET_TIMEOUT_SECONDS,
    },
    broker_connection_retry_on_startup=True,
)

# Celery Beat: nhac task sap den han moi sang (gio theo CELERY_TIMEZONE)
celery_app.conf.beat_schedule = {
    "remind-due-tasks-every-morning": {
        "task": "app.worker.tasks.remind_due_tasks",
        "schedule": crontab(hour=REMIND_DUE_TASKS_HOUR, minute=REMIND_DUE_TASKS_MINUTE),
    },
}


@celery_setup_logging.connect
def _configure_worker_logging(**_: object) -> None:
    # Co receiver cho signal nay thi Celery khong tu cau hinh lai root logger
    # -> worker/beat log cung format va LOG_LEVEL voi API
    setup_logging()
