import asyncio
import os
import smtplib
from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.constants import CELERY_MAX_RETRIES
from app.crud import comment as crud_comment
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.worker import db as worker_db
from app.worker import tasks as worker_tasks
from app.worker.tasks import (
    Email,
    build_assign_notification,
    build_comment_notification,
    build_due_reminder,
    get_due_soon_task_ids,
)
from tests.conftest import make_project, make_task, make_user

MAILPIT_API_URL = os.environ.get("MAILPIT_API_URL", "http://localhost:8025")

# ---- build_*: logic chon nguoi nhan + noi dung mail (goi thang voi DB test) ----


async def test_comment_notification_goes_to_assignee(
    db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    task = await make_task(
        db_session, await make_project(db_session), admin_user,
        title="Deploy", assignee_id=member_user.id,
    )
    comment = await crud_comment.create_comment(
        db_session, task.id, CommentCreate(content="ship it"), author_id=admin_user.id
    )

    email = await build_comment_notification(db_session, comment.id)

    assert email is not None
    assert email.to == member_user.email
    assert "Deploy" in email.subject
    assert "ship it" in email.body and admin_user.full_name in email.body


async def test_comment_notification_skipped(
    db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    project = await make_project(db_session)
    locked = await make_user(db_session, "locked", is_active=False)
    no_assignee = await make_task(db_session, project, admin_user)
    self_assigned = await make_task(db_session, project, admin_user, assignee_id=member_user.id)
    locked_assignee = await make_task(db_session, project, admin_user, assignee_id=locked.id)

    cases = [
        (no_assignee, admin_user),  # task chua co assignee
        (self_assigned, member_user),  # assignee tu comment
        (locked_assignee, admin_user),  # assignee bi khoa
    ]
    for task, author in cases:
        comment = await crud_comment.create_comment(
            db_session, task.id, CommentCreate(content="x"), author_id=author.id
        )
        assert await build_comment_notification(db_session, comment.id) is None
    assert await build_comment_notification(db_session, 999999) is None


async def test_assign_notification(
    db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    task = await make_task(
        db_session, await make_project(db_session), admin_user,
        title="Deploy", assignee_id=member_user.id,
    )

    email = await build_assign_notification(db_session, task.id, assigned_by=admin_user.id)
    assert email is not None
    assert email.to == member_user.email
    assert "Deploy" in email.subject and admin_user.full_name in email.body

    # Tu assign cho chinh minh thi khong can bao
    assert await build_assign_notification(db_session, task.id, member_user.id) is None


async def test_due_soon_selection(
    db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    project = await make_project(db_session)
    today = date.today()

    async def task_due(offset_days: int, **fields: object) -> int:
        fields.setdefault("assignee_id", member_user.id)
        task = await make_task(
            db_session, project, admin_user, due_date=today + timedelta(days=offset_days),
            **fields,
        )
        return task.id

    due_today = await task_due(0)
    due_tomorrow = await task_due(1)
    await task_due(2)
    await task_due(-1)  # da qua han
    await task_due(0, status=TaskStatus.DONE)
    await task_due(0, assignee_id=None)
    await make_task(db_session, project, admin_user, assignee_id=member_user.id)  # khong co han

    assert await get_due_soon_task_ids(db_session) == [due_today, due_tomorrow]

    email = await build_due_reminder(db_session, due_tomorrow)
    assert email is not None
    assert email.to == member_user.email
    assert (today + timedelta(days=1)).isoformat() in email.body


async def test_due_reminder_rechecks_task_before_sending(
    db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    task = await make_task(
        db_session, await make_project(db_session), admin_user,
        due_date=date.today(), assignee_id=member_user.id,
    )
    # Task duoc DONE sau luc quet nhung truoc khi job gui chay
    task.status = TaskStatus.DONE
    await db_session.commit()
    assert await build_due_reminder(db_session, task.id) is None


# ---- than Celery task (chay eager qua .apply()) ------------------------------


def test_worker_engine_does_not_pool_connections() -> None:
    # Moi lan chay task la 1 asyncio.run() (event loop moi); connection asyncpg
    # trong pool thuoc loop cu se loi tu task thu 2 -> worker bat buoc NullPool
    assert isinstance(worker_db.worker_engine.pool, NullPool)


def _apply(job, *args: object) -> object:
    # .apply() chay task dong bo ngay trong process (eager), tra loi neu task loi
    return job.apply(args=args).get()


async def test_tasks_run_against_db_repeatedly(
    committed_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    celery_delay: dict[str, MagicMock],
) -> None:
    """Chay than task that (asyncio.run + WorkerSession tro ve DB test) nhieu lan
    lien tiep, gom ca job quet remind_due_tasks."""
    admin = await make_user(committed_session, "admin_w")
    member = await make_user(committed_session, "member_w")
    task = await make_task(
        committed_session, await make_project(committed_session), admin,
        title="Release", assignee_id=member.id, due_date=date.today(),
    )
    comment = await crud_comment.create_comment(
        committed_session, task.id, CommentCreate(content="hi"), author_id=admin.id
    )
    sent: list[str] = []
    monkeypatch.setattr(worker_tasks, "send_email", lambda to, subject, body: sent.append(subject))

    # Task sync goi asyncio.run() -> chay tren thread rieng nhu worker that
    for _ in range(2):
        await asyncio.to_thread(_apply, worker_tasks.send_comment_notification, comment.id)
    await asyncio.to_thread(_apply, worker_tasks.send_assign_notification, task.id, admin.id)
    await asyncio.to_thread(_apply, worker_tasks.send_due_reminder, task.id)
    count = await asyncio.to_thread(_apply, worker_tasks.remind_due_tasks)

    assert len(sent) == 4 and all("Release" in s for s in sent)
    # remind_due_tasks khong tu gui mail: tach moi task thanh 1 job rieng
    assert count == 1
    celery_delay["send_due_reminder"].assert_called_once_with(task.id)


def _fake_email() -> Email:
    return Email(to="someone@example.com", subject="s", body="b")


def test_send_task_retries_transient_smtp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_tasks, "run_with_session", lambda fn: _fake_email())
    send = MagicMock(side_effect=smtplib.SMTPServerDisconnected("down"))
    monkeypatch.setattr(worker_tasks, "send_email", send)

    result = worker_tasks.send_comment_notification.apply(args=(1,))

    assert result.failed()
    assert send.call_count == CELERY_MAX_RETRIES + 1


def test_send_task_does_not_retry_non_transient_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_tasks, "run_with_session", lambda fn: _fake_email())
    send = MagicMock(side_effect=ValueError("bug"))
    monkeypatch.setattr(worker_tasks, "send_email", send)

    result = worker_tasks.send_comment_notification.apply(args=(1,))

    assert result.failed()
    assert send.call_count == 1


def _mailpit_available() -> bool:
    try:
        return httpx.get(f"{MAILPIT_API_URL}/api/v1/info", timeout=1).is_success
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _mailpit_available(), reason="Mailpit is not running")
def test_mail_is_delivered_to_mailpit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gui that qua SMTP toi Mailpit (settings.smtp_*), roi doc lai qua API."""
    subject = f"taskhub-test-{uuid4().hex}"
    email = Email(to="mailpit@example.com", subject=subject, body="hello from pytest")
    monkeypatch.setattr(worker_tasks, "run_with_session", lambda fn: email)

    _apply(worker_tasks.send_assign_notification, 1, 2)

    resp = httpx.get(
        f"{MAILPIT_API_URL}/api/v1/search", params={"query": f'subject:"{subject}"'}
    )
    messages = resp.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["To"][0]["Address"] == email.to
    assert messages[0]["From"]["Address"] == settings.mail_from
