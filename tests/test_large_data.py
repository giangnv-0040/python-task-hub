"""Test voi du lieu lon: gioi han upload, file lon, N+1, pagination, job quet.

Du lieu tao bang bulk INSERT (1 cau SQL cho ca lo) de test van chay nhanh.
"""

import asyncio
import hashlib
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import event, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.config import settings
from app.core.constants import MAX_LIMIT
from app.models.associations import task_tags
from app.models.project import Project
from app.models.tag import Tag
from app.models.task import Task
from app.models.user import User
from app.worker import tasks as worker_tasks
from tests.conftest import auth_headers, make_project, make_task, make_user

MB = 1024 * 1024


async def _bulk_create_tasks(
    db: AsyncSession, project: Project, creator: User, count: int, **fields: object
) -> None:
    await db.execute(
        insert(Task),
        [
            {"project_id": project.id, "created_by": creator.id, "title": f"T{i:04d}", **fields}
            for i in range(count)
        ],
    )
    await db.commit()


@contextmanager
def _count_queries(engine: AsyncEngine) -> Iterator[list[str]]:
    statements: list[str] = []

    def _record(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _record)


# ---- upload --------------------------------------------------------------------


async def test_upload_over_limit_returns_413_and_leaves_no_file(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_size", 1 * MB)
    task = await make_task(db_session, await make_project(db_session), admin_user)

    resp = await client.post(
        f"/api/tasks/{task.id}/attachments",
        files={"file": ("big.bin", os.urandom(1 * MB + 1), "application/zip")},
        headers=auth_headers(admin_user),
    )

    assert resp.status_code == 413
    # Phan file da ghi do dang phai duoc don sach (storage cua client la tmp_path)
    assert list(tmp_path.iterdir()) == []
    listed = await client.get(
        f"/api/tasks/{task.id}/attachments", headers=auth_headers(admin_user)
    )
    assert listed.json()["total"] == 0


async def test_upload_at_exact_limit_is_accepted(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "max_upload_size", 1 * MB)
    task = await make_task(db_session, await make_project(db_session), admin_user)

    resp = await client.post(
        f"/api/tasks/{task.id}/attachments",
        files={"file": ("edge.bin", os.urandom(1 * MB), "application/zip")},
        headers=auth_headers(admin_user),
    )

    assert resp.status_code == 201
    assert resp.json()["size"] == 1 * MB


async def test_large_file_roundtrip_is_byte_identical(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    # Nhieu chunk FILE_CHUNK_SIZE, duoi MAX_UPLOAD_SIZE mac dinh
    content = os.urandom(8 * MB + 123)
    task = await make_task(db_session, await make_project(db_session), admin_user)
    headers = auth_headers(admin_user)

    upload = await client.post(
        f"/api/tasks/{task.id}/attachments",
        files={"file": ("big.zip", content, "application/zip")},
        headers=headers,
    )
    assert upload.status_code == 201
    assert upload.json()["size"] == len(content)

    download = await client.get(
        f"/api/attachments/{upload.json()['id']}/download", headers=headers
    )
    assert download.status_code == 200
    assert download.headers["content-length"] == str(len(content))
    assert hashlib.sha256(download.content).digest() == hashlib.sha256(content).digest()


# ---- N+1 -----------------------------------------------------------------------


async def _seed_tasks_with_tags(
    db: AsyncSession, project: Project, creator: User, count: int
) -> None:
    tags = [Tag(name=f"tag-{project.id}-{i}", color="red") for i in range(3)]
    db.add_all(tags)
    await _bulk_create_tasks(db, project, creator, count)
    await db.flush()
    task_ids = (await db.scalars(select(Task.id).where(Task.project_id == project.id))).all()
    await db.execute(
        insert(task_tags),
        [{"task_id": tid, "tag_id": tag.id} for tid in task_ids for tag in tags],
    )
    await db.commit()


async def _queries_for(
    client: AsyncClient, engine: AsyncEngine, url: str, user: User, expected_items: int
) -> int:
    headers = auth_headers(user)
    with _count_queries(engine) as statements:
        resp = await client.get(url, params={"limit": MAX_LIMIT}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == expected_items
    assert all(len(t["tags"]) == 3 for t in resp.json())
    return len(statements)


async def test_list_tasks_query_count_does_not_grow_with_rows(
    client: AsyncClient, db_session: AsyncSession, engine: AsyncEngine, admin_user: User
) -> None:
    small = await make_project(db_session, "small")
    await _seed_tasks_with_tags(db_session, small, admin_user, 5)
    small_queries = await _queries_for(
        client, engine, f"/api/projects/{small.id}/tasks", admin_user, 5
    )

    big = await make_project(db_session, "big")
    await _seed_tasks_with_tags(db_session, big, admin_user, MAX_LIMIT)
    big_queries = await _queries_for(
        client, engine, f"/api/projects/{big.id}/tasks", admin_user, MAX_LIMIT
    )
    all_queries = await _queries_for(client, engine, "/api/tasks", admin_user, MAX_LIMIT)

    # selectinload: 1 query task + 1 query tag cho ca trang, khong phai 1 query/task
    assert big_queries == small_queries
    assert all_queries <= small_queries


# ---- pagination ----------------------------------------------------------------


async def test_paginating_many_tasks_returns_every_row_once(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    total = 250
    project = await make_project(db_session)
    await _bulk_create_tasks(db_session, project, admin_user, total)
    headers = auth_headers(admin_user)

    seen: list[int] = []
    page_sizes: list[int] = []
    for skip in range(0, total + MAX_LIMIT, MAX_LIMIT):
        resp = await client.get(
            f"/api/projects/{project.id}/tasks",
            params={"skip": skip, "limit": MAX_LIMIT},
            headers=headers,
        )
        assert resp.status_code == 200
        page_sizes.append(len(resp.json()))
        seen.extend(t["id"] for t in resp.json())

    assert page_sizes == [MAX_LIMIT, MAX_LIMIT, total - 2 * MAX_LIMIT, 0]
    assert len(seen) == len(set(seen)) == total
    assert seen == sorted(seen)


# ---- job quet remind_due_tasks -------------------------------------------------


async def test_remind_due_tasks_fans_out_many_tasks(
    committed_session: AsyncSession, celery_delay: dict[str, MagicMock]
) -> None:
    due_count = 1000
    admin = await make_user(committed_session, "admin_big")
    member = await make_user(committed_session, "member_big")
    project = await make_project(committed_session)
    await _bulk_create_tasks(
        committed_session,
        project,
        admin,
        due_count,
        assignee_id=member.id,
        due_date=date.today(),
    )
    # Task khong co han -> khong duoc chon
    await _bulk_create_tasks(committed_session, project, admin, 500, assignee_id=member.id)

    started = time.perf_counter()
    count = await asyncio.to_thread(lambda: worker_tasks.remind_due_tasks.apply().get())
    elapsed = time.perf_counter() - started

    assert count == due_count
    delay = celery_delay["send_due_reminder"]
    assert delay.call_count == due_count
    assert len({c.args[0] for c in delay.call_args_list}) == due_count
    # Chi 1 query lay id (khong load ca object/assignee) -> nhanh du voi vai nghin task
    assert elapsed < 5
