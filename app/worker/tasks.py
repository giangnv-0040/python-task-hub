"""Celery task gui mail thong bao (Ngay 7).

Moi task chi nhan id (khong nhan object/email) va tu doc lai DB luc chay: du
lieu luon moi nhat (vd task da bi xoa / doi assignee truoc khi worker kip chay)
va payload tren broker nho, serialize JSON duoc.

Phan doc DB + dung noi dung mail tach thanh ham async `build_*` nhan session
(test goi thang voi session DB test); than task sync chi lo chay ham do va gui.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from smtplib import SMTPException

from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.constants import (
    CELERY_MAX_RETRIES,
    CELERY_RETRY_BACKOFF_MAX_SECONDS,
    CELERY_RETRY_BACKOFF_SECONDS,
    DUE_SOON_DAYS,
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
from app.models.comment import Comment
from app.models.task import Task, TaskStatus
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


async def _get_active_user(db: AsyncSession, user_id: int) -> User | None:
    user = await db.get(User, user_id)
    return user if user is not None and user.is_active else None


async def build_comment_notification(db: AsyncSession, comment_id: int) -> Email | None:
    """Mail bao assignee co comment moi; bo qua neu task chua co assignee, assignee
    bi khoa, hoac chinh assignee la nguoi comment."""
    comment = await db.get(Comment, comment_id)
    if comment is None:
        return None
    task = await db.get(Task, comment.task_id)
    if task is None or task.assignee_id is None or task.assignee_id == comment.author_id:
        return None
    assignee = await _get_active_user(db, task.assignee_id)
    author = await db.get(User, comment.author_id)
    if assignee is None or author is None:
        return None
    return Email(
        to=assignee.email,
        subject=EMAIL_COMMENT_SUBJECT.format(task_title=task.title),
        body=EMAIL_COMMENT_BODY.format(
            author=author.full_name, task_title=task.title, content=comment.content
        ),
    )


async def build_assign_notification(
    db: AsyncSession, task_id: int, assigned_by: int
) -> Email | None:
    """Mail bao nguoi duoc assign; bo qua neu tu assign cho chinh minh."""
    task = await db.get(Task, task_id, options=[joinedload(Task.assignee)])
    if task is None or task.assignee is None or task.assignee_id == assigned_by:
        return None
    assigner = await db.get(User, assigned_by)
    if not task.assignee.is_active or assigner is None:
        return None
    return Email(
        to=task.assignee.email,
        subject=EMAIL_ASSIGN_SUBJECT.format(task_title=task.title),
        body=EMAIL_ASSIGN_BODY.format(assigner=assigner.full_name, task_title=task.title),
    )


def _due_soon_conditions(today: date) -> list[ColumnElement[bool]]:
    # Dung chung cho buoc quet (remind_due_tasks) va buoc kiem tra lai truoc khi
    # gui (send_due_reminder) - 1 dinh nghia "sap den han" duy nhat (R33).
    # date.today() cung nguon gio voi validator due_date o schema (R40).
    return [
        Task.status != TaskStatus.DONE,
        Task.assignee_id.is_not(None),
        Task.due_date >= today,
        Task.due_date <= today + timedelta(days=DUE_SOON_DAYS),
    ]


async def get_due_soon_task_ids(db: AsyncSession) -> list[int]:
    result = await db.execute(
        select(Task.id).where(*_due_soon_conditions(date.today())).order_by(Task.id)
    )
    return list(result.scalars().all())


async def build_due_reminder(db: AsyncSession, task_id: int) -> Email | None:
    """Kiem tra lai dieu kien luc gui: task co the da DONE / doi assignee sau
    luc quet."""
    task = await db.scalar(
        select(Task)
        .options(joinedload(Task.assignee))
        .where(Task.id == task_id, *_due_soon_conditions(date.today()))
    )
    if task is None or not task.assignee.is_active:
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
