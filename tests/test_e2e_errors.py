from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from kombu.exceptions import OperationalError as BrokerError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MAX_LIMIT
from app.crud import comment as crud_comment
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate
from tests.conftest import (
    DEFAULT_TEST_PASSWORD,
    auth_headers,
    make_project,
    make_task,
    make_user,
)

# ---- 401 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "/tasks"),
        ("GET", "/projects"),
        ("GET", "/tags"),
        ("GET", "/users/me"),
        ("POST", "/tasks/1/comments"),
        ("GET", "/attachments/1/download"),
    ],
)
async def test_protected_endpoints_require_auth(
    client: AsyncClient, method: str, url: str
) -> None:
    resp = await client.request(method, url)
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"
    assert "message" in resp.json()["error"]


async def test_invalid_token_is_unauthorized(client: AsyncClient) -> None:
    resp = await client.get("/tasks", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


async def test_login_wrong_password(client: AsyncClient, member_user: User) -> None:
    resp = await client.post(
        "/users/login", data={"username": member_user.username, "password": "wrong-pass"}
    )
    assert resp.status_code == 401


@pytest.mark.parametrize(
    ("username", "email"),
    [("member1", "other@example.com"), ("other", "member1@example.com")],
)
async def test_register_duplicate_username_or_email_returns_409(
    client: AsyncClient, member_user: User, username: str, email: str
) -> None:
    resp = await client.post(
        "/users/register",
        json={
            "username": username,
            "email": email,
            "full_name": "Dup",
            "password": DEFAULT_TEST_PASSWORD,
        },
    )
    assert resp.status_code == 409


async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/users/login", data={"username": "ghost", "password": DEFAULT_TEST_PASSWORD}
    )
    assert resp.status_code == 401


# ---- 403 -------------------------------------------------------------------


async def test_inactive_user_forbidden(client: AsyncClient, db_session: AsyncSession) -> None:
    locked = await make_user(db_session, "locked", is_active=False)
    resp = await client.get("/tasks", headers=auth_headers(locked))
    assert resp.status_code == 403


async def test_create_project_forbidden_for_non_admin(
    client: AsyncClient, pm_user: User
) -> None:
    resp = await client.post("/projects", json={"name": "X"}, headers=auth_headers(pm_user))
    assert resp.status_code == 403


async def test_create_tag_forbidden_for_non_admin(
    client: AsyncClient, member_user: User
) -> None:
    resp = await client.post(
        "/tags", json={"name": "x", "color": "red"}, headers=auth_headers(member_user)
    )
    assert resp.status_code == 403


async def test_pm_cannot_manage_other_pm_project(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, pm_user: User
) -> None:
    other_pm = await make_user(db_session, "pm2", role=UserRole.PM)
    project = await make_project(db_session, manager=other_pm)
    task = await make_task(db_session, project, admin_user)
    headers = auth_headers(pm_user)

    create = await client.post(
        f"/projects/{project.id}/tasks", json={"title": "T"}, headers=headers
    )
    assign = await client.post(
        f"/tasks/{task.id}/assign", json={"assignee_id": pm_user.id}, headers=headers
    )
    assert (create.status_code, assign.status_code) == (403, 403)


async def test_member_cannot_delete_other_member_comment(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, member_user: User
) -> None:
    author = await make_user(db_session, "author")
    task = await make_task(db_session, await make_project(db_session), admin_user)
    comment = await crud_comment.create_comment(
        db_session, task.id, CommentCreate(content="mine"), author_id=author.id
    )
    resp = await client.delete(
        f"/tasks/{task.id}/comments/{comment.id}", headers=auth_headers(member_user)
    )
    assert resp.status_code == 403


# ---- 404 / 409 / 422 -------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("GET", "/projects/999999", None),
        ("GET", "/projects/999999/tasks", None),
        ("POST", "/tasks/999999/comments", {"content": "x"}),
        ("POST", "/tasks/999999/bookmark", None),
        ("DELETE", "/tasks/999999/comments/1", None),
        ("GET", "/tasks/999999/attachments", None),
        ("GET", "/attachments/999999/download", None),
        ("DELETE", "/attachments/999999", None),
    ],
)
async def test_missing_resources_return_404(
    client: AsyncClient, admin_user: User, method: str, url: str, body: dict | None
) -> None:
    resp = await client.request(method, url, json=body, headers=auth_headers(admin_user))
    assert resp.status_code == 404


