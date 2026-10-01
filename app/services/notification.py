"""Day job gui mail thong bao len Celery tu request (Ngay 7).

Chi goi SAU khi DB commit thanh cong (SPEC). `.delay()` publish len broker qua
kombu la socket I/O dong bo -> chay trong threadpool de khong chan event loop
(R26). Broker loi thi chi log, khong lam hong response cua thao tac da luu (R32).
"""

import logging

from celery import Task as CeleryTask
from fastapi.concurrency import run_in_threadpool

from app.models.comment import Comment
from app.models.task import Task
from app.worker.tasks import send_assign_notification, send_comment_notification

logger = logging.getLogger(__name__)


async def _enqueue(job: CeleryTask, *args: int) -> None:
    try:
        await run_in_threadpool(job.delay, *args)
    except Exception:
        # Ngoai le duy nhat duoc bat rong (R27): side-effect sau commit
        logger.exception("Failed to enqueue Celery task %s%s", job.name, args)


async def notify_comment_created(comment: Comment) -> None:
    await _enqueue(send_comment_notification, comment.id)


async def notify_task_assigned(task: Task, assigned_by: int) -> None:
    await _enqueue(send_assign_notification, task.id, assigned_by)
