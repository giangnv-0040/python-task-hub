"""Celery task gui mail thong bao (Ngay 7).

Moi task chi nhan id (khong nhan object/email) va tu doc lai DB luc chay: du
lieu luon moi nhat (vd task da bi xoa / doi assignee truoc khi worker kip chay)
va payload tren broker nho, serialize JSON duoc.

Phan doc DB + dung noi dung mail tach thanh ham async `build_*` nhan session
(test goi thang voi session DB test); than task sync chi lo chay ham do va gui.
"""

from dataclasses import dataclass
from datetime import date
from smtplib import SMTPException

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CELERY_MAX_RETRIES,
    CELERY_RETRY_BACKOFF_MAX_SECONDS,
    CELERY_RETRY_BACKOFF_SECONDS,
)
from app.core.mail import send_email
from app.core.messages import (
    EMAIL_ASSIGN_BODY,
    EMAIL_ASSIGN_SUBJECT,
    EMAIL_COMMENT_BODY,
    EMAIL_COMMENT_SUBJECT,
    EMAIL_DUE_REMINDER_BODY,
    EMAIL_DUE_REMINDER_SUBJECT,
)
from app.crud import comment as crud_comment
from app.crud import task as crud_task
from app.crud import user as crud_user
from app.models.task import Task
from app.models.user import User
from app.worker.celery_app import celery_app
from app.worker.db import run_with_session

# Chi retry loi transient (SMTP/mang/DB tam thoi khong ket noi duoc); loi logic
# retry cung fail y het nen de fail luon (R43). Moi task chi gui 1 mail cho 1
# nguoi nhan -> retry khong lam ai nhan trung mail cua nguoi khac.
TRANSIENT_TASK_EXCEPTIONS = (SMTPException, OSError, OperationalError)
RETRY_POLICY = {
    "retry_backoff": CELERY_RETRY_BACKOFF_SECONDS,
    "retry_backoff_max": CELERY_RETRY_BACKOFF_MAX_SECONDS,
    "retry_jitter": True,
    "max_retries": CELERY_MAX_RETRIES,
}
SEND_MAIL_TASK_KWARGS = {"autoretry_for": TRANSIENT_TASK_EXCEPTIONS, **RETRY_POLICY}


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


def _is_active(user: User | None) -> bool:
    return user is not None and user.is_active


async def _load_task_and_actor(
    db: AsyncSession, task_id: int, actor_id: int
) -> tuple[Task, User] | None:
    """Khoi lookup chung cua mail comment/assign (R33): task kem assignee va
    nguoi thuc hien hanh dong. None neu khong can gui: task khong ton tai, chua
    co assignee / assignee bi khoa, hoac chinh assignee la nguoi thuc hien."""
    task = await crud_task.get_task_with_assignee(db, task_id)
    if task is None or task.assignee_id == actor_id or not _is_active(task.assignee):
        return None
    actor = await crud_user.get_user(db, actor_id)
    return (task, actor) if actor is not None else None


async def build_comment_notification(db: AsyncSession, comment_id: int) -> Email | None:
    """Mail bao assignee co comment moi."""
    comment = await crud_comment.get_comment(db, comment_id)
    if comment is None:
        return None
    loaded = await _load_task_and_actor(db, comment.task_id, comment.author_id)
    if loaded is None:
        return None
    task, author = loaded
    return Email(
        to=task.assignee.email,
        subject=EMAIL_COMMENT_SUBJECT.format(task_title=task.title),
        body=EMAIL_COMMENT_BODY.format(
            author=author.full_name, task_title=task.title, content=comment.content
        ),
    )


async def build_assign_notification(
    db: AsyncSession, task_id: int, assigned_by: int
) -> Email | None:
    """Mail bao nguoi duoc assign."""
    loaded = await _load_task_and_actor(db, task_id, assigned_by)
    if loaded is None:
        return None
    task, assigner = loaded
    return Email(
        to=task.assignee.email,
        subject=EMAIL_ASSIGN_SUBJECT.format(task_title=task.title),
        body=EMAIL_ASSIGN_BODY.format(assigner=assigner.full_name, task_title=task.title),
    )


async def get_due_soon_task_ids(db: AsyncSession) -> list[int]:
    # date.today(): cung nguon gio voi validator due_date o schema (R40)
    return await crud_task.get_due_soon_task_ids(db, date.today())


async def build_due_reminder(db: AsyncSession, task_id: int) -> Email | None:
    """Kiem tra lai dieu kien luc gui: task co the da DONE / doi assignee sau
    luc quet."""
    task = await crud_task.get_due_soon_task(db, task_id, date.today())
    if task is None or not _is_active(task.assignee):
        return None
    return Email(
        to=task.assignee.email,
        subject=EMAIL_DUE_REMINDER_SUBJECT.format(task_title=task.title),
        body=EMAIL_DUE_REMINDER_BODY.format(
            task_title=task.title, due_date=task.due_date.isoformat()
        ),
    )


def _send(email: Email | None) -> None:
    if email is not None:
        send_email(to=email.to, subject=email.subject, body=email.body)


@celery_app.task(**SEND_MAIL_TASK_KWARGS)
def send_comment_notification(comment_id: int) -> None:
    _send(run_with_session(lambda db: build_comment_notification(db, comment_id)))


@celery_app.task(**SEND_MAIL_TASK_KWARGS)
def send_assign_notification(task_id: int, assigned_by: int) -> None:
    _send(run_with_session(lambda db: build_assign_notification(db, task_id, assigned_by)))


@celery_app.task(**SEND_MAIL_TASK_KWARGS)
def send_due_reminder(task_id: int) -> None:
    _send(run_with_session(lambda db: build_due_reminder(db, task_id)))


# Chi retry loi DB (xay ra truoc khi enqueue job nao): neu retry ca loi publish
# giua vong lap thi cac job da enqueue truoc do se bi enqueue lai
@celery_app.task(autoretry_for=(OperationalError,), **RETRY_POLICY)
def remind_due_tasks() -> int:
    """Celery Beat, chay moi sang: tach moi task sap den han thanh 1 job
    `send_due_reminder` rieng -> 1 mail loi chi retry dung mail do, khong gui lai
    cho nhung nguoi da nhan (R32, R43)."""
    task_ids = run_with_session(get_due_soon_task_ids)
    for task_id in task_ids:
        send_due_reminder.delay(task_id)
    return len(task_ids)