async def test_assign_to_unknown_user_returns_404(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session), admin_user)
    resp = await client.post(
        f"/tasks/{task.id}/assign",
        json={"assignee_id": 999999},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 404


async def test_bookmark_twice_returns_409(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session), admin_user)
    headers = auth_headers(admin_user)
    first = await client.post(f"/tasks/{task.id}/bookmark", headers=headers)
    second = await client.post(f"/tasks/{task.id}/bookmark", headers=headers)
    assert (first.status_code, second.status_code) == (204, 409)


async def test_upload_disallowed_content_type_returns_415(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    task = await make_task(db_session, await make_project(db_session), admin_user)
    resp = await client.post(
        f"/tasks/{task.id}/attachments",
        files={"file": ("x.exe", b"MZ", "application/x-msdownload")},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 415


@pytest.mark.parametrize(
    "params", [{"limit": MAX_LIMIT + 1}, {"limit": 0}, {"skip": -1}, {"status": "NOPE"}]
)
async def test_list_tasks_invalid_query_returns_422(
    client: AsyncClient, admin_user: User, params: dict
) -> None:
    resp = await client.get("/tasks", params=params, headers=auth_headers(admin_user))
    assert resp.status_code == 422


# ---- filter + pagination GET /tasks ------------------------------------


async def test_list_tasks_filter_and_pagination(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    project = await make_project(db_session)
    for i in range(5):
        await make_task(
            db_session, project, admin_user, title=f"H{i}", priority=TaskPriority.HIGH
        )
    await make_task(db_session, project, admin_user, title="L", priority=TaskPriority.LOW)
    await make_task(
        db_session,
        project,
        admin_user,
        title="P",
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
    )
    headers = auth_headers(admin_user)

    async def page(**params: object) -> tuple[list[str], int]:
        resp = await client.get("/tasks", params=params, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        return [t["title"] for t in body["items"]], body["total"]

    assert await page(priority="LOW") == (["L"], 1)
    assert await page(status="IN_PROGRESS") == (["P"], 1)
    high_todo = {"status": "TODO", "priority": "HIGH", "limit": 2}
    assert await page(**high_todo, skip=0) == (["H0", "H1"], 5)
    assert await page(**high_todo, skip=2) == (["H2", "H3"], 5)
    assert await page(**high_todo, skip=4) == (["H4"], 5)
    assert await page(status="DONE") == ([], 0)


async def test_list_project_tasks_pagination(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    project = await make_project(db_session)
    for i in range(3):
        await make_task(db_session, project, admin_user, title=f"T{i}")
    resp = await client.get(
        f"/projects/{project.id}/tasks",
        params={"skip": 1, "limit": 1},
        headers=auth_headers(admin_user),
    )
    assert [t["title"] for t in resp.json()["items"]] == ["T1"]
    assert resp.json()["total"] == 3


async def test_list_projects_pagination(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
) -> None:
    for name in ("A", "B", "C"):
        await make_project(db_session, name)
    resp = await client.get(
        "/projects", params={"skip": 0, "limit": 2}, headers=auth_headers(admin_user)
    )
    assert [p["name"] for p in resp.json()["items"]] == ["A", "B"]
    assert resp.json()["total"] == 3


# ---- side-effect sau commit (R32) ------------------------------------------


async def test_comment_saved_even_if_broker_is_down(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    celery_delay: dict[str, MagicMock],
) -> None:
    celery_delay["send_comment_notification"].side_effect = BrokerError("redis down")
    task = await make_task(db_session, await make_project(db_session), admin_user)

    resp = await client.post(
        f"/tasks/{task.id}/comments",
        json={"content": "still saved"},
        headers=auth_headers(admin_user),
    )

    assert resp.status_code == 201
    saved = await crud_comment.get_task_comment(db_session, task.id, resp.json()["id"])
    assert saved is not None
